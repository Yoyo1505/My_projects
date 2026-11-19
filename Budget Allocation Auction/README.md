# Budget Allocation Auction

**Domain:** Mechanism design / finance operations · **Technique:** VCG (Clarke pivot) payments, auction simulation · **Role fit:** Applied AI Engineer

Applies the VCG mechanism from [AI Engineering](../AI%20Engineering/) to a budgeting problem: cost centers hold private information about how much value they would extract from extra funding, and the planner needs them to report it honestly. Executed notebook: [`Budget Allocation Auction.ipynb`](Budget%20Allocation%20Auction.ipynb); code in `budget_auction.py`.

## Problem
If the planner simply believes the requests, units exaggerate. Can the allocation rule be designed so that honest reporting is the best strategy, and what does that cost?

## Approach
1. Structure from the synthetic Cashi demo data (six cost centers, overspend money); valuations simulated: each unit has a concave marginal value of money that decays geometrically. 240 units, 30 slots each, 480 budget slots.
2. Four mechanisms: VCG with exact Clarke payments, proportional allocation, first-price and uniform price.
3. Tests: efficiency under honest, inflated and best-response reports; a truthfulness test on 2,000 sampled misreports; individual rationality; revenue; sweeps over the number of units and the budget.

## Results (seed 2026)
| Mechanism | Misreport beats truth (2,000 tests) | Efficiency, honest | Efficiency, best response |
|---|---|---|---|
| VCG | 0 | 1.000 | 1.000 |
| Uniform price | 2 | 1.000 | 1.000 |
| First price | 378 (18.9%) | 1.000 | 0.980 |
| Proportional | 1,001 (50.1%) | 0.990 | 0.986 |

VCG collects 66.4% of the budget as payments and is not budget-balanced; no truthful unit has negative utility.

## Conclusions
See the notebook. VCG makes honest reporting rational; the price is a payment rule that is not budget-balanced. Efficiency gaps are small because the simulated market is homogeneous.

## Run
```bash
pip install -r requirements.txt
python "../Cashi RAG/seed_demo_data.py"      # only if aggs/_consolidado.parquet is missing
jupyter notebook "Budget Allocation Auction.ipynb"
```

## Stack
Python, NumPy, pandas, PyArrow, Matplotlib.

## Limits & security
A simulation: valuations are invented and the overspend ratio is exactly 1.03 for every demo center, so the results do not depend on the data. Truthfulness is tested by sampling, not proven. No real budgets, no credentials.
