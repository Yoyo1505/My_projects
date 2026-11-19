# Risk and Execution Platform

**Domain:** Quantitative finance · **Technique:** Black-Litterman, regime-mixture VaR, liquidity-adjusted VaR (Almgren-Chriss style), Heston-priced hedging · **Role fit:** Applied AI Engineer / finance

A pipeline that chains four decisions for an ETF portfolio and tests each one out of sample: how to allocate, how much could be lost given the market regime, how much it costs to exit, and whether an options hedge is worth its premium. It applies the theory in [Quantitative Trading](../Quantitative%20Trading/) and [Financial Risk Analysis](../Financial%20Risk%20Analysis/) to one end-to-end decision. Executed notebook: [`Risk and Execution Platform.ipynb`](Risk%20and%20Execution%20Platform.ipynb); the code is in `riskexec.py`.

## Problem
Allocation, risk, liquidity and hedging are usually produced by separate tools. The question is how they interact: a portfolio that looks safe by VaR can be costly to exit at scale, and a hedge that cuts tail risk has to be judged by its premium drag.

## Approach
1. **Allocation:** Black-Litterman with an inverse-volatility prior and a mechanical momentum view (no hindsight), yearly rebalance from 2018.
2. **Regime-aware VaR:** 3-component Gaussian mixture on (20-day volatility, 5-day return), refit every 63 days; compared with historical and EWMA Student-t VaR using Kupiec and Christoffersen tests.
3. **Liquidity-adjusted VaR:** VaR plus an Almgren-Chriss style linear-impact liquidation cost for $1bn, $10bn and $50bn portfolios over 1, 3 and 5 days.
4. **Hedge:** quarterly 95% SPY put sized to the portfolio beta, marked to market daily with Heston prices (initial variance from the VIX).

## Results (run 2026-11-19, 10 ETFs, out of sample 2018 to 2026)
| Step | Result |
|---|---|
| Allocation | Black-Litterman (momentum view) Sharpe 0.62 vs 0.72 equal weight and 0.75 inverse-vol prior: the view added no value |
| VaR 99% breach rate | historical 0.96% (clustered, Christoffersen p = 0.006), EWMA-t 1.78%, regime mixture 1.78% (both fail Kupiec, p = 0.007) |
| Liquidity | LVaR 208 bps at $1bn, 284 bps at $10bn (1-day exit), 622 bps at $50bn; a 5-day exit halves the cost |
| Hedge (100%) | CVaR 99% 2.98% to 1.98%, max drawdown -20.9% to -17.9%, Sharpe 0.69 to 0.73, CAGR 7.3% to 6.1%; about 3.6% a year in premium and only 4 of 35 quarters paid out |

## Conclusions
See the notebook. Short version: every simple baseline (historical VaR, equal weight) was harder to beat than the elaborate method, and the hedge is insurance, not a return source.

## Run
```bash
pip install -r requirements.txt
jupyter notebook "Risk and Execution Platform.ipynb"
```

## Stack
Python, pandas, NumPy, SciPy, scikit-learn, yfinance, Matplotlib.

## Limits & security
Hedge prices are Heston model prices with assumed parameters, not market quotes; the impact coefficient is an assumption; one historical path; no taxes, financing or transaction costs. Downloads live data, so numbers change when re-run. Educational, not investment advice. No credentials.
