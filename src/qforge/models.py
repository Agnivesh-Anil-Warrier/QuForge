"""Classical CNN backbone, 2-qubit VQC classification head, and full QCQ-CNN model architecture."""

from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn as nn

from qforge.qsim import simulate_2q_vqc
from qforge.quantum_filter import QuantumFilter


# ---------------------------------------------------------------------------
# Classical Backbone CNN
# ---------------------------------------------------------------------------

class ClassicalBackbone(nn.Module):
    """Classical CNN mapping quantum feature maps to rotation angles (h0, h1) in [-pi, pi].
    
    Architecture:
      Conv(in_channels -> 16, 3x3, pad 1) + ReLU + MaxPool2d(2, 2)
      Conv(16 -> 32, 3x3, pad 1) + ReLU + MaxPool2d(2, 2)
      Flatten (32 * 3 * 3 = 288)
      Linear(288 -> 64) + ReLU
      Linear(64 -> 2)
      tanh * pi -> (h0, h1)
    """

    def __init__(self, in_channels: int = 4):
        super().__init__()
        self.in_channels = in_channels

        # If in_channels is 1 (mode 'none'), use stride=2 to downsample 28x28 -> 14x14
        if in_channels == 1:
            self.conv1 = nn.Conv2d(1, 16, kernel_size=3, stride=2, padding=1)
        else:
            self.conv1 = nn.Conv2d(in_channels, 16, kernel_size=3, stride=1, padding=1)

        self.relu1 = nn.ReLU(inplace=True)
        self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)  # 14x14 -> 7x7

        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1)
        self.relu2 = nn.ReLU(inplace=True)
        self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)  # 7x7 -> 3x3

        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(32 * 3 * 3, 64)
        self.relu3 = nn.ReLU(inplace=True)
        self.fc2 = nn.Linear(64, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.
        
        Args:
            x: Feature map tensor of shape (B, 4, 14, 14) or (B, 1, 28, 28).
        Returns:
            Rotation angles (h0, h1) of shape (B, 2) scaled to [-pi, pi].
        """
        out = self.pool1(self.relu1(self.conv1(x)))
        out = self.pool2(self.relu2(self.conv2(out)))
        out = self.flatten(out)
        out = self.relu3(self.fc1(out))
        out = self.fc2(out)
        # Scale through tanh to valid rotation angles in [-pi, pi]
        angles = torch.tanh(out) * float(np.pi)
        return angles


# ---------------------------------------------------------------------------
# 2-Qubit Variational Quantum Classifier (VQC) Head
# ---------------------------------------------------------------------------

class VQCHead(nn.Module):
    """2-qubit Variational Quantum Classifier head.
    
    Circuit:
      - ZZ Feature Map: H on both qubits, RZ(h_i), CNOT, RZ(h0*h1), CNOT.
      - RealAmplitudes Ansatz (reps=2): 3 layers of RY with CNOT entanglement (6 params).
      - Measurement: <Z0> in [-1, 1].
      - Trainable scale & bias: logit = scale * <Z0> + bias.
    """

    def __init__(self, seed: int = 42):
        super().__init__()
        rng = torch.Generator()
        rng.manual_seed(seed)
        
        # 6 trainable ansatz parameters
        init_weights = torch.rand(6, generator=rng, dtype=torch.float32) * 2.0 * float(np.pi)
        self.weights = nn.Parameter(init_weights)

        # Trainable scale and bias
        self.scale = nn.Parameter(torch.tensor(1.0, dtype=torch.float32))
        self.bias = nn.Parameter(torch.tensor(0.0, dtype=torch.float32))

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        """Forward pass.
        
        Args:
            h: Rotation angles of shape (B, 2)
        Returns:
            Unnormalized binary logits of shape (B,)
        """
        expval_z0 = simulate_2q_vqc(h, self.weights)
        logits = self.scale * expval_z0 + self.bias
        return logits


# ---------------------------------------------------------------------------
# Full Hybrid QCQ-CNN Model
# ---------------------------------------------------------------------------

class HybridQCQModel(nn.Module):
    """Full hybrid quantum-classical-quantum model for Brain MRI classification."""

    def __init__(
        self,
        filter_mode: str = "frozen_random",
        filter_depth: int = 1,
        seed: int = 42,
        cache_dir: Optional[Union[str, Path]] = None,
    ):
        super().__init__()
        self.filter_mode = filter_mode.lower()
        self.filter_depth = filter_depth
        self.seed = seed

        # 1. Front Quantum Filter
        self.quantum_filter = QuantumFilter(
            mode=filter_mode,
            depth=filter_depth,
            seed=seed,
            cache_dir=cache_dir,
        )

        # 2. Classical CNN Backbone
        in_channels = 1 if self.filter_mode == "none" else 4
        self.backbone = ClassicalBackbone(in_channels=in_channels)

        # 3. 2-Qubit VQC Classifier Head
        self.vqc_head = VQCHead(seed=seed)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """End-to-end forward pass.
        
        Args:
            x: Image batch of shape (B, 1, 28, 28) with values in [0, 1].
        Returns:
            Logits of shape (B,) for BCEWithLogitsLoss.
        """
        feat = self.quantum_filter(x)
        angles = self.backbone(feat)
        logits = self.vqc_head(angles)
        return logits

    def get_parameter_groups(self, lr_backbone: float = 1e-3, lr_filter: float = 1e-2):
        """Construct separate optimizer parameter groups for backbone and trainable quantum filter."""
        groups = []
        if self.filter_mode == "trainable":
            groups.append({
                "params": [self.quantum_filter.weights],
                "lr": lr_filter,
                "name": "quantum_filter",
            })

        # Backbone and VQC head parameters
        other_params = list(self.backbone.parameters()) + list(self.vqc_head.parameters())
        if self.filter_mode == "classical_conv":
            other_params += list(self.quantum_filter.conv.parameters())

        groups.append({
            "params": other_params,
            "lr": lr_backbone,
            "name": "backbone_and_head",
        })
        return groups
