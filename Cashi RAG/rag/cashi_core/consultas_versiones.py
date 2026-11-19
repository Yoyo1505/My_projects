# -*- coding: utf-8 -*-
"""rag/cashi_core/consultas_versiones.py — Gasto "con la versión de la semana N".

Cada jueves se archiva una copia del Real 2026 (datos/r26_semNN.parquet = «versión de la semana NN»: lo que se sabía
de cada semana cuando se tomó esa copia). Aquí se responde, por ejemplo:
    "dame el gasto con la versión de la semana 40"                 -> semanas 1 a 40 en esa versión
    "gasto de la semana 30 con la versión de la semana 40"         -> la semana 30 vista desde la versión 40
    "gasto de la semana 1 a la 30 con la versión r26sem40"
y se compara contra la versión más reciente archivada (cuánto cambió después). Por cuenta si se pide "por cuenta".
Conexión DuckDB propia por llamada en memoria (los snapshots viven fuera de dashboard.duckdb).
"""
from __future__ import annotations

import time
from functools import lru_cache

from rag.cashi_core.comun import *  # noqa: F401,F403

_RE_VERSION = [
    re.compile(r"\br26\s*_?\s*sem\s*_?\s*(\d{1,2})\b"),
    re.compile(r"\bversion(?:es)?\s+(?:de\s+)?(?:la\s+)?(?:semana\s+|sem\s+)?(?:r26\s*)?(\d{1,2})\b"),
]
_RE_RANGO = re.compile(r"\bsemanas?\s+(\d{1,2})\s+(?:a|al|hasta|-)\s+(?:la\s+)?(?:semana\s+)?(\d{1,2})\b")
_RE_SEMANA = re.compile(r"\bsemana\s+(\d{1,2})\b")


@lru_cache(maxsize=1)
def _catalogo_cuentas():
    """cuenta mayor -> (grupo de cuentas, cuenta), del catálogo oficial (el mismo que usa Comparación de Versiones)."""
    cta = pd.read_excel(BASE_DIR / "datos" / "Catálogo grupo cuentas.xlsx", dtype=str)
    cta = cta.rename(columns={"Cta Mayor": "cta_mayor"})

    def _limpia(s):
        s = s.fillna("").astype(str).str.strip()
        return s.where(s != "", "No Clasificado")

    out = pd.DataFrame({"cta_mayor": cta["cta_mayor"].astype(str).str.strip(),
                        "grupo": _limpia(cta["Grupo de Cuentas"]), "cuenta": _limpia(cta["Cuentas"])})
    return out.drop_duplicates(subset=["cta_mayor"], keep="first").reset_index(drop=True)


@lru_cache(maxsize=1)
def _cecos_digitales():
    p = BASE_DIR / "aggs" / "ceco_digitales.json"
    return tuple(str(c).strip() for c in json.loads(p.read_text(encoding="utf-8"))) if p.exists() else ()


@lru_cache(maxsize=48)
def _agrega_snapshot(sem_arch: int, s_ini: int, s_fin: int, canal: str) -> "pd.DataFrame":
    """Real por cuenta mayor de una versión archivada, en un rango de semanas y canal. Se agrega ANTES de unir con el
    catálogo (23 M de filas por snapshot): así tarda segundos y el resultado, que es chico, queda en caché."""
    dig = _cecos_digitales()
    where_canal = ""
    if dig and canal in ("Fisico", "Digital"):
        # anti/semi-join contra una tabla chica: con una lista literal de 154 textos el filtro tardaba 3.6 s; así ~0.1 s
        where_canal = f" AND ID_CENTRO_COSTOS {'NOT IN' if canal == 'Fisico' else 'IN'} (SELECT ceco FROM dig)"
    fp = (BASE_DIR / "datos" / f"r26_sem{sem_arch}.parquet").as_posix()
    con = duckdb.connect(":memory:")
    try:
        con.register("dig", pd.DataFrame({"ceco": list(dig)}))
        return con.execute(f"""
            SELECT CAST(ID_CONCEPTO_CUENTA_NIV3 AS VARCHAR) AS cta_mayor, SUM("SUM_MONTO_MNX_CONS_(SUMA)") AS monto
            FROM read_parquet('{fp}')
            WHERE SEMANA_EKT BETWEEN {int(s_ini)} AND {int(s_fin)} {where_canal}
            GROUP BY 1
        """).fetch_df()
    finally:
        con.close()


def _por_etiqueta(df_cta, col_et: str, alias: str):
    """Une la agregación por cuenta mayor con el catálogo y suma por grupo o por cuenta."""
    m = df_cta.merge(_catalogo_cuentas(), on="cta_mayor", how="left")
    m[col_et] = m[col_et].fillna("No Clasificado")
    out = m.groupby(col_et, as_index=False)["monto"].sum()
    return out.rename(columns={col_et: "etiqueta", "monto": alias})


