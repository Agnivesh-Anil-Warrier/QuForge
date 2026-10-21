"""NISQ Hardware Noise Modeling and Depolarizing Channel Simulator.

Implements the noise models described in Chapter 4.6 of the QForge Project Report:
  - Depolarizing channel: E_dep(rho) = (1 - gamma) * rho + (gamma / 2^n) * I
  - Error rate scaling: gamma for single-qubit rotations, 2*gamma for 2-qubit CNOTs
  - Finite-shot measurement statistical sampling (e.g. 128 to 1024 shots)
"""

from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import torch
import torch.nn as nn

from qforge.qsim import (
    simulate_2q_vqc,
    simulate_2q_vqc_correlated,
    simulate_4q_filter,
)


def apply_depolarizing_channel(
    state_or_expvals: torch.Tensor,
    gamma: float,
    num_qubits: int = 1,
) -> torch.Tensor:
    """Apply depolarizing channel to expectation values.
    
    For Pauli-Z observables, under an n-qubit depolarizing channel
    E_dep(rho) = (1 - gamma) * rho + (gamma / 2^n) * I,
    the expectation value scales linearly as:
      <Z>_noisy = (1 - gamma) * <Z>_ideal
    since Tr(Z * I) = 0.
    
    Args:
        state_or_expvals: Ideal Pauli expectation values tensor in [-1.0, 1.0].
        gamma: Depolarizing error rate in [0.0, 1.0].
        num_qubits: Number of qubits affected.
    Returns:
        Noisy expectation values scaled by (1 - gamma).
    """
    if gamma <= 0.0:
        return state_or_expvals
    decay = float(max(0.0, 1.0 - gamma))
    return state_or_expvals * decay


def apply_finite_shot_noise(
    expvals: torch.Tensor,
    shots: Optional[int] = None,
    seed: Optional[int] = None,
) -> torch.Tensor:
    """Simulate statistical finite-shot measurement shot noise.
    
    For an expectation <Z> in [-1, 1], the probability of measuring state |0> is:
      p0 = (1 + <Z>) / 2
    Sampling k ~ Binomial(shots, p0), the estimated expectation is:
      <Z>_shots = (2 * k - shots) / shots
      
    Args:
        expvals: Expectation values in [-1.0, 1.0].
        shots: Number of finite shots (e.g. 128, 256, 512, 1024). If None, return exact.
        seed: Random seed for reproducibility.
    Returns:
        Tensor with empirical finite-shot expectation values in [-1.0, 1.0].
    """
    if shots is None or shots <= 0:
        return expvals

    device = expvals.device
    p0 = torch.clamp((1.0 + expvals) * 0.5, 0.0, 1.0)

    # Binomial sampling
    p0_np = p0.detach().cpu().numpy()
    rng = np.random.default_rng(seed)
    counts_0 = rng.binomial(n=shots, p=p0_np)
    noisy_expvals = (2.0 * counts_0 - shots) / float(shots)

    return torch.tensor(noisy_expvals, dtype=expvals.dtype, device=device)


class NoisyQuantumEvaluator:
    """Evaluates hybrid quantum models under parameterized NISQ hardware noise and finite shots."""

    def __init__(
        self,
        single_qubit_gamma: float = 0.0,
        two_qubit_gamma_multiplier: float = 2.0,
        shots: Optional[int] = None,
        seed: int = 42,
    ):
        self.gamma_1q = single_qubit_gamma
        self.gamma_2q = single_qubit_gamma * two_qubit_gamma_multiplier
        self.shots = shots
        self.seed = seed

    def evaluate_filter_output(self, feat_map: torch.Tensor) -> torch.Tensor:
        """Apply depolarizing and shot noise to 4-channel quantum filter feature map."""
        if self.gamma_1q > 0.0:
            feat_map = apply_depolarizing_channel(feat_map, self.gamma_1q, num_qubits=4)
        if self.shots is not None:
            feat_map = apply_finite_shot_noise(feat_map, self.shots, seed=self.seed)
        return feat_map

    def evaluate_vqc_logits(
        self,
        h: torch.Tensor,
        vqc_head: nn.Module,
    ) -> torch.Tensor:
        """Evaluate VQC classification head under simulated NISQ noise."""
        is_correlated = hasattr(vqc_head, "readout")

        if is_correlated:
            ideal_expvals = simulate_2q_vqc_correlated(h, vqc_head.weights)
            # Observables [Z0, Z1] affected by gamma_1q; [Z0*Z1] affected by two-qubit gamma_2q
            noisy_expvals = ideal_expvals.clone()
            noisy_expvals[:, :2] = apply_depolarizing_channel(noisy_expvals[:, :2], self.gamma_1q)
            noisy_expvals[:, 2] = apply_depolarizing_channel(noisy_expvals[:, 2], self.gamma_2q)

            if self.shots is not None:
                noisy_expvals = apply_finite_shot_noise(noisy_expvals, self.shots, seed=self.seed)

            logits = vqc_head.readout(noisy_expvals).squeeze(-1)
        else:
            ideal_expval = simulate_2q_vqc(h, vqc_head.weights)
            noisy_expval = apply_depolarizing_channel(ideal_expval, self.gamma_1q)
            if self.shots is not None:
                noisy_expval = apply_finite_shot_noise(noisy_expval, self.shots, seed=self.seed)
            logits = vqc_head.scale * noisy_expval + vqc_head.bias

        return logits

    def forward_noisy_model(self, model: nn.Module, x: torch.Tensor) -> torch.Tensor:
        """Run full end-to-end forward pass with simulated NISQ noise at quantum stages."""
        # 1. Front Quantum Filter with noise
        feat = model.quantum_filter(x)
        if model.filter_mode in ["frozen_random", "trainable"]:
            feat = self.evaluate_filter_output(feat)

        # 2. Classical CNN Backbone (noiseless classical computation)
        angles = model.backbone(feat)

        # 3. Terminal VQC Head with noise
        logits = self.evaluate_vqc_logits(angles, model.vqc_head)
        return logits
