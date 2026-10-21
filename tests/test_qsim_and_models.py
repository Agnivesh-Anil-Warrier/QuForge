"""Comprehensive tests for PyTorch quantum simulator parity with PennyLane, filter modes, and hybrid architectures."""

import numpy as np
import pennylane as qml
import pytest
import torch
import torch.nn as nn

from qforge.models import ClassicalBackbone, HybridQCQModel, VQCHead, CorrelatedVQCHead
from qforge.qsim import simulate_2q_vqc, simulate_2q_vqc_correlated, simulate_4q_filter
from qforge.quantum_filter import QuantumFilter, pennylane_filter_circuit


# ---------------------------------------------------------------------------
# Test 1: 4-Qubit Simulator vs PennyLane Output & Gradient Parity
# ---------------------------------------------------------------------------

def test_4q_simulator_vs_pennylane_parity():
    """Verify that PyTorch statevector simulator exactly matches PennyLane (atol < 1e-5) on outputs and gradients."""
    torch.manual_seed(101)
    
    # Single patch input in [0, 1]
    patch = torch.tensor([0.25, 0.65, 0.15, 0.85], dtype=torch.float32)
    weights_sim = torch.nn.Parameter(torch.rand(1, 4, 2, dtype=torch.float32) * 2.0 * float(np.pi))
    weights_pl = torch.nn.Parameter(weights_sim.detach().clone())

    # 1. Simulator forward + backward
    out_sim = simulate_4q_filter(patch.unsqueeze(0), weights_sim)[0]
    loss_sim = out_sim.sum()
    loss_sim.backward()
    grad_sim = weights_sim.grad

    # 2. PennyLane forward + backward
    out_pl = pennylane_filter_circuit(weights_pl, patch)
    loss_pl = out_pl.sum()
    loss_pl.backward()
    grad_pl = weights_pl.grad

    # Assert exact parity
    np.testing.assert_allclose(
        out_sim.detach().numpy(),
        out_pl.detach().numpy(),
        atol=1e-5,
        err_msg="PyTorch simulator output deviates from PennyLane reference!"
    )
    np.testing.assert_allclose(
        grad_sim.detach().numpy(),
        grad_pl.detach().numpy(),
        atol=1e-5,
        err_msg="PyTorch simulator gradient deviates from PennyLane reference!"
    )


# ---------------------------------------------------------------------------
# Test 2: 2-Qubit VQC Head Simulator vs PennyLane Parity
# ---------------------------------------------------------------------------

