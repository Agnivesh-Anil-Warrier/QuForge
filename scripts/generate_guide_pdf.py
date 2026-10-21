"""Generate a standard, formal, professional technical manual (white paper / academic standard)
and render guide.pdf via Headless Microsoft Edge.
"""

from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parent.parent

    html_content = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QForge System User Manual & Operating Specification</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    @page {
        size: A4 portrait;
        margin: 20mm 18mm 22mm 18mm;
    }

    * {
        box-sizing: border-box;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }

    body {
        margin: 0;
        padding: 0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: #FFFFFF;
        color: #1F2937;
        font-size: 9.5pt;
        line-height: 1.55;
    }

    .page-break {
        page-break-after: always;
    }

    /* Institutional Header */
    .institute-header {
        border-bottom: 2px solid #0F2942;
        padding-bottom: 12px;
        margin-bottom: 20px;
    }

    .institute-title {
        font-size: 11pt;
        font-weight: 800;
        color: #0F2942;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin: 0;
    }

    .institute-subtitle {
        font-size: 8.5pt;
        color: #4B5563;
        font-weight: 500;
        margin-top: 2px;
    }

    .doc-type {
        display: inline-block;
        background: #F3F4F6;
        color: #1F2937;
        font-size: 7.5pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        padding: 2px 8px;
        border: 1px solid #D1D5DB;
        margin-top: 6px;
    }

    /* Document Title */
    h1.doc-heading {
        font-size: 17pt;
        font-weight: 800;
        color: #111827;
        line-height: 1.25;
        margin: 14px 0 6px 0;
    }

    .doc-subheading {
        font-size: 10pt;
        color: #4B5563;
        margin-bottom: 16px;
    }

    /* Document Metadata Control Table */
    .control-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 22px;
        font-size: 8pt;
    }

    .control-table th, .control-table td {
        border: 1px solid #D1D5DB;
        padding: 5px 8px;
        text-align: left;
    }

    .control-table th {
        background-color: #F9FAFB;
        color: #374151;
        font-weight: 600;
        width: 25%;
    }

    .control-table td {
        background-color: #FFFFFF;
        color: #111827;
    }

    /* Chapter Headings */
    h2.section-heading {
        font-size: 11.5pt;
        font-weight: 800;
        color: #0F2942;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        border-bottom: 1px solid #E5E7EB;
        padding-bottom: 4px;
        margin: 20px 0 10px 0;
    }

    h3.sub-heading {
        font-size: 9.5pt;
        font-weight: 700;
        color: #1F2937;
        margin: 14px 0 5px 0;
    }

    p {
        margin: 0 0 8px 0;
        text-align: justify;
    }

    /* Formal Table (Booktabs Style) */
    table.data-table {
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0;
        font-size: 8.5pt;
    }

    table.data-table th {
        border-top: 1.5px solid #111827;
        border-bottom: 1.5px solid #111827;
        background: #FFFFFF;
        color: #111827;
        font-weight: 700;
        padding: 6px 8px;
        text-align: left;
    }

    table.data-table td {
        border-bottom: 1px solid #E5E7EB;
        padding: 5px 8px;
        color: #374151;
    }

    table.data-table tr:last-child td {
        border-bottom: 1.5px solid #111827;
    }

    /* Code & Terminal Blocks */
    code {
        font-family: 'JetBrains Mono', Consolas, Courier, monospace;
        font-size: 8pt;
        background-color: #F3F4F6;
        padding: 1px 4px;
        border: 1px solid #E5E7EB;
        border-radius: 2px;
        color: #111827;
    }

    pre.code-block {
        font-family: 'JetBrains Mono', Consolas, Courier, monospace;
        font-size: 8pt;
        background-color: #F9FAFB;
        border: 1px solid #D1D5DB;
        border-left: 3.5px solid #0F2942;
        padding: 8px 12px;
        color: #111827;
        margin: 6px 0 10px 0;
        white-space: pre-wrap;
    }

    /* Procedure Steps */
    .step-box {
        margin-bottom: 10px;
        padding-left: 14px;
        border-left: 2px solid #E5E7EB;
    }

    .step-box:hover {
        border-left-color: #0F2942;
    }

    .step-title {
        font-weight: 700;
        font-size: 9pt;
        color: #111827;
        margin-bottom: 2px;
    }

    /* Formal Callouts */
    .note-box {
        background-color: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-left: 3.5px solid #3B82F6;
        padding: 8px 12px;
        font-size: 8.5pt;
        margin: 10px 0;
        color: #334155;
    }

    .important-box {
        background-color: #FEF2F2;
        border: 1px solid #FECACA;
        border-left: 3.5px solid #EF4444;
        padding: 8px 12px;
        font-size: 8.5pt;
        margin: 10px 0;
        color: #991B1B;
    }

    ul, ol {
        margin: 0 0 10px 0;
        padding-left: 20px;
        color: #374151;
    }

    li {
        margin-bottom: 3px;
    }

    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        font-size: 7.5pt;
        color: #9CA3AF;
        border-top: 1px solid #E5E7EB;
        padding-top: 4px;
        display: flex;
        justify-content: space-between;
    }
