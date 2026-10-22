"""Generate demo_workflow_guide.html and compile demo_workflow_guide.pdf.

Provides a comprehensive, step-by-step presentation & viva demonstration walkthrough
for both the Interactive Web Studio (app_web.py) and the Desktop Research Workstation (app.py).
"""

import base64
import os
from pathlib import Path
import subprocess
import sys


def get_base64_image(path: Path) -> str:
    """Encode an image to a base64 data URI."""
    if not path.exists():
        print(f"Warning: Image {path} not found.")
        return ""
    suffix = path.suffix.lower().replace(".", "")
    if suffix == "jpg":
        suffix = "jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/{suffix};base64,{encoded}"


def main():
    root = Path(__file__).resolve().parent.parent
    figures_dir = root / "reports" / "figures"
    samples_dir = root / "sample for docs"

    print("Loading image assets for Demo Workflow Guide...")
    img_fig1 = get_base64_image(figures_dir / "fig1_learning_curves.png")
    img_fig2 = get_base64_image(figures_dir / "fig2_parameter_drift.png")
    img_fig3 = get_base64_image(figures_dir / "fig3_confusion_and_roc.png")
    img_fig4 = get_base64_image(figures_dir / "fig4_ablations.png")
    img_fig5 = get_base64_image(figures_dir / "fig5_quantum_feature_maps.png")
    img_noise = get_base64_image(figures_dir / "noise_resilience.png")

    img_glioma = get_base64_image(samples_dir / "01_glioma_Tr-gl_987.jpg")
    img_meningioma = get_base64_image(samples_dir / "04_meningioma_Tr-me_969.jpg")
    img_pituitary = get_base64_image(samples_dir / "07_pituitary_Tr-pi_139.jpg")
    img_notumor = get_base64_image(samples_dir / "09_notumor_Tr-no_284.jpg")

    template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QForge Demo & Operational Walkthrough Guide</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    @page {
        size: A4 portrait;
        margin: 14mm 14mm 16mm 14mm;
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
        font-size: 8.8pt;
        line-height: 1.48;
    }

    .page-break {
        page-break-after: always;
        break-after: page;
    }

    /* Header Bar */
    .header-bar {
        border-bottom: 2.5px solid #005A9C;
        padding-bottom: 6px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
    }

    .inst-title {
        font-size: 10pt;
        font-weight: 800;
        color: #005A9C;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }

    .inst-subtitle {
        font-size: 7.8pt;
        color: #4B5563;
        font-weight: 500;
    }

    .tag-badge {
        display: inline-block;
        background: #EFF6FF;
        color: #1D4ED8;
        font-size: 7.5pt;
        font-weight: 700;
        text-transform: uppercase;
        padding: 2px 8px;
        border: 1px solid #BFDBFE;
        border-radius: 2px;
    }

    /* Titles */
    h1.doc-title {
        font-size: 15.5pt;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.2;
        margin: 4px 0 3px 0;
    }

    .doc-subtitle {
        font-size: 9pt;
        color: #475569;
        margin-bottom: 10px;
    }

    /* Control Metadata Table */
    .meta-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 12px;
        font-size: 7.8pt;
    }

    .meta-table th, .meta-table td {
        border: 1px solid #CBD5E1;
        padding: 4px 7px;
        text-align: left;
    }

    .meta-table th {
        background-color: #F8FAFC;
        color: #334155;
        font-weight: 700;
        width: 22%;
    }

    /* Section Headings */
    h2.section-heading {
        font-size: 10.5pt;
        font-weight: 800;
        color: #0F2942;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        border-bottom: 1px solid #CBD5E1;
        padding-bottom: 3px;
        margin: 14px 0 8px 0;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    h3.sub-heading {
        font-size: 9.2pt;
        font-weight: 700;
        color: #1E293B;
        margin: 8px 0 4px 0;
    }

    /* Fast Launch Quick Cards */
    .launch-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-bottom: 12px;
    }

    .launch-card {
        border: 1px solid #CBD5E1;
        border-radius: 4px;
        padding: 9px;
        background-color: #F8FAFC;
    }

    .launch-card.web {
        border-left: 4px solid #00E5FF;
        background: #F0FDFA;
    }

    .launch-card.desktop {
        border-left: 4px solid #B26BFF;
        background: #FAF5FF;
    }

    .launch-title {
        font-weight: 800;
        font-size: 8.8pt;
        color: #0F172A;
        margin-bottom: 3px;
    }

    /* Code Snippets */
    code {
        font-family: 'JetBrains Mono', Consolas, monospace;
        font-size: 7.6pt;
        background-color: #F1F5F9;
        padding: 1px 4px;
        border: 1px solid #E2E8F0;
        border-radius: 2px;
        color: #0F172A;
    }

    pre.code-block {
        font-family: 'JetBrains Mono', Consolas, monospace;
        font-size: 7.8pt;
        background-color: #0F172A;
        color: #38BDF8;
        padding: 6px 10px;
        border-radius: 3px;
        margin: 3px 0 6px 0;
        overflow-x: auto;
    }

    /* Tables */
    table.data-table {
        width: 100%;
        border-collapse: collapse;
        margin: 6px 0 10px 0;
        font-size: 7.8pt;
    }

    table.data-table th {
        border-top: 1.5px solid #0F172A;
        border-bottom: 1.5px solid #0F172A;
        background: #F8FAFC;
        color: #0F172A;
        font-weight: 700;
        padding: 4px 6px;
        text-align: left;
    }

    table.data-table td {
        border-bottom: 1px solid #E2E8F0;
        padding: 3.5px 6px;
        color: #334155;
    }

    /* Step Walkthrough Cards */
    .step-card {
        border: 1px solid #E2E8F0;
        border-radius: 3px;
        padding: 7px 9px;
        margin-bottom: 7px;
        background: #FFFFFF;
    }

    .step-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 3px;
    }

    .step-num {
        font-size: 7.8pt;
        font-weight: 800;
        color: #005A9C;
        letter-spacing: 0.5px;
    }

    .step-action {
        font-size: 7.2pt;
        font-weight: 700;
        background: #E0F2FE;
        color: #0369A1;
        padding: 1px 5px;
        border-radius: 2px;
    }

    /* Callouts & Scripts */
    .script-box {
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-left: 3.5px solid #10B981;
        padding: 5px 8px;
        margin: 5px 0;
        font-size: 7.8pt;
    }

    .script-box strong {
        color: #065F46;
    }

    .warning-box {
        background: #FFFBEB;
        border: 1px solid #FDE68A;
        border-left: 3.5px solid #F59E0B;
        padding: 5px 8px;
        margin: 5px 0;
        font-size: 7.8pt;
        color: #92400E;
    }

    .defense-qa {
        border: 1px solid #CBD5E1;
        border-radius: 3px;
        padding: 5px 8px;
        margin-bottom: 6px;
        background: #F8FAFC;
    }

    .defense-q {
        font-weight: 700;
        color: #1E293B;
        font-size: 8pt;
        margin-bottom: 2px;
    }

    .defense-a {
        color: #475569;
        font-size: 7.6pt;
    }

    .img-row {
        display: flex;
        gap: 8px;
        margin: 6px 0;
        align-items: center;
    }

    .img-box {
        flex: 1;
        border: 1px solid #CBD5E1;
        border-radius: 2px;
        padding: 4px;
        background: #FFFFFF;
        text-align: center;
    }

    .img-box img {
        max-width: 100%;
        max-height: 90px;
        object-fit: contain;
    }

    .img-caption {
        font-size: 6.8pt;
        color: #64748B;
        margin-top: 2px;
    }
