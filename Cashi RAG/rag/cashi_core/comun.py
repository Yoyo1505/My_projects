# -*- coding: utf-8 -*-
"""
rag/cashi_core/comun.py â€” (antes en financial_rag.py) Constantes y helpers del motor Cashi.
Motor RAG Unificado 'Cashi' Avanzado (Financiero + Documental + AnalÃ­tico)
VersiÃ³n Multi-Plano Multi-Dimensional con Insensibilidad a PuntuaciÃ³n, Formateo Contable Estricto y Streaming PyArrow.

Soporta:
- Insensibilidad total a puntuaciÃ³n (re.sub) y acentos (unicodedata NFKD).
- Mapeo exhaustivo de CECOs (con y sin ceros a la izquierda), PDC/PDV, Cuentas, Grupos, Divisiones, Territorios.
- Motor de AgrupaciÃ³n Multi-Dimensional DinÃ¡mica (ej. "gasto por territorio por semana", "gasto por divisiÃ³n por mes", "gasto por ceco por semana").
- Grafos / Planos:
  * Plano 1 (Contable): Grupo de Cuentas -> Cuentas -> PosPre
  * Plano 2 (Territorial): DivisiÃ³n -> Territorio -> PDC -> CECO
  * Plano 3 (Temporal & Series): AÃ±o -> Trimestre -> Mes -> Semana & Serie (R25, R26, P26, NVO)
  * Plano 4 (Servicios): ID Servicio -> Servicio -> Cuentas
- EjecuciÃ³n DuckDB vectorizada con PyArrow Zero-Copy streaming (`fetch_arrow_table`).
- TelemetrÃ­a y Linaje de Datos (SQL ejecutado, tiempo ms, filas procesadas, origen parquet).
"""
from __future__ import annotations

import json
import math
import os
import re
import time
import unicodedata
from difflib import SequenceMatcher

try:  # Resolvedor ML de entidades (rag/cashi_ml); si falla, Cashi usa solo el mapa de tokens
    from rag.cashi_ml.inferir import ajustar_con_mapa, alternativas_para_boton
except Exception:  # pragma: no cover
    def ajustar_con_mapa(_texto, mapa):
        return dict(mapa), [], []

    def alternativas_para_boton(_texto, _incierta, maximo=3):
        return []
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import duckdb
import polars as pl
import pandas as pd
from rag.query import LocalRAG

UMBRAL_INTENCION_ML = 0.6  # confianza mÃ­nima del clasificador de intenciÃ³n para cambiar la ruta

try:  # LÃ©xico de sinÃ³nimos (rag/lexico); si falla, la consulta sigue sin canonizar
    from rag.lexico import canonizar as _canonizar
except Exception:  # pragma: no cover
    def _canonizar(texto):
        return texto

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
AGGS_DIR = BASE_DIR / "aggs"
CONS_PATH = AGGS_DIR / "_consolidado.parquet"
DDB_PATH = AGGS_DIR / "dashboard.duckdb"
META_PATH = AGGS_DIR / "_meta.json"

STOP_WORDS = {
    "de", "del", "por", "en", "el", "la", "los", "las", "un", "una", "unos", "unas",
    "al", "con", "para", "sin", "sobre", "tras", "vs", "a", "o", "y", "que", "se", "es"
}

# Palabras del vocabulario financiero/temporal tan comunes en el catÃ¡logo o en
# cualquier pregunta de negocio que NO sirven para distinguir una entidad de
# otra en `mejor_entidad`. "gasto"/"gastos" aparece en ~40% de los nombres de
# Grupo de Cuentas/Cuenta ("Gastos de NÃ³mina", "Gastos Extraordinarios"...);
# "ano" (aÃ±o sin acento tras normalizar) es parte normal de casi cualquier
# pregunta temporal y solo coincide por accidente con la cuenta "Gastos de
# Fin de AÃ±o". Sin esto, preguntas genÃ©ricas disparan sugerencias falsas.
PALABRAS_GENERICAS_CATALOGO = {"gasto", "gastos", "ano", "anos"}

