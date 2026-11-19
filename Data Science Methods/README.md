# Data Science Methods

**Domain:** Statistics / ML · **Technique:** Bayesian nonparametrics, causal ML, sparse recovery · **Role fit:** Applied AI Engineer

Three executed notebooks applying statistical methods to real data. Each ends with Conclusions; numbers and caveats are also in `results.md`.

## Notebooks
| Notebook | Problem | Data | Key result |
|---|---|---|---|
| `Bayesian Nonparametrics - Dirichlet Process Mixtures` | Find market regimes without fixing their number | SPY returns 2005 to 2026 (yfinance) | 8 active regimes ordered by volatility (3.7% to 70.4% annualised); BIC on a fixed-K mixture picks 6, so the count is a modelling choice |
| `Causal Inference - Double Machine Learning` | Effect of median income on house value, adjusting for confounders | California housing (20,640 block groups) | Naive OLS 0.197; DML with boosting 0.0725 (CI 0.067 to 0.078); in a simulation with true effect 0.5, DML bias -0.002 vs naive +0.176 |
| `Compressed Sensing - Sparse Signal Recovery` | Reconstruct an image from 10% to 40% of its pixels | 128 x 128 crop of a real photograph | L1 recovery (16.9 to 19.6 dB) lost to linear interpolation (17.9 to 21.2 dB): the image is only approximately sparse |

## Run
```bash
pip install -r requirements.txt
jupyter notebook notebooks/
```

## Stack
NumPy, SciPy, scikit-learn, pandas, statsmodels, yfinance, Matplotlib, Jupyter.

## Limits & security
The causal estimate is observational and cannot prove causality; the regime model ignores time ordering; compressed sensing is shown on one image and one basis. Public data only; no credentials.
