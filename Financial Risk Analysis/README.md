# Financial Risk Analysis (Market Risk Lab)

**Domain:** Quantitative finance · **Technique:** VaR/CVaR, EWMA Monte Carlo, backtesting · **Role fit:** Applied AI Engineer / finance

Historical, parametric and EWMA Student-t Monte Carlo VaR/CVaR for an equal-weight SPY/QQQ/TLT/GLD portfolio, with Kupiec (coverage) and Christoffersen (independence) backtests.

## Approach
1. Eight years of adjusted prices via yfinance; log returns.
2. 1-day 99% VaR three ways, plus historical CVaR.
3. Rolling 500-day window backtest of each method.

## Results (run 2026-11-19, alpha = 1%)
| Method | Breach rate | Kupiec p | Christoffersen p |
|---|---|---|---|
| Historical | 1.06% | 0.818 | 0.160 |
| Parametric normal | 1.72% | 0.011 | 0.468 |
| EWMA + Student-t MC | 1.59% | 0.034 | 0.395 |

Historical VaR is calibrated; the normal model under-covers (fat tails), and so does the EWMA-t variant in this sample. Portfolio 99% VaR/CVaR: 2.24% / 3.06% (historical).

## Run
```bash
pip install -r requirements.txt
python risk_lab.py --tickers SPY QQQ TLT GLD --alpha 0.01
jupyter notebook notebooks/      # exploratory notebooks 01–03
```

## Stack
pandas, numpy, scipy, yfinance, matplotlib.

## Limits & security
Linear equal-weight book only; no options or factor shocks yet (GARCH and stress scenarios are next). Public market data; no credentials.
