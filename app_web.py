"""QForge Web Studio: Modern Interactive Hybrid Quantum-Classical MRI Diagnostic Platform.

Author: Team QForge (IIIT Kottayam)
Lead: Yashwanth S (2024BCS0264)
Run with: .\\.venv\\Scripts\\streamlit.exe run app_web.py
"""

import io
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import streamlit as st
import torch
import torch.nn.functional as F

from qforge.models import HybridQCQModel
from qforge.noise import NoisyQuantumEvaluator


# ---------------------------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="QForge | Quantum-Classical MRI Studio",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Global dark-mode aesthetic */
    .stApp {
        background-color: #060910;
        color: #D7E4EA;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    }
    .metric-card {
        background: #0A1019;
        border: 1px solid #1B2A3A;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .status-badge-malignant {
        background-color: rgba(255, 77, 94, 0.15);
        color: #FF4D5E;
        border: 1px solid #FF4D5E;
        border-radius: 6px;
        padding: 4px 12px;
        font-weight: 700;
        display: inline-block;
    }
    .status-badge-benign {
        background-color: rgba(57, 255, 136, 0.15);
        color: #39FF88;
        border: 1px solid #39FF88;
        border-radius: 6px;
        padding: 4px 12px;
        font-weight: 700;
        display: inline-block;
    }
    .highlight-cyan {
        color: #00E5FF;
        font-weight: bold;
    }
    .highlight-violet {
        color: #B26BFF;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cached Model Loader
# ---------------------------------------------------------------------------

@st.cache_resource
def load_cached_models():
    """Instantiate and cache the 3 hybrid architecture variants."""
    models = {
        "Model A (Frozen Random)": HybridQCQModel(filter_mode="frozen_random", seed=42),
        "Model B (Trainable Filter)": HybridQCQModel(filter_mode="trainable", seed=42),
        "Model B + Correlated Readout": HybridQCQModel(
            filter_mode="trainable", use_correlated_readout=True, seed=42
        ),
    }
    for m in models.values():
        m.eval()
    return models


MODELS = load_cached_models()


# ---------------------------------------------------------------------------
# Preprocessing Helper
# ---------------------------------------------------------------------------

def preprocess_image(pil_img: Image.Image) -> Tuple[torch.Tensor, np.ndarray]:
    """Convert input image to 28x28 normalized grayscale tensor and numpy array."""
    img_gray = pil_img.convert("L").resize((28, 28), Image.Resampling.BICUBIC)
    arr_28 = np.array(img_gray, dtype=np.float32) / 255.0
    tensor_28 = torch.from_numpy(arr_28).unsqueeze(0).unsqueeze(0)  # (1, 1, 28, 28)
    return tensor_28, arr_28


def generate_synthetic_mri(pattern: str = "glioma") -> Image.Image:
    """Generate representative synthetic MRI slice for quick demo testing."""
    x = np.linspace(-1, 1, 128)
    y = np.linspace(-1, 1, 128)
    xx, yy = np.meshgrid(x, y)
    r = np.sqrt(xx**2 + yy**2)

    # Skull / brain outer boundary
    brain = (r < 0.85).astype(float) * 0.4
    ventricles = ((np.abs(xx) < 0.15) & (np.abs(yy) < 0.4)).astype(float) * 0.1

    if pattern == "glioma":
        # Hyperintense infiltrative lesion in left lobe
        tumor = np.exp(-((xx - 0.35)**2 + (yy - 0.25)**2) / 0.04) * 0.55
    else:
        # Circumscribed focal lesion
        tumor = np.exp(-((xx + 0.35)**2 + (yy + 0.35)**2) / 0.015) * 0.40

    img_arr = np.clip(brain - ventricles + tumor + np.random.normal(0, 0.02, xx.shape), 0.0, 1.0)
    return Image.fromarray((img_arr * 255).astype(np.uint8))


# ---------------------------------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------------------------------

with st.sidebar:
    st.image("https://raw.githubusercontent.com/Agnivesh-Anil-Warrier/QuForge/main/assets/banner.png" if False else "https://img.shields.io/badge/IIIT_Kottayam-Quantum_Computing-00E5FF?style=for-the-badge", use_container_width=True)
    st.title("⚛️ QForge Studio")
    st.caption("Hybrid Quantum-Classical-Quantum CNN (QCQ-CNN)")

    st.markdown("---")
    st.markdown("**Team QForge (IIIT Kottayam)**")
    st.markdown("- **Yashwanth S** *(Team Lead — 2024BCS0264)*")
    st.markdown("- Agnivesh Anil Warrier *(2024BCS0256)*")
    st.markdown("- N. Vishnuvardhan Reddy *(2024BCD0064)*")
    st.markdown("- B. Bharath Kumar *(2024BCS0160)*")
    st.markdown("- A. Krishna Bharadwaj Reddy *(2024BCS0295)*")

    st.markdown("---")
    st.markdown("### 🎛️ Simulation Controls")
    selected_model_name = st.selectbox(
        "Select Active Architecture",
        [
            "Model B + Correlated Readout (Our Full Model)",
            "Model B (Trainable Filter + Single-Qubit VQC)",
            "Model A (Frozen Random Baseline — Nature 2025)",
        ],
    )

    st.markdown("### ⚡ NISQ Noise Settings")
    sim_noise = st.checkbox("Enable Simulated Quantum Noise", value=False)
    gamma_rate = st.slider("Depolarizing Rate γ", 0.00, 0.05, 0.02, step=0.005) if sim_noise else 0.0
    shots = st.select_slider("Measurement Shots", options=[128, 256, 512, 1024, "Infinite (Exact)"], value=1024) if sim_noise else None
    shots_int = None if shots == "Infinite (Exact)" else shots

    st.markdown("---")
    st.info("💡 **Tip**: Upload an MRI slice or use the 1-click presets in Tab 1 to test live inference.")


# ---------------------------------------------------------------------------
# Main Tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs([
    "🔬 Live MRI Inference & Quantum Filters",
    "📊 Benchmark Matrix & Statistics",
    "🛡️ NISQ Noise Resilience (Ch 4.6)",
    "📑 Publication Figures & Report",
])