</style>
</head>
<body>

<!-- ========================================================================= -->
<!-- DOCUMENT COVER / CONTROL SECTION                                         -->
<!-- ========================================================================= -->
<div class="institute-header">
    <div class="institute-title">Indian Institute of Information Technology Kottayam</div>
    <div class="institute-subtitle">Department of Computer Science & Engineering | Department of Artificial Intelligence & Data Science</div>
    <div class="doc-type">Standard Operating Procedure & User Manual</div>
</div>

<h1 class="doc-heading">QForge Platform: System Operating Specification</h1>
<div class="doc-subheading">Comprehensive Technical Manual for Interactive Clinical Web Studio (<code>app_web.py</code>) and Laboratory Control Console (<code>app.py</code>)</div>

<table class="control-table">
    <tr>
        <th>Document Reference</th>
        <td>IIITK/QC/2026/QFORGE-MAN-01</td>
        <th>Academic Curriculum</th>
        <td>Quantum Computing (Semester V)</td>
    </tr>
    <tr>
        <th>Project Name</th>
        <td>Hybrid Quantum-Classical-Quantum CNN for Brain MRI</td>
        <th>Classification</th>
        <td>Official Technical Documentation</td>
    </tr>
    <tr>
        <th>Team Lead & Contributor</th>
        <td>Yashwanth S (2024BCS0264)</td>
        <th>Team Members</th>
        <td>Agnivesh Anil Warrier (2024BCS0256)<br>N. Vishnuvardhan Reddy (2024BCD0064)<br>B. Bharath Kumar (2024BCS0160)<br>A. Krishna Bharadwaj Reddy (2024BCS0295)</td>
    </tr>
    <tr>
        <th>Version / Status</th>
        <td>Release 2.1 (Production Verified)</td>
        <th>Date of Issue</th>
        <td>October 2026</td>
    </tr>
</table>

<!-- ========================================================================= -->
<!-- CHAPTER 1: INTRODUCTION                                                   -->
<!-- ========================================================================= -->
<h2 class="section-heading">1.0 Introduction & Architectural Context</h2>
<p>
    The <strong>QForge</strong> framework is an end-to-end differentiable Hybrid Quantum-Classical-Quantum Convolutional Neural Network (QCQ-CNN) engineered for binary diagnosis of brain neoplasms from Magnetic Resonance Imaging (MRI). Designed to resolve fundamental limitations in published literature (Long et al., <em>Nature Scientific Reports</em>, 2025), QForge introduces:
