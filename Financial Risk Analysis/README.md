# Financial Risk Analysis

Python notebooks for **market and portfolio risk**: exploratory analysis, VaR/CVaR-style metrics, and portfolio scenarios.

## Structure

```text
Financial Risk Analysis/
├── notebooks/
│   ├── 01-exploratory-analysis.ipynb
│   ├── 02-risk-metrics.ipynb
│   └── 03-portfolio-analysis.ipynb
├── requirements.txt
└── README.md
```

## Setup

```powershell
cd "Financial Risk Analysis"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
jupyter notebook notebooks/
```

## Stack

pandas, numpy, matplotlib, scipy, yfinance.
