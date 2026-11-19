# Results: real-data versions of the three notebooks

All numbers below are copied from the executed outputs stored in each notebook. Run date: 2026-11-19. The SPY numbers come from a live Yahoo Finance download and will change as new trading days arrive.

## 1. Bayesian Nonparametrics - Dirichlet Process Mixtures

Data: SPY daily adjusted close, 2005-01-03 to 2026-11-19, features = daily log return and log of 21-day realised volatility.

Key numbers:
- 5,485 observations after warm-up.
- DP mixture (concentration 1.0, truncation 10) converged in 650 iterations; **8 components** have weight above 0.01.
- Active count is 8 for concentration 0.1, 1.0 and 10.0.
- Regime 0 (calmest): 1,934 days (35.3%), within-regime annualised vol 3.7%. Regime 7 (most volatile): 127 days (2.3%), annualised vol 70.4%.
- Fixed-K GMM by BIC selects **K = 6** (BIC 27,356.6); K = 9 gives 27,363.2 and K = 5 gives 27,365.2.
- From-scratch CRP, expected tables (formula vs 5-run mean): alpha 0.5: 5.29 vs 5.60; alpha 1: 9.19 vs 8.40; alpha 5: 35.52 vs 35.40.

Caveats and failures:
- The DP count (8) and the BIC-optimal K (6) disagree. The 0.01 weight threshold is a heuristic, and GMM uses only 3 restarts.
- Regimes 3 and 4 are small (86 and 109 days). Their annualised mean returns (+7.3 and -8.0 as printed) extrapolate a few extreme days and are not meaningful as annual returns. Only the volatility columns should be read.
- Unsupervised, in-sample, no out-of-sample test. This describes the sample and is not a forecast.

## 2. Causal Inference - Double Machine Learning

Data: sklearn `fetch_california_housing` (n = 20,640). Treatment = MedInc (per $10k), outcome = log(MedHouseVal), 7 controls. The fallback loan dataset was not needed.

Key numbers (effect on log house value per $10k of median income):
- Naive OLS: 0.1972 (SE 0.0020), CI [0.1933, 0.2012].
- OLS with controls: 0.1886 (SE 0.0035), CI [0.1818, 0.1954].
- DML, linear nuisances: 0.1889 (SE 0.0035); out-of-fold R^2 0.505 (outcome), 0.610 (treatment).
- **DML, gradient-boosting nuisances: 0.0725 (SE 0.0028), CI [0.0671, 0.0780]**; out-of-fold R^2 0.835 (outcome), 0.813 (treatment).
- Sensitivity, 300 boosting iterations at learning rate 0.05: 0.0703 (SE 0.0028), CI [0.0649, 0.0757].
- Simulation, true theta = 0.5, 20 replications: naive OLS mean 0.6764 (bias +0.176); DML mean 0.4978 (bias -0.002, RMSE 0.0096), 95% CI coverage 0.95.

Caveats and failures:
- Observational data. These estimates are adjusted associations and do not prove causality.
- The linear-nuisance DML and the gradient-boosting DML differ by about 0.12. The estimate depends strongly on how the confounders are modelled, and the linear residualisers are weak (R^2 about 0.5 to 0.6).
- The coverage figure rests on 20 replications and is imprecise. The simulation's treatment and outcome equations were chosen by me.
- The outcome is top-coded at $500k.
- Boosting was cut to 100 iterations at learning rate 0.1 for run time (about 3 to 7 s per fit on this machine). The 300-iteration check above shows the estimate does not depend on this choice.

## 3. Compressed Sensing - Sparse Signal Recovery

Data: `load_sample_image('china.jpg')`, grayscale, 128 by 128 centre crop. Sparsity basis = orthonormal 2-D DCT. Recovery = L1 (LASSO) by FISTA, with lambda chosen on a 20% hold-out of measured pixels. Baseline = linear interpolation.

Key numbers (PSNR, dB):
- Oracle top-k DCT (full knowledge): 23.28 at 10% of coefficients, 27.29 at 25%, 31.02 at 40%.
- DCT energy: 1,796 of 16,384 coefficients (11.0%) hold 99% of the energy.
- **L1 recovery: 16.89 (10% of pixels), 18.36 (25%), 19.60 (40%).**
- **Linear interpolation: 17.88 (10%), 19.74 (25%), 21.21 (40%).**
- Solver checks: estimated ||A||_2^2 = 1.0 (step size valid); objective identical after 500 and 3000 iterations.

Caveats and failures:
- **The method did not beat naive interpolation at any tested sampling rate.** The result is reported as measured. The likely cause (weak incoherence between pixel sampling and the DCT basis) was not tested.
- Each rate is a single random draw (seed 0). The image is a single crop, so there are no error bars.
- Lambda was selected from six values; 0.1 was chosen at every rate.
