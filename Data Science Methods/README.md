# Data Science Methods

**Domain:** Statistics / ML theory · **Technique:** Bayesian nonparametrics, causal ML, sparse recovery · **Role fit:** Applied AI Engineer

Three from-scratch notebooks on statistical methods that go beyond standard supervised learning.

## Notebooks
| Notebook | Problem | Approach |
|---|---|---|
| `Bayesian Nonparametrics - Dirichlet Process Mixtures` | Cluster data without fixing the number of clusters | Dirichlet process prior, Chinese restaurant process, Gibbs sampling |
| `Causal Inference - Double Machine Learning` | Estimate a treatment effect with many confounders | Residualisation with ML nuisance models, Neyman-orthogonal score, comparison with OLS and LASSO |
| `Compressed Sensing - Sparse Signal Recovery` | Recover a sparse signal from few measurements | L1 minimisation / LASSO, recovery vs. number of measurements |

## Run
```bash
pip install -r requirements.txt
jupyter notebook notebooks/
```

## Stack
NumPy, SciPy, scikit-learn, pandas, Matplotlib, seaborn, Jupyter.

## Limits & security
Synthetic data with known ground truth, so results show the methods work, not how they behave on messy real data. No credentials.