# ===========================================================================
# TAB 1: Live Diagnostic Inference
# ===========================================================================

with tab1:
    st.subheader("Live Diagnostic Inference & 4-Channel Quantum Filter Visualization")
    st.write("Upload a brain MRI scan or select a preset to evaluate quantum feature map extraction and classification.")

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    with col_btn1:
        use_glioma = st.button("🧪 Sample 1: Malignant Glioma")
    with col_btn2:
        use_benign = st.button("🧪 Sample 2: Benign Meningioma")

    uploaded_file = st.file_uploader("Or Upload MRI Image (JPG / PNG)", type=["png", "jpg", "jpeg"])

    pil_image = None
    if use_glioma:
        pil_image = generate_synthetic_mri("glioma")
    elif use_benign:
        pil_image = generate_synthetic_mri("benign")
    elif uploaded_file is not None:
        pil_image = Image.open(uploaded_file)
    else:
        # Default placeholder demo
        pil_image = generate_synthetic_mri("glioma")

    tensor_28, arr_28 = preprocess_image(pil_image)

    # Determine active model
    if "Correlated" in selected_model_name:
        active_model = MODELS["Model B + Correlated Readout"]
        model_tag = "Model B + Correlated Readout"
    elif "Model B" in selected_model_name:
        active_model = MODELS["Model B (Trainable Filter)"]
        model_tag = "Model B (Trainable Filter)"
    else:
        active_model = MODELS["Model A (Frozen Random)"]
        model_tag = "Model A (Frozen Random)"

    # Forward pass
    with torch.no_grad():
        # 1. Quantum Filter features
        feat_map = active_model.quantum_filter(tensor_28)  # (1, 4, 14, 14)
        if sim_noise and gamma_rate > 0.0:
            evaluator = NoisyQuantumEvaluator(
                single_qubit_gamma=gamma_rate,
                two_qubit_gamma_multiplier=2.0,
                shots=shots_int,
                seed=42,
            )
            feat_map = evaluator.evaluate_filter_output(feat_map)

        # 2. Classical CNN backbone
        angles = active_model.backbone(feat_map)  # (1, 2)

        # 3. VQC Head
        if sim_noise and gamma_rate > 0.0:
            logits = evaluator.evaluate_vqc_logits(angles, active_model.vqc_head)
        else:
            logits = active_model.vqc_head(angles)

        prob_malignant = float(torch.sigmoid(logits).item())
        prob_benign = 1.0 - prob_malignant
        is_malignant = prob_malignant >= 0.5

    # Layout: MRI, Quantum Channels, Prediction
    col_input, col_channels, col_result = st.columns([1, 2, 1.2])

    with col_input:
        st.markdown("**1. Preprocessed Input (28×28)**")
        fig_in, ax_in = plt.subplots(figsize=(3, 3), dpi=150)
        ax_in.imshow(arr_28, cmap="bone")
        ax_in.axis("off")
        ax_in.set_title("Normalized MRI Slice", fontsize=9, color="#D7E4EA")
        fig_in.patch.set_facecolor("#0A1019")
        st.pyplot(fig_in)
        plt.close(fig_in)

    with col_channels:
        st.markdown("**2. Quantum Filter Channels $\\langle Z_i \\rangle$ (14×14 each)**")
        fig_ch, axes = plt.subplots(1, 4, figsize=(10, 2.5), dpi=150)
        ch_names = ["Qubit 0 (Wire 0)", "Qubit 1 (Wire 1)", "Qubit 2 (Wire 2)", "Qubit 3 (Wire 3)"]
        feat_np = feat_map.squeeze(0).cpu().numpy()

        for i in range(4):
            im = axes[i].imshow(feat_np[i], cmap="magma", vmin=-1.0, vmax=1.0)
            axes[i].set_title(ch_names[i], fontsize=8, color="#00E5FF")
            axes[i].axis("off")

        fig_ch.patch.set_facecolor("#0A1019")
        st.pyplot(fig_ch)
        plt.close(fig_ch)

    with col_result:
        st.markdown("**3. Diagnostic Classification**")
        st.markdown(f"<div class='metric-card'>"
                    f"<p style='margin:0; font-size:12px; color:#6F8896;'>ACTIVE ARCHITECTURE</p>"
                    f"<p style='margin:0; font-size:14px; font-weight:bold; color:#00E5FF;'>{model_tag}</p>"
                    f"<hr style='border-color:#1B2A3A; margin:8px 0;'>"
                    f"<p style='margin:0; font-size:12px; color:#6F8896;'>DIAGNOSTIC OUTCOME</p>"
                    f"{'<span class=\"status-badge-malignant\">MALIGNANT NEOPLASM</span>' if is_malignant else '<span class=\"status-badge-benign\">BENIGN NEOPLASM</span>'}"
                    f"<p style='margin:8px 0 0 0; font-size:24px; font-weight:bold; color:#D7E4EA;'>{max(prob_malignant, prob_benign)*100:.1f}%</p>"
                    f"<p style='margin:0; font-size:11px; color:#6F8896;'>Classification Confidence</p>"
                    f"</div>", unsafe_allow_html=True)

        st.progress(float(prob_malignant))
        st.caption(f"Malignant probability: {prob_malignant*100:.2f}% | Benign probability: {prob_benign*100:.2f}%")

    # Quantum state introspection
    st.markdown("---")
    st.markdown("### ⚛️ Terminal VQC Quantum State Introspection")
    col_vqc1, col_vqc2 = st.columns([1, 1])

    with col_vqc1:
        st.markdown("**Latent Rotation Angle Vector $h = [h_0, h_1]^T$ in $[-\\pi, \\pi]$**")
        h0_val = float(angles[0, 0].item())
        h1_val = float(angles[0, 1].item())
        st.write(f"- Angle $h_0$: `{h0_val:.4f}` rad (`{h0_val/np.pi:.2f}π`)")
        st.write(f"- Angle $h_1$: `{h1_val:.4f}` rad (`{h1_val/np.pi:.2f}π`)")

    with col_vqc2:
        st.markdown("**Measured Pauli-Z Observable Basis**")
        if hasattr(active_model.vqc_head, "readout"):
            from qforge.qsim import simulate_2q_vqc_correlated
            expvals = simulate_2q_vqc_correlated(angles, active_model.vqc_head.weights)[0].cpu().numpy()
            st.write(f"- Single Observable $\\langle Z_0 \\rangle$: `{expvals[0]:.4f}`")
            st.write(f"- Single Observable $\\langle Z_1 \\rangle$: `{expvals[1]:.4f}`")
            st.write(f"- **Entanglement Observable $\\langle Z_0 Z_1 \\rangle$**: `{expvals[2]:.4f}` *(Preserves 2-Qubit Entanglement)*")
        else:
            from qforge.qsim import simulate_2q_vqc
            z0_val = float(simulate_2q_vqc(angles, active_model.vqc_head.weights)[0].item())
            st.write(f"- Single Observable $\\langle Z_0 \\rangle$: `{z0_val:.4f}`")
            st.caption("*(Single-qubit readout discards second-qubit and joint entanglement)*")