class ConsultasVersionesMixin:
    @staticmethod
    def _versiones_archivadas() -> list[int]:
        out = []
        for fp in (BASE_DIR / "datos").glob("r26_sem*.parquet"):
            try:
                out.append(int(fp.stem.replace("r26_sem", "")))
            except ValueError:
                continue
        return sorted(out)

    @staticmethod
    def _parse_version(norm: str):
        """(versión, (sem_ini, sem_fin) | None) a partir de la pregunta normalizada; (None, None) si no menciona versión."""
        v, span = None, None
        for rx in _RE_VERSION:
            m = rx.search(norm)
            if m:
                v, span = int(m.group(1)), m.span()
                break
        if v is None:
            return None, None
        resto = norm[:span[0]] + " " + norm[span[1]:]
        m = _RE_RANGO.search(resto)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            return v, (min(a, b), max(a, b))
        m = _RE_SEMANA.search(resto)
        if m:
            s = int(m.group(1))
            return v, (s, s)
        return v, None

    def _es_consulta_version(self, norm: str) -> bool:
        return bool(re.search(r"\bversion(es)?\b", norm) or re.search(r"\br26\s*_?\s*sem\s*_?\s*\d", norm)) \
            and self._parse_version(norm)[0] is not None

    def _responder_version(self, texto: str, norm: str) -> dict:
        v, span = self._parse_version(norm)
        archivadas = self._versiones_archivadas()
        if v not in archivadas:
            lista = ", ".join(str(s) for s in archivadas) or "ninguna"
            return self._respuesta_sin_datos(
                f"No tengo archivada la versión de la semana **{v}**. Versiones disponibles: **{lista}**.")
        vig = archivadas[-1]
        s_ini, s_fin = span if span else (1, v)
        por_cuenta = "cuenta" in norm.replace("grupo de cuenta", "").replace("grupos de cuenta", "")
        col_et = "cuenta" if por_cuenta else "grupo"
        et_txt = "Cuenta" if por_cuenta else "Grupo de Cuentas"

        canal = getattr(self._tl, "canal", "Fisico")
        t0 = time.perf_counter()
        d_ver = _por_etiqueta(_agrega_snapshot(v, s_ini, s_fin, canal), col_et, "ver")
        d_vig = _por_etiqueta(_agrega_snapshot(vig, s_ini, s_fin, canal), col_et, "vig") if vig != v else None
        dt_ms = round((time.perf_counter() - t0) * 1000)

        df = d_ver if d_vig is None else d_ver.merge(d_vig, on="etiqueta", how="outer")
        df = df.fillna(0.0)
        if df.empty or float(df["ver"].abs().sum()) == 0.0:
            return self._respuesta_sin_datos(f"La versión de la semana **{v}** no tiene gasto en las semanas {s_ini} a {s_fin}.")
        df = df.sort_values("ver", key=lambda s: s.abs(), ascending=False)

        c_ver, c_vig = f"Real versión sem {v}", f"Real vigente sem {vig}"
        tabla = []
        for _, r in df.iterrows():
            fila = {et_txt: r["etiqueta"], c_ver: float(r["ver"])}
            if d_vig is not None:
                fila[c_vig] = float(r["vig"])
                fila["Cambio posterior (vs versión)"] = float(r["vig"] - r["ver"])
            tabla.append(fila)

        tot_ver = float(df["ver"].sum())
        periodo = f"semana {s_ini}" if s_ini == s_fin else f"semanas {s_ini} a {s_fin}"
        datos = [f"- **Versión:** semana {v}", f"- **Periodo:** {periodo}", f"- **Canal:** {canal}",
                 f"- **Real en esa versión:** {M(tot_ver)}"]
        nota = ""
        if d_vig is not None:
            tot_vig = float(df["vig"].sum())
            datos += [f"- **Real en la versión vigente (sem {vig}):** {M(tot_vig)}",
                      f"- **Cambio posterior:** {M(tot_vig - tot_ver)}"]
            nota = "El cambio posterior es lo que se registró en esas semanas después de que se archivó la versión."
        if s_fin > v:
            nota += (" " if nota else "") + f"Las semanas posteriores a la {v} no estaban completas cuando se archivó esa versión."
        titulo = f"Gasto con la versión de la semana {v} ({periodo})"
        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": "Gasto por versión archivada",
            "titulo": titulo,
            "respuesta_ejecutiva": "### Gasto por versión\n" + "\n".join(datos) + (f"\n\n{nota}" if nota else ""),
            "tabla": tabla,
            "sql_linaje": {
                "sql_ejecutado": f"-- r26_sem{v}.parquet (y r26_sem{vig}.parquet para comparar), SEMANA_EKT {s_ini}..{s_fin}, "
                                 f"monto constante, agrupado por {et_txt}",
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": [f"r26_sem{v}.parquet"] + ([f"r26_sem{vig}.parquet"] if d_vig is not None else []),
            },
        }
