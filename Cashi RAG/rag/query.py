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
    # Parámetros estándar de BM25 (Robertson/Sparck-Jones): k1 controla la
    # saturación de la frecuencia de término (más repeticiones de la misma
    # palabra suman cada vez menos), b controla cuánto penaliza a los
    # documentos más largos que el promedio. 1.5 / 0.75 son los valores por
    # defecto de facto (Lucene, Elasticsearch, rank_bm25) y no requieren
    # tuning para un corpus de este tamaño.
    K1 = 1.5
    B = 0.75

    def __init__(self):
        # Reconstruye el índice automáticamente si algún .md/.py cambió desde
        # la última vez — antes había que acordarse de correr
        # `python rag/indexer.py` a mano tras editar documentación, y si no
        # se hacía, el buscador documental respondía en silencio con
        # contenido desactualizado. best-effort: si falla (permisos, disco),
        # se sigue con el índice que ya exista en vez de tronar el motor.
        try:
            from rag import indexer as _indexer
            if _indexer.index_esta_desactualizado():
                _indexer.build_index()
        except Exception as e:
            print(f"[Cashi LocalRAG Warning] No se pudo verificar/reconstruir el índice documental: {e}")

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
        avgdl = self.store.get("avgdl") or 1.0
        doc_freqs = self.store["doc_freqs"]
        chunks = self.store["chunks"]

        scores = []
        for ch in chunks:
            score = 0.0
            tf_dict = ch["tokens"]
            doc_len = ch.get("doc_len") or sum(tf_dict.values()) or 1

            for t in tokens:
                tf = tf_dict.get(t)
                if not tf:
                    continue
                df = doc_freqs.get(t, 1)
                idf = math.log((num_docs + 1) / (df + 0.5)) + 1.0
                # Término BM25 real (antes: tf/doc_len sin saturación ni
                # normalización por longitud — en la práctica era TF-IDF,
                # aunque el resto del sistema lo llamaba "BM25 Engine").
                numerador = tf * (self.K1 + 1)
                denominador = tf + self.K1 * (1 - self.B + self.B * (doc_len / avgdl))
                score += idf * (numerador / denominador)

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
