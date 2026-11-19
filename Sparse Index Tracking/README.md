# Sparse Index Tracking

**Domain:** Quantitative finance · **Technique:** L1-regularised non-negative regression (compressed-sensing idea), walk-forward evaluation · **Role fit:** Applied AI Engineer / finance

Replicates the S&P 500 (SPY) with a small number of stocks chosen by sparse recovery. Applies the compressed-sensing and LASSO ideas from [Data Science Methods](../Data%20Science%20Methods/) to a real portfolio problem. Executed notebook: [`Sparse Index Tracking.ipynb`](Sparse%20Index%20Tracking.ipynb); code in `sparse_tracking.py`.

## Problem
Holding all 500 stocks is costly. How few stocks are needed to follow the index, and does a sparse-recovery method choose them better than simple rules?

## Approach
1. Data: 8 years of adjusted closes for SPY and 38 large US stocks (yfinance).
2. Method: $\min_{w\ge0}\tfrac12\lVert r_{idx}-Rw\rVert^2+\lambda\mathbf 1^\top w$, with $\lambda$ found by bisection to give exactly K stocks, then a constrained re-fit (long-only, sum to one) on the selected set.
3. Baselines: top-K by market-cap proxy (equal and dollar-volume weights), 200 random K-subsets, greedy forward selection.
4. Evaluation: walk-forward, 3 years of training and 6 months of holding, 10 windows (2021 to 2026); tracking error, correlation, return gap, turnover.

## Results (annualised, out of sample)
| K = 15 | Tracking error | Correlation with SPY | Turnover per rebalance |
|---|---|---|---|
| Sparse (L1) | 6.09% | 0.945 | 0.47 |
| Top-15 by market cap, equal | 6.56% | 0.926 | 0.06 |
| Random 15 (median) | 7.32% | n/a | 1.36 |
| Greedy forward selection | 5.39% | 0.951 | 0.58 |

The sparse method beats the naive baselines at K = 10 to 20 but loses to greedy selection and is worse than simple baselines at K = 5. Sparse K = 15 has a cumulative out-of-sample return of 66.2% against 66.5% for SPY.

## Conclusions
See the notebook. L1 gives a competitive, low-overfitting selection, but a simple greedy search was better and turnover is high.

## Run
```bash
pip install -r requirements.txt
jupyter notebook "Sparse Index Tracking.ipynb"
```

## Stack
Python, NumPy, SciPy, pandas, scikit-learn, yfinance, Matplotlib.

## Limits & security
The 38-stock universe is large-today stocks (survivorship and hindsight bias); baseline market caps use a current shares-outstanding snapshot; no transaction costs; one seed. Downloads live data (cached in `data/`, git-ignored). Educational, not investment advice. No credentials.
