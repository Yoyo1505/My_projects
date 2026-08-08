# -*- coding: utf-8 -*-
"""
actualizar.py — Orquesta la actualización semanal completa.

    SQL Server  --extraer_sql.py-->  r25/r26/p26.parquet
    Nvo Plan 2026.xlsx (si cambió) -> nvo_plan_2026.parquet
                                          |
                                    build_data.py  ->  aggs/*.parquet
                                          |
                                    estado.json  ->  la app se refresca sola

Escribe su progreso en `estado.json` para que la app lo muestre en vivo.

Uso:
    python actualizar.py            # solo si hay datos nuevos
    python actualizar.py --force    # siempre
    python actualizar.py --check    # ¿hay novedades? exit 0 = sí, 1 = no
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.resolve()
DL = Path.home() / "Downloads"
ESTADO = BASE / "estado.json"
LOG = BASE / "actualizacion.log"

NVO_XLSX = DL / "Nvo Plan 2026.xlsx"
NVO_PQ = BASE / "nvo_plan_2026.parquet"
PY = sys.executable

# La consola de Windows es cp1252: imprimir acentos (o el U+FFFD que mete
# errors="replace") lanza UnicodeEncodeError y aborta la actualización.
# Forzamos UTF-8 en stdout/stderr y no dependemos de la codificación del entorno.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def log(msg: str):
    linea = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        print(linea, flush=True)
    except UnicodeEncodeError:              # consola sin UTF-8: no perdemos el log
        print(linea.encode("ascii", "replace").decode("ascii"), flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(linea + "\n")


def set_estado(fase: str, pct: int, detalle: str = "", error: str | None = None):
    import os
    ESTADO.write_text(json.dumps({
        "fase": fase, "pct": pct, "detalle": detalle, "error": error,
        "actualizado": datetime.now().isoformat(timespec="seconds"),
        "corriendo": fase not in ("listo", "error", "sin_cambios"),
        "pid": os.getpid(),          # la app lo usa para detectar un proceso muerto
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _entorno_utf8() -> dict:
    """Los hijos también deben hablar UTF-8, o su print() de acentos los mata."""
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def corre(script: str, *args) -> int:
    """Ejecuta un script del proyecto y transmite su salida al log."""
    cmd = [PY, str(BASE / script), *args]
    log(f"$ {' '.join(cmd[1:])}")
    p = subprocess.Popen(cmd, cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", bufsize=1,
                         env=_entorno_utf8())
    for linea in p.stdout:
        linea = linea.rstrip()
        if linea:
            log(f"  | {linea}")
    return p.wait()


def nvo_plan_desactualizado() -> bool:
    if not NVO_XLSX.exists():
        return False
    if not NVO_PQ.exists():
        return True
    return NVO_XLSX.stat().st_mtime > NVO_PQ.stat().st_mtime


def regenerar_nvo_plan():
    """Convierte el Excel del Nvo Plan (265 MB, formato ancho) a parquet."""
    import polars as pl
    log(f"Nvo Plan: {NVO_XLSX.name} es más nuevo que el parquet, reconvirtiendo...")
    t0 = time.time()
    for kw in ({"infer_schema_length": 0},
               {"read_csv_options": {"infer_schema_length": 0}},
               {"read_options": {"infer_schema_length": 0}}):
        try:
            df = pl.read_excel(NVO_XLSX, **kw)
            break
        except TypeError:
            continue
    else:
        df = pl.read_excel(NVO_XLSX)
    tmp = NVO_PQ.with_suffix(".parquet.tmp")
    df.write_parquet(tmp)
    tmp.replace(NVO_PQ)
    log(f"Nvo Plan: {df.height:,} filas -> {NVO_PQ.name} ({time.time()-t0:.0f}s)")


def hay_novedades(sem: list[str] = ()) -> bool:
    """True si hay datos nuevos. Lanza si no se pudo consultar SQL
    (un fallo de red NO debe leerse como 'todo al día')."""
    rc = corre("extraer_sql.py", "--check", *sem)
    if rc == 2:
        # el motivo real ya quedó en el log: lo repetimos en el mensaje
        detalle = ""
        try:
            lineas = LOG.read_text(encoding="utf-8").splitlines()[-14:]
            err = [l for l in lineas if "ERROR" in l or "IM003" in l or "driver" in l.lower()]
            if err:
                detalle = " · " + err[-1].split("| ", 1)[-1][:150]
        except Exception:
            pass
        raise RuntimeError(f"no se pudo consultar SQL Server{detalle}")
    if rc == 0:
        return True
    if nvo_plan_desactualizado():
        log("Nvo Plan: el Excel cambió")
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--semana", type=int, default=None,
                    help="semana EKT a extraer (por defecto, la vigente)")
    args = ap.parse_args()
    sem = ["--semana", str(args.semana)] if args.semana is not None else []

    if args.check:
        try:
            sys.exit(0 if hay_novedades(sem) else 1)
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(2)   # 0=hay novedades · 1=sin cambios · 2=no se pudo saber

    t0 = time.time()
    try:
        set_estado("comprobando", 2, "buscando datos nuevos en SQL Server")
        if not args.force and not hay_novedades(sem):
            log("Sin cambios. Nada que actualizar.")
            set_estado("sin_cambios", 100, "los datos ya estaban al día")
            return

        set_estado("extrayendo", 10, "trayendo Real 2025 / Real 2026 / Plan 2026 de SQL Server (~10 min)")
        rc = corre("extraer_sql.py", *(["--force"] if args.force else []), *sem)
        if rc != 0:
            # 0x40010004 = DBG_TERMINATE_PROCESS: alguien lo mató (Ctrl-C, cerrar
            # ventana). La extracción tarda ~10 min; no está colgada.
            if rc == 1073807364:
                raise RuntimeError(
                    "la extracción se canceló desde fuera (Ctrl-C o ventana cerrada). "
                    "Tarda ~10 min: déjala correr, ahora imprime avance por lotes.")
            raise RuntimeError(f"extraer_sql.py falló (código {rc})")

        if args.force or nvo_plan_desactualizado():
            set_estado("nvo_plan", 35, "reconvirtiendo Nvo Plan 2026.xlsx")
            regenerar_nvo_plan()

        set_estado("agregando", 45, "build_data.py — une 95 M filas y precomputa (~8 min)")
        rc = corre("build_data.py", "--rebuild", *sem)
        if rc != 0:
            raise RuntimeError(f"build_data.py falló (código {rc})")

        mins = (time.time() - t0) / 60
        log(f"[OK] actualización completa en {mins:.1f} min")
        set_estado("listo", 100, f"terminado en {mins:.1f} min")

    except Exception as e:
        log(f"[ERROR] {e}")
        log(traceback.format_exc())
        set_estado("error", 0, "la actualización falló", error=str(e)[:300])
        sys.exit(1)


if __name__ == "__main__":
    main()