</style>
</head>
<body>

<!-- ========================================================================= -->
<!-- PAGE 1: COVER & DEMO BLUEPRINT                                           -->
<!-- ========================================================================= -->
<div class="header-bar">
    <div>
        <div class="inst-title">Indian Institute of Information Technology Kottayam</div>
        <div class="inst-subtitle">Department of Computer Science & Engineering | Semester V Quantum Computing</div>
    </div>
    <div class="tag-badge">Official Demo Blueprint</div>
</div>

<h1 class="doc-title">QForge System Demonstration & Operating Playbook</h1>
<div class="doc-subtitle">Comprehensive, Step-by-Step Viva & Faculty Presentation Manual for <code>app_web.py</code> & <code>app.py</code></div>

<table class="meta-table">
    <tr>
        <th>Project Title</th>
        <td>Hybrid Quantum-Classical-Quantum CNN for Brain MRI (QCQ-CNN)</td>
        <th>Target Deliverables</th>
        <td>Clinical Web Studio & Desktop Lab Console</td>
    </tr>
    <tr>
        <th>Team Lead & Presenter</th>
        <td>Yashwanth S (2024BCS0264)</td>
        <th>Project Team</th>
        <td>Agnivesh Anil Warrier, N. Vishnuvardhan Reddy, B. Bharath Kumar, A. Krishna Bharadwaj Reddy</td>
    </tr>
    <tr>
        <th>Benchmark Platform</th>
        <td>Deduplicated Kaggle Brain MRI (5,222 Clean Slices)</td>
        <th>Verification Level</th>
        <td>23/23 Pytest Unit Tests Passing (Exact Parity with PennyLane)</td>
    </tr>
