"""Vectorized pure-PyTorch statevector simulator for batched 4-qubit quanvolution & 2-qubit VQC."""

import numpy as np
import torch
import torch.nn as nn


def ry_matrix(theta: torch.Tensor) -> torch.Tensor:
    """Compute single-qubit RY rotation unitary for a batch of angles.
    
    RY(theta) = [[cos(theta/2), -sin(theta/2)],
                 [sin(theta/2),  cos(theta/2)]]
    Args:
        theta: Tensor of shape (M,)
    Returns:
        Complex tensor of shape (M, 2, 2)
    """
    half_theta = theta * 0.5
    c = torch.cos(half_theta)
    s = torch.sin(half_theta)
    row0 = torch.stack([c, -s], dim=-1)
    row1 = torch.stack([s, c], dim=-1)
    return torch.stack([row0, row1], dim=-2).to(torch.complex64)


def rz_matrix(phi: torch.Tensor) -> torch.Tensor:
    """Compute single-qubit RZ rotation unitary for a batch of angles.
    
    RZ(phi) = [[exp(-i*phi/2), 0],
               [0, exp(i*phi/2)]]
    Args:
        phi: Tensor of shape (M,)
    Returns:
        Complex tensor of shape (M, 2, 2)
    """
    half_phi = phi.to(torch.complex64) * 0.5
    e_neg = torch.exp(-1.0j * half_phi)
    e_pos = torch.exp(1.0j * half_phi)
    zeros = torch.zeros_like(phi, dtype=torch.complex64)
    row0 = torch.stack([e_neg, zeros], dim=-1)
    row1 = torch.stack([zeros, e_pos], dim=-1)
    return torch.stack([row0, row1], dim=-2)


def hadamard_matrix(M: int, device: torch.device) -> torch.Tensor:
    """Generate batched 2x2 Hadamard gate matrix."""
    val = float(1.0 / np.sqrt(2.0))
    H = torch.tensor([[val, val], [val, -val]], dtype=torch.complex64, device=device)
    return H.unsqueeze(0).expand(M, 2, 2)


def apply_gate_4q(state: torch.Tensor, U: torch.Tensor, wire: int) -> torch.Tensor:
    """Apply batched single-qubit gate U (M, 2, 2) to wire in 4-qubit state (M, 2, 2, 2, 2)."""
    if wire == 0:
        return torch.einsum("mja, mabcd -> mjbcd", U, state)
    elif wire == 1:
        return torch.einsum("mjb, mabcd -> majcd", U, state)
    elif wire == 2:
        return torch.einsum("mjc, mabcd -> mabjd", U, state)
    elif wire == 3:
        return torch.einsum("mjd, mabcd -> mabcj", U, state)
    else:
        raise ValueError(f"Invalid wire index {wire} for 4-qubit circuit.")


def cnot_4q(state: torch.Tensor, control: int, target: int) -> torch.Tensor:
    """Apply CNOT gate between adjacent qubits in 4-qubit state (M, 2, 2, 2, 2)."""
    if control == 0 and target == 1:
        return torch.stack([state[:, 0, :, :, :], state[:, 1, :, :, :].flip(dims=[1])], dim=1)
    elif control == 1 and target == 2:
        return torch.stack([state[:, :, 0, :, :], state[:, :, 1, :, :].flip(dims=[2])], dim=2)
    elif control == 2 and target == 3:
        return torch.stack([state[:, :, :, 0, :], state[:, :, :, 1, :].flip(dims=[3])], dim=3)
    else:
        raise ValueError(f"Unsupported CNOT control={control}, target={target} in 4-qubit simulator.")


def expval_z_4q(state: torch.Tensor) -> torch.Tensor:
    """Measure Pauli-Z expectations on all 4 qubits.
    
    Args:
        state: Tensor of shape (M, 2, 2, 2, 2)
    Returns:
        Tensor of shape (M, 4) with expectations in [-1.0, 1.0]
    """
    prob = state.real**2 + state.imag**2
    z0 = prob[:, 0, :, :, :].sum(dim=(1, 2, 3)) - prob[:, 1, :, :, :].sum(dim=(1, 2, 3))
    z1 = prob[:, :, 0, :, :].sum(dim=(1, 2, 3)) - prob[:, :, 1, :, :].sum(dim=(1, 2, 3))
    z2 = prob[:, :, :, 0, :].sum(dim=(1, 2, 3)) - prob[:, :, :, 1, :].sum(dim=(1, 2, 3))
    z3 = prob[:, :, :, :, 0].sum(dim=(1, 2, 3)) - prob[:, :, :, :, 1].sum(dim=(1, 2, 3))
    return torch.stack([z0, z1, z2, z3], dim=-1)