# Vocabulario de dimensiones para desgloses ("... por territorio", "desglosado por zona").
# Solo el lÃ©xico de la dimensiÃ³n (singular, plural, sinÃ³nimos); la pregunta completa no
# se enumera. Texto ya normalizado (sin acentos ni mayÃºsculas).
_TERMINOS_DIMENSION = {
    "zona": "zona", "zonas": "zona",
    "region": "region", "regiones": "region",
    "territorio": "territorio", "territorios": "territorio",
    "division": "division", "divisiones": "division",
    "grupo de cuentas": "grupo_cuentas", "grupos de cuentas": "grupo_cuentas",
    "grupo": "grupo_cuentas", "grupos": "grupo_cuentas",
    "cuenta": "cuenta", "cuentas": "cuenta",
    "ceco": "ceco", "cecos": "ceco", "centro de costo": "ceco", "centros de costo": "ceco",
    "pdc": "pdc", "pdcs": "pdc", "pdv": "pdc", "pdvs": "pdc",
    "agrupador de reales": "agrupador_reales", "agrupadores de reales": "agrupador_reales",
    "semana": "semana", "semanas": "semana",
    "mes": "mes", "meses": "mes",
}
# Adjetivos de desglose temporal que no llevan preposiciÃ³n ("gasto semanal", "gasto mensual")
_ADJ_DIMENSION = {"semanal": "semana", "mensual": "mes"}
_ORDEN_DIMENSIONES = ["zona", "region", "territorio", "division", "grupo_cuentas", "cuenta",
                      "ceco", "pdc", "agrupador_reales", "semana", "mes"]
_RE_DIMENSION = re.compile(
    r"\b(?:por|cada|desglos\w*(?: por)?)\s+(?:(?:cada|la|el|los|las)\s+)?("
    + "|".join(sorted(map(re.escape, _TERMINOS_DIMENSION), key=len, reverse=True)) + r")\b"
)
_RE_ADJ_DIMENSION = re.compile(r"\b(" + "|".join(_ADJ_DIMENSION) + r")\b")
# Pedido de listado: "dame las zonas en el territorio X", "dame los territorios de la
# divisiÃ³n Y", "cuÃ¡ntas zonas hay en...". El tÃ©rmino va tras un verbo de pedido o un
# artÃ­culo plural/cuÃ¡ntos, y seguido de un conector o del fin de la frase. "gasto de la
# divisiÃ³n norte" NO entra: ahÃ­ el tÃ©rmino solo nombra el filtro.
_RE_LISTADO_DIMENSION = re.compile(
    r"(?:^|\b(?:dame|muestrame|dime|lista|listame|cuales|que|cuantos|cuantas|las|los)\s+)("
    + "|".join(sorted(map(re.escape, _TERMINOS_DIMENSION), key=len, reverse=True))
    + r")\s*(?=en\b|de\b|del\b|hay\b|tiene\b|tienen\b|$)"
)
# "dame el gasto para los territorios de la division norte": plural tras para/de + artículo.
_RE_PLURAL_DIMENSION = re.compile(
    r"\b(?:para|de)\s+(?:los|las)\s+("
    + "|".join(sorted((map(re.escape, (t for t in _TERMINOS_DIMENSION if t.endswith("s")))), key=len, reverse=True))
    + r")\s+(?:de|del|en)\b"
)


_NUM_UNIDADES = {"uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
                 "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13,
                 "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18,
                 "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintidos": 22, "veintitres": 23,
                 "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27,
                 "veintiocho": 28, "veintinueve": 29}
_NUM_DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70,
                "ochenta": 80, "noventa": 90}


def _numeros_a_digitos(norm_query: str) -> str:
    """'cinco' -> '5', 'treinta y dos' -> '32' (0-99). Texto ya normalizado."""
    def _decena(m):
        u = m.group(2)
        return str(_NUM_DECENAS[m.group(1)] + (_NUM_UNIDADES[u] if u else 0))
    t = re.sub(r"\b(treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa)"
               r"(?:\s+y\s+(uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve))?\b", _decena, norm_query)
    return re.sub(r"\b(" + "|".join(sorted(_NUM_UNIDADES, key=len, reverse=True)) + r")\b",
                  lambda m: str(_NUM_UNIDADES[m.group(1)]), t)


# Columna de agrupaciÃ³n de cada dimensiÃ³n de variaciÃ³n: (expresiÃ³n SQL, alias, filtro de NULL)
VAR_DIM_COLUMNAS = {
    "ceco": ("ID_CENTRO_COSTOS", "CECO", "AND ID_CENTRO_COSTOS IS NOT NULL"),
    "pdc": ("ECO_PDV", "PDV", "AND ECO_PDV IS NOT NULL AND ECO_PDV != 0"),
    "cuenta": ("cat_Cuentas", "Cuenta", "AND cat_Cuentas IS NOT NULL AND cat_Cuentas != '0'"),
    "grupo_cuentas": ("cat_Grupo_de_Cuentas", "Grupo_Cuentas", "AND cat_Grupo_de_Cuentas IS NOT NULL"),
    "division": ("cat_Direccion_Division", "Division", "AND cat_Direccion_Division IS NOT NULL"),
    "territorio": ("COALESCE(NULLIF(cat_Subdireccion_Territorio, '0'), cat_Direccion_Division)", "Territorio", ""),
    "zona": ("COALESCE(NULLIF(cat_Subdireccion_Zona, '0'), 'No Clasificado')", "Zona", ""),
    "region": ("COALESCE(NULLIF(cat_Subdireccion_Region, '0'), 'No Clasificado')", "Region", ""),
}


