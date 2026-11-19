# Results: QAOA for cardinality-constrained portfolio selection

Problem: choose exactly K = 4 of 12 ETFs, minimising q x'Sigma x - mu'x with q = 0.5. Estimates use 2015-2022 only; test is 2023-01-03 to 2026-11-19. Source: `Quantum Portfolio Selection.ipynb`.

Key numbers
1. Brute-force optimum (exact): SPY, QQQ, GLD, XLK, f = -0.288860. Feasible-subset median f = -0.126968.
2. QUBO penalty A = 0.008. Global minimum is feasible; QUBO, direct penalised objective and Ising form agree to 1.3e-15.
3. Qiskit check (p = 2): state fidelity 1.000000, <C> = 0.005317181 from numpy and from qiskit SparsePauliOp.
4. QAOA X mixer, best expected cost: p = 1 -0.14474, p = 2 -0.15206, p = 3 -0.16020 (optimum -0.28886). P(optimum) = 0.0018 to 0.0031.
5. QAOA XY mixer with Dicke initial state: best <C> = -0.17631 (p = 2); P(feasible) = 1.000000 at all p; P(optimum) = 0.0026 to 0.0051.
6. Every QAOA configuration's best sampled feasible portfolio is the optimum. Uniform random feasible subsets with 4096 shots also hit it in 99.5% of repetitions, so this is not evidence of advantage.
7. Greedy forward selection and top-4 in-sample Sharpe both return the brute-force optimum (rank 1 of 495).
8. Out of sample, equal weight, SPY/QQQ/GLD/XLK: ann. return 23.29%, vol 16.42%, Sharpe 1.418, max drawdown -16.89%. Random 4-subset median Sharpe 1.122; equal weight of all 12: Sharpe 1.253.

Caveats and failures
- QAOA did not reach the optimum in expectation (best AR over all states 0.596; AR over feasible subsets 0.307). It only matched the optimum in sampling, which a uniform random sampler also achieves.
- Depth results are not monotone (XY p = 3 worse than p = 2). COBYLA with 6 starts is not converged; treat depth comparisons as indicative only.
- The penalty margin is thin: the best infeasible state is only 0.00048 above the best feasible state.
- The QAOA-chosen subset equals the classical optimum, so the test result says nothing specific about QAOA. The subset is only as good as the in-sample mu and Sigma, and one 2023-2026 test path is not a robustness test.
- No transaction costs; arithmetic annualisation (x252); rf = 0. The final bar (2026-11-19) is included as returned by yfinance.
