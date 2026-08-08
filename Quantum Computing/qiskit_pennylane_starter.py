"""
Quantum Computing & Quantum AI Starter Script
-----------------------------------------------
This script demonstrates a basic Quantum Circuit and Quantum Variational Classifier
using PennyLane and Qiskit.
"""

import numpy as np

def quantum_circuit_demo():
    try:
        import pennylane as qml
        
        # 1. Define a 2-qubit quantum device (simulator)
        dev = qml.device("default.qubit", wires=2)

        # 2. Define a quantum circuit function
        @qml.qnode(dev)
        def circuit(params):
            qml.RX(params[0], wires=0)
            qml.RY(params[1], wires=1)
            qml.CNOT(wires=[0, 1])
            return qml.expval(qml.PauliZ(1))

        # 3. Execute with sample parameters
        sample_params = np.array([np.pi / 4, np.pi / 2])
        expectation_value = circuit(sample_params)
        print("✅ PennyLane Quantum Circuit Executed Successfully!")
        print(f"Expectation Value <Z1>: {expectation_value:.4f}")

    except ImportError:
        print("⚠️ PennyLane is not installed yet. Run: pip install pennylane")

def qiskit_demo():
    try:
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator

        # Create a 2-qubit Quantum Circuit (Bell State)
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])

        print("\n✅ Qiskit Quantum Circuit Created:")
        print(qc)

    except ImportError:
        print("⚠️ Qiskit is not installed yet. Run: pip install qiskit qiskit-aer")

if __name__ == "__main__":
    print("--- Quantum Computing & AI Setup Test ---")
    quantum_circuit_demo()
    qiskit_demo()
