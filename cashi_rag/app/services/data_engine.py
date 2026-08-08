# -*- coding: utf-8 -*-
"""
app/services/data_engine.py — Servicio y Gestión de Carga de Datos Parquet / DuckDB
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Tuple

import polars as pl
import streamlit as st

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
AGGS_DIR = BASE_DIR / "aggs"


def get_version_datos() -> str:
    m = AGGS_DIR / "_meta.json"
    return f"{m.stat().st_mtime_ns}" if m.exists() else "0"


@st.cache_resource(show_spinner="Cargando agregados financieros...")
def cargar_todos_los_agregados(version: str) -> Tuple[Dict[str, Any], Dict[str, pl.DataFrame]]:
    meta_p = AGGS_DIR / "_meta.json"
    if not meta_p.exists():
        st.error(f"Falta el archivo `{meta_p}`. Ejecute primero: `python build_data.py --rebuild`.")
        st.stop()
    meta = json.loads(meta_p.read_text(encoding="utf-8"))

    nombres_aggs = [
        "global", "division", "territorio", "zona", "region", "pdc",
        "grupo_cuentas", "cuentas", "formato", "naturaleza", "agrupador_reales",
        "agrupa1", "agrupa2", "agrupa3", "agrupador", "agrupadores",
        "clasificacion2", "trimestre", "estatus", "segmento1", "segmento2"
    ]

    aggs = {}
    for nombre in nombres_aggs:
        fp = AGGS_DIR / f"{nombre}.parquet"
        if fp.exists():
            aggs[nombre] = pl.read_parquet(fp)

    return meta, aggs