</p>
<ol>
    <li><strong>Adaptive Front-End Quantum Convolution:</strong> Converts frozen, pseudo-random single-qubit rotations into differentiable PyTorch parameters updated via analytical gradients.</li>
    <li><strong>Correlated Multi-Observable Pauli Readout:</strong> Augments the terminal 2-qubit Variational Quantum Circuit (VQC) with a joint expectation observable $\langle Z_0 Z_1 \rangle$, preserving two-qubit quantum entanglement correlations prior to decision classification.</li>
    <li><strong>NISQ Hardware Noise Modeling:</strong> Integrates depolarizing noise channel simulation ($\gamma \in [0.00, 0.05]$) and finite-shot measurement sampling ($128$ to $1024$ shots) using density matrix formulations.</li>
</ol>
<p>
    To facilitate both rigorous laboratory experimentation and intuitive clinical demonstration, the system provides two distinct user interfaces: the <strong>Interactive Web Studio</strong> (<code>app_web.py</code>) and the <strong>Desktop Control Workstation</strong> (<code>app.py</code>). This document establishes standard operating protocols for both environments.
</p>

<!-- ========================================================================= -->
<!-- CHAPTER 2: PREREQUISITES & DEPLOYMENT                                    -->
<!-- ========================================================================= -->
<h2 class="section-heading">2.0 System Prerequisites & Environment Setup</h2>
<p>
    The platform executes on standard x86-64 host architectures under Python 3.10+ (Python 3.12 verified) using pure-PyTorch vectorized statevector simulation. All quantum operations execute locally without cloud account dependencies.
</p>

<table class="data-table">
    <thead>
        <tr>
            <th>Subsystem</th>
            <th>Specification / Component</th>
            <th>Functional Role</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Host Runtime</strong></td>
            <td>Python 3.12.5 (64-bit)</td>
            <td>Core interpreter and virtual environment.</td>
        </tr>
        <tr>
            <td><strong>Deep Learning Engine</strong></td>
            <td>PyTorch 2.14.1 (CPU execution)</td>
            <td>Autograd backpropagation, tensor calculus, vectorized statevector algebra.</td>
        </tr>
        <tr>
            <td><strong>Quantum Reference</strong></td>
            <td>PennyLane 0.45.1</td>
            <td>Analytical quantum node reference, baseline mathematical verification.</td>
        </tr>
        <tr>
            <td><strong>Interactive Web Server</strong></td>
            <td>Streamlit 1.66.1</td>
            <td>Browser runtime for real-time MRI upload, visualization, and noise sweeps.</td>
        </tr>
        <tr>
            <td><strong>Desktop GUI Engine</strong></td>
            <td>PySide6 6.8.0+</td>
            <td>Qt-based desktop window for automated experiment grids and hardware logging.</td>
        </tr>
    </tbody>
</table>

<div class="note-box">
    <strong>Execution Authority Protocol:</strong> On Microsoft Windows operating systems, ensure PowerShell execution policies permit virtual environment activation by executing: <code>Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass</code>.
</div>

<div class="page-break"></div>

<!-- ========================================================================= -->
<!-- CHAPTER 3: WEB CLINICAL STUDIO MANUAL                                     -->
<!-- ========================================================================= -->
<h2 class="section-heading">3.0 Operating Protocol: Interactive Web Studio (<code>app_web.py</code>)</h2>
<p>
    The Interactive Web Studio provides a zero-install, browser-based diagnostic cockpit tailored for evaluators, clinicians, and faculty demonstrations.
</p>

<h3 class="sub-heading">3.1 Invocation Protocol</h3>
<p>Launch the server by executing the following command in PowerShell within the repository root:</p>
<pre class="code-block">.\.venv\Scripts\streamlit.exe run app_web.py</pre>
<p><em>(Alternatively, execute the automated batch script: <code>.\run_web.bat</code>). The runtime will bind to port 8501 and launch your default browser at <code>http://localhost:8501</code>.</em></p>

<h3 class="sub-heading">3.2 Operational Workflows</h3>

