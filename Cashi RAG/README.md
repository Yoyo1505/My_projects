# Cashi RAG

**Domain:** GenAI / RAG · **Role fit:** Applied AI Engineer / Forward Deployed Engineer

> Security: no secrets are committed. The HTTP server binds to `127.0.0.1` by default; to share it set `CASHI_HOST=0.0.0.0` and `CASHI_API_TOKEN`. CORS is off unless `CASHI_CORS_ORIGIN` is set. See [SECURITY.md](../SECURITY.md).

[![Demo](https://img.shields.io/badge/demo-GitHub_Pages-blue)](https://yoyo1505.github.io/My_projects/cashi/)

Local **Retrieval-Augmented Generation** for financial/code knowledge: indexing, search, optional numeric engine, HTTP API, **Streamlit UI**, and a **static HTML/JS** demo for GitHub Pages.

---

## Two versions (both kept)

| Version | Open |
|---------|------|
| **Static (no server)** | [GitHub Pages – Cashi](https://yoyo1505.github.io/My_projects/cashi/) · `../docs/cashi/index.html` |
| **Streamlit** | `streamlit run app.py` |
| **CLI** | `python rag/query.py "your question"` |
| **Mappings** | [MAPPINGS.md](MAPPINGS.md) |
| **Versions detail** | [VERSIONS.md](VERSIONS.md) |
| **RAG guide** | [RAG_GUIDE.md](RAG_GUIDE.md) |

---

## Reproducible demo

```powershell
cd "Cashi RAG"
python -m pip install -r requirements.txt
python seed_demo_data.py
python rag/server_api.py
```

Open `http://localhost:8507/`. The demo uses only synthetic data and does not require SQL credentials or corporate datasets.

Health check: `http://localhost:8507/health`

Example API request:

```powershell
curl.exe -X POST http://localhost:8507/ -H "Content-Type: application/json" -d '{"q":"gasto de nomina en division centro semana 38","mode":"financial"}'
```

## 1) Static HTML/JS (GitHub Pages)

```text
../docs/cashi/
├── index.html           # Browser UI + client-side TF–IDF
└── data/chunks.json     # Exported chunks (no Python at runtime)
```

Enable Pages: repo **Settings → Pages → Branch `main` → `/docs`**.

Refresh chunks after changing docs/code:

```powershell
# from Cashi RAG/
python rag/indexer.py
# from repo root
python docs/_export_demo_data.py
```

---

## 2) Streamlit + Python toolkit

### Setup

```powershell
cd "Cashi RAG"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

### CLI

```powershell
python rag/indexer.py
python rag/query.py "how does indexing work"
python rag/server_api.py
```

### Structure

```text
Cashi RAG/
├── app.py
├── rag/
│   ├── indexer.py
│   ├── query.py
│   ├── financial_rag.py
│   ├── server_api.py
│   └── build_fast_json.py
├── docs/sample_knowledge.md
├── MAPPINGS.md
├── VERSIONS.md
├── RAG_GUIDE.md
├── requirements.txt
└── README.md
```

### Stack

Python, Streamlit, Polars, DuckDB (numeric path).

---

## What gets mapped?

- **Documents → chunks** (Markdown headings / Python functions)  
- **Query → ranked snippets** (TF–IDF style)  
- **Natural language → entities** (division, territorio, grupo, CECO, week) when consolidado exists  
- **Synonyms → account groups** (nómina, flete, renta, …)

Full tables: **[MAPPINGS.md](MAPPINGS.md)**.

---

## Notes

- `rag/index_store.json` is gitignored; rebuilt locally.  
- Numeric answers need optional `aggs/_consolidado.parquet` (not required for doc/code demo).  
- Static Pages demo never needs your PC online as a server.
