# Quantitative Trading

**Domain:** Quantitative finance · **Technique:** Stochastic control, stochastic volatility, portfolio theory · **Role fit:** Applied AI Engineer / finance

Three NumPy/SciPy notebooks on execution, valuation and portfolio construction.

## Notebooks
| Notebook | Problem | Approach |
|---|---|---|
| `Trading Execution - Almgren-Chriss Optimal Execution` | How to liquidate a position balancing market impact against price risk | Almgren–Chriss mean-variance cost, SLSQP optimisation, sensitivity to risk aversion, strategy comparison |
| `Portfolio Optimization - Markowitz and Black-Litterman` | Allocate capital under estimation error | Mean-variance, covariance shrinkage, Black–Litterman views, efficient frontier |
| `Option Pricing - Heston Stochastic Volatility` | Price options when volatility is random | Heston model, characteristic-function pricing, volatility smile, calibration |

## Run
```bash
pip install -r requirements.txt
jupyter notebook notebooks/
```

## Stack
NumPy, SciPy, pandas, Matplotlib, Jupyter.

## Limits & security
Educational implementations on simulated or sample data, not production pricing libraries; no transaction-cost or liquidity validation on real order books. No credentials. For a market-risk application see [Financial Risk Analysis](../Financial%20Risk%20Analysis/).
