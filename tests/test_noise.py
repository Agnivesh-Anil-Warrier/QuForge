"""Unit tests for NISQ hardware noise and finite-shot measurement simulation."""

import numpy as np
import pytest
import torch

from qforge.models import HybridQCQModel
from qforge.noise import (
    NoisyQuantumEvaluator,
    apply_depolarizing_channel,
    apply_finite_shot_noise,
)


def test_depolarizing_channel_scaling():
    """Verify depolarizing channel strictly attenuates expectations by (1 - gamma)."""
    expvals = torch.tensor([0.8, -0.6, 0.4, -0.2], dtype=torch.float32)
    gamma = 0.05
    noisy = apply_depolarizing_channel(expvals, gamma=gamma)
    expected = expvals * (1.0 - gamma)
    assert torch.allclose(noisy, expected, atol=1e-6)

    # Gamma = 0 should be exact identity
    assert torch.equal(apply_depolarizing_channel(expvals, gamma=0.0), expvals)


def test_finite_shot_bounds_and_reproducibility():
    """Verify finite-shot simulation yields bounded expectations in [-1.0, 1.0]."""
    expvals = torch.tensor([0.75, -0.5, 0.0], dtype=torch.float32)
    shots = 512
    noisy1 = apply_finite_shot_noise(expvals, shots=shots, seed=42)
    noisy2 = apply_finite_shot_noise(expvals, shots=shots, seed=42)

    assert noisy1.min() >= -1.0
    assert noisy1.max() <= 1.0
    assert torch.equal(noisy1, noisy2), "Identical seed should yield identical shot samples!"


def test_noisy_evaluator_forward_pass():
    """Verify full noisy forward pass for standard and correlated hybrid models."""
    B = 2
    x = torch.rand(B, 1, 28, 28)
    evaluator = NoisyQuantumEvaluator(
        single_qubit_gamma=0.02,
        two_qubit_gamma_multiplier=2.0,
        shots=1024,
        seed=101,
    )

    # Test standard model
    model_std = HybridQCQModel(filter_mode="trainable", use_correlated_readout=False, seed=42)
    logits_std = evaluator.forward_noisy_model(model_std, x)
    assert logits_std.shape == (B,)
    assert not torch.isnan(logits_std).any()

    # Test correlated model
    model_corr = HybridQCQModel(filter_mode="trainable", use_correlated_readout=True, seed=42)
    logits_corr = evaluator.forward_noisy_model(model_corr, x)
    assert logits_corr.shape == (B,)
    assert not torch.isnan(logits_corr).any()
