# Quantitative Trading

**Domain:** Quantitative finance · **Technique:** Optimal execution, portfolio theory, stochastic volatility · **Role fit:** Applied AI Engineer / finance

Three executed notebooks applied to real market data (yfinance). Each ends with Conclusions; numbers and caveats are also in `results.md`.

## Notebooks
| Notebook | Problem | Data | Key result |
|---|---|---|---|
| `Trading Execution - Almgren-Chriss Optimal Execution` | Liquidate 5% or 20% of daily volume at minimum cost and risk | SPY and AAPL, 2 years | Selling 20% of SPY's ADV at once costs about 21 bps vs about 3 bps spread over the day; risk aversion trades cost for risk |
| `Portfolio Optimization - Markowitz and Black-Litterman` | Allocate across 10 ETFs; test out of sample | 10 ETFs, 2015 to 2026, yearly rebalance from 2018 | Max-Sharpe (Sharpe 1.04 in-sample) falls to 0.703 out of sample vs 0.717 for equal weight; Black-Litterman 0.984 but with hindsight views |
| `Option Pricing - Heston Stochastic Volatility` | Price SPY options with stochastic volatility | Live SPY option chain (3 expiries, 56 calls) | Price error 0.37 USD vs 2.24 USD for flat Black-Scholes; Feller condition violated, parameters weakly identified |

## Run
```bash
pip install -r requirements.txt
jupyter notebook notebooks/
```

## Stack
NumPy, SciPy, pandas, scikit-learn, yfinance, Matplotlib, Jupyter.

## Limits & security
Impact coefficients in the execution model are assumed, not estimated; the Black-Litterman views were chosen with hindsight (an upper bound, not a clean test); the Heston calibration used intraday quotes with stale prices. The option notebook downloads live data, so results change when re-run. Educational, not trading advice. No credentials. For a market-risk application see [Financial Risk Analysis](../Financial%20Risk%20Analysis/).
