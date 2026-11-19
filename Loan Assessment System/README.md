# Loan Assessment System

**Domain:** Credit risk · **Technique:** sklearn pipelines, calibration, cost-sensitive thresholds · **Role fit:** Applied AI Engineer / finance

Dual-model notebook (approval classifier + loan-amount regressor) and a critical analysis of what the approval model actually learns, on `data/loan_approval_dataset.csv` (4,269 applications).

## Notebooks
| Notebook | Content |
|---|---|
| `Loan Assessment System` | Random forest approval model (96.25% on a sequential split) and Ridge amount model (R² 0.867) |
| `Credit Scoring Analysis` | Baseline comparison, cross-validation, permutation importance, calibration, cost-based threshold, group error rates |

## Results
- Approval is almost a one-variable rule: CIBIL above 550 means 99% to 100% approval, 550 or below about 10%. The rule alone reaches 95.4% accuracy.
- Stratified 5-fold CV: random forest 98.4% accuracy and 0.998 AUC; logistic regression 91.7% and 0.968. Credit score dominates importance (0.475 AUC drop), then loan term (0.029).
- Probabilities are under-confident in the middle range; with a 5x cost for bad approvals the best threshold is 0.65 instead of 0.5 (cost 200 vs 254).
- Approval and error rates differ by about one point or less across education and self-employment groups.

## Conclusions
See the notebook. High accuracy is not a result until it is compared with a simple baseline; here the baseline is a one-line rule.

## Run
```bash
pip install -r requirements.txt
jupyter notebook notebooks/
```

## Stack
pandas, numpy, scikit-learn, matplotlib, seaborn.

## Limits & security
The dataset looks synthetic or simplified (a near-deterministic rule is unusual in real credit data), has no time dimension and no protected attributes such as age or gender, so this is not a fairness audit. Public data; no credentials.