</table>

<h2 class="section-heading">1.0 Quick-Start Launcher Cheat-Sheet</h2>
<div class="launch-grid">
    <div class="launch-card web">
        <div class="launch-title">🌐 1. Interactive Web Studio (app_web.py)</div>
        <p style="margin: 0 0 3px 0; font-size: 7.8pt; color: #475569;">
            Best for: <strong>Examiner walkthroughs, 1-click clinical inference, quantum feature maps, live NISQ depolarizing noise tests</strong>.
        </p>
        <pre class="code-block">python app_web.py</pre>
        <div style="font-size: 7.2pt; color: #0E7490;">
            <em>Auto-opens in browser at:</em> <code>http://localhost:8501</code><br>
            <em>Alternate launcher:</em> Double-click <code>run_web.bat</code>
        </div>
    </div>

    <div class="launch-card desktop">
        <div class="launch-title">🖥️ 2. Desktop Lab Workstation (app.py)</div>
        <p style="margin: 0 0 3px 0; font-size: 7.8pt; color: #475569;">
            Best for: <strong>Training automation, live loss chart dynamics, 434 img/s throughput telemetry, statistical p-value matrices</strong>.
        </p>
        <pre class="code-block">python app.py</pre>
        <div style="font-size: 7.2pt; color: #7E22CE;">
            <em>Launches dark-mode Qt GUI</em> (AMD Ryzen / Intel optimized)<br>
            <em>Alternate launcher:</em> Double-click <code>run_app.bat</code>
        </div>
    </div>
</div>

<h2 class="section-heading">2.0 Recommended 5-Minute Live Demo Agenda</h2>
<table class="data-table">
    <thead>
        <tr>
            <th style="width: 12%;">Time</th>
            <th style="width: 24%;">Phase</th>
            <th style="width: 36%;">Action Performed on Screen</th>
            <th style="width: 28%;">Examiner Takeaway / Value</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>0:00 - 0:45</strong></td>
            <td>Architecture Context</td>
            <td>Explain QCQ-CNN pipeline: 4Q Filter &rarr; Classical CNN &rarr; 2Q VQC Head.</td>
            <td>Clear problem framing: resolving Nature 2025 single-qubit bottleneck.</td>
        </tr>
        <tr>
            <td><strong>0:45 - 2:30</strong></td>
            <td><strong>Web Studio Demo</strong><br>(<code>app_web.py</code>)</td>
            <td>
                1. Click <code>[ LOAD: GLIOMA SAMPLE ]</code> &rarr; Malignant outcome.<br>
                2. Explain 4-channel quantum feature maps.<br>
                3. Click <code>[ LOAD: MENINGIOMA SAMPLE ]</code> &rarr; Benign.<br>
                4. Toggle <strong>Simulated Noise</strong> (&gamma;=0.02) to prove Model B resilience.
            </td>
            <td>Interactive clinical diagnosis, real-time quantum kernel inspection, fault tolerance under hardware noise.</td>
        </tr>
        <tr>
            <td><strong>2:30 - 4:00</strong></td>
            <td><strong>Desktop Lab Demo</strong><br>(<code>app.py</code>)</td>
            <td>
                1. Navigate to <strong>Tab 2 (RUNNER)</strong>.<br>
                2. Hit <code>[ > RUN EXPERIMENT ]</code> (smoke test) &rarr; show 434 img/s.<br>
                3. Switch to <strong>Tab 3 (RESULTS)</strong> &rarr; show 5-seed p=0.220 table.
            </td>
            <td>Rigorous engineering proof: 434 img/s speedup via pure-PyTorch einsum and statistical rigor.</td>
        </tr>
        <tr>
            <td><strong>4:00 - 5:00</strong></td>
            <td>Viva & Q&A Defense</td>
            <td>Answer faculty questions using Chapter 5 mathematical proofs and deduplication audit logs.</td>
            <td>Demonstrates deep mastery of both quantum circuits and ML data integrity.</td>
        </tr>
    </tbody>
