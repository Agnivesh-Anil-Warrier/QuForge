# QForge: Hybrid Quantum-Classical Brain MRI Classifier (QCQ-CNN)

Reproducing and extending Long et al. (2025), *"Hybrid quantum-classical-quantum convolutional neural networks"*, Scientific Reports 15, 31780.

## 🎯 Project Overview
- **Paper Baseline**: 4-qubit quantum convolutional filter (quanvolution) with **frozen random parameters** + Classical CNN backbone + 2-qubit Variational Quantum Classifier (VQC) head.
- **QForge Contribution**: Upgrade the quantum convolutional filter to **trainable end-to-end parameters** optimized via PyTorch autograd gradients.
- **Goal**: Rigorously test whether end-to-end trainable quantum filters provide measurable performance benefits (Accuracy, F1, ROC-AUC) or if parameters remain trapped (parameter drift $||\theta - \theta_{\text{init}}||$).

---

## 💻 Environment & Setup

### Target Hardware Specification
Designed for CPU-only execution (e.g. AMD Ryzen 7 5700U / 8 physical cores / 16 threads / 16 GB RAM).

### Virtual Environment Setup

#### Windows (PowerShell)
```powershell
# In case script execution is blocked on Windows:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Create and activate venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade build tools
python -m pip install --upgrade pip setuptools wheel

# Install CPU PyTorch and dependencies
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

#### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

> **Note**: Always invoke the virtual environment explicitly if running automated scripts:
> - Windows: `.\.venv\Scripts\python.exe ...`
> - Linux/macOS: `./.venv/bin/python ...`

---

## 📁 Repository Structure
```
qforge-qmri/
├── README.md               # Project documentation and reproduction instructions
├── requirements.txt        # High-level dependencies (excluding PyTorch)
├── requirements-lock.txt   # Exact pinned versions
├── configs/
│   └── base.yaml           # Default hyperparameters & dataset mapping
├── data/
│   ├── raw/                # Unprocessed Kaggle MRI dataset (gitignored)
│   ├── cache/              # Cached preprocessed .npy tensors (gitignored)
│   └── splits/             # Stratified train/val/test CSV manifests
├── src/
│   └── qforge/
│       ├── data.py           # Dataset pipeline, label mapping, deduplication
│       ├── qsim.py           # Vectorized pure-PyTorch 4-qubit statevector simulator
│       ├── quantum_filter.py # Frozen, Trainable, Classical-conv, and None filters
│       ├── models.py         # Classical backbone & 2-qubit VQC head
│       ├── train.py          # Resumable training engine with epoch checkpointing
│       ├── evaluate.py       # Evaluation metrics, ROC-AUC, confusion matrices
│       └── utils.py          # Seeding, YAML configs, logging, timing
├── scripts/
│   ├── run_experiment.py   # Run single experiment configuration
│   ├── run_all.py          # Automated sequential experiment grid runner
│   └── make_report.py      # Generate figures and report summary tables
├── tests/                  # Pytest suite validating statevector sim vs PennyLane
├── results/
│   ├── hardware_info.txt   # Detected system hardware specs
│   ├── runs/               # Experiment logs, metrics, and checkpoints
│   ├── figures/            # Plots, curves, and visualization outputs
│   └── summary.csv         # Aggregated benchmark results across seeds
└── notebooks/              # Exploration and visualization notebooks
```

---

## 🏷️ Dataset & Label Mapping
- **Source**: Kaggle *Brain Tumor MRI Dataset* (Masoud Nickparvar, CC0).
- **Binary Classification Mapping**:
  - `glioma` $\to$ **Malignant (1)**
  - `meningioma` & `pituitary` $\to$ **Benign (0)**
  - `notumor` $\to$ **Excluded** (Task is Benign vs. Malignant tumor diagnosis)
- **Image Preprocessing**: Grayscale conversion, resized to $28 \times 28$, normalized to $[0, 1]$, cached as `.npy` tensors.

---

## 🔬 Documented Paper Deviations
1. **Simulation Framework**: PyTorch vectorized statevector simulator + PennyLane reference, replacing IBM Qiskit Aer to achieve fast batch processing on CPU.
2. **Batch Training**: Batch size 32 with Adam optimizer (paper used batch size 1).
3. **Trainable Filter**: End-to-end autograd optimization through the quantum convolution stage with separate learning rate.
