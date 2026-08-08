# Cashi RAG — Guide

## Purpose

Cashi retrieves **relevant passages** from local documentation and code so you can ask operational/finance questions without hardcoding answers. Optionally, it answers **numeric** questions from pre-aggregated parquet data.

## Mental model

```text
Question
   │
   ├─► Code/Doc path:  tokenize → score chunks → show sources
   │
   └─► Financial path: detect entities (div/terr/grupo/ceco/week)
                         → SQL-like query on consolidado
                         → structured JSON answer
```

## Day-1 walkthrough (Streamlit)

1. `pip install -r requirements.txt`  
2. `streamlit run app.py`  
3. Click an example or type *how does indexing work*  
4. Expand raw hits to see file + score  

## Day-1 walkthrough (static)

1. Open https://yoyo1505.github.io/My_projects/cashi/  
2. Search the same examples  
3. No install, no Python  

## Rebuild knowledge

After editing `docs/` or `rag/*.py`:

```powershell
python rag/indexer.py
python docs/_export_demo_data.py   # from repo root — updates Pages payload
```

## See also

- [MAPPINGS.md](MAPPINGS.md) — all maps  
- [VERSIONS.md](VERSIONS.md) — Streamlit vs HTML  
