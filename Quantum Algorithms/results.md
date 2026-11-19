# Results

All three notebooks were executed top to bottom with `nbconvert --execute`, with fixed seeds (7). No cell raised an error. Every number below is taken from the executed outputs in the notebooks.

## Variational Quantum Eigensolver - VQE.ipynb

Key numbers (H2, STO-3G, 2 qubits):
1. Exact total ground energy at R = 0.735 A: -1.1373060 Ha (electronic -1.8572750 Ha plus nuclear repulsion 0.7199690 Ha).
2. Electronic ground energy of the published two-qubit Hamiltonian at 0.735 A: -1.85727503 Ha. Ours: -1.85727502 Ha.
3. COBYLA with exact expectation values: 162 evaluations, error 4.4e-16 Ha against exact diagonalisation.
4. COBYLA with shot noise (8192 shots per measurement basis): 75 evaluations. True error at the returned parameters 2.77e-4 Ha; best iterate 1.97e-4 Ha. Both are below chemical accuracy (1.6 mHa).
5. Exact equilibrium bond length of the STO-3G curve: 0.7349 A, total energy -1.137306 Ha.
6. Largest |VQE - exact| over the 0.3 to 2.5 A scan (23 points, best of 3 starts): 7.4e-8 Ha.

Caveats:
* The coefficients at the other bond lengths were **not taken from a published table**. I could not find a multi-distance table I could verify. They are computed in the notebook from the STO-3G basis (Hehre, Stewart & Pople 1969). Checks: the 0.735 A magnitudes match the published set, and the total energy at 0.7414 A (-1.1372702 Ha) matches a benchmark value found online (-1.1372701747 Ha, arXiv 2610.10254).
* The encoding differs from the published one by a single-qubit basis change, so the XX term appears as YY and some signs differ. Spectra agree.
* Shot noise is simulated with AerSimulator with no hardware noise. The ansatz is real-amplitude, which suffices for the H2 ground state.

## Quantum Approximate Optimization - QAOA.ipynb

Key numbers (Zachary karate club; 12-node induced subgraph for QAOA):
1. Exact max cut of the 12-node subgraph: 16 (16 optimal bitstrings, including global flips).
2. QAOA p = 1: expectation 13.337, approximation ratio 0.8336, P(optimal cut) 0.0475.
3. QAOA p = 2: expectation 14.163, approximation ratio 0.8852, P(optimal cut) 0.1419.
4. QAOA p = 3: expectation 14.731, approximation ratio 0.9207, P(optimal cut) 0.2729.
5. Greedy with 1-flip local search on the 12 nodes: cut 15 (ratio 0.9375). Random cuts: mean 11.045 (ratio 0.6903).
6. Full 34-node graph: greedy 52; random mean 39.00 (best of 20000: 54); multi-start local search 61; Goemans-Williamson-style rounding 61.

Caveats and failures:
* At p = 1 to 3, QAOA on this subgraph does not beat the greedy cut of 15 in expectation value (14.731 at p = 3). It reaches the optimum in its best of 2048 shots at every p.
* The 34-node graph was **not solved by QAOA**: a statevector needs 2^34 amplitudes (275 GB). The 34-node result of 61 is the best cut found by heuristics and is **not proven optimal**. The Burer-Monteiro relaxation value (63.489) is a feasible point, not a certified upper bound, so it does not bound the optimum.
* Angles were optimised by COBYLA with 30 random starts per depth. There is no guarantee of a global optimum for p = 2 and p = 3.
* The NumPy simulator agrees with a Qiskit circuit at p = 1 (difference 3.9e-14). The deeper layers were not cross-checked against Qiskit.

## Quantum Error Correction - Surface Codes.ipynb

Key numbers (code-capacity bit-flip noise, MWPM decoder):
1. d = 3 rotated surface code, exact enumeration of all 512 error patterns at p = 0.10: P_L = 0.119695. Monte Carlo with 200000 shots: 0.119015.
2. Surface code at p = 0.10 (8000 shots per point): P_L = 0.11650 (d = 3), 0.12325 (d = 5), 0.13412 (d = 7).
3. Surface code at p = 0.02: P_L = 0.00613 (d = 3), 0.00125 (d = 5), 0.00088 (d = 7).
4. Threshold crossings: d = 3 and d = 5 at p = 0.0937; d = 5 and d = 7 at p = 0.0833.
5. Repetition code at p = 0.10 (exact): 0.02800 (d = 3), 0.00856 (d = 5), 0.00273 (d = 7). No crossing for p in [0.02, 0.16].
6. Repetition code, d = 3 at p = 0.10: Monte Carlo 0.02702 +/- 0.00036, about 2.7 standard errors below the exact value.

Caveats and failures:
* **Code simulated:** rotated planar surface codes for d = 3, 5, 7 and bit-flip repetition codes. **No toric code was simulated.** Noise is code-capacity only: independent X errors, perfect syndromes, no measurement errors, no circuit-level noise, no depolarising errors.
* **Threshold is uncertain.** The crossings disagree by about 0.01, and the curves are close near the crossing. A preliminary run with 4000 shots per point gave crossings at 0.0797 and 0.0962. The honest statement is roughly 0.08 to 0.10. The literature value for this noise model is around 10% (not reproduced here).
* **Unresolved:** the repetition-code Monte Carlo point at d = 3 is 2.7 standard errors below its exact value. The decoder matches the exact enumeration, so I attribute this to sampling, but I did not confirm it with a larger run.
* **Decoder details:** unweighted MWPM with networkx exact matching. Qubits with identical check patterns were merged into one decoding edge; for d >= 3 these pairs differ by a stabiliser, so the merge does not change the logical outcome.
* **Runtime:** the d = 7 sweep takes about 170 s of the notebook run.

## Notes on the run

* `requirements.txt` was rewritten to list only the packages the notebooks import. PennyLane was removed because no notebook uses it.
* `README.md` and files outside this folder were not modified.
* During execution, the QEC notebook file was briefly found with different content (a different notebook's cells, which failed with a SyntaxError). The file was then verified to match the intended build, and the notebook was re-executed successfully. The cause is unknown; another process may write to this folder.
