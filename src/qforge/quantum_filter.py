"""Quantum filter modules supporting frozen_random, trainable, classical_conv, and none modes, plus PennyLane reference."""

from pathlib import Path
from typing import Optional, Union
import numpy as np
import pennylane as qml
import torch
import torch.nn as nn
import torch.nn.functional as F

from qforge.qsim import simulate_4q_filter


# ---------------------------------------------------------------------------
# PennyLane Reference Implementation
# ---------------------------------------------------------------------------

_PL_DEV_4Q = None


def get_pennylane_4q_device():
    """Lazily instantiate 4-qubit PennyLane device."""
    global _PL_DEV_4Q
    if _PL_DEV_4Q is None:
        _PL_DEV_4Q = qml.device("default.qubit", wires=4)
    return _PL_DEV_4Q


def pennylane_filter_circuit(weights: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    """PennyLane reference implementation of the 4-qubit quantum convolutional filter.
    
    Args:
        weights: Variational parameters of shape (L, 4, 2)
        x: Patch pixel values of shape (4,), values in [0.0, 1.0]
    Returns:
        Tensor of shape (4,) containing Pauli-Z expectations
    """
    dev = get_pennylane_4q_device()

    @qml.qnode(dev, interface="torch", diff_method="backprop")
    def _circuit(w, patch):
        # 1. Angle encoding
        for i in range(4):
            qml.RY(np.pi * patch[i], wires=i)
        # 2. Variational layers
        L = w.shape[0]
        for l in range(L):
            for i in range(4):
                qml.RZ(w[l, i, 0], wires=i)
                qml.RY(w[l, i, 1], wires=i)
            qml.CNOT(wires=[0, 1])
            qml.CNOT(wires=[1, 2])
            qml.CNOT(wires=[2, 3])
        # 3. Measurement
        return [qml.expval(qml.PauliZ(i)) for i in range(4)]

    expvals = _circuit(weights, x)
    return torch.stack(expvals)


# ---------------------------------------------------------------------------
# High-Performance Quantum Filter Module
# ---------------------------------------------------------------------------

class QuantumFilter(nn.Module):
    """Quantum quanvolution filter module with 4 operation modes.
    
    Modes:
      1. 'frozen_random': Fixed parameters (buffer), cached outputs for deterministic speedup.
      2. 'trainable': Identical seeded parameter initialization, differentiable autograd parameters.
      3. 'classical_conv': Conv2d(1, 4, 2, stride=2) + tanh control baseline.
      4. 'none': Pass-through mode (returns (B, 1, 28, 28) for standard CNN).
    """

    def __init__(
        self,
        mode: str = "frozen_random",
        depth: int = 1,
        seed: int = 42,
        cache_dir: Optional[Union[str, Path]] = None,
    ):
        super().__init__()
        self.mode = mode.lower()
        self.depth = depth
        self.seed = seed
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None

        valid_modes = ["frozen_random", "trainable", "classical_conv", "none"]
        if self.mode not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Choose from: {valid_modes}")

        # Deterministic weight initialization
        rng = torch.Generator()
        rng.manual_seed(seed)
        init_weights = torch.rand(depth, 4, 2, generator=rng, dtype=torch.float32) * 2.0 * float(np.pi)

        if self.mode == "frozen_random":
            self.register_buffer("weights", init_weights)
        elif self.mode == "trainable":
            self.weights = nn.Parameter(init_weights.clone())
            self.register_buffer("initial_weights", init_weights.clone())
        elif self.mode == "classical_conv":
            self.conv = nn.Conv2d(in_channels=1, out_channels=4, kernel_size=2, stride=2)
            # Initialize weights with standard kaiming or normal
            nn.init.kaiming_uniform_(self.conv.weight, a=np.sqrt(5))
        elif self.mode == "none":
            # No-op filter
            pass

    @property
    def parameter_drift(self) -> float:
        """Compute parameter drift ||theta - theta_init|| for trainable filter mode."""
        if self.mode != "trainable":
            return 0.0
        return torch.norm(self.weights - self.initial_weights).item()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass of quantum filter.
        
        Args:
            x: Input image tensor of shape (B, 1, 28, 28) with values in [0, 1].
        Returns:
            Output feature map:
              - Modes 'frozen_random', 'trainable', 'classical_conv': shape (B, 4, 14, 14)
              - Mode 'none': shape (B, 1, 28, 28)
        """
        if self.mode == "none":
            return x

        if self.mode == "classical_conv":
            return torch.tanh(self.conv(x))

        # Quantum simulation modes ('frozen_random' or 'trainable')
        B, C, H, W = x.shape
        assert H == 28 and W == 28, f"Expected 28x28 input, got {H}x{W}"

        # Extract 2x2 non-overlapping patches (stride 2) -> (B, 4, 196)
        patches = F.unfold(x, kernel_size=2, stride=2)  # (B, 4, 196)
        patches = patches.permute(0, 2, 1).contiguous()   # (B, 196, 4)
        flat_patches = patches.view(-1, 4)                # (B * 196, 4)

        # Simulate through fast pure-PyTorch statevector simulator
        # Weights shape: (L, 4, 2)
        out_expvals = simulate_4q_filter(flat_patches, self.weights)  # (B * 196, 4)

        # Reshape to (B, 196, 4) -> (B, 4, 14, 14)
        out_feature_map = out_expvals.view(B, 14, 14, 4).permute(0, 3, 1, 2).contiguous()
        return out_feature_map
