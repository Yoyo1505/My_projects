# -*- coding: utf-8 -*-
"""Cashi RAG – simple Streamlit demo (browser, no login)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

BASE = Path(__file__).parent.resolve()

st.set_page_config(page_title="Cashi RAG", page_icon="◈", layout="wide")

st.markdown(
    """
<style>
.stApp {
  background: radial-gradient(900px 500px at 0% 0%, #1e293b 0%, #0b1220 50%, #070b14 100%);
  color: #e2e8f0;
}
h1, h2, h3 { color: #f8fafc !important; }
.stMarkdown p, label, .stCaption { color: #cbd5e1 !important; }
div[data-testid="stChatMessage"] {
  background: rgba(15,23,42,.75);
  border: 1px solid rgba(148,163,184,.15);
  border-radius: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("◈ Cashi RAG")
st.caption("Local retrieval demo — index docs/code, ask questions, see matching chunks.")

# ---- ensure index ----
index_path = BASE / "rag" / "index_store.json"


def ensure_index() -> bool:
    if index_path.exists():
        return True
    with st.spinner("Building index (first run)…"):
        try:
            from rag.indexer import build_index
            build_index()
            return index_path.exists()
        except Exception as e:
            st.error(f"Indexer failed: {e}")
            return False


col_a, col_b = st.columns([2, 1])
with col_b:
    if st.button("Rebuild index", use_container_width=True):
        try:
            from rag.indexer import build_index
            build_index()
            st.success("Index rebuilt.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

if not ensure_index():
    st.stop()

from rag.query import LocalRAG, ask  # noqa: E402

rag = LocalRAG()
n_chunks = len(rag.store["chunks"]) if rag.store else 0
st.success(f"Index ready · **{n_chunks}** chunks · source: `docs/` + `rag/` + README")

# ---- examples ----
examples = [
    "how does indexing work",
    "what is Cashi",
    "metrics glossary Real Plan Forecast",
    "how does the API work",
]
st.markdown("**Try an example**")
ex_cols = st.columns(len(examples))
for i, ex in enumerate(examples):
    if ex_cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
        st.session_state["cashi_q"] = ex

q = st.text_input(
    "Your question",
    value=st.session_state.get("cashi_q", "how does indexing work"),
    key="cashi_input",
)
top_k = st.slider("Top results", 1, 8, 4)

if st.button("Search", type="primary") or st.session_state.get("cashi_q"):
    query = q.strip() or "how does indexing work"
    results = rag.search(query, top_k=top_k)

    st.subheader("Answer (retrieved context)")
    st.markdown(ask(query, top_k=top_k))

    st.subheader("Raw hits")
    if not results or (isinstance(results[0], dict) and results[0].get("error")):
        st.warning(results[0].get("error") if results else "No hits")
    else:
        for i, r in enumerate(results, 1):
            with st.expander(f"{i}. {r.get('file')} · {r.get('heading')} · score {r.get('score')}"):
                st.code(r.get("snippet", ""), language=r.get("type", "text"))

st.divider()
st.markdown(
    """
### How others try this project

From the repo root:

```powershell
cd "Cashi RAG"
pip install -r requirements.txt
streamlit run app.py
```

Or CLI only (no browser):

```powershell
python rag/indexer.py
python rag/query.py "how does indexing work"
```

**Note:** This demo retrieves from local docs/code. Numeric finance answers
(`financial_rag.py`) need optional `aggs/_consolidado.parquet` (not in git).
"""
)