def _leer_top_n(norm_query: str, por_defecto: int = 10) -> int:
    """CuÃ¡ntos resultados pide la pregunta: "los 5 cecos", "top 3", "5 pdv". Acotado a 1..50."""
    m = (re.search(r"\b(?:top|los|las)\s+(\d{1,3})\b", norm_query)
         or re.search(r"\b(\d{1,3})\s+(?:cecos?|pdvs?|centros|cuentas|grupos|divisiones|territorios)\b", norm_query))
    if not m:
        return por_defecto
    return max(1, min(50, int(m.group(1))))


def _detectar_dimensiones(norm_query: str) -> List[str]:
    """Dimensiones pedidas para desglosar (en orden canÃ³nico), leÃ­das de la pregunta
    normalizada: 'por <tÃ©rmino>', 'desglosado por <tÃ©rmino>', 'semanal' y listados
    ('dame las zonas en ...')."""
    encontradas = {_TERMINOS_DIMENSION[m] for m in _RE_DIMENSION.findall(norm_query)}
    encontradas |= {_TERMINOS_DIMENSION[m] for m in _RE_LISTADO_DIMENSION.findall(norm_query)}
    encontradas |= {_TERMINOS_DIMENSION[m] for m in _RE_PLURAL_DIMENSION.findall(norm_query)}
    encontradas |= {_ADJ_DIMENSION[m] for m in _RE_ADJ_DIMENSION.findall(norm_query)}
    return [d for d in _ORDEN_DIMENSIONES if d in encontradas]