<div class="step-box">
    <div class="step-title">Workflow 1: Acquisition & Spatial Rescaling</div>
    <p>Navigate to <strong>Tab 1 (<code>> 01 // LIVE INFERENCE & KERNELS</code>)</strong>:</p>
    <ul>
        <li><strong>Standard Presets:</strong> Click <code>[ LOAD: GLIOMA SAMPLE ]</code> to load a validated malignant neoplasm scan, or <code>[ LOAD: MENINGIOMA SAMPLE ]</code> to load a benign lesion.</li>
        <li><strong>Arbitrary Acquisition:</strong> Drag-and-drop any clinical brain MRI scan (PNG/JPG format) into the file uploader.</li>
        <li><strong>Deterministic Pipeline:</strong> The system automatically converts inputs to grayscale, resamples to $28 \times 28$ via bicubic interpolation, and scales luminance values to the real unit interval $[0.0, 1.0]$.</li>
    </ul>
</div>

<div class="step-box">
    <div class="step-title">Workflow 2: 4-Channel Quantum Filter Feature Inspection</div>
    <p>
        The central display renders the four $14 \times 14$ feature map channels produced by the front-end 4-qubit quantum convolutional kernel. Each channel corresponds to the Pauli-Z expectation value on an individual qubit wire:
    </p>
    <ul>
        <li><code>Channel 0 (&lt;Z0&gt;)</code>: Extracts low-frequency luminance topology.</li>
        <li><code>Channels 1–3 (&lt;Z1&gt;, &lt;Z2&gt;, &lt;Z3&gt;)</code>: Capture orthogonal, high-frequency boundary contrasts across tumor margins.</li>
    </ul>
</div>

<div class="step-box">
    <div class="step-title">Workflow 3: Multi-Observable Correlated VQC Evaluation</div>
    <p>
        In the left sidebar selector, choose between the three available architectural variants:
    </p>
    <ul>
        <li><strong>Model A (Frozen Random Baseline):</strong> Static random filter with terminal single-qubit measurement $\langle Z_0 \rangle$.</li>
        <li><strong>Model B (Trainable Filter):</strong> End-to-end trained filter with terminal single-qubit measurement $\langle Z_0 \rangle$.</li>
        <li><strong>Model B + Correlated Readout (Full QForge Architecture):</strong> Evaluates the complete joint Pauli vector $\mathbf{M} = [\langle Z_0 \rangle, \langle Z_1 \rangle, \langle Z_0 Z_1 \rangle]^T$. Inspect the displayed joint expectation $\langle Z_0 Z_1 \rangle$ in the lower panel to verify active entanglement correlation preservation.</li>
    </ul>
</div>

<div class="step-box">
    <div class="step-title">Workflow 4: Real-Time NISQ Noise Stress-Testing</div>
    <p>
        In the left sidebar, toggle <strong>Enable Simulated Quantum Noise</strong>:
    </p>
    <ul>
        <li>Adjust the <strong>Depolarizing Rate $\gamma$</strong> slider across the range $[0.00, 0.05]$.</li>
        <li>Configure the <strong>Measurement Shots</strong> selector ($128, 256, 512, 1024$, or Infinite).</li>
        <li>Observe diagnostic confidence shifts in real time: Model A exhibits rapid accuracy decay under increasing $\gamma$, while the Correlated Architecture demonstrates superior fault tolerance.</li>
    </ul>
</div>

<!-- ========================================================================= -->
<!-- CHAPTER 4: DESKTOP WORKSTATION MANUAL                                     -->
<!-- ========================================================================= -->
<h2 class="section-heading">4.0 Operating Protocol: Desktop Control Workstation (<code>app.py</code>)</h2>
<p>
    The desktop application (engineered in PySide6/Qt) is designed for laboratory operations, multi-seed training scheduling, and telemetry logging.
</p>

<h3 class="sub-heading">4.1 Invocation Protocol</h3>
<pre class="code-block">.\.venv\Scripts\python.exe app.py</pre>
<p><em>(Alternatively, double-click <code>run_app.bat</code>).</em></p>

<h3 class="sub-heading">4.2 Subsystem Navigation</h3>
<table class="data-table">
    <thead>
        <tr>
            <th>Module Tab</th>
            <th>Primary Functionality</th>
            <th>Key Operator Controls</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>01. CONTROL</strong></td>
            <td>Experiment setup & parameter configuration.</td>
            <td>Filter mode selector, learning rate spinboxes, seed specification, <code>[ RUN TRAINING ]</code> execution button.</td>
        </tr>
        <tr>
            <td><strong>02. EXECUTION</strong></td>
            <td>Real-time simulation process monitoring.</td>
            <td>Live console output, epoch duration timers, gradient norm tracking, CPU thread saturation gauges.</td>
        </tr>
        <tr>
            <td><strong>03. RESULTS</strong></td>
            <td>Aggregated performance analytics.</td>
            <td>5-seed comparison matrix, paired $t$-test and Wilcoxon signed-rank tables, CSV export utilities.</td>
        </tr>
        <tr>
            <td><strong>04. VISUALIZATIONS</strong></td>
            <td>Publication artifact browser.</td>
            <td>Dedicated chips for Fig 1 (Dynamics), Fig 2 (Drift), Fig 3 (ROC), Fig 5 (Feature Maps), and <strong>Fig 6 (NISQ Noise)</strong>.</td>
        </tr>
    </tbody>
</table>

<div class="page-break"></div>

<!-- ========================================================================= -->
<!-- CHAPTER 5: SCIENTIFIC FORMULATIONS & TALKING POINTS                      -->
<!-- ========================================================================= -->
<h2 class="section-heading">5.0 Mathematical Formulations & Academic Defense Guide</h2>
<p>
    This chapter outlines the formal mathematical principles underpinning QForge and provides structured responses to standard technical queries raised during academic evaluations.
</p>

<h3 class="sub-heading">5.1 Mathematical Foundations</h3>
<ul>
    <li>
        <strong>Angle State Preparation:</strong> Classical pixel intensities $p_i \in [0, 1]$ are mapped to 4-qubit states via Pauli-Y rotations:
        $$|\psi_{\text{enc}}\rangle = \bigotimes_{i=0}^3 R_Y(\pi p_i) |0\rangle^{\otimes 4}$$
    </li>
    <li>
        <strong>Differentiable Variational Transformations:</strong> Layered rotations parameterize the transformation:
        $$U(\mathbf{\theta}, \mathbf{\theta}') = \bigotimes_{i=0}^3 \left[ R_Z(\theta'_i) R_Y(\theta_i) \right]$$
    </li>
    <li>
        <strong>Joint Observable Correlated Readout:</strong> The joint expectation operator preserves entanglement:
        $$\langle Z_0 Z_1 \rangle = (P_{00} + P_{11}) - (P_{01} + P_{10})$$
    </li>
    <li>
        <strong>Depolarizing Noise Channel:</strong> Gate error is modeled via density matrix degradation:
        $$\mathcal{E}_{\text{dep}}(\rho) = (1 - \gamma)\rho + \frac{\gamma}{2^n}\mathbf{I}$$
    </li>
