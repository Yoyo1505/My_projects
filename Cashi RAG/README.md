# Cashi RAG

Local **Retrieval-Augmented Generation** toolkit for financial/code knowledge: TF–IDF style indexing, CLI query, and a tiny HTTP API.

## Structure

```text
Cashi RAG/
├── rag/
│   ├── indexer.py         # Build local index from .md / .py
│   ├── query.py           # Search & CLI
│   ├── financial_rag.py   # Numeric Q&A over parquet aggs (optional)
│   ├── build_fast_json.py # Fast JSON helpers for aggregates
│   └── server_api.py      # Simple HTTP API
├── docs/                  # Sample knowledge base
├── requirements.txt
└── README.md
```

## Setup

```powershell
cd "Cashi RAG"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
# 1) Build index over docs + source
python rag/indexer.py

# 2) Ask a question
python rag/query.py "how does the indexer chunk markdown"

# 3) Optional HTTP API
python rag/server_api.py
```

## Notes

- Index is written to `rag/index_store.json` (gitignored).
- `financial_rag.py` expects optional `aggs/_consolidado.parquet` for numeric queries; without it, code/doc RAG still works.
