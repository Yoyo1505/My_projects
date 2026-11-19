# Quantum Algorithms

**Domain:** Quantum computing · **Technique:** Variational algorithms, error correction · **Role fit:** Applied AI Engineer / research

Three notebooks that simulate quantum algorithms with NumPy/SciPy, plus a Qiskit/PennyLane starter script.

## Notebooks
| Notebook | Problem | Approach |
|---|---|---|
| `Variational Quantum Eigensolver - VQE` | Find a Hamiltonian's ground-state energy | Parameterised ansatz, classical optimiser |
| `Quantum Approximate Optimization - QAOA` | Solve combinatorial problems such as max-cut | Alternating cost/mixer layers, parameter optimisation |
| `Quantum Error Correction - Surface Codes` | Protect qubits from noise | Stabiliser codes, logical error rate vs. physical error rate |

`starters/qiskit_pennylane_starter.py` is a minimal circuit and variational example for the two SDKs.

## Run
```bash
pip install -r requirements.txt
jupyter notebook notebooks/
python starters/qiskit_pennylane_starter.py
```

## Stack
NumPy, SciPy, Matplotlib, Qiskit, PennyLane.

## Limits & security
Classical simulation of small systems only; no hardware results. If you later use IBM Quantum, load the token from an environment variable and never commit it.
