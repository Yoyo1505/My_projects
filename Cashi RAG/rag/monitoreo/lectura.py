# -*- coding: utf-8 -*-
"""Lectura de los resultados del modelo (aggs/monitoreo/scores.parquet y estado.json) para el tablero y Cashi.

No importa scikit-learn: el tablero corre en un entorno sin él y solo consume lo que dejó `python -m rag.monitoreo score`.
Si no hay resultados (modelo sin entrenar/puntuar), todo devuelve vacío y las vistas se muestran sin la parte ML.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd

SALIDA = Path(__file__).resolve().parents[2] / "aggs" / "monitoreo"
_CACHE = {"mt": None, "df": None}


def _scores() -> Optional[pd.DataFrame]:
    ruta = SALIDA / "scores.parquet"
    if not ruta.exists():
        return None
    mt = ruta.stat().st_mtime
    if _CACHE["mt"] != mt:
        try:
            df = pd.read_parquet(ruta)
            df["ceco"] = df["ceco"].astype(str)
            _CACHE["df"], _CACHE["mt"] = df, mt
        except Exception:
            return None
    return _CACHE["df"]


def estado() -> Optional[dict]:
    ruta = SALIDA / "estado.json"
    try:
        return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None
    except Exception:
        return None


def scores(canal: str, ini: int, fin: int) -> pd.DataFrame:
    """Filas del modelo (score ≥ 0.95 o alerta) del canal en semanas ini..fin. Vacío si no hay resultados."""
    df = _scores()
    if df is None:
        return pd.DataFrame(columns=["ceco", "sem", "real", "score", "concordancia", "alerta", "causas"])
    return df[(df["canal"] == canal) & (df["sem"] >= ini) & (df["sem"] <= fin)].copy()
