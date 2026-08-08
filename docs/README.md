# Static demos (GitHub Pages)

These demos run **in the browser only** (HTML + JavaScript).  
No Python, Streamlit, or local server is required after Pages is enabled.

## URLs (after enabling Pages)

Base: `https://yoyo1505.github.io/My_projects/`

| Demo | Path |
|------|------|
| Landing | `/` or `/index.html` |
| Territory Dashboard | `/territory/` |
| Cashi RAG | `/cashi/` |

## Enable GitHub Pages

1. Open the repo on GitHub → **Settings** → **Pages**
2. **Source**: Deploy from a branch
3. **Branch**: `main`
4. **Folder**: `/docs`
5. Save — wait 1–2 minutes, then open the URL above

## Refresh demo data (maintainers)

From the repo root (local Python still used only to rebuild JSON assets):

```powershell
# Rebuild Territory Dashboard/aggs if needed, then:
python -c "exec(open('docs/_export_demo_data.py', encoding='utf-8').read())"
```

Or re-run the export commands documented in the commit history / maintain scripts.

## Note

Full Python apps remain in:

- `Territory Dashboard/` (Streamlit)
- `Cashi RAG/` (Streamlit + CLI)

Static pages are the **public, always-on** demos.
