# Sparse Index Tracking: results

Data: Yahoo Finance (yfinance 1.7.0, adjusted close), 2018-11-19 to 2026-11-18, 38 stocks plus SPY as target. Walk-forward: 3-year train, 6-month hold, 10 windows, out-of-sample test periods 2021-11-22 to 2026-11-18.

## Key numbers (annualised, out of sample)

1. Sparse K=15 TE: 6.09% vs top-15 by market-cap proxy (equal weight) 6.56%, top-15 DV-weighted 8.94%, random K=15 median 7.32% (5-95%: 6.73%-8.20%).
2. Greedy forward selection beats sparse at every K: K=15 5.39% vs 6.09%; K=20 4.86% vs 5.23%. **The sparse method does not beat greedy.**
3. Sparse K=5 TE 14.34%, worse than top-5 equal weight (12.55%) and the random median (12.11%).
4. Sparse K=15 correlation with SPY 0.9446; return gap 0.17% per year.
5. Sparse K=15 cumulative out-of-sample return 66.17% vs SPY 66.50%.
6. Overfitting: sparse K=15 in-sample TE 5.23% vs out-of-sample window mean 5.90% (OOS/IS 1.13). Greedy shows a larger gap (OOS/IS 1.40).
7. Turnover per rebalance: sparse K=15 0.473 vs top-15 equal 0.059 and random K=15 median 1.362.

## Caveats and failures

- Post re-fit holdings are fewer than K: the SLSQP re-fit sets some selected weights to exactly zero. Mean held counts are 9.5 for K=10, 14.3 for K=15, and 19.2 for K=20. The lambda bisection gave exactly K non-zeros in every window (exact fraction 1.0), so the shortfall comes from the re-fit.
- Universe is 38 tickers, not the ~40 in the brief.
- Market-cap proxy uses a single shares-outstanding snapshot (small look-ahead in share counts).
- Weights are held constant within each test window; daily drift and transaction costs are not modelled.
- Single seed (42) for random draws; results are one walk-forward path, not a confidence interval over data.
- The notebook was executed in place with nbconvert (0 errors across 10 code cells).
