# -*- coding: utf-8 -*-
"""
app/services/financial_calculations.py — Motor de Cálculo Financiero y Formateo Contable
"""
from __future__ import annotations

import pandas as pd

MEDIDAS = ["Real_2025", "Plan_2026", "Real_2026"]

COLOR = {
    "Real_2025": "#64748b",
    "Plan_2026": "#e60000",
    "Real_2026": "#f43f5e",
    "Forecast_Cierre": "#8a93a0"
}

NOMBRE = {
    "Real_2025": "Real 2025",
    "Plan_2026": "Plan 2026",
    "Real_2026": "Real 2026",
    "Forecast_Cierre": "Forecast"
}


def M(v) -> str:
    """Formatea valor a Millones de Pesos (MDP)."""
    if v is None or pd.isna(v):
        return "—"
    return f"{v / 1e6:,.1f} MDP"


def P(v) -> str:
    """Formatea porcentaje genérico."""
    if v is None or pd.isna(v):
        return "—"
    return f"{v:+.1f}%"


def MC(v) -> str:
    """Formato contable estricto: Positivo = Gasto (entre paréntesis), Negativo = Ahorro (sin paréntesis)."""
    if v is None or pd.isna(v):
        return "—"
    s = M(abs(v))
    return f"({s})" if v > 0 else s


def PC(v) -> str:
    """Formato contable de porcentaje: Positivo = entre paréntesis, Negativo = sin paréntesis."""
    if v is None or pd.isna(v):
        return "—"
    return f"({abs(v):,.1f}%)" if v > 0 else f"{abs(v):,.1f}%"


def calcular_medidas(d: dict, total_r26: float = 0.0, total_r25: float = 0.0, total_p26: float = 0.0) -> dict:
    """Calcula todas las métricas y variaciones financieras respetando las reglas corporativas."""
    r25 = d.get("Real_2025", 0.0) or 0.0
    p26 = d.get("Plan_2026", 0.0) or 0.0
    r26 = d.get("Real_2026", 0.0) or 0.0

    vs_plan_abs = r26 - p26
    vs_plan_pct = (vs_plan_abs / abs(p26) * 100) if p26 else 0.0

    vs_aa_abs = r26 - r25
    vs_aa_pct = (vs_aa_abs / abs(r25) * 100) if r25 else 0.0

    pct_r25 = (r25 / total_r25 * 100) if total_r25 else 0.0
    pct_p26 = (p26 / total_p26 * 100) if total_p26 else 0.0
    pct_r26 = (r26 / total_r26 * 100) if total_r26 else 0.0

    cumplimiento = (r26 / abs(p26) * 100) if p26 else 0.0

    return {
        "Real_2025": r25,
        "Pct_r25": pct_r25,
        "Plan_2026": p26,
        "Pct_p26": pct_p26,
        "Real_2026": r26,
        "Pct_r26": pct_r26,
        "Vs_Plan_Abs": vs_plan_abs,
        "Vs_Plan_Pct": vs_plan_pct,
        "Vs_AA_Abs": vs_aa_abs,
        "Vs_AA_Pct": vs_aa_pct,
        "Cumplimiento_Plan": cumplimiento,
    }
