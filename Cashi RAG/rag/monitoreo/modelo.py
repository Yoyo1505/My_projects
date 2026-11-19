# -*- coding: utf-8 -*-
"""Detector no supervisado de CECO-semana raros: Isolation Forest + error de reconstrucción PCA (contraste).

Sin etiquetas: no se reporta accuracy/precision/recall. Se evalúa con estabilidad de scores, tasa de alertas,
concordancia con el detector estadístico, drift y backtesting walk-forward (ver `backtest`).
Los scores del ensemble son percentiles (0-1) contra la distribución del entrenamiento; una fila es alerta si
supera el umbral calibrado Y la desviación contra su mediana previa es material en pesos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl

from . import config as C
from .features import FEATURES, NOMBRES, elegibles


class ModeloNoEntrenado(RuntimeError):
    pass


def _matriz(df: pl.DataFrame) -> np.ndarray:
    faltan = [c for c in FEATURES if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas para puntuar: {faltan}")
    return df.select(FEATURES).to_numpy().astype(np.float64)


def _ecdf(ref_ordenado: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.searchsorted(ref_ordenado, x, side="right") / max(len(ref_ordenado), 1)


def _scores_crudos(obj: dict, X: np.ndarray):
    Xs = obj["scaler"].transform(X)
    s_if = -obj["iforest"].score_samples(Xs)
    rec = obj["pca"].inverse_transform(obj["pca"].transform(Xs))
    s_pca = ((Xs - rec) ** 2).sum(axis=1)
    return Xs, s_if, s_pca


def _ensemble(obj: dict, s_if: np.ndarray, s_pca: np.ndarray) -> np.ndarray:
    return (_ecdf(obj["ref_if"], s_if) + _ecdf(obj["ref_pca"], s_pca)) / 2.0


def _psi_ref(X: np.ndarray) -> list:
    out = []
    for j in range(X.shape[1]):
        edges = np.unique(np.quantile(X[:, j], np.linspace(0, 1, 11)))
        if len(edges) < 3:
            out.append({"edges": edges.tolist(), "p": [1.0]})
            continue
        e = np.concatenate(([-np.inf], edges[1:-1], [np.inf]))
        p = np.histogram(X[:, j], bins=e)[0] / len(X)
        out.append({"edges": e.tolist(), "p": p.tolist()})
    return out


def psi(ref: list, X: np.ndarray) -> dict:
    """Population Stability Index por feature de `X` (ventana reciente) contra la distribución de entrenamiento."""
    res = {}
    for j, nombre in enumerate(FEATURES):
        e, p = np.array(ref[j]["edges"]), np.array(ref[j]["p"])
        if len(p) < 2 or len(X) == 0:
            res[nombre] = 0.0
            continue
        q = np.histogram(X[:, j], bins=e)[0] / len(X)
        p, q = np.clip(p, 1e-4, None), np.clip(q, 1e-4, None)
        res[nombre] = float(((q - p) * np.log(q / p)).sum())
    return res


def entrenar(feat: pl.DataFrame, fin_entrenamiento: int, sem_calibracion: int = C.SEM_CALIBRACION,
             semilla: int = C.SEMILLA, piso: float = C.IMPACTO_MIN_CECO) -> dict:
    """Entrena con semanas ≤ fin_entrenamiento (las últimas `sem_calibracion` solo calibran el umbral). Devuelve
    {"obj": objetos sklearn + referencias, "meta": metadatos}. Excluye del conjunto normal las filas que el
    detector estadístico ya considera críticas (contaminación)."""
    from sklearn.decomposition import PCA
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import RobustScaler

    el = elegibles(feat, C.HISTORIA_MIN).filter(pl.col("sem") <= fin_entrenamiento)
    contaminada = (pl.col("zr8").abs() >= C.ZR_CONTAMINACION) & ((pl.col("real") - pl.col("med8")).abs() >= piso)
    fin_train = fin_entrenamiento - sem_calibracion
    tr_all = el.filter(pl.col("sem") <= fin_train)
    tr = tr_all.filter(~contaminada)
    ca = el.filter(pl.col("sem") > fin_train)
    if tr.height < C.MIN_FILAS_ENTRENAMIENTO or ca.height == 0:
        raise ValueError(f"Datos insuficientes para entrenar: {tr.height} filas de entrenamiento, {ca.height} de calibración "
                         f"(mínimo {C.MIN_FILAS_ENTRENAMIENTO} y ≥ 1 semana de calibración).")
    X = _matriz(tr)
    scaler = RobustScaler().fit(X)
    Xs = scaler.transform(X)
    iforest = IsolationForest(n_estimators=C.N_ARBOLES, max_samples=min(256, len(Xs)), random_state=semilla, n_jobs=-1).fit(Xs)
    pca = PCA(n_components=min(6, X.shape[1] - 1), random_state=semilla).fit(Xs)
    obj = {"scaler": scaler, "iforest": iforest, "pca": pca}
    _, s_if, s_pca = _scores_crudos(obj, X)
    obj["ref_if"], obj["ref_pca"] = np.sort(s_if), np.sort(s_pca)
    obj["psi_ref"] = _psi_ref(X)
    obj["centro"] = scaler.center_.copy()
    Xc = _matriz(ca)
    _, c_if, c_pca = _scores_crudos(obj, Xc)
    ens_c = _ensemble(obj, c_if, c_pca)
    obj["umbral"] = float(np.quantile(ens_c, C.CUANTIL_ALERTA))
    obj["piso"] = float(piso)
    meta = {
        "fin_entrenamiento": int(fin_entrenamiento), "sem_calibracion": int(sem_calibracion),
        "filas_entrenamiento": int(tr.height), "filas_calibracion": int(ca.height),
        "filas_excluidas_contaminacion": int(tr_all.height - tr.height),
        "features": FEATURES, "semilla": int(semilla), "umbral": obj["umbral"], "piso_materialidad_mxn": float(piso),
        "hiperparametros": {"n_arboles": C.N_ARBOLES, "max_samples": int(min(256, len(Xs))), "pca_componentes": int(pca.n_components_),
                            "cuantil_alerta": C.CUANTIL_ALERTA, "zr_contaminacion": C.ZR_CONTAMINACION},
        "distribucion_scores_ensemble_calibracion": {q: float(np.quantile(ens_c, q)) for q in (0.5, 0.9, 0.99, 0.999)},
    }
    return {"obj": obj, "meta": meta}


def puntuar(obj: dict, df: pl.DataFrame) -> pl.DataFrame:
    """Agrega score_if, score_pca, score (percentil del ensemble), concordancia y alerta a `df` (filas ya elegibles)."""
    if not obj or "iforest" not in obj:
        raise ModeloNoEntrenado("No hay modelo entrenado: corre `python -m rag.monitoreo train` primero.")
    if df.is_empty():
        return df.with_columns(pl.lit(0.0).alias("score"), pl.lit(False).alias("alerta"), pl.lit(False).alias("concordancia"),
                               pl.lit(0.0).alias("score_if"), pl.lit(0.0).alias("score_pca"))
    X = _matriz(df)
    _, s_if, s_pca = _scores_crudos(obj, X)
    r_if, r_pca = _ecdf(obj["ref_if"], s_if), _ecdf(obj["ref_pca"], s_pca)
    ens = (r_if + r_pca) / 2.0
    material = np.abs(df["real"].to_numpy() - df["med8"].to_numpy()) >= obj["piso"]
    return df.with_columns(
        pl.Series("score_if", r_if), pl.Series("score_pca", r_pca), pl.Series("score", ens),
        pl.Series("concordancia", (r_if >= 0.98) & (r_pca >= 0.98)),
        pl.Series("alerta", (ens >= obj["umbral"]) & material))


def causas(obj: dict, df: pl.DataFrame, k: int = 3) -> list:
    """Explicación APROXIMADA por perturbación: cuánto baja la rareza al llevar cada feature a su valor típico
    (mediana del entrenamiento). Se mide sobre los scores crudos (el percentil se satura cerca de 1) y se reporta
    como porcentaje de la rareza explicada por cada feature; no es una atribución exacta."""
    if df.is_empty():
        return []
    X = _matriz(df)
    _, s_if, s_pca = _scores_crudos(obj, X)
    sd_if, sd_pca = float(np.std(obj["ref_if"])) or 1.0, float(np.std(obj["ref_pca"])) or 1.0
    caidas = np.zeros((len(X), X.shape[1]))
    for j in range(X.shape[1]):
        Xp = X.copy()
        Xp[:, j] = obj["centro"][j]
        _, p_if, p_pca = _scores_crudos(obj, Xp)
        caidas[:, j] = (s_if - p_if) / sd_if + (s_pca - p_pca) / sd_pca
    caidas = np.clip(caidas, 0.0, None)
    out = []
    for i in range(len(X)):
        tot = caidas[i].sum()
        if tot <= 0:
            out.append("")
            continue
        top = np.argsort(-caidas[i])[:k]
        out.append("; ".join(f"{NOMBRES[FEATURES[j]]} ({caidas[i, j] / tot * 100:.0f}%)" for j in top if caidas[i, j] / tot >= 0.10))
    return out


def backtest(feat: pl.DataFrame, ultima_sem: int, semanas: int = C.SEMANAS_BACKTEST, semilla: int = C.SEMILLA) -> list:
    """Walk-forward: para cada semana t reciente entrena SOLO con semanas < t, puntúa t, y compara con el modelo
    de la semana anterior sobre las mismas filas. Métricas sin etiquetas: alertas, concordancia con el detector
    estadístico (Jaccard) y estabilidad de ranking (correlación de Spearman entre modelos consecutivos)."""
    res, previo = [], None
    for t in range(ultima_sem - semanas + 1, ultima_sem + 1):
        try:
            m = entrenar(feat, t - 1, semilla=semilla)
        except ValueError:
            continue
        fila_t = elegibles(feat, C.HISTORIA_MIN).filter(pl.col("sem") == t)
        if fila_t.is_empty():
            continue
        p = puntuar(m["obj"], fila_t)
        est = ((p["zr8"].abs() >= C.ZR_UMBRAL) & ((p["real"] - p["med8"]).abs() >= m["obj"]["piso"])).to_numpy()
        al = p["alerta"].to_numpy()
        union = int((al | est).sum())
        fila = {"sem": int(t), "filas": int(p.height), "alertas": int(al.sum()), "tasa_alertas": float(al.mean()),
                "alertas_estadistico": int(est.sum()), "jaccard_vs_estadistico": float((al & est).sum() / union) if union else None,
                "spearman_vs_modelo_previo": None}
        if previo is not None:
            s_prev = pd.Series(puntuar(previo, fila_t)["score"].to_numpy()).rank()
            fila["spearman_vs_modelo_previo"] = float(s_prev.corr(pd.Series(p["score"].to_numpy()).rank()))
        previo = m["obj"]
        res.append(fila)
    return res
