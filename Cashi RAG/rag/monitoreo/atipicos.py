# -*- coding: utf-8 -*-
"""Semanas atípicas por entidad (CECO, grupo de cuentas o total), sin listas fijas de semanas.

Para cada semana con historia suficiente compara el monto contra la mediana de TODAS las semanas
previas de la misma entidad (solo pasado, sin fuga) con z robusto. Una semana es atípica si
|z| ≥ ZR_UMBRAL **y** la desviación en pesos supera el piso de materialidad (un MAD diminuto no
basta). Las semanas atípicas consecutivas se agrupan en bloques.
"""
from __future__ import annotations

from typing import List

import warnings

import numpy as np
import pandas as pd

from . import config as C


def _matriz(df_long: pd.DataFrame, clave: str, semanas: List[int]) -> tuple:
    """Pivote entidad × semana (0 donde no hay fila; `presente` marca las que sí tuvieron dato)."""
    p = df_long.pivot_table(index=clave, columns="sem", values="monto", aggfunc="sum")
    p = p.reindex(columns=semanas)
    presente = p.notna().to_numpy()
    return p.index.to_numpy(), p.fillna(0.0).to_numpy(float), presente


def _percentil_filas(xm: np.ndarray, q: float) -> np.ndarray:
    """Percentil `q` (0-1, interpolación lineal) por fila ignorando NaN, vectorizado (np.nanpercentile en 2D es un
    bucle por fila: ~2 s con 20 mil CECOs). Filas sin datos → NaN."""
    xs = np.sort(xm, axis=1)                       # los NaN quedan al final
    n = (~np.isnan(xm)).sum(axis=1)
    pos = np.clip((n - 1) * q, 0, None)
    lo = np.floor(pos).astype(int)
    hi = np.minimum(np.ceil(pos).astype(int), np.maximum(n - 1, 0))
    fil = np.arange(len(xm))
    v = xs[fil, lo] * (1 - (pos - lo)) + xs[fil, hi] * (pos - lo)
    return np.where(n > 0, v, np.nan)


def _mediana_mad(x: np.ndarray, pres: np.ndarray) -> tuple:
    """Mediana y MAD por fila, solo con las celdas presentes. MAD=0 → media absoluta (marca `metodo`)."""
    xm = np.where(pres, x, np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)      # filas sin datos → NaN, se descartan con `ok`
        med = np.nanmedian(xm, axis=1)
        mad = np.nanmedian(np.abs(xm - med[:, None]), axis=1)
        q1, q3 = _percentil_filas(xm, 0.25), _percentil_filas(xm, 0.75)
    iqr = (q3 - q1) / 2.0      # escala en unidades de MAD: MAD ≈ 0.6745σ y IQR ≈ 1.349σ → MAD ≈ IQR/2
    # MAD → (si es 0) IQR → (si también es 0: serie casi constante) 5% de la mediana. Nunca escala 0.
    # (La media absoluta no se usa de respaldo: la inflan justo los atípicos que se quieren detectar.)
    piso_rel = np.maximum(0.05 * np.abs(med), 1.0)
    metodo = np.where(mad > 0, "MAD", np.where(iqr > 0, "IQR", "PISO_RELATIVO"))
    esc = np.where(mad > 0, mad, np.where(iqr > 0, iqr, piso_rel))
    return med, esc, metodo