# ===========================================================================
# TAB 2: Benchmark Matrix & Statistics
# ===========================================================================

with tab2:
    st.subheader("Experimental Benchmarks & Statistical Verification")
    st.write("Rigorous 5-seed evaluation on the deduplicated Kaggle Brain Tumor MRI benchmark:")

    bench_data = {
        "Architecture": [
            "Model A (Frozen Random — Nature 2025)",
            "Model B (Trainable Filter)",
            "Model B + Correlated Readout (QForge Full)",
        ],
        "Front Quantum Filter": ["Frozen (Random Unitary)", "Trainable (Autograd)", "Trainable (Autograd)"],
        "VQC Readout": ["Single <Z0>", "Single <Z0>", "Correlated [<Z0>, <Z1>, <Z0*Z1>]"],
        "Test Accuracy": ["85.75% ± 1.66%", "85.36% ± 1.14%", "87.25% ± 0.95%"],
        "ROC-AUC": ["87.33% ± 1.94%", "87.34% ± 1.11%", "88.90% ± 0.85%"],
        "F1 Score": ["77.77% ± 3.44%", "77.58% ± 1.61%", "79.80% ± 1.20%"],
        "Parameter Drift ||θ - θ₀||": ["0.0000 rad", "1.8286 ± 0.93 rad", "1.9120 ± 0.80 rad"],
    }
    st.table(bench_data)

    st.markdown("### 📌 Key Findings for Faculty Review")
    st.markdown("""
    1. **Parameter Plasticity**: Trainable quantum filters exhibit substantial Euclidean drift ($||\\theta - \\theta_0||_2 \\approx 1.83\\text{ rad}$), confirming active non-vanishing gradient descent through the quantum Hilbert space.
    2. **Reservoir Projector Effect**: When using a single $\\langle Z_0 \\rangle$ readout, frozen random filters match trainable filters ($p > 0.05$), behaving as zero-cost non-linear reservoir projectors.
    3. **Correlated Readout Advantage**: Augmenting the terminal VQC with joint observable $\\langle Z_0 Z_1 \\rangle$ breaks the bottleneck by capturing multi-qubit entanglement correlations, improving test accuracy to **87.25%** and AUC to **88.90%**.
    """)


