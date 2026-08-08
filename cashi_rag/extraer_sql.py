
# -*- coding: utf-8 -*-
"""
extraer_sql.py — Trae Real 2025 / Real 2026 / Plan 2026 desde SQL Server
                 y los deja como parquet en la carpeta del proyecto.

Reemplaza a los notebooks "Real 2025.ipynb", "Real 2026.ipynb", "Plan 2026.ipynb"
(solo la parte de extracción; las agrupaciones ya viven en build_data.py).

Credenciales: se leen de .env (nunca del código). Ver .env.ejemplo.

Uso:
    python extraer_sql.py              # solo si SQL tiene más filas que el parquet
    python extraer_sql.py --force      # siempre re-extrae
    python extraer_sql.py --check      # NO extrae; solo dice si hay datos nuevos (exit 0/1)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import semana

BASE = Path(__file__).parent.resolve()
ENV = BASE / ".env"

# tabla SQL -> (Origen, Año). El nombre del parquet lo da semana.py: cambia
# cada semana (r26_sem28.parquet), no se sobrescribe el de la semana pasada.
TABLAS = {
    "Real 2025": ("Real", 2025),
    "Real 2026": ("Real", 2026),
    "Plan 2026": ("Plan", 2026),
}


# La consola de Windows es cp1252 y el log lleva 'Δ' y '·'. Corriendo bajo
# actualizar.py hay PYTHONIOENCODING=utf-8, pero a mano no: forzamos UTF-8
# aquí también para no morir con UnicodeEncodeError a media extracción.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def log(m):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
    except UnicodeEncodeError:
        print(f"[{time.strftime('%H:%M:%S')}] "
              + m.encode("ascii", "replace").decode("ascii"), flush=True)


def cargar_env() -> dict:
    """Lee .env. Las variables de entorno reales tienen prioridad."""
    cfg = {}
    if ENV.exists():
        for linea in ENV.read_text(encoding="utf-8-sig").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            cfg[k.strip()] = v.strip()
    for k in ("SQL_SERVER", "SQL_DATABASE", "SQL_USER", "SQL_PASSWORD", "SQL_DRIVER"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    faltan = [k for k in ("SQL_SERVER", "SQL_DATABASE", "SQL_USER", "SQL_PASSWORD") if not cfg.get(k)]
    if faltan:
        sys.exit(f"ERROR: faltan {faltan} en {ENV} o en las variables de entorno.\n"
                 f"       Copia .env.ejemplo a .env y llénalo.")
    cfg.setdefault("SQL_DRIVER", "ODBC Driver 17 for SQL Server")
    return cfg


# Orden de preferencia. El primero de .env va al frente; el resto son respaldos.
# "ODBC Driver 17" puede fallar con IM003 "Acceso denegado" al cargar
# msodbcsql17.dll (política de endpoint), aunque pyodbc.drivers() lo liste.
_DRIVERS_FALLBACK = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
]
_DRIVER_OK: list[str] = []      # cache del driver que sí funcionó


def _cadena(cfg: dict, driver: str) -> str:
    extra = "Encrypt=no;" if driver == "ODBC Driver 18 for SQL Server" else ""
    return (f"DRIVER={{{driver}}};SERVER={cfg['SQL_SERVER']};"
            f"DATABASE={cfg['SQL_DATABASE']};UID={cfg['SQL_USER']};"
            f"PWD={cfg['SQL_PASSWORD']};TrustServerCertificate=yes;{extra}")


def conectar(cfg: dict, timeout: int = 10):
    """Prueba los drivers ODBC en orden hasta que uno cargue."""
    import pyodbc

    if _DRIVER_OK:
        return pyodbc.connect(_cadena(cfg, _DRIVER_OK[0]), autocommit=True, timeout=timeout)

    instalados = set(pyodbc.drivers())
    orden = [cfg["SQL_DRIVER"]] + [d for d in _DRIVERS_FALLBACK if d != cfg["SQL_DRIVER"]]
    errores = []
    for drv in orden:
        if drv not in instalados:
            continue
        try:
            cn = pyodbc.connect(_cadena(cfg, drv), autocommit=True, timeout=timeout)
            if drv != cfg["SQL_DRIVER"]:
                log(f"  aviso: '{cfg['SQL_DRIVER']}' no cargó; usando '{drv}'")
            _DRIVER_OK.append(drv)
            return cn
        except Exception as e:
            errores.append(f"{drv}: {str(e)[:80]}")
    raise RuntimeError("ningún driver ODBC pudo conectar.\n  " + "\n  ".join(errores))


# En SQL la columna lleva ESPACIOS; el parquet la guarda con guiones bajos
# (el notebook original hacía c.strip().replace(" ", "_")).
MONTO_SQL = "SUM_MONTO_MNX_CONS (SUMA)"
MONTO = "SUM_MONTO_MNX_CONS_(SUMA)"

# Tolerancia RELATIVA al comparar sumas. Antes era 1.0 peso absoluto: sobre
# montos de ~17,000 millones, el redondeo entre el numeric de SQL y el double
# del parquet lo superaba casi siempre y "siempre había datos nuevos".
# 1e-9 relativo (~17 pesos sobre 17,000M) ignora el redondeo y sigue
# detectando correcciones reales de importe.
TOL_REL = 1e-9
TOL_ABS = 1.0      # piso, para tablas con montos pequeños o suma cero


def _diferente(a: float, b: float) -> bool:
    return abs(a - b) > max(TOL_ABS, TOL_REL * max(abs(a), abs(b)))


def firma_sql(cur, tabla: str) -> tuple[int, float]:
    """(filas, suma de montos). Detecta tanto altas como correcciones de importe."""
    cur.execute(f'SELECT COUNT(*), COALESCE(SUM(CAST([{MONTO_SQL}] AS FLOAT)), 0) FROM [{tabla}]')
    n, s = cur.fetchone()
    return int(n), float(s or 0.0)


def firma_parquet(p: Path) -> tuple[int, float]:
    if not p.exists():
        return -1, 0.0
    import duckdb
    n, s = duckdb.connect().execute(
        f'''SELECT COUNT(*), COALESCE(SUM(CAST("{MONTO}" AS DOUBLE)), 0)
            FROM read_parquet('{p.as_posix()}')''').fetchone()
    return int(n), float(s or 0.0)


def hay_novedades(cfg: dict, sem: int | None = None) -> tuple[bool, dict]:
    """Compara (filas, suma de montos) SQL vs el parquet DE ESTA SEMANA.
    El conteo solo no basta: SQL puede corregir un importe sin cambiar filas.

    Si el parquet de la semana en curso no existe todavía, hay novedad por
    definición: aún no se ha extraído el corte de esta semana."""
    nom = semana.nombres(sem)
    det = {}
    with conectar(cfg) as cn:
        cur = cn.cursor()
        for tabla in TABLAS:
            n_sql, s_sql = firma_sql(cur, tabla)
            destino = BASE / nom[tabla]
            n_pq, s_pq = firma_parquet(destino)
            if n_pq < 0:                       # no existe el parquet de esta semana
                cambio, motivo = True, "parquet de la semana aún no existe"
            elif n_sql != n_pq:
                cambio, motivo = True, "cambió el número de filas"
            elif _diferente(s_sql, s_pq):
                cambio, motivo = True, "cambió el monto"
            else:
                cambio, motivo = False, ""
            det[tabla] = {"sql": n_sql, "parquet": n_pq, "archivo": nom[tabla],
                          "monto_sql": s_sql, "monto_pq": s_pq,
                          "cambio": cambio, "motivo": motivo}
    return any(d["cambio"] for d in det.values()), det


LOTE = 500_000       # filas por fetchmany; da un latido cada ~10-20 s


def extraer(cfg: dict, tabla: str, destino: Path, origen: str, anio: int, total: int = 0):
    """Replica la lógica del notebook: normaliza encabezados, tipa SEMANA_EKT,
    agrega Origen / Año / Combinada, y escribe el parquet.

    Lee por lotes en vez de un read_database() de un golpe: la tabla grande
    tarda ~9 min y antes no imprimía nada en todo ese rato, así que la
    actualización parecía colgada y se cancelaba a mano (el log mostraba
    DBG_TERMINATE_PROCESS). Ahora informa avance en cada lote."""
    import polars as pl

    log(f"  {tabla}: leyendo{f' {total:,} filas' if total else ''}...")
    t0 = time.time()
    partes, leidas = [], 0
    with conectar(cfg, timeout=0) as cn:
        cur = cn.cursor()
        cur.execute(f"SELECT * FROM [{tabla}]")
        cols = [d[0] for d in cur.description]
        while True:
            filas = cur.fetchmany(LOTE)
            if not filas:
                break
            partes.append(pl.DataFrame(
                {c: [f[i] for f in filas] for i, c in enumerate(cols)},
                infer_schema_length=None))
            leidas += len(filas)
            pct = f" ({leidas*100//total}%)" if total else ""
            log(f"    {tabla}: {leidas:,} filas{pct} · {time.time()-t0:.0f}s")
    df = pl.concat(partes, how="vertical") if partes else pl.DataFrame(
        {c: [] for c in cols})
    del partes

    df = df.rename({c: c.strip().replace(" ", "_") for c in df.columns})
    if "SEMANA_EKT" in df.columns:
        df = df.with_columns(pl.col("SEMANA_EKT").cast(pl.Int64, strict=False))
    df = df.with_columns([
        pl.lit(origen).alias("Origen"),
        pl.lit(anio).cast(pl.Int64).alias("Año"),
    ])
    df = df.with_columns(
        pl.concat_str([pl.col("Origen"), pl.col("Año").cast(pl.Utf8)], separator=" ").alias("Combinada"))

    # escritura atómica: .tmp -> rename, para que build_data nunca lea un parquet a medias
    tmp = destino.with_suffix(".parquet.tmp")
    df.write_parquet(tmp)
    tmp.replace(destino)
    log(f"  {tabla}: {df.height:,} filas -> {destino.name} "
        f"({destino.stat().st_size/1e6:.0f} MB, {time.time()-t0:.0f}s)")
    del df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-extrae aunque los conteos coincidan")
    ap.add_argument("--check", action="store_true", help="solo comprueba; exit 0 si hay novedades, 1 si no")
    ap.add_argument("--semana", type=int, default=None,
                    help="semana EKT para nombrar los parquet (por defecto, la vigente)")
    args = ap.parse_args()

    cfg = cargar_env()
    sem = args.semana if args.semana is not None else semana.semana_ekt()
    ini, fin = semana.rango_semana(sem)
    log(f"SQL Server {cfg['SQL_SERVER']} · base {cfg['SQL_DATABASE']}")
    log(f"Semana EKT {sem} ({ini} a {fin}) · destino: {', '.join(semana.nombres(sem).values())}")

    try:
        hay, det = hay_novedades(cfg, sem)
    except Exception as e:
        # exit 2 = error. NO usar 1: en --check el 1 significa "sin cambios"
        # y un fallo de red se leería como "todo al día".
        print(f"ERROR de conexión: {str(e)[:200]}", file=sys.stderr)
        sys.exit(2)

    for t, d in det.items():
        pq = f"{d['parquet']:,}" if d["parquet"] >= 0 else "(no existe)"
        marca = f"  <-- {d['motivo']}" if d["cambio"] else ""
        log(f"  {t:12s} filas SQL={d['sql']:>12,}  parquet={pq:>14}{marca}")
        if d["parquet"] >= 0:
            dif = d["monto_sql"] - d["monto_pq"]
            log(f"  {'':12s} monto SQL={d['monto_sql']/1e6:>12,.1f}M  "
                f"parquet={d['monto_pq']/1e6:>12,.1f}M  Δ={dif/1e6:+,.1f}M")

    if args.check:
        log("HAY DATOS NUEVOS" if hay else "sin cambios")
        sys.exit(0 if hay else 1)

    if not hay and not args.force:
        log("Sin cambios. Nada que hacer (usa --force para re-extraer).")
        return

    nom = semana.nombres(sem)
    log("Extrayendo...")
    t0 = time.time()
    for tabla, (origen, anio) in TABLAS.items():
        if det[tabla]["cambio"] or args.force:
            extraer(cfg, tabla, BASE / nom[tabla], origen, anio, total=det[tabla]["sql"])
        else:
            log(f"  {tabla}: sin cambios, se conserva {nom[tabla]}")
    log(f"[OK] extracción en {(time.time()-t0)/60:.1f} min")
    log(f"Siguiente paso: python build_data.py --rebuild --semana {sem}")


if __name__ == "__main__":
    main()
