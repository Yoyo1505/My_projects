# -*- coding: utf-8 -*-
"""Variaciones semana N contra semana N-1 de Real, Plan y FCST SIE, por grupo de cuentas o cuenta.

Reglas: cada serie se compara contra SU PROPIA semana anterior. Además se muestran Real vs Plan y
Real vs FCST SIE de la semana N. Los totales salen de la suma exacta, sin LIMIT. Las filas atípicas
(las que mueven el resultado) se marcan con el mismo criterio robusto de `atipicos.py`.
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import pandas as pd

from . import config as C
from .atipicos import detectar

DIMS = {"grupo": "cat_Grupo_de_Cuentas", "cuenta": "cat_Cuentas"}


def _pct(a, b):
    """% de a sobre |b|; 0 si b=0 (nunca infinito)."""
    return np.where(b != 0, a / np.abs(b) * 100.0, 0.0)


def _serie_semanal(ejecutar, tabla, m_col, col, where_extra, params, sem_max):
    """Real y Plan por (entidad, sem) para sem 1..sem_max, en una sola consulta."""
    return ejecutar(f"""
        SELECT {col} AS ent, sem, Serie, SUM({m_col}) AS monto
        FROM {tabla}
        WHERE Serie IN ('R26', 'P26') AND sem BETWEEN 1 AND {int(sem_max)} AND {col} IS NOT NULL {where_extra}
        GROUP BY 1, 2, 3
    """, list(params))


def variaciones(ejecutar: Callable[[str, list], pd.DataFrame], semana: int, dim: str = "grupo",
                tabla: str = "consolidado", m_col: str = "monto_cons",
                tabla_fcst: Optional[str] = "agg_fcst_srv_cuenta", f_col: str = "FCST_cons",
                where_extra: str = "", params: Optional[list] = None,
                where_fcst: str = "", params_fcst: Optional[list] = None) -> pd.DataFrame:
    """Una fila por grupo/cuenta: Real_N, Real_N1, Var_Real, Var_Real_Pct, Plan_N, Plan_N1, Var_Plan,
    Var_Plan_Pct, FCST_N, FCST_N1, Var_FCST, Real_vs_Plan, Real_vs_FCST y `atipico` (bool)."""
    col = DIMS[dim]
    semana = int(semana)
    params = params or []
    d = _serie_semanal(ejecutar, tabla, m_col, col, where_extra, params, semana)
    if d.empty:
        return pd.DataFrame()
    w = d.pivot_table(index="ent", columns=["Serie", "sem"], values="monto", aggfunc="sum").fillna(0.0)

    def g(serie, s):
        return w[(serie, s)] if (serie, s) in w.columns else pd.Series(0.0, index=w.index)

    out = pd.DataFrame(index=w.index)
    out["Real_N"], out["Real_N1"] = g("R26", semana), g("R26", semana - 1)
    out["Plan_N"], out["Plan_N1"] = g("P26", semana), g("P26", semana - 1)
    if tabla_fcst:
        f = ejecutar(f"""SELECT {col} AS ent, sem, SUM({f_col}) AS f FROM {tabla_fcst}
                         WHERE sem IN ({semana}, {semana - 1}) AND {col} IS NOT NULL {where_fcst}
                         GROUP BY 1, 2""", list(params_fcst or []))
        fp = f.pivot_table(index="ent", columns="sem", values="f", aggfunc="sum").reindex(out.index).fillna(0.0)
        out["FCST_N"] = fp[semana] if semana in fp.columns else 0.0
        out["FCST_N1"] = fp[semana - 1] if (semana - 1) in fp.columns else 0.0
    else:
        out["FCST_N"] = out["FCST_N1"] = 0.0
    out["Var_Real"] = out["Real_N"] - out["Real_N1"]
    out["Var_Real_Pct"] = _pct(out["Var_Real"], out["Real_N1"])
    out["Var_Plan"] = out["Plan_N"] - out["Plan_N1"]
    out["Var_Plan_Pct"] = _pct(out["Var_Plan"], out["Plan_N1"])
    out["Var_FCST"] = out["FCST_N"] - out["FCST_N1"]
    out["Real_vs_Plan"] = out["Real_N"] - out["Plan_N"]
    out["Real_vs_FCST"] = out["Real_N"] - out["FCST_N"]
    for c in out.columns:                      # sin ruido de punto flotante (1e-13)
        out[c] = out[c].round(4 if c.endswith("Pct") else 2)

    # Atípico = la semana N de esa entidad se sale de su historia (solo semanas previas).
    largo = d[d["Serie"] == "R26"].rename(columns={"monto": "monto"})[["ent", "sem", "monto"]]
    piso = C.IMPACTO_MIN_GRUPO if dim == "grupo" else C.IMPACTO_MIN_GRUPO / 4
    a = detectar(largo[largo["sem"] <= semana], "ent", piso)
    marcados = set(a.loc[a["sem"] == semana, "ent"])
    out["atipico"] = out.index.isin(marcados)
    out = out.reset_index().rename(columns={"ent": col})
    return out.reindex(out["Var_Real"].abs().sort_values(ascending=False).index).reset_index(drop=True)
