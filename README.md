# QForge: Hybrid Quantum-Classical Brain MRI Classifier (QCQ-CNN)

Reproducing and extending Long et al. (2025), *"Hybrid quantum-classical-quantum convolutional neural networks"*, Scientific Reports 15, 31780.

## 🎯 Project Overview
- **Paper Baseline**: 4-qubit quantum convolutional filter (quanvolution) with **frozen random parameters** + Classical CNN backbone + 2-qubit Variational Quantum Classifier (VQC) head.
- **QForge Contribution**: Upgrade the front-end quantum convolutional filter to **trainable end-to-end parameters** optimized via PyTorch autograd gradients.
- **Goal**: Rigorously test whether end-to-end trainable quantum filters provide measurable generalization gains (Accuracy, F1, ROC-AUC) or if parameters remain trapped (parameter drift $||\theta - \theta_{\text{init}}||$).

---

## 💻 Environment & Setup

### Target Hardware Specification
Designed for CPU-only execution (e.g., AMD Ryzen 7 5700U / 8 physical cores / 16 threads / 16 GB RAM).

### Virtual Environment Setup

#### Windows (PowerShell)
```powershell
# In case script execution is blocked on Windows PowerShell:
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

> **Note**: To invoke virtual environment executables reliably on Windows:
> - `.\.venv\Scripts\python.exe <script.py>`
> - `.\.venv\Scripts\pytest.exe`

---

## 🚀 Execution & Reproduction Guide

### Phase 1: Data Pipeline & Leakage Deduplication
```powershell
.\.venv\Scripts\python.exe scripts\prepare_data.py
```
- Deduplicates images via MD5 and perceptual hashing (pruned 110 cross-split duplicates).
- Caches preprocessed $28 \times 28$ grayscale tensors as `.npy` in `data/cache/`.

### Phase 2 & 4: Parity Tests, Smoke Tests & Time Budgeting
```powershell
# Run unit tests (PennyLane parity, output shapes, gradient flow, determinism)
.\.venv\Scripts\pytest.exe -v

# Run smoke test & timing benchmark
.\.venv\Scripts\python.exe scripts\benchmark_and_smoke.py
```

### Phase 5: Sequential Grid Experiment Runner
```powershell
# Run the automated experiment grid with checkpointing and resume support
.\.venv\Scripts\python.exe scripts\run_all.py
```
- Sequentially executes 32 configurations (Model A, B, C, D + Ablations).
- Checkpoints every epoch; automatically resumes interrupted runs without re-training.
- Real-time logging to `results/progress.log`.

### Phase 6 & 7: Statistical Analysis & Visualization Engine
```powershell
.\.venv\Scripts\python.exe scripts\make_report.py
```
- Aggregates all completed runs into `results/summary.csv` and `results/table_main_comparison.csv`.
- Executes paired $t$-test and Wilcoxon signed-rank tests into `results/statistical_tests.json`.
- Renders publication-grade figures in `reports/figures/` and `results/figures/`.
- Generates comprehensive markdown report at `reports/final_report.md`.

---

## 📊 Summary of Main Experimental Findings

Across independent seeds on the deduplicated Kaggle Brain Tumor MRI benchmark:

| Model Architecture | Seeds | Test Accuracy | Balanced Acc | F1 Score | ROC-AUC | Parameter Drift | Test Loss |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (`frozen_random`)** | 5 | **85.75% ± 1.66%** | **82.34% ± 2.49%** | **77.77% ± 3.44%** | **87.33% ± 1.94%** | $0.0000 \pm 0.0000$ rad | $0.7609 \pm 0.1024$ |
| **Model B (`trainable`)** | 5 | **85.36% ± 1.14%** | **82.22% ± 1.17%** | **77.58% ± 1.61%** | **87.34% ± 1.11%** | **1.8286 ± 0.9318** rad | $0.7007 \pm 0.0557$ |

### Scientific Verdict (Paired Statistical Significance)
- **Accuracy Difference**: $\Delta = -0.39\%$, $t = -1.454$, $p = 0.220$ (two-tailed paired $t$-test across all 5 matched seeds).
- **ROC-AUC Difference**: $\Delta = +0.004\%$, $p = 0.997$ (comparable ranking across thresholds).
- **Test Loss**: Model B achieves lower cross-entropy test loss ($0.7007$ vs. $0.7609$, $\Delta = -0.060$).
- **Interpretation**: While trainable quantum filters display strong parameter plasticity ($||\theta - \theta_0||_2 \approx 1.83\text{ rad}$) without vanishing gradients, overall binary diagnostic accuracy is statistically indistinguishable from a frozen random filter. The frozen pseudo-random quantum circuit acts as an effective, zero-compute non-linear reservoir projector.

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
│   ├── prepare_data.py     # Dataset preprocessing & perceptual deduplication
│   ├── benchmark_and_smoke.py # Smoke test & hardware timing benchmark
│   ├── run_all.py          # Automated sequential experiment grid runner
│   └── make_report.py      # Statistical analysis, publication figures & report generator
├── tests/                  # Pytest suite validating statevector sim vs PennyLane
├── results/
│   ├── hardware_info.txt   # System hardware specs
│   ├── runs/               # Experiment logs, metrics, and checkpoints
│   ├── figures/            # Generated publication figures
│   ├── summary.csv         # Aggregated group performance metrics
│   └── statistical_tests.json # Paired t-test and Wilcoxon results
└── reports/
    ├── final_report.md     # Full empirical evaluation report
    └── figures/            # Embedded report figures (Fig 1 - 5)
```

---

## 🏷️ Dataset & Label Mapping
- **Source**: Kaggle *Brain Tumor MRI Dataset* (Masoud Nickparvar, CC0).
- **Binary Classification Formulation**:
  - `glioma` $\to$ **Malignant (1)**
  - `meningioma` & `pituitary` $\to$ **Benign (0)**
  - `notumor` $\to$ **Excluded** (Task is Benign vs. Malignant tumor diagnosis)
- **Image Preprocessing**: Grayscale conversion, resized to $28 \times 28$, normalized to $[0, 1]$, cached as `.npy` tensors.

---

## 🔬 Documented Paper Deviations
1. **Simulation Engine**: PyTorch vectorized statevector simulator + PennyLane reference, replacing IBM Qiskit Aer to achieve 434 img/s throughput on CPU.
2. **Batch Training**: Batch size 32 with Adam optimizer (paper used batch size 1).
3. **Trainable Filter**: End-to-end autograd optimization through the quantum convolution stage with separate learning rate.
4. **Data Leakage Elimination**: Hash-based deduplication removed 110 cross-split duplicates present in the raw Kaggle dataset.

---

## ⚠️ Known Limitations
1. **Statevector Simulation**: Exact classical statevector simulation on CPU; does not model quantum hardware noise, gate infidelity, or decoherence.
2. **Spatial Downsampling**: $28 \times 28$ resolution limits spatial detail compared to high-resolution clinical scans.
3. **Binary Taxonomy**: Grouping meningioma and pituitary tumors as benign is an established clinical convention for binary classification but simplifies the multi-class diagnostic task.
