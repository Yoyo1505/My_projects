# My Projects – Data Analysis, Finance, AI Dashboards & RAG

Portfolio of applied Python projects **and** static browser demos.  
**Territory Dashboard** and **Cashi RAG** each keep **two versions**:

| | Streamlit / Python | Static HTML/JS (GitHub Pages) |
|--|--------------------|-------------------------------|
| Needs your PC as a server? | Yes while running | **No** |
| Best for | Full interaction / development | Always-on portfolio links |

---

## Live demos (static)

Enable once: GitHub → **Settings → Pages → Branch `main` → folder `/docs`**.

| Demo | URL |
|------|-----|
| Landing | https://yoyo1505.github.io/My_projects/ |
| Territory Dashboard | https://yoyo1505.github.io/My_projects/territory/ |
| Cashi RAG | https://yoyo1505.github.io/My_projects/cashi/ |

Local static preview: open `docs/index.html` or `python -m http.server` inside `docs/`.

---

## Projects

| Project | What’s inside | Docs |
|---------|---------------|------|
| **[Territory Dashboard](Territory%20Dashboard/)** | Streamlit app + seed data + mappings | [MAPPINGS](Territory%20Dashboard/MAPPINGS.md) · [VERSIONS](Territory%20Dashboard/VERSIONS.md) |
| **[Cashi RAG](Cashi%20RAG/)** | Streamlit + CLI/API RAG + mappings | [MAPPINGS](Cashi%20RAG/MAPPINGS.md) · [VERSIONS](Cashi%20RAG/VERSIONS.md) |
| **[Financial Risk Analysis](Financial%20Risk%20Analysis/)** | Risk notebooks | README in folder |
| **[Loan Assessment System](Loan%20Assessment%20System/)** | Credit ML notebook + CSV | README in folder |
| **[Quantum Computing](Quantum%20Computing/)** | Qiskit / PennyLane starter | README in folder |

Static site sources live under **[docs/](docs/)** (see [docs/README.md](docs/README.md)).

---

## Run Streamlit versions (optional)

```powershell
# Territory
cd "Territory Dashboard"
pip install -r requirements.txt
streamlit run app.py

# Cashi
cd "..\Cashi RAG"
pip install -r requirements.txt
streamlit run app.py
```

---

## Mappings (high level)

### Territory

- **Territorial tree:** Agrupa 1 → División → Territorio → Zona → Región → PDC  
- **Accounting tree:** Grupo de Cuentas → Cuentas → PosPre  
- **Measures:** Real 2025/2026, Plan, Nvo Plan, Forecast  
- **Files:** `aggs/*.parquet` (Streamlit) ↔ `docs/territory/data/demo.json` (static)  

Full detail: [Territory Dashboard/MAPPINGS.md](Territory%20Dashboard/MAPPINGS.md)

### Cashi

- **Docs/code → chunks** (headings / functions)  
- **Query → TF–IDF ranking**  
- **Optional NL → entities** (division, territorio, grupo, CECO, week)  
- **Files:** `rag/index_store.json` ↔ `docs/cashi/data/chunks.json`  

Full detail: [Cashi RAG/MAPPINGS.md](Cashi%20RAG/MAPPINGS.md)

---

## Maintain static exports

```powershell
python docs/_export_demo_data.py
git add docs
git commit -m "Refresh static demo data"
git push
```

---

## Notes

- Public demos use **synthetic** data only.  
- More build ideas: [PROJECT IDEAS.md](PROJECT%20IDEAS.md).
