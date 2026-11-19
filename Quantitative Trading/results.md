# Results summary

Run environment: Windows, Python 3.13.5, yfinance 1.7.0. Each notebook was executed in place with nbconvert. Market data are pulled from Yahoo Finance at run time, so numbers will move if the notebooks are re-run on a later date. The figures below come from the executed outputs.

## 1. Trading Execution - Almgren-Chriss Optimal Execution

Key numbers (SPY and AAPL, 501 sessions, 2024-11-19 to 2026-11-18; $c = 1$ unless stated):

1. SPY: daily log-return vol 1.06% (16.9% annualised), last full-session close $730.20, 60-day ADV 44.80M shares.
2. AAPL: daily log-return vol 1.82% (28.9% annualised), last close $352.45, 60-day ADV 42.80M shares.
3. SPY, sell 20% ADV: Almgren-Chriss expected cost 3.116 bps, cost std dev 52.7 bps. TWAP 3.079 bps, std dev 56.7 bps. Immediate 21.23 bps, std dev 0.
4. AAPL, sell 20% ADV: Almgren-Chriss 5.334 bps, std dev 90.3 bps. TWAP 5.271 bps, std dev 97.0 bps. Immediate 36.35 bps.
5. Optimality check (SPY, 20%): objective $E + \lambda V$ is 2,363,971 for the solution against 2,390,395 for TWAP. The gradient at the solution is about $10^{-12}$ of its TWAP value.
6. Risk-aversion sensitivity (SPY, 20%): as $c$ rises from 0.1 to 100, expected cost rises from 3.08 to 10.08 bps and std dev falls from 56.2 to 13.9 bps. The first-interval sale rises from 10.3% to 61.8% of the order.

Caveats:
- The impact coefficients $\theta_P = \theta_T = 0.10$ are assumptions, not estimates. The dollar costs scale directly with them. Because $\theta_P = \theta_T$, $\gamma = \eta$ for each ticker.
- The model is linear with one asset, and it has no bid-ask spread, no intraday volume curve and no price-dependent risk.
- Immediate sale has zero std dev by the model's convention, which is why it shows 0.
- The bps std dev is identical for 5% and 20% orders because the linear model scales exactly with size.
- At $c = 1$ the Almgren-Chriss schedule has about 1.2% higher expected cost than TWAP for SPY (3.116 against 3.079 bps). That is the intended trade for lower risk.
- No failures. All cells ran cleanly.

## 2. Portfolio Optimization - Markowitz and Black-Litterman

Key numbers (10 ETFs, adjusted closes, 2015-01-02 to 2026-11-18, 2,987 daily returns):

1. Ledoit-Wolf shrinkage intensity 0.0090, so the shrinkage is light.
2. Historical annual returns: QQQ 18.8%, SPY 13.9%, and TLT 0.0%. Annual vol ranges from 6.7% (IEF) to 22.3% (IWM).
3. Minimum-variance portfolio (full sample): expected return 3.2%, volatility 5.6%. Weights are IEF 78.0%, DBC 10.9%, SPY 10.5%.
4. Max-Sharpe on historical means (full sample, in-sample): Sharpe 1.04. This is an in-sample figure and is overfit. Weights are QQQ 41.1%, GLD 35.8%, IEF 16.4%, DBC 6.7%.
5. Black-Litterman views: the posterior QQQ minus SPY spread is 1.8% against the 2.0% view. The posterior GLD return is 3.1% against the 5.0% view, because the view is shrunk toward the prior.
6. Out-of-sample backtest, 2018 to 2026-11-18, yearly rebalance, rf = 0. Sharpe and max drawdown:
   - Equal weight: Sharpe 0.717, max drawdown -22.4%, CAGR 8.34%.
   - Min variance (LW): Sharpe 0.600, max drawdown -15.9%, CAGR 3.46%.
   - Max Sharpe (historical means): Sharpe 0.703, max drawdown -21.6%, CAGR 8.22%, average turnover 39.6%.
   - Black-Litterman max Sharpe: Sharpe 0.984, max drawdown -24.0%, CAGR 13.97%, average turnover 14.2%.

Caveats:
- The Black-Litterman backtest is not a clean out-of-sample test. The prior weights are the current fund sizes from yfinance, which already reflect the 2018 to 2026 growth of SPY and QQQ. The QQQ-over-SPY view was also written with that history known. Read the Black-Litterman Sharpe and return as an upper bound.
- The market-cap-style prior is fund total assets, a proxy for market value. It is not true market capitalisation.
- The views and $\delta = 2.5$ and $\tau = 0.05$ are assumptions.
- Historical means are noisy, so the max-Sharpe and Black-Litterman weights are concentrated.
- The Sharpe ratios use rf = 0.
- Every SLSQP call returned success.

## 3. Option Pricing - Heston Stochastic Volatility

Key numbers (SPY options, live quotes on 2026-11-19 at 12:18 New York time; the market was in its regular session):

1. Spot $718.72 (previous close $733.50). Risk-free rate 4.153% from the 13-week bill.
2. Three expiries: 2026-12-24 (35 days), 2027-01-29 (71 days) and 2027-03-19 (120 days). The calibration set has 56 calls with strikes from $690 to $754.
3. Implied $q$ from put-call parity: -1.21%, -0.43% and -0.05%. These values are negative, so they are not dividend yields. They reflect the parity forwards (722.44, 725.16 and 728.73) sitting above the spot quote, which means spot and option quotes were not taken at the same instant.
4. Calibrated Heston parameters: $\kappa = 14.19$, $\theta = 0.0536$ (long-run vol 23.1%), $\xi = 3.41$, $\rho = -0.674$, $v_0 = 0.0976$ (initial vol 31.2%).
5. Feller quantity $2\kappa\theta - \xi^2 = -10.09$, so the Feller condition is violated. It was not imposed.
6. Heston price RMSE 0.367 USD (n = 56), against 2.235 USD for flat Black-Scholes at ATM implied vol.
7. Heston implied-vol RMSE 0.339 vol points against the market.
8. Market implied vol: 0.18 to 0.21 (Dec-24), 0.17 to 0.24 (Jan-29) and 0.18 to 0.23 (Mar-19). The smile slopes down with strike, and the calibrated curve follows it.
9. Pricer checks: with $\xi \to 0$ the Heston price is 3.965695 against Black-Scholes 3.965696. Put-call parity holds. One price takes 3.7 ms.

Failures and caveats:
- **First calibration attempt failed to fit.** It used a $\pm 10\%$ moneyness band, no spread filter and a $\xi$ upper bound of 3.0. The fit gave a price RMSE of 3.15 USD, dominated by one wide-quoted 655 strike with a 61% implied vol. The solver stopped at $\xi = 3.0$, its bound. The filters were then tightened to $\pm 5\%$ moneyness, a 20% relative-spread cap and volume of at least 10, and the bound was raised to 5.0. That is the version in the notebook.
- The calibration uses 56 quotes to fit 5 parameters, so $\kappa$, $\xi$ and $v_0$ trade off against each other. The parameters are weakly identified and should be read as a fit to one snapshot, not as stable estimates.
- Only two starting points were used, with at most 60 function evaluations each, to keep the run within the 900 s cell limit. Both starts reached the same RMSE, but the search was not exhaustive.
- The solver stopped on the ftol condition rather than on gradient tolerance.
- Quotes were not all fresh. The median last-trade age was 24 min (Dec-24), 42 min (Jan-29) and 27 min (Mar-19).
- The market was open at run time, so this is not a stale-price case.
- The price RMSE of 0.367 USD is a fit to mid prices, not an out-of-sample test.
