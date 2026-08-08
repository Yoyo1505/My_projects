# -*- coding: utf-8 -*-
"""
rag/query.py — Buscador e interfaz de consulta RAG para el Dashboard Vista Territorio
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(__file__).parent.parent.resolve()
INDEX_FILE = BASE_DIR / "rag" / "index_store.json"


def tokenize(text: str) -> List[str]:
    text = text.lower()
    words = re.findall(r"\b[a-z0-9_áéíóúñ]+\b", text)
    return [w for w in words if len(w) > 1]


class LocalRAG:
    def __init__(self):
        if not INDEX_FILE.exists():
            self.store = None
        else:
            self.store = json.loads(INDEX_FILE.read_text(encoding="utf-8"))

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.store:
            return [{"error": "El índice RAG no ha sido construido. Ejecute `python rag/indexer.py`."}]

        tokens = tokenize(query)
        if not tokens:
            return []

        num_docs = self.store["num_docs"]
        doc_freqs = self.store["doc_freqs"]
        chunks = self.store["chunks"]

        scores = []
        for ch in chunks:
            score = 0.0
            tf_dict = ch["tokens"]
            doc_len = sum(tf_dict.values()) or 1

            for t in tokens:
                if t in tf_dict:
                    tf = tf_dict[t]
                    df = doc_freqs.get(t, 1)
                    idf = math.log((num_docs + 1) / (df + 0.5)) + 1.0
                    score += (tf / doc_len) * idf

            if score > 0:
                scores.append((score, ch))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, ch in scores[:top_k]:
            results.append({
                "score": round(score, 4),
                "file": ch["file"],
                "heading": ch["heading"],
                "start_line": ch["start_line"],
                "end_line": ch["end_line"],
                "type": ch["type"],
                "snippet": ch["content"][:400] + ("..." if len(ch["content"]) > 400 else "")
            })

        return results


def ask(query: str, top_k: int = 3) -> str:
    rag = LocalRAG()
    results = rag.search(query, top_k=top_k)

    if not results or "error" in results[0]:
        return results[0].get("error", "No se encontraron resultados relevantes.") if results else "Sin coincidencias."

    output = [f"### Resultados RAG para: '{query}'\n"]
    for i, r in enumerate(results, 1):
        output.append(f"**{i}. [{r['file']}]({r['file']}#L{r['start_line']}-L{r['end_line']})** — `{r['heading']}` (Score: {r['score']})")
        output.append("```" + r["type"])
        output.append(r["snippet"])
        output.append("```\n")

    return "\n".join(output)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "medidas variaciones formula real 2026"
    print(ask(q))
