# Cashi RAG

Local **Retrieval-Augmented Generation** toolkit: index Markdown/Python, search with TF–IDF-style ranking, optional HTTP API, and a **Streamlit demo UI**.

## How to try it (browser demo)

```powershell
cd "Cashi RAG"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Open **http://localhost:8501** — no login.  
First run builds `rag/index_store.json` automatically from `docs/` + source.

## CLI (no UI)

```powershell
python rag/indexer.py
python rag/query.py "how does indexing work"
python rag/server_api.py
# then: http://localhost:8000/?q=how+does+indexing+work&mode=code
```

## Structure

```text
Cashi RAG/
├── app.py                 # Streamlit demo (main entry for visitors)
├── rag/
│   ├── indexer.py         # Build local index
│   ├── query.py           # Search + CLI
│   ├── financial_rag.py   # Numeric Q&A (needs optional parquet aggs)
│   ├── build_fast_json.py
│   └── server_api.py      # HTTP API
├── docs/sample_knowledge.md
├── requirements.txt
└── README.md
```

## Why there was no “test” before

After cleaning the monorepo, **Cashi** kept only the RAG library + CLI.  
**Territory Dashboard** had Streamlit; Cashi did not — so visitors had no one-click UI.  
`app.py` is the browser demo so anyone can try retrieval from this folder.

## Notes

- Index file `rag/index_store.json` is gitignored (rebuilt locally).
- `financial_rag.py` needs `aggs/_consolidado.parquet` for number queries; **doc/code RAG works without it**.
