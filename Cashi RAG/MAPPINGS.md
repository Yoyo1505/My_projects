# Cashi RAG — Mappings

How **documents, entities, query modes, synonyms, files, and both UIs** map together.

---

## 1. Runtime map (two versions)

| Layer | Streamlit / Python | Static web (HTML/JS) |
|-------|--------------------|----------------------|
| Entry | `app.py` or CLI / API | `../docs/cashi/index.html` |
| Index | `rag/index_store.json` (built by `indexer.py`) | `../docs/cashi/data/chunks.json` |
| Search | `rag/query.py` (TF–IDF style) | Same idea in browser JS |
| Numeric Q&A | `rag/financial_rag.py` + optional parquet | Not in static demo (docs only) |
| HTTP | `rag/server_api.py` | N/A (static) |
| Hosting | Local process | GitHub Pages |

---

## 2. Module map

| File | Role |
|------|------|
| `rag/indexer.py` | Walks repo `.md` / `.py` → chunks → `index_store.json` |
| `rag/query.py` | `LocalRAG.search` / `ask()` + CLI |
| `rag/financial_rag.py` | Entity-aware numeric engine (DuckDB over consolidado) |
| `rag/build_fast_json.py` | Helpers to materialize fast JSON from aggs |
| `rag/server_api.py` | GET/POST `?q=&mode=code|financial` |
| `app.py` | Streamlit chat/search UI |
| `docs/sample_knowledge.md` | Seed knowledge for demos |

---

## 3. Document → chunk map (code/doc RAG)

### Indexing rules

| Source type | Chunk boundary | Stored fields |
|-------------|----------------|---------------|
| Markdown (`.md`) | Headings `#` … | `file`, `heading`, `start_line`, `end_line`, `type=markdown`, `content` |
| Python (`.py`) | `def` / `class` | `file`, `heading` (function/class name), lines, `type=python`, `content` |

### Ignored paths when indexing

`.git`, `__pycache__`, `.tmp`, `_ddb_tmp`, `aggs`, `_respaldo`

### Scoring (both Python and JS)

1. Tokenize query and document text (lowercase, length > 1).  
2. For each chunk, TF of query terms × IDF across corpus.  
3. Rank by score; return top‑k with snippet.

### Static export map

```text
index_store.json chunks[]
        │
        ▼ slim
chunks.json { "chunks": [ { file, heading, type, content[:1200], start_line, end_line } ] }
```

Tokens are **recomputed in the browser** so the static payload stays small.

---

## 4. Financial entity maps (`financial_rag.py`)

Built at engine init from `aggs/_consolidado.parquet` (optional):

| Map name | Key | Value | Detection in query |
|----------|-----|-------|--------------------|
| `map_divisiones` | normalized text | original `cat_Direccion_Division` | Token match (len>3) |
| `map_territorios` | normalized text | original `cat_Subdireccion_Territorio` | Token match |
| `map_grupos` | normalized text | original `cat_Grupo_de_Cuentas` | Substring / synonyms |

Normalization: NFKD, strip accents, lower, trim.

### Synonym map (grupo de cuentas)

| Concept key | Example triggers |
|-------------|------------------|
| `nomina` | nomina, sueldo, salario, personal |
| `mantenimiento` | mantenimiento, mtto, edificio |
| `publicidad` | publicidad, mercadotecnia |
| `renta` | renta, luz, telefono, alquiler |
| `flete` | flete, traslado, transporte |
| `operacion` | operacion, operativo, gastos de operacion |
| `honorarios` | honorario, asesoria, consultoria |

### Query intent map

| Signal in text | Behavior |
|----------------|----------|
| `semana N` / `hasta semana N` | Cut / accumulate to week N |
| `por semana`, `semanal`, … | Weekly breakdown path |
| `ceco` + number | Filter cost center |
| Division token | `_query_division` |
| Territorio token | `_query_territorio` |
| Grupo / synonym | `_query_grupo` |
| `match` / `mapeo` / `cruces` | CECO match report |
| (default) | `_query_general` |

Without consolidado parquet, financial maps are empty and **code/doc RAG still works**.

---

## 5. API mode map

| `mode` | Backend | Response shape |
|--------|---------|----------------|
| `code` (default for static) | `query.ask` | Markdown-like ranked snippets |
| `financial` | `FinancialRAGEngine.query` | Structured JSON (amounts, filters) |

Example (local server):

```text
GET /?q=how+does+indexing+work&mode=code
GET /?q=gasto+division+norte&mode=financial
```

---

## 6. Knowledge base map (demo docs)

| Section in `docs/sample_knowledge.md` | Topics |
|---------------------------------------|--------|
| What is Cashi | Product definition |
| Metrics glossary | Real, Plan, Forecast, IMOR, variance |
| How indexing works | Pipeline steps |
| API | How to call the local server |

Streamlit + static demos both surface these via retrieval.

---

## 7. File / path map

```text
Cashi RAG/
├── app.py                     # Streamlit demo
├── rag/
│   ├── indexer.py
│   ├── query.py
│   ├── financial_rag.py
│   ├── server_api.py
│   ├── build_fast_json.py
│   └── index_store.json       # local only (gitignored)
├── docs/sample_knowledge.md
├── MAPPINGS.md                # this file
├── VERSIONS.md
├── RAG_GUIDE.md
└── README.md

../docs/cashi/                 # static GitHub Pages copy
├── index.html
└── data/chunks.json
```

---

## 8. End-to-end flow

```text
Markdown/Python sources
        │
        ▼
  rag/indexer.py  ──► index_store.json
        │                    │
        │                    ├─► Streamlit app.py / CLI query.py
        │                    │
        │                    └─► export ──► docs/cashi/data/chunks.json
        │                                         │
        │                                         └─► HTML/JS search (Pages)
        │
        └─ (optional) aggs/_consolidado.parquet
                         │
                         └─► financial_rag.py numeric answers
```

---

## 9. Mapping to Territory Dashboard

| Territory concept | Cashi use |
|-------------------|-----------|
| `cat_Direccion_Division` | `map_divisiones` |
| `cat_Subdireccion_Territorio` | `map_territorios` |
| `cat_Grupo_de_Cuentas` | `map_grupos` + synonyms |
| Week / SMR | `sem` filters in financial queries |
| PDC / CECO | CECO regex + consolidado columns when present |
| `docs/territory` narrative | Can be indexed if placed under Cashi tree |

Cashi does **not** embed the Streamlit dashboard; it retrieves **text** (and optional numbers from parquet).
