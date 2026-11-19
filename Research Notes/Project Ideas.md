# Project Ideas – Portfolio Roadmap

Ideas aligned with this repo: **finance**, **Streamlit dashboards**, **RAG**, **risk**, and **data engineering**.  
Pick one, create a folder with a Title Case name (no underscores), and ship a short README + demo.

## A. Dashboard modules (fit next to Territory Dashboard)

1. **Executive KPI Cockpit**  
   One-page CEO view: revenue, margin, YoY, forecast vs plan, top 5 risks. Auto-refresh mock or CSV.

2. **Alert Center**  
   Rule engine + simple ML anomaly flags (z-score / isolation forest) on weekly series; inbox of open/closed alerts.

3. **What-If Simulator**  
   Sliders for price, volume, FX, opex; live P&L bridge and waterfall chart.

4. **Cash Flow Tower**  
   13-week cash forecast, collections aging, burn runway; stress scenarios.

5. **Store / Branch Heatmap**  
   Map or matrix of PDC/stores by IMOR, sales, contribution; click-through to detail.

6. **Plan vs Actual Variance Studio**  
   Tree + waterfalls by account; commentary layer (export notes for RAG).

7. **Forecast Accuracy Tracker**  
   MAPE/bias by product and week; champion-challenger models (naive vs SARIMA vs light GBM).

8. **Credit Watchlist**  
   Portfolio of counterparties with PD/LGD mock scores, limit utilization, early-warning signals.

## B. Full projects (new folders)

9. **Market Risk Lab**  
   Historical and parametric VaR, CVaR, backtesting (Kupiec), factor shocks on a sample book.

10. **Credit Scoring Pipeline**  
    End-to-end: dirty CSV → feature store → logistic / XGBoost → SHAP dashboard → decision threshold.

11. **Fraud Detection Demo**  
    Imbalanced transactions, precision-recall curves, streaming-style batch scorer in Streamlit.

12. **Portfolio Optimizer**  
    Mean-variance and risk-parity; efficient frontier Plotly; constraint editor.

13. **Earnings Call RAG**  
    Ingest 10-K / transcripts (public samples); ask questions with citations (pair with Cashi patterns).

14. **Invoice & Document OCR Desk**  
    Upload PDFs, extract fields, reconcile to a ledger sample; exception queue UI.

15. **Supply Chain Demand App**  
    Hierarchical forecast (SKU → category → channel); inventory policy calculator.

16. **ESG Metrics Board**  
    Carbon intensity, diversity KPIs, peer benchmarks from open datasets; downloadable pack.

17. **FX & Rates Monitor**  
    Live/public API rates, carry table, simple hedge P&L simulator.

18. **Banking Stress Test Sandbox**  
    Simplified ICAAP-style scenarios on synthetic balance sheet; capital and liquidity gauges.

## C. How to add one cleanly

```text
My_projects/
  New Project Name/
    README.md
    requirements.txt
    app.py            # if Streamlit
    src/
    data/sample/      # tiny public or synthetic only
```

Checklist:

- English Title Case folder name (no underscores)  
- Synthetic or open data only in git  
- One-screen demo that runs with `streamlit run app.py` or a notebook  
- 5–10 line README: problem, method, how to run, stack  

## D. Suggested order (fast impact)

1. Executive KPI Cockpit  
2. Alert Center  
3. What-If Simulator  
4. Credit Scoring Pipeline  
5. Earnings Call RAG (extends Cashi RAG)  
6. Market Risk Lab (extends Financial Risk Analysis)  