# ===========================================================================
# TAB 3: NISQ Noise Resilience
# ===========================================================================

with tab3:
    st.subheader("NISQ Hardware Noise Resilience (Chapter 4.6)")
    st.write("Evaluation of model robustness under depolarizing quantum gate noise and finite measurement shots:")

    noise_fig_path = PROJECT_ROOT / "results" / "figures" / "noise_resilience.png"
    if noise_fig_path.exists():
        st.image(str(noise_fig_path), caption="Depolarizing Error Rate (γ) vs. Classification Accuracy (%)", use_container_width=True)
    else:
        st.warning("Noise resilience chart not found. Run scripts/evaluate_noise.py to generate.")

    st.markdown("### 🔍 Chapter 4.6 Findings")
    st.markdown("""
    - **Model A (Frozen Filter)** experiences a **-10.54% drop** in accuracy under typical NISQ hardware noise levels ($\\gamma = 0.02 - 0.03$).
    - **Model B (Trainable Filter)** suffers only a **-3.87% drop**.
    - **Model B + Correlated Readout** demonstrates superior noise resilience with only a **-2.75% drop**, retaining over **84.5% accuracy** even under high gate error rates.
    """)


# ===========================================================================
# TAB 4: Scientific Figures & Documentation
# ===========================================================================

with tab4:
    st.subheader("Publication Figures & Research Artifacts")
    fig_cols = st.columns(2)

    figs = [
        ("Learning Dynamics (Fig 1)", PROJECT_ROOT / "reports" / "figures" / "fig1_learning_curves.png"),
        ("Quantum Parameter Drift (Fig 2)", PROJECT_ROOT / "reports" / "figures" / "fig2_parameter_drift.png"),
        ("Confusion Matrices & ROC (Fig 3)", PROJECT_ROOT / "reports" / "figures" / "fig3_confusion_and_roc.png"),
        ("Quantum Feature Maps (Fig 5)", PROJECT_ROOT / "reports" / "figures" / "fig5_quantum_feature_maps.png"),
    ]

    for idx, (title, path) in enumerate(figs):
        with fig_cols[idx % 2]:
            st.markdown(f"**{title}**")
            if path.exists():
                st.image(str(path), use_container_width=True)
            else:
                st.info(f"Figure not found at {path}")
