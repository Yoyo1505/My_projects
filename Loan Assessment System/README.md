# Loan Assessment System

**Domain:** Credit risk · **Technique:** sklearn pipelines (classification + regression) · **Role fit:** Applied AI Engineer / finance

Dual-model notebook: loan approval classification and loan amount regression on `data/loan_approval_dataset.csv`.

## Approach
Preprocessing and models are wrapped in sklearn pipelines to avoid train/test leakage; the notebook compares classifiers and reports approval metrics plus regression error.

## Run
```bash
pip install pandas numpy scikit-learn matplotlib seaborn jupyter
jupyter notebook notebooks/
```

## Stack
pandas, numpy, scikit-learn, matplotlib, seaborn.

## Limits & security
- Public dataset; results are not representative of a real lender.
- Next steps: SHAP explanations, fairness checks across protected groups, and probability calibration before any threshold decision.
