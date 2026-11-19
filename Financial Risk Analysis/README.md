# Financial Risk Analysis (Market Risk Lab)

**Domain:** Quantitative finance · **Technique:** VaR/CVaR, EWMA Monte Carlo, backtesting · **Role fit:** Applied AI Engineer / finance

Historical, parametric and EWMA Student-t Monte Carlo VaR/CVaR for an equal-weight SPY/QQQ/TLT/GLD portfolio, with Kupiec (coverage) and Christoffersen (independence) backtests.

## Notebooks
| Notebook | Content |
|---|---|
| `01-exploratory-analysis` | Returns and volatility of the assets |
| `02-risk-metrics` | VaR and CVaR |
| `03-portfolio-analysis` | Diversification and portfolio risk |
| `04-market-risk-lab` | Backtested comparison of three VaR methods (summary below) |

## Approach
Eight years of adjusted prices (yfinance), log returns; 1-day 99% VaR three ways plus historical CVaR; rolling 500-day backtest.

## Results (run 2026-11-19, alpha = 1%)
| Method | Breach rate | Kupiec p | Christoffersen p |
|---|---|---|---|
| Historical | 1.06% | 0.818 | 0.160 |
| Parametric normal | 1.72% | 0.011 | 0.468 |
| EWMA + Student-t MC | 1.59% | 0.034 | 0.395 |

Excess kurtosis is 6.46, so the normal model is too optimistic (VaR 1.83% vs 2.25% historical; CVaR 3.06%). Only the historical estimator passes; breaches fall in 2022, 2024, 2025 and 2026.

## Conclusions
See `04-market-risk-lab`. A risk model is a hypothesis: report it with a backtest. The simplest estimator was the only one not rejected.

## Run
```bash
pip install -r requirements.txt
python risk_lab.py --tickers SPY QQQ TLT GLD --alpha 0.01
jupyter notebook notebooks/
```

## Stack
pandas, numpy, scipy, yfinance, matplotlib.

## Limits & security
Linear equal-weight book; only 16 to 26 breaches per method, so tests have limited power; no options, factor shocks, GARCH or stress scenarios yet. Public market data; no credentials.
