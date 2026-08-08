# Territory Dashboard

Public **Streamlit** demo: territorial financial drill-down, KPIs, charts, and AI-style variance notes on synthetic data.

## Structure

```text
Territory Dashboard/
├── app.py                 # Streamlit app
├── seed_demo_data.py      # Synthetic aggregates (created under aggs/)
├── requirements.txt
├── .streamlit/config.toml
└── README.md
```

## Setup

```powershell
cd "Territory Dashboard"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Open **http://localhost:8501** — no login.

On first run, if `aggs/` is missing, `seed_demo_data.py` generates demo data automatically.

## Stack

Streamlit, Polars, Pandas, Plotly.