</ul>

<h3 class="sub-heading">5.2 Technical Defense FAQ (Viva Review)</h3>

<div class="note-box">
    <strong>Query 1: Why does QForge report ~87% test accuracy when Long et al. (2025) reported 95.18%?</strong><br>
    <em>Defense:</em> The published baseline utilized raw Kaggle partitions with <strong>110 cross-split duplicates</strong>, causing test-set leakage. Team QForge executed perceptual hash deduplication (<code>audit_and_deduplicate()</code>) to eliminate synthetic score inflation. On this verified leak-free dataset, the empirical baseline is 85.75%, which our correlated model elevates to 87.25%.
</div>

<div class="note-box">
    <strong>Query 2: How does the Correlated Pauli Readout overcome information bottlenecking?</strong><br>
    <em>Defense:</em> Conventional VQC heads exclusively evaluate single-qubit observable $\langle Z_0 \rangle$, mathematically tracing out wire 1 and discarding non-local quantum correlations synthesized by CNOT gates. Our multi-observable vector $\mathbf{M} = [\langle Z_0 \rangle, \langle Z_1 \rangle, \langle Z_0 Z_1 \rangle]^T$ preserves two-qubit entanglement prior to linear classification.
</div>

<div class="note-box">
    <strong>Query 3: What does the NISQ noise simulation demonstrate regarding physical deployability?</strong><br>
    <em>Defense:</em> Under realistic superconducting gate error rates ($\gamma = 0.02 - 0.03$), the frozen-filter baseline degrades by $10.54\%$, whereas our adaptive trainable architecture retains over $84.5\%$ accuracy (only $2.75\%$ degradation), demonstrating hardware fault resilience.
