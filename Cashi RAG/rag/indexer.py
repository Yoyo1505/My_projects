# -*- coding: utf-8 -*-
"""
rag/indexer.py — Indexador BM25 de la base de conocimiento de Cashi

Indexa ÚNICAMENTE los .md de `rag/conocimiento/` (datos de gasto, estructura,
tipos de consulta). Nada más del proyecto se indexa.

NO indexa código Python (.py) ni documentación técnica/de arquitectura del
proyecto: Cashi es un asistente de consulta de datos financieros, no debe
poder citar ni exponer código fuente o documentación interna del sistema a
través de la ruta "documental" del chat. Por eso, además de .py, se excluyen
explícitamente las carpetas de documentación técnica (`documentacion`, `docs`,
`agentes_auditoria`, `.ai_council`) — ver EXCLUIR_CARPETAS.

Excluye estrictamente:
- Código Python (.py) — nunca se indexa, sin excepción.
- Carpetas de documentación técnica/de código: documentacion, docs,
  agentes_auditoria, .ai_council.
- Carpetas de respaldo (_backup_*, _respaldo*, respaldos)
- Entornos virtuales, .git, __pycache__, .tmp, _ddb_tmp
- Archivos Parquet, aggs, aggs_versiones, logs y el propio index_store.json
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(__file__).parent.parent.resolve()
INDEX_FILE = BASE_DIR / "rag" / "index_store.json"
# Solo se indexa la base de conocimiento de Cashi. Antes se recorría TODO el
# proyecto y Cashi citaba bitácoras y auditorías internas (MIGRACION_DASH_*.md,
# PARIDAD_*.md) como "evidencia" de preguntas de datos (2026-09-30).
RAIZ_INDEXADA = BASE_DIR / "rag" / "conocimiento"

# Diccionario de Sinónimos para Expansión
SINONIMOS = {
    "ceco": ["centro_de_costos", "ceco", "centro_costo", "centro_costos"],
    "centro_de_costos": ["ceco", "centro_costo", "centro_costos"],
    "pdc": ["punto_de_contacto", "pdc"],
    "punto_de_contacto": ["pdc", "punto_de_contacto"],
    "pdv": ["punto_de_venta", "pdv", "tienda", "sucursal"],
    "punto_de_venta": ["pdv", "punto_de_venta", "tienda"],
    "plan": ["presupuesto", "plan", "p26"],
    "presupuesto": ["plan", "presupuesto", "p26"],
    "real": ["ejercido", "real", "gasto", "r26", "r25"],
    "ejercido": ["real", "ejercido", "gasto"],
    "forecast": ["proyeccion", "forecast", "estimado"],
    "proyeccion": ["forecast", "proyeccion", "estimado"],
    "variacion": ["desviacion", "diferencia", "variacion", "delta", "sobreconsumo"],
    "desviacion": ["variacion", "desviacion", "sobregasto", "sobreconsumo"],
    "anomalia": ["atipico", "anomalia", "outlier", "irregularidad"],
}

# Carpetas y patrones a excluir
EXCLUIR_CARPETAS = {
    ".git", "__pycache__", ".tmp", "_ddb_tmp", "aggs", "aggs_versiones",
    "respaldos", "_respaldo", "node_modules", ".venv", "venv", "env", "logs",
    ".gemini", "brain", "scratch", ".system_generated",
    # Documentación técnica/de código del proyecto: Cashi no debe poder citarla.
    "documentacion", "docs", "agentes_auditoria", ".ai_council",
}


def es_ruta_excluida(rel_path: str) -> bool:
    parts = rel_path.lower().split("/")
    for p in parts:
        if p in EXCLUIR_CARPETAS:
            return True
        if p.startswith("_backup_") or p.startswith("_respaldo"):
            return True
    return False


def tokenize(text: str) -> List[str]:
    """Tokeniza y normaliza texto eliminando acentos y caracteres especiales."""
    text = text.lower()
    # Normalización básica de caracteres españoles
    remap = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for k, v in remap.items():
        text = text.replace(k, v)
    words = re.findall(r"\b[a-z0-9_]+\b", text)
    return [w for w in words if len(w) > 1]


def expand_tokens(tokens: List[str]) -> List[str]:
    """Agrega sinónimos a los tokens para mejorar cobertura del RAG."""
    expanded = list(tokens)
    for t in tokens:
        if t in SINONIMOS:
            expanded.extend(SINONIMOS[t])
    return expanded


def chunk_markdown(content: str, file_path: str) -> List[Dict[str, Any]]:
    chunks = []
    lines = content.splitlines()
    current_heading = "General"
    current_lines = []
    start_line = 1

    for idx, line in enumerate(lines, 1):
        if line.startswith("#"):
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    chunks.append({
                        "file": file_path,
                        "heading": current_heading,
                        "start_line": start_line,
                        "end_line": idx - 1,
                        "type": "markdown",
                        "content": text
                    })
                current_lines = []
            current_heading = line.lstrip("#").strip()
            start_line = idx
        current_lines.append(line)

    if current_lines:
        text = "\n".join(current_lines).strip()
        if text:
            chunks.append({
                "file": file_path,
                "heading": current_heading,
                "start_line": start_line,
                "end_line": len(lines),
                "type": "markdown",
                "content": text
            })

    return chunks


def index_esta_desactualizado() -> bool:
    """True si el índice no existe, o si algún .md/.py indexable se modificó
    después de la última reconstrucción — permite reconstruir el índice solo
    cuando hace falta (ver `LocalRAG.__init__` en rag/query.py) en vez de
    depender de que alguien recuerde correr `python rag/indexer.py` a mano
    tras editar documentación o código."""
    if not INDEX_FILE.exists():
        return True
    index_mtime = INDEX_FILE.stat().st_mtime

    for root, _, files in os.walk(RAIZ_INDEXADA):
        rpath = Path(root)
        try:
            rel_root = rpath.relative_to(BASE_DIR).as_posix()
        except ValueError:
            continue
        if es_ruta_excluida(rel_root):
            continue
        for file in files:
            if not file.endswith(".md"):
                continue
            file_path = rpath / file
            rel_file = file_path.relative_to(BASE_DIR).as_posix()
            if es_ruta_excluida(rel_file):
                continue
            try:
                if file_path.stat().st_mtime > index_mtime:
                    return True
            except OSError:
                continue
    return False


def build_index():
    print("[RAG Indexer] Indexando documentación de datos (.md)...", flush=True)
    all_chunks = []

    for root, _, files in os.walk(RAIZ_INDEXADA):
        rpath = Path(root)
        try:
            rel_root = rpath.relative_to(BASE_DIR).as_posix()
        except ValueError:
            continue

        if es_ruta_excluida(rel_root):
            continue

        for file in files:
            if file.endswith(".parquet") or file == "index_store.json":
                continue

            file_path = rpath / file
            rel_file = file_path.relative_to(BASE_DIR).as_posix()

            if es_ruta_excluida(rel_file):
                continue

            if file.endswith(".md"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    all_chunks.extend(chunk_markdown(content, rel_file))
                except Exception as e:
                    print(f"  [Error MD] {rel_file}: {e}")

    # Calcular estadísticas BM25
    doc_freqs = Counter()
    total_len = 0
    indexed_chunks = []

    for idx, ch in enumerate(all_chunks):
        toks = tokenize(ch["content"] + " " + ch["heading"])
        toks_expanded = expand_tokens(toks)
        tf = Counter(toks_expanded)

        doc_len = len(toks)
        total_len += doc_len

        for t in set(toks_expanded):
            doc_freqs[t] += 1

        ch["id"] = idx
        ch["doc_len"] = doc_len
        ch["tokens"] = dict(tf)
        indexed_chunks.append(ch)

    num_docs = len(indexed_chunks)
    avgdl = (total_len / num_docs) if num_docs > 0 else 1.0

    store = {
        "num_docs": num_docs,
        "avgdl": avgdl,
        "doc_freqs": dict(doc_freqs),
        "chunks": indexed_chunks
    }

    INDEX_FILE.parent.mkdir(exist_ok=True)
    INDEX_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[RAG Indexer] ¡Éxito! {num_docs} fragmentos indexados con BM25 en `{INDEX_FILE.name}`.", flush=True)


if __name__ == "__main__":
    build_index()
