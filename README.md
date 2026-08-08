# My Projects – Data Analysis, Finance, AI Dashboards & RAG

Lean portfolio: Python projects **plus static browser demos** (no server required).

## Live demos (GitHub Pages)

After enabling Pages on folder `/docs` (Settings → Pages → Branch `main` /docs):

| Demo | Link |
|------|------|
| Landing | https://yoyo1505.github.io/My_projects/ |
| Territory Dashboard | https://yoyo1505.github.io/My_projects/territory/ |
| Cashi RAG | https://yoyo1505.github.io/My_projects/cashi/ |

Local preview without Pages:

```powershell
# any static server, or open the HTML files directly
start docs/index.html
```

## Projects (source)

| Project | Type | Run (optional / offline) |
|---------|------|---------------------------|
| **[Cashi RAG](Cashi%20RAG/)** | RAG + Streamlit | `streamlit run app.py` or static `docs/cashi/` |
| **[Territory Dashboard](Territory%20Dashboard/)** | Streamlit dashboard | `streamlit run app.py` or static `docs/territory/` |
| **[Financial Risk Analysis](Financial%20Risk%20Analysis/)** | Risk notebooks | open `notebooks/` |
| **[Loan Assessment System](Loan%20Assessment%20System/)** | Credit ML notebook | open `notebooks/` |
| **[Quantum Computing](Quantum%20Computing/)** | Quantum starters | `python qiskit_pennylane_starter.py` |

## Notes

- Static demos use **synthetic data** and pure **HTML/JS** (Chart.js CDN for charts).
- No production secrets or SQL pipelines in this repo.
- More ideas: [PROJECT IDEAS.md](PROJECT%20IDEAS.md) · Pages setup: [docs/README.md](docs/README.md).