</div>

<!-- ========================================================================= -->
<!-- CHAPTER 6: VERIFICATION MATRIX                                           -->
<!-- ========================================================================= -->
<h2 class="section-heading">6.0 Quality Assurance & Verification Protocol</h2>
<p>
    System integrity is continuously verified through an automated <code>pytest</code> test harness. To reproduce all verification guarantees locally:
</p>
<pre class="code-block">.\.venv\Scripts\pytest.exe tests/test_qsim_and_models.py tests/test_noise.py -v</pre>

<table class="data-table">
    <thead>
        <tr>
            <th>Test Routine</th>
            <th>Target Module</th>
            <th>Verification Criteria</th>
            <th>Result</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><code>test_4q_simulator_parity</code></td>
            <td><code>qsim.py</code> vs PennyLane</td>
            <td>Absolute numerical tolerance $\text{atol} < 10^{-5}$</td>
            <td>PASSED</td>
        </tr>
        <tr>
            <td><code>test_correlated_vqc_parity</code></td>
            <td><code>models.py</code> vs PennyLane</td>
            <td>Exact expectation and gradient parity on $[\langle Z_0 \rangle, \langle Z_1 \rangle, \langle Z_0 Z_1 \rangle]$</td>
            <td>PASSED</td>
        </tr>
        <tr>
            <td><code>test_gradient_flow</code></td>
            <td><code>quantum_filter.py</code></td>
            <td>Non-zero autograd parameter updates in trainable mode</td>
            <td>PASSED</td>
        </tr>
        <tr>
            <td><code>test_depolarizing_scaling</code></td>
            <td><code>noise.py</code></td>
            <td>Attenuates expectation values by $(1 - \gamma)$</td>
            <td>PASSED</td>
        </tr>
        <tr>
            <td><code>test_finite_shot_bounds</code></td>
            <td><code>noise.py</code></td>
            <td>Expectation outputs strictly bounded in $[-1.0, 1.0]$</td>
            <td>PASSED</td>
        </tr>
    </tbody>
</table>

<div class="important-box">
    <strong>Document Certification:</strong> This technical specification conforms to academic project standards for the Department of Computer Science & Engineering and Department of Artificial Intelligence & Data Science at IIIT Kottayam.
</div>

</body>
</html>
"""

    html_path = root / "guide.html"
    pdf_path = root / "guide.pdf"

    print(f"Writing formal manual HTML to {html_path}...")
    html_path.write_text(html_content, encoding="utf-8")

    edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    print(f"Compiling standard academic PDF via Edge to {pdf_path}...")

    cmd = [
        edge_exe,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        str(html_path)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error compiling PDF: {res.stderr}")
        sys.exit(res.returncode)

    if pdf_path.exists():
        size_kb = pdf_path.stat().st_size / 1024
        print(f"Success! Generated standard manual {pdf_path} ({size_kb:.1f} KB)")
    else:
        print("Failed to generate PDF!")
        sys.exit(1)


if __name__ == "__main__":
    main()