def normalizar_texto(texto: str) -> str:
    """Normaliza texto eliminando acentos, puntuaciÃ³n y espacios redundantes."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    cadena = "".join([c for c in nfkd if not unicodedata.combining(c)])
    cadena = re.sub(r"[^\w\s]", " ", cadena)
    return " ".join(cadena.lower().split())

def token_match(key_norm: str, query_norm: str) -> bool:
    """Coincidencia de tokens tolerante a puntuaciÃ³n y variaciones."""
    if not key_norm or not query_norm or len(key_norm.strip()) < 2:
        return False
    if key_norm in ("0", "null", "none", "sin"):
        return False
    if key_norm in query_norm or query_norm in key_norm:
        return True
    key_tokens = [t for t in re.findall(r"\w+", key_norm) if t not in STOP_WORDS and len(t) > 2]
    query_tokens = [t for t in re.findall(r"\w+", query_norm) if t not in STOP_WORDS and len(t) > 2]
    if not key_tokens or not query_tokens:
        return False
    matches = 0
    for kt in key_tokens:
        kt_stem = kt.rstrip("s")
        if any(kt_stem == qt.rstrip("s") or kt_stem in qt for qt in query_tokens):
            matches += 1
    return (matches / len(key_tokens)) >= 0.65


# Umbral para APLICAR un match fuzzy como filtro real de la consulta SQL.
# 0.85 (no 0.65): un match parcial dÃ©bil sin competencia (p.ej. 2 de 3
# tokens) ya NO se usa a ciegas para filtrar â€” ver UMBRAL_SUGERENCIA abajo.
UMBRAL_AUTO_APLICAR = 0.85
# Umbral mÃ­nimo para OFRECER un candidato como "Â¿quisiste decir...?" sin
# aplicarlo como filtro. Por debajo de esto se considera ruido y se ignora.
UMBRAL_SUGERENCIA = 0.45


def mejor_entidad(mapa: Dict[str, str], norm_query: str) -> Tuple[Optional[str], int, List[Tuple[str, float]]]:
    """Mejor coincidencia de `mapa` (catÃ¡logo normalizado -> valor real) contra `norm_query`.

    Devuelve (valor, tier, candidatos):
      tier 2 = substring exacto en cualquier direcciÃ³n, o coincidencia fuzzy que
               cubre TODOS los tokens distintivos de la clave (alta confianza).
      tier 1 = coincidencia fuzzy fuerte (ratio >= UMBRAL_AUTO_APLICAR, <1.0) â€”
               se aplica como filtro salvo que otro tipo de entidad logre tier 2
               en la misma consulta (ver `_parse_nlu`), para evitar que un
               nombre de PDC/cuenta largo que comparte palabras genÃ©ricas
               (p.ej. "division", "norte") con la consulta gane por accidente
               sobre la coincidencia real y mÃ¡s especÃ­fica.
      tier 0 = sin match aplicable. `candidatos` trae hasta 3 valores con
               UMBRAL_SUGERENCIA <= ratio < UMBRAL_AUTO_APLICAR â€” demasiado
               dÃ©biles para usarse como filtro silencioso, pero suficientes
               para ofrecerlos como sugerencia ("Â¿quisiste decir...?") en vez
               de adivinar o de responder con el consolidado global sin avisar.
    """
    mejor_valor, mejor_tier, mejor_ratio = None, 0, 0.0
    candidatos: List[Tuple[str, float]] = []
    # len(t) >= 2 (no > 2): abreviaturas de 2 letras como "Ch"/"Sb"/"Ru" que
    # aparecen en nombres de PDC SÃ deben contar como token distintivo â€” si se
    # descartan, un nombre como "Territorio Ch Centro" reduce sus tokens a
    # ["territorio", "centro"], que logran cobertura 100% (tier 2) contra
    # cualquier consulta que solo diga "territorio centro", generando un falso
    # positivo con un PDC que nadie mencionÃ³.
    query_tokens = [t for t in re.findall(r"\w+", norm_query)
                    if t not in STOP_WORDS and t not in PALABRAS_GENERICAS_CATALOGO and len(t) >= 2]

    for key_norm, valor in mapa.items():
        if not key_norm or len(key_norm.strip()) < 2 or key_norm in ("0", "null", "none", "sin"):
            continue
        if key_norm in norm_query or norm_query in key_norm:
            return valor, 2, []

        key_tokens = [t for t in re.findall(r"\w+", key_norm)
                      if t not in STOP_WORDS and t not in PALABRAS_GENERICAS_CATALOGO and len(t) >= 2]
        if not key_tokens or not query_tokens:
            continue

        matches = 0
        for kt in key_tokens:
            kt_stem = kt.rstrip("s")
            if len(kt_stem) <= 3:
                # Tokens cortos (abreviaturas tipo "ch"/"sb", o palabras
                # comunes de 3 letras): solo igualdad exacta. La comprobaciÃ³n
                # "estÃ¡ contenido en" de abajo es demasiado permisiva para
                # cadenas cortas â€” "no" aparece como substring de "alguno"
                # por pura coincidencia y generaba sugerencias falsas.
                encontrado = any(kt_stem == qt.rstrip("s") for qt in query_tokens)
            else:
                encontrado = any(kt_stem == qt.rstrip("s") or kt_stem in qt for qt in query_tokens)
            if encontrado:
                matches += 1

        ratio = matches / len(key_tokens)
        if ratio >= 0.999:
            return valor, 2, []  # cobertura total de tokens = tan confiable como un substring exacto
        if ratio >= UMBRAL_AUTO_APLICAR:
            if ratio > mejor_ratio:
                mejor_valor, mejor_tier, mejor_ratio = valor, 1, ratio
        elif ratio >= UMBRAL_SUGERENCIA:
            candidatos.append((valor, ratio))

    candidatos.sort(key=lambda x: x[1], reverse=True)
    return mejor_valor, mejor_tier, candidatos[:3]

def fuzzy_match_typo(cadena: str, candidatos_dict: Dict[str, str], umbral: float = 0.75) -> Optional[str]:
    """Fuzzy matching tolerante a typos: busca mejor coincidencia de palabras.
    Prioriza candidatos con palabras coincidentes exactas, luego fuzzy matching."""
    mejor_match = None
    mejor_ratio = 0.0
    mejor_exactas = 0

    cadena_tokens = [t for t in re.findall(r"\w+", cadena) if len(t) >= 2]
    if not cadena_tokens:
        return None

    for key_norm, valor in candidatos_dict.items():
        if not key_norm or len(key_norm.strip()) < 2:
            continue

        key_tokens = [t for t in re.findall(r"\w+", key_norm) if len(t) >= 2]
        if not key_tokens:
            continue

        # Contar coincidencias exactas (prioridad)
        exactas = sum(1 for ct in cadena_tokens if ct in key_tokens)

        # Calcular ratio fuzzy para palabras que NO coinciden exactamente
        fuzzy_ratios = []
        for ct in cadena_tokens:
            if ct in key_tokens:
                fuzzy_ratios.append(1.0)  # match exacto
            else:
                best_token_ratio = max(
                    (SequenceMatcher(None, ct, kt).ratio() for kt in key_tokens),
                    default=0.0
                )
                fuzzy_ratios.append(best_token_ratio)

        ratio = sum(fuzzy_ratios) / len(fuzzy_ratios) if fuzzy_ratios else 0.0

        # Priorizar por exactas, luego por ratio
        es_mejor = (exactas > mejor_exactas) or (exactas == mejor_exactas and ratio > mejor_ratio)
        if es_mejor:
            mejor_exactas = exactas
            mejor_ratio = ratio
            mejor_match = valor

    return mejor_match if mejor_ratio >= umbral else None

def M(v: float | int | None) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "â€”"
    return f"{v / 1e6:,.2f} MDP"


__all__ = [n for n in list(globals()) if not n.startswith('__')]