</table>

<div class="warning-box">
    <strong>Pre-Demo Verification:</strong> Both tools run locally on CPU without cloud credentials. The virtual environment includes PyTorch, PennyLane, Streamlit, and PySide6.
</div>

<div class="page-break"></div>

<!-- ========================================================================= -->
<!-- PAGE 2: WALKTHROUGH FOR APP_WEB.PY                                        -->
<!-- ========================================================================= -->
<div class="header-bar">
    <div>
        <div class="inst-title">Part I: Clinical Web Studio Walkthrough</div>
        <div class="inst-subtitle">Step-by-step Operator Script for <code>app_web.py</code></div>
    </div>
    <div class="tag-badge">Interface 1 (Web)</div>
</div>

<h2 class="section-heading">3.0 Interactive Web Studio Walkthrough (app_web.py)</h2>
<p style="margin-bottom: 6px;">
    The Web Studio provides an intuitive, high-impact clinical instrument panel configured for live demonstration.
</p>

<div class="step-card">
    <div class="step-header">
        <span class="step-num">STEP 1: INITIATE WEB APPLICATION</span>
        <span class="step-action">TERMINAL COMMAND</span>
    </div>
    <pre class="code-block">python app_web.py</pre>
    <p style="margin: 0; font-size: 7.6pt; color: #475569;">
        The system detects execution mode, binds to <code>http://localhost:8501</code>, and automatically opens your web browser.
    </p>
</div>

