# Quantum Portfolio Selection

**Domain:** Quantum computing applied to finance · **Technique:** QUBO / Ising formulation, QAOA with penalty and constraint-preserving (ring XY) mixers · **Role fit:** Applied AI Engineer / research

Applies QAOA, studied in [Quantum Algorithms](../Quantum%20Algorithms/), to cardinality-constrained portfolio selection: choose exactly K = 4 of 12 ETFs to minimise risk minus return. Executed notebook: [`Quantum Portfolio Selection.ipynb`](Quantum%20Portfolio%20Selection.ipynb); code in `qpo.py`.

## Problem
Selecting exactly K assets is a combinatorial problem. Can QAOA find the best subset, and is it better than brute force, a greedy algorithm or random sampling?

## Approach
1. Data: 12 liquid ETFs (yfinance), training 2015 to 2022 (expected returns, Ledoit-Wolf covariance), test 2023 to 2026.
2. Formulation: $\min_x\ q\,x^\top\Sigma x-\mu^\top x+A(\sum x_i-K)^2$ as a QUBO, converted to an Ising Hamiltonian; verified against the direct objective on all 4,096 bitstrings.
3. QAOA by NumPy statevector (cross-checked with Qiskit) at depth p = 1 to 3 with the standard X mixer and with a ring XY mixer starting from the Dicke state.
4. Baselines: brute force over the 495 feasible portfolios, greedy forward selection, top-4 by in-sample Sharpe, random subsets; out-of-sample evaluation of the chosen subsets.

## Results
| Method | P(optimal portfolio) | P(feasible) |
|---|---|---|
| Random feasible portfolio | 0.20% | 100% |
| QAOA, X mixer, p = 1 to 3 | 0.18% to 0.31% | about 34% |
| QAOA, ring XY mixer, p = 1 to 3 | 0.26% to 0.51% | 100% |

- Every method (QAOA samples, brute force, greedy, top-4 Sharpe) selects SPY, QQQ, GLD, XLK; out-of-sample (2023 to 2026, equal weight) Sharpe 1.42 against 1.12 for the median random subset and 1.25 for all 12.
- QAOA matched but did not beat the classical methods, and COBYLA did not converge at depth 3.

## Conclusions
See the notebook. The value is the formulation and an honest benchmark: at simulable sizes QAOA offers no advantage over brute force, greedy search or random sampling.

## Run
```bash
pip install -r requirements.txt
python download.py                            # refreshes data/adj_close.csv (cached, git-ignored)
jupyter notebook "Quantum Portfolio Selection.ipynb"
```

## Stack
Python, NumPy, SciPy, pandas, Qiskit (cross-check), yfinance, Matplotlib.

## Limits & security
Twelve qubits, noiseless simulation, one train/test split, no transaction costs; the out-of-sample result reflects the selection rule, not the quantum algorithm. Educational, not investment advice. No credentials.