def test_2q_vqc_simulator_vs_pennylane_parity():
    """Verify 2-qubit VQC head simulation matches PennyLane reference to atol < 1e-5."""
    dev = qml.device("default.qubit", wires=2)

    @qml.qnode(dev, interface="torch", diff_method="backprop")
    def _pl_vqc(w, h_vec):
        qml.Hadamard(wires=0)
        qml.Hadamard(wires=1)
        qml.RZ(h_vec[0], wires=0)
        qml.RZ(h_vec[1], wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RZ(h_vec[0] * h_vec[1], wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RY(w[0], wires=0)
        qml.RY(w[1], wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RY(w[2], wires=0)
        qml.RY(w[3], wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RY(w[4], wires=0)
        qml.RY(w[5], wires=1)
        return qml.expval(qml.PauliZ(0))

    torch.manual_seed(202)
    h = torch.tensor([0.45, -0.75], dtype=torch.float32)
    weights_sim = torch.nn.Parameter(torch.rand(6, dtype=torch.float32) * 2.0 * float(np.pi))
    weights_pl = torch.nn.Parameter(weights_sim.detach().clone())

    out_sim = simulate_2q_vqc(h.unsqueeze(0), weights_sim)[0]
    out_sim.backward()
    grad_sim = weights_sim.grad

    out_pl = _pl_vqc(weights_pl, h)
    out_pl.backward()
    grad_pl = weights_pl.grad

    np.testing.assert_allclose(out_sim.item(), out_pl.item(), atol=1e-5)
    np.testing.assert_allclose(grad_sim.detach().numpy(), grad_pl.detach().numpy(), atol=1e-5)


# ---------------------------------------------------------------------------
# Test 3: Quantum Filter Modes, Shapes, and Value Bounds
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["frozen_random", "trainable", "classical_conv", "none"])
def test_quantum_filter_modes(mode):
    """Test output shapes and value bounds for all 4 quantum filter modes."""
    B = 2
    x = torch.rand(B, 1, 28, 28)
    qf = QuantumFilter(mode=mode, depth=1, seed=42)
    out = qf(x)

    if mode == "none":
        assert out.shape == (B, 1, 28, 28)
    else:
        assert out.shape == (B, 4, 14, 14)
        assert out.min() >= -1.0 - 1e-5
        assert out.max() <= 1.0 + 1e-5


# ---------------------------------------------------------------------------
# Test 4: Gradient Flow in Trainable Mode vs Zero in Frozen Mode
# ---------------------------------------------------------------------------

def test_gradient_flow_frozen_vs_trainable():
    """Verify that trainable filter computes non-zero gradients, while frozen filter has requires_grad=False."""
    x = torch.rand(2, 1, 28, 28)
    targets = torch.tensor([1.0, 0.0])

    # Trainable mode
    model_trainable = HybridQCQModel(filter_mode="trainable", seed=42)
    assert model_trainable.quantum_filter.weights.requires_grad is True
    logits_tr = model_trainable(x)
    loss_tr = nn.BCEWithLogitsLoss()(logits_tr, targets)
    loss_tr.backward()
    assert model_trainable.quantum_filter.weights.grad is not None
    assert model_trainable.quantum_filter.weights.grad.norm().item() > 0.0

    # Frozen mode
    model_frozen = HybridQCQModel(filter_mode="frozen_random", seed=42)
    assert not hasattr(model_frozen.quantum_filter, "grad") or model_frozen.quantum_filter.weights.grad is None
    assert model_frozen.quantum_filter.weights.requires_grad is False


# ---------------------------------------------------------------------------
# Test 5: Seed Identity Between Frozen and Trainable Initial Weights
# ---------------------------------------------------------------------------

def test_seed_identity_between_modes():
    """Verify that frozen_random and trainable modes initialize identical weights for the same seed."""
    seed = 999
    model_frozen = HybridQCQModel(filter_mode="frozen_random", seed=seed)
    model_trainable = HybridQCQModel(filter_mode="trainable", seed=seed)
    
    assert torch.equal(
        model_frozen.quantum_filter.weights,
        model_trainable.quantum_filter.weights
    ), "Initial weights differ between frozen and trainable modes for identical seed!"


# ---------------------------------------------------------------------------
# Test 6: End-to-End Hybrid Model Across All Modes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["frozen_random", "trainable", "classical_conv", "none"])
def test_hybrid_model_end_to_end(mode):
    """Verify end-to-end forward pass, loss computation, and backpropagation across all 4 modes."""
    B = 4
    x = torch.rand(B, 1, 28, 28)
    y = torch.tensor([0.0, 1.0, 0.0, 1.0])

    model = HybridQCQModel(filter_mode=mode, filter_depth=1, seed=42)
    logits = model(x)
    
    assert logits.shape == (B,), f"Expected logits shape ({B},), got {logits.shape}"
    loss = nn.BCEWithLogitsLoss()(logits, y)
    loss.backward()
    
    # Check that backbone and head received gradients
    assert model.backbone.fc2.weight.grad is not None
    assert model.vqc_head.weights.grad is not None
    assert model.vqc_head.scale.grad is not None
    assert model.vqc_head.bias.grad is not None


# ---------------------------------------------------------------------------
# Test 7: Correlated Multi-Observable Pauli Readout vs PennyLane & End-to-End
# ---------------------------------------------------------------------------

def test_correlated_vqc_simulator_vs_pennylane_parity():
    """Verify [<Z0>, <Z1>, <Z0*Z1>] measurement matches PennyLane to atol < 1e-5."""
    dev = qml.device("default.qubit", wires=2)

    @qml.qnode(dev, interface="torch", diff_method="backprop")
    def _pl_vqc_correlated(w, h_vec):
        qml.Hadamard(wires=0)
        qml.Hadamard(wires=1)
        qml.RZ(h_vec[0], wires=0)
        qml.RZ(h_vec[1], wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RZ(h_vec[0] * h_vec[1], wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RY(w[0], wires=0)
        qml.RY(w[1], wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RY(w[2], wires=0)
        qml.RY(w[3], wires=1)
        qml.CNOT(wires=[0, 1])
        qml.RY(w[4], wires=0)
        qml.RY(w[5], wires=1)
        return [
            qml.expval(qml.PauliZ(0)),
            qml.expval(qml.PauliZ(1)),
            qml.expval(qml.PauliZ(0) @ qml.PauliZ(1)),
        ]

    torch.manual_seed(303)
    h = torch.tensor([0.55, -0.35], dtype=torch.float32)
    weights_sim = torch.nn.Parameter(torch.rand(6, dtype=torch.float32) * 2.0 * float(np.pi))
    weights_pl = torch.nn.Parameter(weights_sim.detach().clone())

    out_sim = simulate_2q_vqc_correlated(h.unsqueeze(0), weights_sim)[0]  # shape (3,)
    loss_sim = out_sim.sum()
    loss_sim.backward()

    expvals_pl = _pl_vqc_correlated(weights_pl, h)
    out_pl = torch.stack(expvals_pl)
    loss_pl = out_pl.sum()
    loss_pl.backward()

    # Verify all 3 observables match
    np.testing.assert_allclose(
        out_sim.detach().numpy(),
        out_pl.detach().numpy(),
        atol=1e-5,
        err_msg="Correlated Pauli-Z expectations deviate from PennyLane!"
    )
    # Verify parameter gradients match
    np.testing.assert_allclose(
        weights_sim.grad.detach().numpy(),
        weights_pl.grad.detach().numpy(),
        atol=1e-5,
        err_msg="Correlated Pauli-Z gradients deviate from PennyLane!"
    )


def test_correlated_vqc_head_and_hybrid_model():
    """Verify CorrelatedVQCHead and HybridQCQModel with correlated readout end-to-end."""
    B = 4
    h = torch.randn(B, 2)
    head = CorrelatedVQCHead(seed=42)
    logits = head(h)
    assert logits.shape == (B,), f"Expected shape ({B},), got {logits.shape}"

    # Backward pass through head
    target = torch.tensor([1.0, 0.0, 1.0, 0.0])
    loss = nn.BCEWithLogitsLoss()(logits, target)
    loss.backward()
    assert head.weights.grad is not None
    assert head.readout.weight.grad is not None
    assert head.readout.bias.grad is not None

    # Full end-to-end hybrid model with correlated readout
    x = torch.rand(B, 1, 28, 28)
    model = HybridQCQModel(filter_mode="trainable", use_correlated_readout=True, seed=42)
    out = model(x)
    assert out.shape == (B,)
    loss_full = nn.BCEWithLogitsLoss()(out, target)
    loss_full.backward()
    assert model.quantum_filter.weights.grad is not None
    assert model.vqc_head.readout.weight.grad is not None