<div class="step-card">
    <div class="step-header">
        <span class="step-num">STEP 2: RUN CLINICAL INFERENCE (GLIOMA NEOPLASM EXAMPLE)</span>
        <span class="step-action">TAB 1: LIVE INFERENCE</span>
    </div>
    <p style="margin: 0 0 3px 0; font-size: 7.8pt;">
        1. On <strong>Tab 1 (<code>&gt; 01 // LIVE INFERENCE & KERNELS</code>)</strong>, click the button: <code>[ LOAD: GLIOMA SAMPLE ]</code>.<br>
        2. Observe the 3 synchronized visual panels rendered instantly on screen:
    </p>
    <ul>
        <li><strong>Panel 1 (Left &mdash; 28&times;28 Normalized Input):</strong> Normalized MRI slice showing the hyperintense left-hemisphere infiltrating glioma lesion.</li>
        <li><strong>Panel 2 (Center &mdash; 4 Quantum Filter Channels):</strong> Displays the 14&times;14 Pauli expectations [&lang;Z0&rang;, &lang;Z1&rang;, &lang;Z2&rang;, &lang;Z3&rang;]. Point out how Wire 0 captures luminance topology while Wires 1&ndash;3 isolate tumor boundary gradients.</li>
        <li><strong>Panel 3 (Right &mdash; Diagnostic Outcome Card):</strong> Highlights the red <code>MALIGNANT NEOPLASM</code> badge with high diagnostic confidence.</li>
    </ul>

    <div class="script-box">
        <strong>What to Say to Evaluators:</strong><br>
        <em>"Here we pass an MRI slice through our 4-qubit quantum convolutional filter. Each 2&times;2 pixel patch is angle-encoded into four qubits, transformed via trainable parameterized unitary gates, and measured in the Pauli-Z basis. This yields 4 orthogonal quantum feature channels that feed our classical backbone."</em>
    </div>
</div>

<div class="step-card">
    <div class="step-header">
        <span class="step-num">STEP 3: COMPARE WITH BENIGN SAMPLE & INSPECT STATE</span>
        <span class="step-action">QUANTUM INTROSPECTION</span>
    </div>
    <p style="margin: 0 0 3px 0; font-size: 7.8pt;">
        1. Click <code>[ LOAD: MENINGIOMA SAMPLE ]</code>.<br>
        2. Watch the diagnostic card transition to green <code>BENIGN NEOPLASM</code>.<br>
        3. Scroll down to <strong>"Terminal VQC Quantum State Introspection"</strong>:
    </p>
    <ul>
        <li>Observe the latent angles: h0, h1 in [-&pi;, &pi;] produced by the classical CNN backbone.</li>
        <li>Observe the measured observables: Single-qubit &lang;Z0&rang;, &lang;Z1&rang;, and the joint entanglement observable <strong>&lang;Z0 Z1&rang;</strong>.</li>
    </ul>

    <div class="script-box">
        <strong>What to Say to Evaluators:</strong><br>
        <em>"Notice the lower introspection panel. In previous literature, the second qubit and the joint correlation &lang;Z0 Z1&rang; were completely discarded by measuring only &lang;Z0&rang;. Our architecture explicitly extracts &lang;Z0 Z1&rang;, directly preserving two-qubit entanglement information for the final diagnostic decision."</em>
    </div>
</div>

<div class="step-card">
    <div class="step-header">
        <span class="step-num">STEP 4: LIVE NISQ HARDWARE NOISE STRESS-TEST</span>
        <span class="step-action">SIDEBAR CONTROLS</span>
    </div>
    <p style="margin: 0 0 3px 0; font-size: 7.8pt;">
        1. In the left sidebar, check <strong>"Enable Simulated Quantum Noise"</strong>.<br>
        2. Set <strong>Depolarizing Rate &gamma;</strong> to <code>0.02</code> and <strong>Measurement Shots</strong> to <code>1024</code>.<br>
        3. Switch between <strong>Model A (Frozen Random)</strong> and <strong>Model B + Correlated Readout</strong>:
    </p>
    <ul>
        <li><strong>Model A:</strong> Accuracy deteriorates dramatically under noise (experiences a -10.54% drop).</li>
        <li><strong>Model B + Correlated:</strong> Remains resilient with only a -2.75% deviation, maintaining reliable diagnostic output.</li>
    </ul>

    <div class="script-box">
        <strong>What to Say to Evaluators:</strong><br>
        <em>"To prove viability on noisy intermediate-scale quantum (NISQ) hardware, we simulate depolarizing gate noise and finite measurement shot noise. Notice that our correlated architecture retains over 84.5% diagnostic accuracy even under typical NISQ hardware noise levels."</em>
    </div>
</div>

<div class="page-break"></div>

<!-- ========================================================================= -->
<!-- PAGE 3: WALKTHROUGH FOR APP.PY                                            -->
<!-- ========================================================================= -->
<div class="header-bar">
    <div>
        <div class="inst-title">Part II: Desktop Research Workstation Walkthrough</div>
        <div class="inst-subtitle">Step-by-step Operator Script for <code>app.py</code></div>
    </div>
    <div class="tag-badge">Interface 2 (Desktop)</div>
</div>

<h2 class="section-heading">4.0 Desktop Research Workstation Walkthrough (app.py)</h2>
<p style="margin-bottom: 6px;">
    The PySide6/Qt desktop instrument panel is engineered for reproducible laboratory experiment dispatch, telemetry logging, and statistical matrix verification.
</p>

<div class="step-card">
    <div class="step-header">
        <span class="step-num">STEP 1: INITIATE DESKTOP WORKSTATION</span>
        <span class="step-action">TERMINAL COMMAND</span>
    </div>
    <pre class="code-block">python app.py</pre>
    <p style="margin: 0; font-size: 7.6pt; color: #475569;">
        Launches the high-performance Quantum-Lab research interface styled with dark theme (#060910 canvas) and monospace typography.
    </p>
</div>

<div class="step-card">
    <div class="step-header">
        <span class="step-num">STEP 2: TAB 1 (DASHBOARD) &mdash; REVIEW EXPERIMENTAL AUDIT</span>
        <span class="step-action">DASHBOARD NAVIGATION</span>
    </div>
    <p style="margin: 0 0 3px 0; font-size: 7.8pt;">
        Direct the evaluators' attention to the 4 instrument stat cards across the top:
    </p>
    <ul>
        <li><code>MODEL A &middot; FROZEN: 85.75%</code> &mdash; Baseline performance with frozen random unitary reservoir.</li>
        <li><code>MODEL B &middot; TRAINABLE: 85.36%</code> &mdash; Differentiable filter with identical single-qubit measurement.</li>
        <li><code>PARAMETER DRIFT: 1.83 RAD</code> &mdash; Direct mathematical proof of non-vanishing gradient descent.</li>
        <li><code>VERDICT: p = 0.220</code> &mdash; Confirms no statistically significant difference on single-qubit readout.</li>
    </ul>

    <div class="script-box">
        <strong>What to Say to Evaluators:</strong><br>
        <em>"Our dashboard summarizes 25 rigorous seed runs on the leak-free dataset. Notice the p-value of 0.220: when using single-qubit readout, a frozen random filter achieves identical classification to a trained filter, proving the Quantum Reservoir Principle. The bottleneck was never the filter; it was the readout."</em>
    </div>
</div>

<div class="step-card">
    <div class="step-header">
        <span class="step-num">STEP 3: TAB 2 (RUNNER) &mdash; DISPATCH REAL-TIME EXPERIMENT</span>
        <span class="step-action">LIVE TELEMETRY MONITORING</span>
    </div>
    <p style="margin: 0 0 3px 0; font-size: 7.8pt;">
        1. Switch to <strong>Tab 2 (RUNNER)</strong>.<br>
        2. Set <code>Filter Mode: trainable</code>, <code>Seed: 42</code>, <code>Max Epochs: 2</code>.<br>
        3. Click the cyan button: <code>[ > RUN EXPERIMENT ]</code>.<br>
        4. Point out the live telemetry features:
    </p>
    <ul>
        <li><strong>Execution Console:</strong> Tagged log streams with <code>[SYS]</code>, <code>[TRAIN]</code>, <code>[DATA]</code>, <code>[OK]</code> indicators and live timestamping.</li>
        <li><strong>Throughput:</strong> Highlighting our <strong>434 img/s pure-PyTorch vectorized engine</strong>, completing an entire epoch in under 7 seconds on CPU.</li>
        <li><strong>Live Dynamics Line Chart:</strong> Training loss (cyan dashed) and validation loss (violet solid) render dynamically per epoch.</li>
    </ul>

    <div class="script-box">
        <strong>What to Say to Evaluators:</strong><br>
        <em>"Observe the training speed: by vectorizing PennyLane statevector math into pure PyTorch einsum operations, we achieved 434 images per second on standard CPU. Training an epoch now takes 7 seconds instead of 30+ minutes, enabling full 5-seed statistical verification."</em>
    </div>
</div>

<div class="step-card">
    <div class="step-header">
        <span class="step-num">STEP 4: TAB 3 & TAB 4 &mdash; STATISTICAL VERIFICATION & FIGURES</span>
        <span class="step-action">RESULTS & ARTIFACTS</span>
    </div>
    <ul>
        <li><strong>Tab 3 (RESULTS):</strong> Click <code>[ SIGNIFICANCE ]</code> to display paired t-test and Wilcoxon signed-rank tables.</li>
        <li><strong>Tab 4 (VISUALIZATIONS):</strong> Click through publication figures:
            <ul>
                <li><code>Fig 1 (Learning Dynamics)</code>: Loss curves over 15 epochs.</li>
                <li><code>Fig 2 (Parameter Drift)</code>: Shows steady weight evolution away from &theta;0.</li>
                <li><code>Fig 3 (ROC & Confusion)</code>: 88.90% AUC achieved by Correlated architecture.</li>
                <li><code>Fig 6 (Noise Resilience)</code>: Accuracy vs depolarizing rate &gamma; in [0.00, 0.05].</li>
            </ul>
        </li>
    </ul>
</div>

<div class="page-break"></div>

<!-- ========================================================================= -->
<!-- PAGE 4: VIVA DEFENSE SCRIPT & FAQS                                        -->
<!-- ========================================================================= -->
<div class="header-bar">
    <div>
        <div class="inst-title">Part III: Viva Defense & Examiner FAQ Script</div>
        <div class="inst-subtitle">Standard Questions & Definitive Answers</div>
    </div>
    <div class="tag-badge">Viva Prep</div>
</div>

<h2 class="section-heading">5.0 Examiner Technical Defense Questions & Answers</h2>

<div class="defense-qa">
    <div class="defense-q">Q1: Why does QForge report ~87.25% test accuracy when Long et al. (Nature Sci Rep 2025) reported 95.18%?</div>
    <div class="defense-a">
        <strong>Definitive Defense:</strong> <em>"The published Nature 2025 study evaluated on raw Kaggle partitions that contained <strong>110 cross-split duplicates</strong> between the training and test sets. This introduced severe data leakage, causing artificial score inflation. We conducted a rigorous perceptual hash audit (<code>audit_and_deduplicate()</code>) using dhash (threshold &le; 6). On the leak-free, clean dataset, the true baseline accuracy is 85.75%, which our correlated readout model elevates to 87.25% (and AUC to 88.90%)."</em>
    </div>
</div>

<div class="defense-qa">
    <div class="defense-q">Q2: Why did making the front quantum filter trainable not beat the frozen filter on single-qubit readout?</div>
    <div class="defense-a">
        <strong>Definitive Defense:</strong> <em>"This was one of our primary research findings: <strong>The Quantum Reservoir Principle</strong>. Because the input patches are 2&times;2 pixels, a frozen random unitary circuit acts as an optimal, zero-cost non-linear kernel projector into Hilbert space. When the terminal readout only measures single observable &lang;Z0&rang;, the model's expressivity is strictly bottlenecked at the output. Gradient descent shifts the filter weights (proven by parameter drift ||&theta; - &theta;0|| &asymp; 1.83 rad), but the single-qubit measurement cannot capture the extra expressive capacity (p = 0.220)."</em>
    </div>
</div>

<div class="defense-qa">
    <div class="defense-q">Q3: How does your Correlated Readout solve the information bottleneck?</div>
    <div class="defense-a">
        <strong>Definitive Defense:</strong> <em>"The terminal 2-qubit VQC uses an entangling CNOT gate to synthesize two-qubit quantum correlations. However, standard architectures trace out qubit 1 and only measure &lang;Z0&rang;. Our correlated head measures the full observable basis: [&lang;Z0&rang;, &lang;Z1&rang;, &lang;Z0 Z1&rang;]. The joint expectation &lang;Z0 Z1&rang; = (P00 + P11) - (P01 + P10) preserves non-local entanglement, improving test accuracy to 87.25% and AUC to 88.90%."</em>
    </div>
</div>

<div class="defense-qa">
    <div class="defense-q">Q4: Does your model suffer from Barren Plateaus?</div>
    <div class="defense-a">
        <strong>Definitive Defense:</strong> <em>"No. Barren plateaus occur primarily in deep circuits with random Haar unitaries across high qubit counts. Our architecture uses shallow circuits (L=1 to 3 layers) over 4 qubits in the filter and 2 qubits in the head, with localized entanglement. Parameter drift metrics confirm active, healthy gradient magnitudes throughout training."</em>
    </div>
</div>

<h2 class="section-heading">6.0 Live Demo Emergency Troubleshooting</h2>
<table class="data-table">
    <thead>
        <tr>
            <th style="width: 25%;">Potential Issue</th>
            <th style="width: 35%;">Root Cause</th>
            <th style="width: 40%;">Immediate 5-Second Fix</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Port 8501 Busy</strong></td>
            <td>Another Streamlit instance is running in background.</td>
            <td>Run: <code>python app_web.py --server.port 8502</code></td>
        </tr>
        <tr>
            <td><strong>Virtual Environment Not Active</strong></td>
            <td>Using system Python instead of project packages.</td>
            <td>Run: <code>.\\.venv\\Scripts\\Activate.ps1</code></td>
        </tr>
        <tr>
            <td><strong>Verification Check Required</strong></td>
            <td>Examiner asks to prove code validity on the spot.</td>
            <td>Run: <code>pytest tests/test_qsim_and_models.py -v</code> (14 tests pass in 3s)</td>
        </tr>
    </tbody>
</table>

<div style="margin-top: 10px; text-align: center; font-size: 7.5pt; font-weight: 600; color: #005A9C;">
    &copy; Team QForge &bull; Department of Computer Science & Engineering &bull; IIIT Kottayam &bull; Academic Year 2026
</div>

</body>
</html>
"""

    html_path = root / "demo_workflow_guide.html"
    print(f"Writing demo workflow HTML to {html_path}...")
    html_path.write_text(template, encoding="utf-8")
    print(f"HTML size: {len(template)} bytes")

    pdf_path = root / "demo_workflow_guide.pdf"
    print(f"Compiling PDF via Headless Microsoft Edge to {pdf_path}...")
    edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not Path(edge_exe).exists():
        edge_exe = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    cmd = [
        edge_exe,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        str(html_path),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error compiling PDF: {res.stderr}")
        sys.exit(res.returncode)

    if pdf_path.exists():
        size_kb = pdf_path.stat().st_size / 1024
        print(f"SUCCESS! Generated {pdf_path} ({size_kb:.1f} KB)")
    else:
        print("Failed to find generated PDF!")
        sys.exit(1)


if __name__ == "__main__":
    main()