def simulate_4q_filter(patches: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
    """Simulate 4-qubit quantum filter for a batch of 2x2 patches.
    
    Args:
        patches: Pixel inputs of shape (M, 4), values in [0.0, 1.0]
        weights: Variational parameters of shape (L, 4, 2)
    Returns:
        Tensor of shape (M, 4) containing Pauli-Z expectations <Z_i> in [-1.0, 1.0]
    """
    M = patches.shape[0]
    device = patches.device
    
    # Initialize |0000> state
    state = torch.zeros((M, 2, 2, 2, 2), dtype=torch.complex64, device=device)
    state[:, 0, 0, 0, 0] = 1.0

    # 1. Angle encoding: RY(pi * x_i) on wire i
    pi_const = float(np.pi)
    for i in range(4):
        u_enc = ry_matrix(pi_const * patches[:, i])
        state = apply_gate_4q(state, u_enc, i)

    # 2. Variational layers
    L = weights.shape[0]
    for l in range(L):
        # RZ(a) then RY(b) per qubit
        for i in range(4):
            u_rz = rz_matrix(weights[l, i, 0].expand(M))
            state = apply_gate_4q(state, u_rz, i)
            u_ry = ry_matrix(weights[l, i, 1].expand(M))
            state = apply_gate_4q(state, u_ry, i)
        # Entangling CNOT chain: 0-1, 1-2, 2-3
        state = cnot_4q(state, 0, 1)
        state = cnot_4q(state, 1, 2)
        state = cnot_4q(state, 2, 3)

    # 3. Measure Pauli-Z expectations
    return expval_z_4q(state)


# ---------------------------------------------------------------------------
# 2-Qubit Statevector Simulator for VQC Classifier Head
# ---------------------------------------------------------------------------

def apply_gate_2q(state: torch.Tensor, U: torch.Tensor, wire: int) -> torch.Tensor:
    """Apply batched single-qubit gate U (B, 2, 2) to wire in 2-qubit state (B, 2, 2)."""
    if wire == 0:
        return torch.einsum("mja, mab -> mjb", U, state)
    elif wire == 1:
        return torch.einsum("mjb, mab -> maj", U, state)
    else:
        raise ValueError(f"Invalid wire index {wire} for 2-qubit circuit.")


def cnot_2q(state: torch.Tensor) -> torch.Tensor:
    """Apply CNOT(0, 1) to 2-qubit state (B, 2, 2)."""
    return torch.stack([state[:, 0, :], state[:, 1, :].flip(dims=[1])], dim=1)


def expval_z0_2q(state: torch.Tensor) -> torch.Tensor:
    """Measure Pauli-Z expectation on qubit 0 for 2-qubit state.
    
    Returns:
        Tensor of shape (B,) with values in [-1.0, 1.0]
    """
    prob = state.real**2 + state.imag**2
    return prob[:, 0, :].sum(dim=1) - prob[:, 1, :].sum(dim=1)


def expval_correlated_2q(state: torch.Tensor) -> torch.Tensor:
    """Measure multi-observable Pauli-Z basis [<Z0>, <Z1>, <Z0*Z1>] on 2-qubit state.
    
    Basis representations:
      P_00 = prob[:, 0, 0]
      P_01 = prob[:, 0, 1]
      P_10 = prob[:, 1, 0]
      P_11 = prob[:, 1, 1]
      
    Expectations:
      <Z0>    = (P_00 + P_01) - (P_10 + P_11)
      <Z1>    = (P_00 + P_10) - (P_01 + P_11)
      <Z0*Z1> = (P_00 + P_11) - (P_01 + P_10)  (Preserves 2-qubit entanglement)
      
    Returns:
        Tensor of shape (B, 3) with expectations in [-1.0, 1.0]
    """
    prob = state.real**2 + state.imag**2
    p00 = prob[:, 0, 0]
    p01 = prob[:, 0, 1]
    p10 = prob[:, 1, 0]
    p11 = prob[:, 1, 1]

    z0 = (p00 + p01) - (p10 + p11)
    z1 = (p00 + p10) - (p01 + p11)
    z0z1 = (p00 + p11) - (p01 + p10)

    return torch.stack([z0, z1, z0z1], dim=-1)


def _build_2q_vqc_state(h: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
    """Internal helper to construct the final 2-qubit statevector."""
    B = h.shape[0]
    device = h.device

    # Initialize |00>
    state = torch.zeros((B, 2, 2), dtype=torch.complex64, device=device)
    state[:, 0, 0] = 1.0

    # Feature map
    H = hadamard_matrix(B, device)
    state = apply_gate_2q(state, H, 0)
    state = apply_gate_2q(state, H, 1)

    state = apply_gate_2q(state, rz_matrix(h[:, 0]), 0)
    state = apply_gate_2q(state, rz_matrix(h[:, 1]), 1)

    state = cnot_2q(state)
    state = apply_gate_2q(state, rz_matrix(h[:, 0] * h[:, 1]), 1)
    state = cnot_2q(state)

    # RealAmplitudes ansatz
    state = apply_gate_2q(state, ry_matrix(weights[0].expand(B)), 0)
    state = apply_gate_2q(state, ry_matrix(weights[1].expand(B)), 1)
    state = cnot_2q(state)

    state = apply_gate_2q(state, ry_matrix(weights[2].expand(B)), 0)
    state = apply_gate_2q(state, ry_matrix(weights[3].expand(B)), 1)
    state = cnot_2q(state)

    state = apply_gate_2q(state, ry_matrix(weights[4].expand(B)), 0)
    state = apply_gate_2q(state, ry_matrix(weights[5].expand(B)), 1)

    return state


def simulate_2q_vqc(h: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
    """Simulate 2-qubit VQC head measuring single-qubit <Z0>."""
    state = _build_2q_vqc_state(h, weights)
    return expval_z0_2q(state)


def simulate_2q_vqc_correlated(h: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
    """Simulate 2-qubit VQC head measuring multi-observable basis [<Z0>, <Z1>, <Z0*Z1>].
    
    Args:
        h: Latent rotation angles of shape (B, 2) in [-pi, pi]
        weights: Trainable RealAmplitudes parameters of shape (6,)
    Returns:
        Tensor of shape (B, 3) containing [<Z0>, <Z1>, <Z0*Z1>]
    """
    state = _build_2q_vqc_state(h, weights)
    return expval_correlated_2q(state)

