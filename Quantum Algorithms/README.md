# Quantum Algorithms

**Domain:** Quantum computing · **Technique:** Variational algorithms, error correction · **Role fit:** Applied AI Engineer / research

Three executed notebooks that apply quantum algorithms to concrete problems, simulated with Qiskit and NumPy, plus a Qiskit/PennyLane starter script.

## Notebooks
| Notebook | Problem | Key result |
|---|---|---|
| `Variational Quantum Eigensolver - VQE` | Ground-state energy of H2 vs bond length | Matches exact diagonalisation to 7.4e-8 Ha across 0.3 to 2.5 A; 8,192-shot error 2.8e-4 Ha (below chemical accuracy); equilibrium 0.7349 A |
| `Quantum Approximate Optimization - QAOA` | Max-cut on the karate club graph (12-node subgraph) | Approximation ratio 0.834 / 0.885 / 0.921 at p = 1, 2, 3, below a greedy heuristic (0.9375); 34-node graph needs 275 GB to simulate |
| `Quantum Error Correction - Surface Codes` | Logical error rate of rotated surface codes (d = 3, 5, 7) with matching decoder | Threshold roughly 8% to 10% under code-capacity X noise; repetition code shown for comparison |

Each notebook ends with Conclusions; numbers and caveats are in `results.md`.

`starters/qiskit_pennylane_starter.py` is a minimal circuit and variational example.

## Run
```bash
pip install -r requirements.txt
jupyter notebook notebooks/
```

## Stack
Qiskit, qiskit-aer, NumPy, SciPy, NetworkX, Matplotlib.

## Limits & security
Noiseless classical simulation of small systems only; no hardware results. The H2 coefficients at other bond lengths are computed in the notebook, not taken from a published table. If you later use IBM Quantum, load the token from an environment variable and never commit it.
