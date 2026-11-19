# -*- coding: utf-8 -*-
"""
rag/lexico — Léxico de sinónimos de Cashi (datos en sinonimos.json, no código).

`canonizar(texto)` reemplaza cada variante por su término canónico, sobre texto ya
normalizado (sin acentos, minúsculas, sin puntuación). Las variantes más largas se
reemplazan primero y solo en límites de palabra, así "centros de costos" gana sobre
"costos". Si el archivo no existe o no se puede leer, el texto pasa tal cual.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

RUTA = Path(__file__).with_name("sinonimos.json")
log = logging.getLogger(__name__)


def _normalizar(s: str) -> str:
    # Misma normalización que financial_rag.normalizar_texto (sin importarlo para evitar ciclos)
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", str(s))
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", sin_acentos).lower().split())


@lru_cache(maxsize=1)
def _reglas():
    try:
        datos = json.loads(RUTA.read_text(encoding="utf-8"))
    except Exception as e:  # sin léxico válido, Cashi sigue igual
        log.warning("cashi lexico: no se pudo leer %s (%s)", RUTA, e)
        return []
    pares = []
    for canonico, variantes in datos.items():
        if canonico.startswith("_") or not isinstance(variantes, list):
            continue
        for v in variantes:
            vn = _normalizar(v)
            if vn and vn != canonico:
                pares.append((vn, canonico))
    # las variantes largas primero, para que "centros de costos" gane sobre "costos"
    pares.sort(key=lambda p: len(p[0]), reverse=True)
    return [(re.compile(rf"(?<!\w){re.escape(v)}(?!\w)"), c) for v, c in pares]


def canonizar(texto_normalizado: str) -> str:
    """Texto normalizado -> texto con variantes reemplazadas por su término canónico."""
    salida = texto_normalizado
    for patron, canonico in _reglas():
        salida = patron.sub(canonico, salida)
    return salida