def detectar(df_long: pd.DataFrame, clave: str, piso: float,
             historia_min: int = C.HISTORIA_MIN, zr_umbral: float = C.ZR_UMBRAL,
             modo: str = "pasado") -> pd.DataFrame:
    """`df_long`: columnas [clave, sem, monto]. Devuelve una fila por (entidad, semana) atípica:
    clave, sem, monto, base (mediana), dif, zr, metodo.

    modo="pasado": cada semana contra la mediana/MAD de las semanas ANTERIORES (sin fuga; es el que
        usa el modelo y la alerta de la semana en curso). No evalúa las primeras `historia_min` semanas.
    modo="retro": cada semana contra la mediana/MAD de TODA la ventana pedida (responde "¿qué semanas
        fueron atípicas?" mirando atrás; sí cubre las primeras semanas)."""
    vacio = pd.DataFrame(columns=[clave, "sem", "monto", "base", "dif", "zr", "metodo"])
    if df_long is None or df_long.empty:
        return vacio
    semanas = sorted(int(s) for s in df_long["sem"].unique())
    ids, x, pres = _matriz(df_long, clave, semanas)
    filas = []
    if modo == "retro":
        ok = pres.sum(axis=1) >= historia_min
        med, esc, metodo = _mediana_mad(x, pres)
        with np.errstate(divide="ignore", invalid="ignore"):
            zr = np.where(esc[:, None] > 0, 0.6745 * (x - med[:, None]) / esc[:, None], 0.0)
        marca = ok[:, None] & pres & (np.abs(zr) >= zr_umbral) & (np.abs(x - med[:, None]) >= piso)
        for i, j in zip(*np.nonzero(marca)):
            filas.append((ids[i], semanas[j], x[i, j], med[i], x[i, j] - med[i], zr[i, j], metodo[i]))
        if not filas:
            return vacio
        return pd.DataFrame(filas, columns=[clave, "sem", "monto", "base", "dif", "zr", "metodo"]) \
                 .sort_values([clave, "sem"]).reset_index(drop=True)
    for j, s in enumerate(semanas):          # bucle por semana (≤53), nunca por fila
        if j < historia_min:
            continue
        previo, pp = x[:, :j], pres[:, :j]
        ok = pp.sum(axis=1) >= historia_min
        if not ok.any():
            continue
        med, esc, metodo = _mediana_mad(previo, pp)
        with np.errstate(divide="ignore", invalid="ignore"):
            zr = np.where(esc > 0, 0.6745 * (x[:, j] - med) / esc, 0.0)
        dif = x[:, j] - med
        marca = ok & pres[:, j] & (np.abs(zr) >= zr_umbral) & (np.abs(dif) >= piso)
        for i in np.flatnonzero(marca):
            filas.append((ids[i], s, x[i, j], med[i], dif[i], zr[i], metodo[i]))
    if not filas:
        return vacio
    out = pd.DataFrame(filas, columns=[clave, "sem", "monto", "base", "dif", "zr", "metodo"])
    return out.sort_values([clave, "sem"]).reset_index(drop=True)


def bloques(atip: pd.DataFrame, clave: str) -> pd.DataFrame:
    """Une semanas atípicas consecutivas por entidad: clave, ini, fin, n, semanas, impacto_neto, zr_max."""
    if atip.empty:
        return pd.DataFrame(columns=[clave, "ini", "fin", "n", "semanas", "impacto_neto", "zr_max", "tipo"])
    a = atip.sort_values([clave, "sem"]).copy()
    a["_g"] = (a.groupby(clave)["sem"].diff().fillna(99) != 1).cumsum()
    g = a.groupby([clave, "_g"]).agg(ini=("sem", "min"), fin=("sem", "max"), n=("sem", "size"),
                                      impacto_neto=("dif", "sum"), zr_max=("zr", lambda s: s.abs().max()),
                                      semanas=("sem", lambda s: ", ".join(str(int(v)) for v in s))).reset_index()
    g["tipo"] = pd.cut(g["n"], [0, 1, 2, 5, 10_000], labels=["PUNTUAL", "TEMPORAL", "PERSISTENTE", "CAMBIO_ESTRUCTURAL"]).astype(str)
    return g.drop(columns="_g")


def texto_semanas(semanas: List[int]) -> str:
    """[6,7,8,12] → '6 a 8 y 12' (siempre dice cuáles, nunca solo cuántas)."""
    s = sorted(int(v) for v in semanas)
    partes, i = [], 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[j] + 1:
            j += 1
        if j - i >= 2:
            partes.append(f"{s[i]} a {s[j]}")
        else:
            partes.extend(str(v) for v in s[i:j + 1])
        i = j + 1
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]
