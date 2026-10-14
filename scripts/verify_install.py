"""Verification script for Phase 0 environment setup.

Checks imports, versions, CPU threads, CUDA status, and executes a 4-qubit PennyLane + PyTorch autograd sanity test.
"""

import sys
import time

def main():
    print("=" * 60)
    print("QForge Environment & Sanity Verification")
    print("=" * 60)
    
    # 1. Imports and versions
    import torch
    import torchvision
    import pennylane as qml
    import numpy as np
    import sklearn
    import scipy
    import pandas as pd
    import matplotlib
    import seaborn
    import yaml
    import tqdm
    import PIL
    import imagehash
    import pytest
    
    print(f"Python Version:       {sys.version.split()[0]}")
    print(f"PyTorch Version:      {torch.__version__}")
    print(f"Torchvision Version:  {torchvision.__version__}")
    print(f"PennyLane Version:    {qml.__version__}")
    print(f"NumPy Version:        {np.__version__}")
    print(f"Scikit-Learn Version: {sklearn.__version__}")
    print(f"SciPy Version:        {scipy.__version__}")
    print(f"Pandas Version:       {pd.__version__}")
    print(f"CUDA Available:       {torch.cuda.is_available()}")
    print(f"PyTorch CPU Threads:  {torch.get_num_threads()}")
    
    # 2. 4-qubit PennyLane + PyTorch Autograd sanity circuit
    print("\nRunning 4-qubit PennyLane + PyTorch Autograd sanity circuit...")
    start_time = time.perf_counter()
    
    dev = qml.device("default.qubit", wires=4)
    
    @qml.qnode(dev, interface="torch", diff_method="backprop")
    def circuit(weights, x):
        # Angle encoding on 4 qubits
        for i in range(4):
            qml.RY(np.pi * x[i], wires=i)
        # Variational layer
        for i in range(4):
            qml.RZ(weights[0, i, 0], wires=i)
            qml.RY(weights[0, i, 1], wires=i)
        # Entangling CNOT chain
        for i in range(3):
            qml.CNOT(wires=[i, i + 1])
        # Return Pauli-Z expectation on all 4 wires
        return [qml.expval(qml.PauliZ(i)) for i in range(4)]
    
    # Random input x in [0, 1] and trainable weights
    torch.manual_seed(42)
    x = torch.tensor([0.1, 0.5, 0.8, 0.3], dtype=torch.float32)
    weights = torch.nn.Parameter(torch.rand(1, 4, 2, dtype=torch.float32) * 2 * np.pi)
    
    # Forward pass
    expvals = circuit(weights, x)
    out_tensor = torch.stack(expvals)
    print(f"Circuit Forward Output: {out_tensor.detach().numpy()}")
    
    # Backward pass
    loss = out_tensor.sum()
    loss.backward()
    
    grad = weights.grad
    elapsed = time.perf_counter() - start_time
    
    assert grad is not None, "Gradient is None!"
    assert not torch.isnan(grad).any(), "Gradient contains NaN!"
    print(f"Computed Gradients Shape: {grad.shape}")
    print(f"Gradient Norm: {grad.norm().item():.6f}")
    print(f"Sanity Check Completed in: {elapsed:.3f}s")
    print("=" * 60)
    print("PHASE 0 ENVIRONMENT VERIFICATION: SUCCESS!")
    print("=" * 60)


if __name__ == "__main__":
    main()
