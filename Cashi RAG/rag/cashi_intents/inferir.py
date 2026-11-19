# -*- coding: utf-8 -*-
"""
rag/cashi_intents/inferir.py — Uso en producción del clasificador de intención.

`predecir(texto)` devuelve (intención, probabilidad) o None si el modelo no existe o
no carga. Cashi lo usa como respaldo: solo cambia la ruta cuando las reglas dejaron la
consulta en una ruta genérica y el clasificador está seguro.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional, Tuple

import joblib

from rag.cashi_intents.entrenar import SALIDA, normalizar_consulta

log = logging.getLogger(__name__)
UMBRAL_CONFIANZA = 0.6


@lru_cache(maxsize=1)
def _cargar():
    if not SALIDA.exists():
        return None
    try:
        return joblib.load(SALIDA)
    except Exception as e:  # sin modelo válido, Cashi sigue con sus reglas
        log.warning("cashi_intents: no se pudo cargar %s (%s)", SALIDA, e)
        return None


@lru_cache(maxsize=512)
def predecir(texto: str) -> Optional[Tuple[str, float]]:
    d = _cargar()
    if d is None or not texto or not texto.strip():
        return None
    modelo = d["modelo"]
    probs = modelo.predict_proba([normalizar_consulta(texto)])[0]
    i = int(probs.argmax())
    return modelo.classes_[i], float(probs[i])
