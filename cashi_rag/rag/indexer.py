# -*- coding: utf-8 -*-
"""
rag/indexer.py — Indexador semántico local para el Dashboard Vista Territorio

Indexa:
- Documentos Markdown (.md)
- Código Python (.py)
- Metadatos de catálogos y esquemas
- Reglas de negocio y linaje
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(__file__).parent.parent.resolve()
INDEX_FILE = BASE_DIR / "rag" / "index_store.json"
INDEX_FILE.parent.mkdir(exist_ok=True)


def tokenize(text: str) -> List[str]:
    text = text.lower()
    words = re.findall(r"\b[a-z0-9_áéíóúñ]+\b", text)
    return [w for w in words if len(w) > 1]


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


def chunk_python(content: str, file_path: str) -> List[Dict[str, Any]]:
    chunks = []
    lines = content.splitlines()
    current_func = "modulo"
    current_lines = []
    start_line = 1

    for idx, line in enumerate(lines, 1):
        if line.strip().startswith("def ") or line.strip().startswith("class "):
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    chunks.append({
                        "file": file_path,
                        "heading": current_func,
                        "start_line": start_line,
                        "end_line": idx - 1,
                        "type": "python",
                        "content": text
                    })
                current_lines = []
            current_func = line.strip().split("(")[0].replace("def ", "").replace("class ", "").strip()
            start_line = idx
        current_lines.append(line)

    if current_lines:
        text = "\n".join(current_lines).strip()
        if text:
            chunks.append({
                "file": file_path,
                "heading": current_func,
                "start_line": start_line,
                "end_line": len(lines),
                "type": "python",
                "content": text
            })

    return chunks


def build_index():
    print("[RAG Indexer] Indexando codebase y documentación...", flush=True)
    all_chunks = []

    # Recorrer archivos .md y .py
    for root, _, files in os.walk(BASE_DIR):
        rpath = Path(root)
        if any(ignored in rpath.parts for ignored in [".git", "__pycache__", ".tmp", "_ddb_tmp", "aggs", "_respaldo"]):
            continue

        for file in files:
            file_path = rpath / file
            rel_path = file_path.relative_to(BASE_DIR).as_posix()

            if file.endswith(".md"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    all_chunks.extend(chunk_markdown(content, rel_path))
                except Exception as e:
                    print(f"  [error] {rel_path}: {e}")
            elif file.endswith(".py"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    all_chunks.extend(chunk_python(content, rel_path))
                except Exception as e:
                    print(f"  [error] {rel_path}: {e}")

    # Calcular frecuencias e índice BM25 / TF-IDF
    doc_freqs = Counter()
    indexed_chunks = []

    for idx, ch in enumerate(all_chunks):
        tokens = tokenize(ch["content"])
        tf = Counter(tokens)
        for t in set(tokens):
            doc_freqs[t] += 1
        ch["id"] = idx
        ch["tokens"] = tf
        indexed_chunks.append(ch)

    store = {
        "num_docs": len(indexed_chunks),
        "doc_freqs": dict(doc_freqs),
        "chunks": indexed_chunks
    }

    INDEX_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[RAG Indexer] Completado: {len(indexed_chunks)} fragmentos indexados en `{INDEX_FILE}`.", flush=True)


if __name__ == "__main__":
    build_index()
