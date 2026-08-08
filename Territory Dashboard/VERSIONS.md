# Territory Dashboard — Two versions

This folder ships **both** a full Streamlit application and a **static HTML/JS** demo for GitHub Pages.

## Side-by-side

| | **Streamlit** | **Static (HTML/JS)** |
|--|---------------|----------------------|
| Path | `Territory Dashboard/app.py` | `docs/territory/index.html` |
| Run | `streamlit run app.py` | Open Pages URL or `docs/index.html` |
| Needs server? | Yes (local process) | **No** (after GitHub Pages) |
| Data | Live recompute from `aggs/` | Snapshot `docs/territory/data/demo.json` |
| Filters (week/month/Q) | Full sidebar | Fixed YTD snapshot (SMR=30) |
| Drill depth | Full terr + account trees | Division → Territory (+ tables) |
| Charts | Plotly | Chart.js |
| Best for | Local analysis, demos with interaction | Portfolio visitors, always-on link |

## When to use which

- **GitHub visitors / recruiters** → static URL (no install).
- **You developing logic / ETL / trees** → Streamlit + `seed_demo_data.py`.
- **Updating the public demo** → regenerate aggs, then re-export `demo.json` (see README).

## Shared design language

- Dark theme (slate / cyan / violet).
- Same measure names and color map (see [MAPPINGS.md](MAPPINGS.md)).
- Synthetic demo data only in the public repo.
