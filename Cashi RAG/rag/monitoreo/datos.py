# -*- coding: utf-8 -*-
"""Lectura de la serie semanal por CECO desde aggs/dashboard.duckdb (solo lectura) para el modelo."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[2]
AGGS = RAIZ / "aggs"
SALIDA = AGGS / "monitoreo"

# Fuente por canal: rollup CECO×semana del canal físico; consolidado del canal digital (111 CECOs).
FUENTES = {"Fisico": "rollup_ceco_general", "Digital": "dg.consolidado_dig"}


def sem_max_real() -> int:
    """Última semana con Real (fuente de verdad: aggs/_meta.json)."""
    with open(AGGS / "_meta.json", encoding="utf-8") as f:
        return int(json.load(f)["sem_max_real"])


def conectar():
    import duckdb
    con = duckdb.connect(str(AGGS / "dashboard.duckdb"), read_only=True)
    con.execute("SET threads=4")
    con.execute("SET memory_limit='4GB'")
    dig = AGGS / "digitales.duckdb"
    if dig.exists():
        con.execute(f"ATTACH '{dig.as_posix()}' AS dg (READ_ONLY)")
    return con


def leer_panel(con, canal: str, hasta: int, m_col: str = "monto_cons") -> pl.DataFrame:
    """ceco, sem, real, plan (Real y Plan 2026 por CECO y semana, semanas 1..hasta; solo filas existentes)."""
    df = con.execute(f"""
        SELECT CAST(ID_CENTRO_COSTOS AS VARCHAR) AS ceco, sem,
               SUM(CASE WHEN Serie = 'R26' THEN {m_col} ELSE 0 END) AS real,
               SUM(CASE WHEN Serie = 'P26' THEN {m_col} ELSE 0 END) AS plan
        FROM {FUENTES[canal]}
        WHERE Serie IN ('R26', 'P26') AND sem BETWEEN 1 AND {int(hasta)} AND ID_CENTRO_COSTOS IS NOT NULL
        GROUP BY 1, 2
        HAVING SUM(CASE WHEN Serie = 'R26' THEN 1 ELSE 0 END) > 0
    """).df()
    return pl.DataFrame({"ceco": df["ceco"].to_numpy(), "sem": df["sem"].to_numpy().astype(np.int32),
                         "real": df["real"].to_numpy().astype(np.float64), "plan": df["plan"].to_numpy().astype(np.float64)})
