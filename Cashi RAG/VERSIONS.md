# Cashi RAG — Two versions

## Side-by-side

| | **Streamlit / Python** | **Static (HTML/JS)** |
|--|------------------------|----------------------|
| Path | `Cashi RAG/app.py` | `docs/cashi/index.html` |
| Run | `streamlit run app.py` | GitHub Pages or open HTML |
| Server needed? | Yes for Streamlit/API | **No** |
| Index | `rag/index_store.json` | `docs/cashi/data/chunks.json` |
| Rebuild index | `python rag/indexer.py` | Re-export chunks after index |
| Numeric finance RAG | Yes (`financial_rag.py`) | Docs/code retrieval only |
| Best for | Dev + full features | Portfolio / always-on demo |

## CLI / API (Python-only extras)

```powershell
python rag/indexer.py
python rag/query.py "how does indexing work"
python rag/server_api.py
```

## Shared behavior

- TF–IDF-style ranking over chunks  
- Same knowledge base (`docs/sample_knowledge.md` + source)  
- Dark UI language (violet/cyan accents)

See [MAPPINGS.md](MAPPINGS.md) for entity and document maps.
