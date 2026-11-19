# -*- coding: utf-8 -*-
"""
rag/cashi_ml/inferir.py — Uso en producción del resolvedor de entidades de Cashi.

Lo llama `financial_rag.py` (motor de Cashi) en Streamlit y en DASH APP. Carga una sola
vez `aggs\\cashi_ml\\entidades.joblib` (lo genera `entrenar.py`). Si el modelo no existe,
devuelve None y Cashi sigue con su lógica anterior: nunca rompe una consulta.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import joblib

from rag.cashi_ml.entrenar import normalizar, resolver, tokens

MODELO = Path(__file__).resolve().parents[2] / "aggs" / "cashi_ml" / "entidades.joblib"
log = logging.getLogger(__name__)

# Una entidad aplicada por el modelo se marca como incierta si:
#   - su probabilidad está por debajo de UMBRAL_INCIERTA, o
#   - otra opción del catálogo (de nombre distinto) tiene probabilidad >= UMBRAL_ALTERNATIVA.
# Cashi responde con la mejor opción y ofrece otras tres como botones.
UMBRAL_INCIERTA = 0.9
UMBRAL_ALTERNATIVA = 0.66   # el "66 %" de competencia del plan; calibrado con gold/holdout

# Palabras de prefijo de catálogo ("Territorio Metro Norte" -> "metro norte")
_PREFIJOS_CATALOGO = {"territorio", "division", "staff", "subdireccion", "direccion", "dir",
                      "zona", "region", "contraloria"}


def tokens_entidad(texto: str) -> list[str]:
    return [t for t in tokens(texto or "") if t not in _PREFIJOS_CATALOGO]


@lru_cache(maxsize=1)
def _cargar():
    if not MODELO.exists():
        return None
    try:
        return joblib.load(MODELO)
    except Exception as e:  # sin modelo válido, Cashi sigue con el mapa de tokens
        log.warning("cashi_ml: no se pudo cargar %s (%s). Reentrena con "
                    "'python -m rag.cashi_ml'.", MODELO, e)
        return None


@lru_cache(maxsize=512)
def _resolver_cacheado(texto: str):
    d = _cargar()
    if d is None:
        return None
    ambiguas: tuple = ()
    ents = resolver(texto, d["indice"], d["ranker"], d["k"])
    vistas: dict = {}
    for e in ents:
        if e["decision"] == "unica":
            dim, canon = e["entidades"][0]
            vistas.setdefault(dim, (canon, e["span"], e["p"], tuple(e.get("alternativas", []))))
        elif e["decision"] == "ambigua" and not ambiguas:
            ambiguas = tuple(e["entidades"])
    return {"unicas": tuple((dim, v[0]) for dim, v in vistas.items()),
            "spans": tuple((dim, v[1]) for dim, v in vistas.items()),
            "probs": tuple((dim, v[2]) for dim, v in vistas.items()),
            "alternativas": tuple((dim, v[3]) for dim, v in vistas.items()),
            "ambiguas": ambiguas}


def resolver_entidades(texto: str) -> Optional[dict]:
    """{'unicas', 'spans', 'probs', 'alternativas', 'ambiguas'} por dimensión.

    'unicas' son entidades seguras; 'ambiguas' son opciones entre las que Cashi debe
    preguntar (la misma frase cabe en dos dimensiones). None si el modelo no está.
    """
    if not texto or not texto.strip():
        return None
    r = _resolver_cacheado(texto.strip())
    if r is None:
        return None
    return {"unicas": dict(r["unicas"]), "spans": dict(r["spans"]),
            "probs": dict(r["probs"]), "alternativas": {d: list(a) for d, a in r["alternativas"]},
            "ambiguas": list(r["ambiguas"])}


_PALABRAS_SIN_ENTIDAD = {
    "gasto", "gastos", "costo", "costos", "total", "real", "para", "de", "del", "el", "la", "los",
    "las", "por", "en", "con", "dame", "dime", "cuanto", "cual", "que",
}


def ajustar_con_mapa(texto: str, mapa: dict) -> tuple[dict, list, list]:
    """Combina el mapa de tokens de Cashi con el resolvedor ML.

    mapa: {dimensión: valor canónico o None} como lo arma `_parse_nlu`.
    Devuelve (mapa ajustado, ambiguas, inciertas):
      - el ML completa las dimensiones que el mapa dejó vacías;
      - si una entidad del mapa es solo parte de una entidad ML más específica
        ("norte" de división dentro de "metro norte" de territorio), se descarta;
      - ambiguas: opciones para preguntar, solo si no hay ninguna otra entidad;
      - inciertas: entidades aplicadas por el ML con probabilidad < UMBRAL_INCIERTA,
        con sus alternativas (para mostrar botones).
    """
    ml = resolver_entidades(texto)
    out = dict(mapa)
    if not ml:
        return out, [], []
    spans, probs, alts = ml["spans"], ml["probs"], ml["alternativas"]
    inciertas = []
    for dim_ml, canon in ml["unicas"].items():
        # Un span hecho solo de palabras funcionales/genéricas ("gasto para") no nombra entidad.
        if set(spans.get(dim_ml, "").split()) <= _PALABRAS_SIN_ENTIDAD:
            continue
        ts = set(tokens_entidad(spans.get(dim_ml, "")))
        for dim_m, val in list(out.items()):
            if dim_m == dim_ml or not val:
                continue
            tv = set(tokens_entidad(val))
            if tv and tv <= ts:
                out[dim_m] = None
        if out.get(dim_ml) is None:
            out[dim_ml] = canon
            opciones = alts.get(dim_ml, [])
            competidora = opciones[0][2] if opciones else 0.0
            if probs.get(dim_ml, 1.0) < UMBRAL_INCIERTA or competidora >= UMBRAL_ALTERNATIVA:
                inciertas.append({"dim": dim_ml, "canon": canon, "span": spans.get(dim_ml, ""),
                                  "p": probs.get(dim_ml), "alternativas": opciones})
    amb = [] if any(out.values()) else ml["ambiguas"]
    return out, amb, inciertas


def reemplazar_entidad(texto: str, span: str, canon: str) -> Optional[str]:
    """Cambia mención (`span`, normalizada) del `texto` por `canon`. None si no la encuentra."""
    palabras = texto.split()
    objetivo = normalizar(span).split()
    n = len(objetivo)
    if not n:
        return None
    for i in range(len(palabras) - n + 1):
        if [normalizar(w) for w in palabras[i:i + n]] == objetivo:
            return " ".join(palabras[:i] + [canon] + palabras[i + n:])
    return None


def alternativas_para_boton(texto: str, incierta: dict, maximo: int = 3) -> list[dict]:
    """Opciones listas para botón: {'etiqueta', 'dim', 'query'} con la mención reemplazada."""
    salida = []
    for dim, canon, _p in incierta.get("alternativas", [])[:maximo]:
        nueva = reemplazar_entidad(texto, incierta.get("span", ""), canon)
        if nueva:
            salida.append({"etiqueta": canon, "dim": dim, "query": nueva})
    return salida

