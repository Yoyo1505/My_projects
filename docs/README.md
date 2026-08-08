# Static demos (GitHub Pages)

Pure **HTML + JavaScript** demos. No Python process required after Pages is enabled.

These are **companions** to the full Streamlit apps in:

- `Territory Dashboard/` ([MAPPINGS](../Territory%20Dashboard/MAPPINGS.md) · [VERSIONS](../Territory%20Dashboard/VERSIONS.md))
- `Cashi RAG/` ([MAPPINGS](../Cashi%20RAG/MAPPINGS.md) · [VERSIONS](../Cashi%20RAG/VERSIONS.md))

---

## Enable GitHub Pages

1. Repo **Settings → Pages**  
2. Source: **Deploy from a branch**  
3. Branch: **`main`**  
4. Folder: **`/docs`**  
5. Save  

URLs:

| Page | Path |
|------|------|
| Landing | https://yoyo1505.github.io/My_projects/ |
| Territory | https://yoyo1505.github.io/My_projects/territory/ |
| Cashi | https://yoyo1505.github.io/My_projects/cashi/ |

---

## Layout

```text
docs/
├── index.html                 # Landing (links both demos)
├── _export_demo_data.py       # Rebuild JSON from Python projects
├── territory/
│   ├── index.html
│   └── data/demo.json         # Snapshot of synthetic finance data
└── cashi/
    ├── index.html
    └── data/chunks.json       # Slim RAG corpus for browser search
```

---

## Mapping: Streamlit data → static JSON

| Streamlit source | Static field |
|------------------|--------------|
| `aggs/global` YTD | `kpis`, `weekly` |
| `aggs/division` | `by_division`, `hierarchy` |
| `aggs/territorio` | `hierarchy[].children` |
| `aggs/grupo_cuentas` | `by_grupo` |
| `aggs/cuentas` | `accounts` |
| `aggs/seguimiento_demo.json` | `cierres` |
| `aggs/riesgos.json` | `riesgos` |
| Cashi `index_store.json` chunks | `chunks.json` |

Full semantic maps live in each project’s **MAPPINGS.md**.

---

## Refresh after code/data changes

```powershell
# From repository root
python "Territory Dashboard\seed_demo_data.py"   # if needed
python "Cashi RAG\rag\indexer.py"                # if docs/code changed
python docs\_export_demo_data.py
```

Commit and push `docs/` so GitHub Pages updates.

---

## Local preview

```powershell
cd docs
python -m http.server 8080
# http://localhost:8080
```
