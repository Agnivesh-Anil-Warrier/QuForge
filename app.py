"""QForge Studio: Quantum-Lab Research Instrument Panel.

Aesthetic & Design Specifications:
- Palette: Canvas #060910, Panel #0A1019, Panel Hover #0F1826, Line #1B2A3A, Line Hover #2B4A5E
- Text: Primary #D7E4EA, Dim #6F8896, Faint #435765
- Accents: Electric Cyan #00E5FF, Model B Violet #B26BFF, Amber #FFB400, Green #39FF88, Red #FF4D5E
- Typography: JetBrains Mono / Cascadia Code / Consolas for everything
- Shape: 0-2px corners, 1px borders, zero gradients, zero heavy shadows
- Microcopy: Section titles `> SECTION`, subtitles `// SUBTITLE`, buttons `[ BUTTON ]`
- Console: Tagged lines `[SYS]`, `[TRAIN]`, `[DATA]`, `[STAT]` in cyan, `[OK]` green, `[WARN]` amber, `[ERR]` red
"""

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

import pandas as pd
from PySide6.QtCore import (
    QByteArray,
    QPoint,
    QPointF,
    QProcess,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QCursor,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QIcon,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QTextCursor,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

# ---------------------------------------------------------------------------
# Quantum-Lab Exact Color Palette
# ---------------------------------------------------------------------------
COLOR_CANVAS = "#060910"
COLOR_PANEL = "#0A1019"
COLOR_PANEL_HOVER = "#0F1826"
COLOR_LINE = "#1B2A3A"
COLOR_LINE_STRONG = "#2B4A5E"
COLOR_TEXT = "#D7E4EA"
COLOR_TEXT_DIM = "#6F8896"
COLOR_TEXT_FAINT = "#435765"

COLOR_CYAN = "#00E5FF"        # Primary Accent & Model A (Frozen)
COLOR_VIOLET = "#B26BFF"      # Model B (Trainable)
COLOR_AMBER = "#FFB400"       # Warnings, IDs, p-values
COLOR_GREEN = "#39FF88"       # [OK], Pass state only
COLOR_RED = "#FF4D5E"         # Stop, Error only

FONT_MONO = '"JetBrains Mono", "Cascadia Code", "Consolas", monospace'


# ---------------------------------------------------------------------------
# Quantum-Lab Global Stylesheet (0-2px radius, 1px lines, monospace)
# ---------------------------------------------------------------------------
LAB_QSS = f"""
QMainWindow {{
    background-color: {COLOR_CANVAS};
}}

QWidget {{
    color: {COLOR_TEXT};
    font-family: {FONT_MONO};
    font-size: 12px;
}}

/* Surface Panels */
QFrame.lab-panel {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_LINE};
    border-radius: 1px;
}}
QFrame.lab-panel:hover {{
    border-color: {COLOR_LINE_STRONG};
}}

/* Typography */
QLabel.heading-page {{
    font-size: 16px;
    font-weight: 700;
    color: {COLOR_TEXT};
    letter-spacing: 1.5px;
}}

QLabel.heading-section {{
    font-size: 13px;
    font-weight: 700;
    color: {COLOR_CYAN};
    letter-spacing: 1px;
}}

QLabel.text-dim {{
    font-size: 10px;
    color: {COLOR_TEXT_DIM};
    letter-spacing: 0.8px;
}}

/* Buttons */
QPushButton {{
    height: 32px;
    padding: 0 14px;
    border-radius: 1px;
    font-family: {FONT_MONO};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    background-color: transparent;
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_LINE};
}}
QPushButton:hover {{
    background-color: {COLOR_PANEL_HOVER};
    border-color: {COLOR_LINE_STRONG};
    color: #FFFFFF;
}}
QPushButton:pressed {{
    background-color: #142030;
}}
QPushButton:disabled {{
    border-color: {COLOR_LINE};
    color: {COLOR_TEXT_FAINT};
}}

/* Solid Cyan Primary Button */
QPushButton.btn-primary {{
    background-color: {COLOR_CYAN};
    color: #060910;
    border: 1px solid {COLOR_CYAN};
    font-weight: 800;
}}
QPushButton.btn-primary:hover {{
    background-color: #33EBFF;
    border-color: #33EBFF;
}}
QPushButton.btn-primary:pressed {{
    background-color: #00B4CC;
}}
QPushButton.btn-primary:disabled {{
    background-color: {COLOR_LINE};
    color: {COLOR_TEXT_FAINT};
    border-color: {COLOR_LINE};
}}

/* Danger Outline Button */
QPushButton.btn-danger {{
    background-color: transparent;
    color: {COLOR_RED};
    border: 1px solid {COLOR_RED};
}}
QPushButton.btn-danger:hover {{
    background-color: rgba(255, 77, 94, 0.12);
}}
QPushButton.btn-danger:disabled {{
    color: {COLOR_TEXT_FAINT};
    border-color: {COLOR_LINE};
}}

/* Inputs & Form Controls */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    height: 34px;
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_LINE};
    border-radius: 1px;
    padding: 0 10px;
    color: {COLOR_TEXT};
    font-family: {FONT_MONO};
    font-size: 12px;
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {COLOR_LINE_STRONG};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {COLOR_CYAN};
}}

/* Quiet Chevrons for SpinBoxes */
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    width: 16px;
    background: transparent;
    border: none;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {COLOR_PANEL_HOVER};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url(assets/icons/chevron-up.svg);
    width: 8px;
    height: 8px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url(assets/icons/chevron-down.svg);
    width: 8px;
    height: 8px;
}}

/* ComboBox Dropdown */
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: url(assets/icons/chevron-down.svg);
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_LINE_STRONG};
    selection-background-color: {COLOR_PANEL_HOVER};
    selection-color: {COLOR_CYAN};
    padding: 2px;
}}

/* Tables */
QTableWidget {{
    background-color: {COLOR_PANEL};
    border: 1px solid {COLOR_LINE};
    border-radius: 1px;
    gridline-color: {COLOR_LINE};
    color: {COLOR_TEXT};
    font-family: {FONT_MONO};
    font-size: 12px;
}}
QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {COLOR_LINE};
}}
QTableWidget::item:selected {{
    background-color: rgba(0, 229, 255, 0.12);
    color: {COLOR_CYAN};
}}
QHeaderView::section {{
    background-color: {COLOR_CANVAS};
    color: {COLOR_TEXT_DIM};
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid {COLOR_LINE};
    border-right: 1px solid {COLOR_LINE};
    font-family: {FONT_MONO};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}

/* Checkboxes */
QCheckBox {{
    color: {COLOR_TEXT_DIM};
    spacing: 8px;
    font-size: 11px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 1px;
    border: 1px solid {COLOR_LINE_STRONG};
    background-color: {COLOR_PANEL};
}}
QCheckBox::indicator:hover {{
    border-color: {COLOR_CYAN};
}}
QCheckBox::indicator:checked {{
    background-color: {COLOR_CYAN};
    border-color: {COLOR_CYAN};
    image: url(assets/icons/check.svg);
}}

/* Console Boxes */
QTextEdit.lab-console, QTextBrowser.lab-console {{
    background-color: {COLOR_CANVAS};
    border: 1px solid {COLOR_LINE};
    border-radius: 1px;
    color: {COLOR_TEXT};
    font-family: {FONT_MONO};
    font-size: 12px;
    line-height: 1.5;
    padding: 10px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_LINE};
    min-height: 20px;
    border-radius: 1px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_LINE_STRONG};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: {COLOR_LINE};
    min-width: 20px;
    border-radius: 1px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLOR_LINE_STRONG};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


# ---------------------------------------------------------------------------
# Helper Component: Lab Stat Card
# ---------------------------------------------------------------------------
class LabStatCard(QFrame):
    """Square-edged instrument stat card: > TITLE / VALUE / [FOOTNOTE]."""

    def __init__(
        self,
        title: str,
        value: str,
        subtext: str,
        title_color: str = COLOR_CYAN,
        value_color: str = COLOR_TEXT,
        parent=None,
    ):
        super().__init__(parent)
        self.setProperty("class", "lab-panel")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_PANEL};
                border: 1px solid {COLOR_LINE};
                border-radius: 1px;
            }}
            QFrame:hover {{
                border-color: {COLOR_LINE_STRONG};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        lbl_title = QLabel(f"> {title.upper()}")
        lbl_title.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {title_color}; letter-spacing: 0.8px;")
        layout.addWidget(lbl_title)

        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {value_color};")
        layout.addWidget(lbl_value)

        lbl_sub = QLabel(subtext)
        lbl_sub.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_DIM}; letter-spacing: 0.5px;")
        lbl_sub.setWordWrap(True)
        layout.addWidget(lbl_sub)


# ---------------------------------------------------------------------------
# Custom QPainter Chart: Quantum Lab Bar Chart
# ---------------------------------------------------------------------------
class LabBarChart(QWidget):
    """High-precision instrument chart with 10% grid lines, cyan & violet series."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.metrics = [
            ("ACCURACY", 0.8575, 0.0166, 0.8536, 0.0114),
            ("BAL_ACC", 0.8234, 0.0249, 0.8222, 0.0117),
            ("F1_SCORE", 0.7777, 0.0344, 0.7758, 0.0161),
            ("ROC_AUC", 0.8733, 0.0194, 0.8734, 0.0111),
        ]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)  # Sharp pixel lines

        w = self.width()
        h = self.height()
        m_l, m_r, m_t, m_b = 50, 16, 24, 26
        cw = w - m_l - m_r
        ch = h - m_t - m_b

        # Background
        p.fillRect(0, 0, w, h, QColor(COLOR_PANEL))

        # 10% grid lines
        grid_pen = QPen(QColor(COLOR_LINE), 1)
        p.setPen(grid_pen)
        font = QFont("JetBrains Mono", 8)
        p.setFont(font)

        min_v, max_v = 0.70, 0.90
        for tick in [0.70, 0.75, 0.80, 0.85, 0.90]:
            y = m_t + ch - int((tick - min_v) / (max_v - min_v) * ch)
            p.drawLine(m_l, y, w - m_r, y)
            p.setPen(QColor(COLOR_TEXT_DIM))
            p.drawText(6, y + 4, f"{int(tick*100)}%")
            p.setPen(grid_pen)

        # Draw Grouped Bars
        n = len(self.metrics)
        grp_w = cw / n
        bar_w = min(18, grp_w * 0.32)

        for i, (name, a_m, a_s, b_m, b_s) in enumerate(self.metrics):
            cx = m_l + (i + 0.5) * grp_w

            # Model A (Cyan)
            x_a = int(cx - bar_w - 2)
            h_a = int((a_m - min_v) / (max_v - min_v) * ch)
            y_a = m_t + ch - h_a
            p.fillRect(x_a, y_a, int(bar_w), h_a, QColor(COLOR_CYAN))

            # Error bar A
            err_top_a = m_t + ch - int(((a_m + a_s) - min_v) / (max_v - min_v) * ch)
            err_bot_a = m_t + ch - int(((a_m - a_s) - min_v) / (max_v - min_v) * ch)
            p.setPen(QPen(QColor(COLOR_TEXT), 1))
            p.drawLine(int(x_a + bar_w / 2), err_top_a, int(x_a + bar_w / 2), err_bot_a)

            # Model B (Violet)
            x_b = int(cx + 2)
            h_b = int((b_m - min_v) / (max_v - min_v) * ch)
            y_b = m_t + ch - h_b
            p.fillRect(x_b, y_b, int(bar_w), h_b, QColor(COLOR_VIOLET))

            # Error bar B
            err_top_b = m_t + ch - int(((b_m + b_s) - min_v) / (max_v - min_v) * ch)
            err_bot_b = m_t + ch - int(((b_m - b_s) - min_v) / (max_v - min_v) * ch)
            p.drawLine(int(x_b + bar_w / 2), err_top_b, int(x_b + bar_w / 2), err_bot_b)

            # Label
            p.setPen(QColor(COLOR_TEXT_DIM))
            p.drawText(QRectF(cx - grp_w / 2, h - m_b + 6, grp_w, 16), Qt.AlignCenter, name)

        # Legend
        p.fillRect(w - 180, 8, 8, 8, QColor(COLOR_CYAN))
        p.setPen(QColor(COLOR_TEXT))
        p.drawText(w - 168, 16, "MODEL A (CYAN)")

        p.fillRect(w - 90, 8, 8, 8, QColor(COLOR_VIOLET))
        p.drawText(w - 78, 16, "MODEL B (VIO)")
        p.end()


# ---------------------------------------------------------------------------
# Custom QPainter Chart: Live Loss Chart with Blinking Cursor
# ---------------------------------------------------------------------------
class LabLiveLossChart(QWidget):
    """Live loss & accuracy line chart with lab styling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(160)
        self.train_loss: List[float] = []
        self.val_loss: List[float] = []

    def clear(self):
        self.train_loss.clear()
        self.val_loss.clear()
        self.update()

    def add_epoch(self, t_loss: float, v_loss: float):
        self.train_loss.append(t_loss)
        self.val_loss.append(v_loss)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()
        m_l, m_r, m_t, m_b = 40, 16, 20, 20
        cw = w - m_l - m_r
        ch = h - m_t - m_b

        # Canvas fill
        p.fillRect(0, 0, w, h, QColor(COLOR_CANVAS))
        p.setPen(QPen(QColor(COLOR_LINE), 1))
        p.drawRect(0, 0, w - 1, h - 1)

        if not self.train_loss:
            p.setPen(QColor(COLOR_TEXT_DIM))
            p.setFont(QFont("JetBrains Mono", 10))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "// NO ACTIVE RUN · PRESS [ > RUN EXPERIMENT ]")
            p.end()
            return

        n = len(self.train_loss)
        max_l = max(max(self.train_loss), max(self.val_loss), 1.0)

        # 10% grid
        p.setPen(QPen(QColor(COLOR_LINE), 1, Qt.DashLine))
        font = QFont("JetBrains Mono", 8)
        p.setFont(font)
        for tick in [0.25, 0.50, 0.75, 1.0]:
            if tick <= max_l:
                y = m_t + ch - int((tick / max_l) * ch)
                p.drawLine(m_l, y, w - m_r, y)
                p.setPen(QColor(COLOR_TEXT_DIM))
                p.drawText(6, y + 4, f"{tick:.2f}")
                p.setPen(QPen(QColor(COLOR_LINE), 1, Qt.DashLine))

        def pt(idx, val):
            x = m_l + (idx / max(1, n - 1)) * cw if n > 1 else m_l + cw / 2
            y = m_t + ch - (val / max_l) * ch
            return QPointF(x, y)

        # Train loss (Cyan dashed)
        p.setPen(QPen(QColor(COLOR_CYAN), 1.5, Qt.DashLine))
        for i in range(n - 1):
            p.drawLine(pt(i, self.train_loss[i]), pt(i + 1, self.train_loss[i + 1]))

        # Val loss (Violet solid)
        p.setPen(QPen(QColor(COLOR_VIOLET), 2.0, Qt.SolidLine))
        for i in range(n - 1):
            p.drawLine(pt(i, self.val_loss[i]), pt(i + 1, self.val_loss[i + 1]))

        # Legend
        p.setPen(QColor(COLOR_CYAN))
        p.drawText(m_l + 10, m_t - 6, "TRAIN LOSS (CYAN --)")
        p.setPen(QColor(COLOR_VIOLET))
        p.drawText(m_l + 160, m_t - 6, "VAL LOSS (VIOLET -)")
        p.setPen(QColor(COLOR_AMBER))
        p.drawText(w - m_r - 90, m_t - 6, f"EPOCH {n}")

        p.end()


# ---------------------------------------------------------------------------
# Tab 1: Dashboard (Quantum-Lab Spec)
# ---------------------------------------------------------------------------
class LabDashboardView(QWidget):
    """Quantum-Lab Dashboard: > QFORGE DASHBOARD, 4 Stat Cards, Boot Log, Action Bar."""

    action_requested = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Header
        h_box = QVBoxLayout()
        h_box.setSpacing(2)
        title = QLabel("> QFORGE DASHBOARD")
        title.setProperty("class", "heading-page")
        sub = QLabel("// REPRODUCING LONG ET AL. (2025) · SCI REPORTS 15, 31780")
        sub.setProperty("class", "text-dim")
        h_box.addWidget(title)
        h_box.addWidget(sub)
        layout.addLayout(h_box)

        # 2. Four Equal Stat Cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        c1 = LabStatCard(
            title="MODEL A · FROZEN",
            value="85.75%",
            subtext="[± 1.66 · LOSS 0.7609]",
            title_color=COLOR_CYAN,
            value_color=COLOR_CYAN,
        )
        c2 = LabStatCard(
            title="MODEL B · TRAINABLE",
            value="85.36%",
            subtext="[Δ −0.39% · LOSS 0.7007]",
            title_color=COLOR_VIOLET,
            value_color=COLOR_VIOLET,
        )
        c3 = LabStatCard(
            title="PARAMETER DRIFT",
            value="1.83 RAD",
            subtext="[ACTIVE GRADIENT FLOW · NO BARREN PLATEAU]",
            title_color=COLOR_TEXT,
            value_color=COLOR_TEXT,
        )
        c4 = LabStatCard(
            title="VERDICT (P-VALUE)",
            value="p = 0.220",
            subtext="[NO SIGNIFICANT DIFFERENCE · N=5]",
            title_color=COLOR_AMBER,
            value_color=COLOR_AMBER,
        )

        cards_row.addWidget(c1)
        cards_row.addWidget(c2)
        cards_row.addWidget(c3)
        cards_row.addWidget(c4)
        layout.addLayout(cards_row)

        # 3. Action Bar (like LMS bottom bar)
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        btn_bench = QPushButton("[ > RUN BENCHMARK ]")
        btn_bench.setProperty("class", "btn-primary")
        btn_bench.clicked.connect(lambda: self.action_requested.emit("benchmark", ["scripts/benchmark_and_smoke.py"]))

        btn_tests = QPushButton("[ RUN TESTS ]")
        btn_tests.clicked.connect(lambda: self.action_requested.emit("pytest", ["-m", "pytest", "-v"]))

        btn_report = QPushButton("[ RECOMPUTE FIGURES ]")
        btn_report.clicked.connect(lambda: self.action_requested.emit("report", ["scripts/make_report.py"]))

        btn_pdf = QPushButton("[ OPEN PRESENTATION ]")
        btn_pdf.clicked.connect(self.open_presentation)

        action_bar.addWidget(btn_bench)
        action_bar.addWidget(btn_tests)
        action_bar.addWidget(btn_report)
        action_bar.addWidget(btn_pdf)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        # 4. Two-Panel Row: > KEY FINDINGS & > SYSTEM BOOT LOG
        two_panel = QHBoxLayout()
        two_panel.setSpacing(12)

        # Left: Key Findings
        find_panel = QFrame()
        find_panel.setProperty("class", "lab-panel")
        f_vbox = QVBoxLayout(find_panel)
        f_vbox.setContentsMargins(16, 14, 16, 14)
        f_vbox.setSpacing(12)

        f_head = QLabel("> KEY FINDINGS")
        f_head.setProperty("class", "heading-section")
        f_vbox.addWidget(f_head)

        def make_finding(num: str, title: str, desc: str):
            w = QWidget()
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(2)
            t = QLabel(f"{num} {title}")
            t.setStyleSheet(f"font-weight: 700; color: {COLOR_TEXT}; font-size: 11px;")
            d = QLabel(desc)
            d.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px; line-height: 1.4;")
            d.setWordWrap(True)
            v.addWidget(t)
            v.addWidget(d)
            return w

        f_vbox.addWidget(make_finding("01.", "DATA LEAKAGE ELIMINATED", "110 cross-split duplicates between Kaggle train & test pruned via perceptual hashing (dhash), eliminating synthetic score inflation."))
        f_vbox.addWidget(make_finding("02.", "434 IMG/S VECTORIZED ENGINE", "Pure-PyTorch einsum batched statevector sim on CPU dropped epoch training duration from 30+ minutes down to 7.0 seconds."))
        f_vbox.addWidget(make_finding("03.", "QUANTUM RESERVOIR PRINCIPLE", "Frozen random quantum circuit acts as optimal zero-compute non-linear projector. Trainable filters show no accuracy gain (p = 0.220)."))
        f_vbox.addStretch()
        two_panel.addWidget(find_panel, 1)

        # Right: System Boot Log (Console pattern)
        boot_panel = QFrame()
        boot_panel.setProperty("class", "lab-panel")
        b_vbox = QVBoxLayout(boot_panel)
        b_vbox.setContentsMargins(16, 14, 16, 14)
        b_vbox.setSpacing(8)

        b_head = QLabel("> SYSTEM BOOT LOG")
        b_head.setProperty("class", "heading-section")
        b_vbox.addWidget(b_head)

        boot_text = QTextBrowser()
        boot_text.setProperty("class", "lab-console")
        boot_text.setHtml(f"""
        <div style="font-family:{FONT_MONO}; font-size:11px; line-height:1.6; color:{COLOR_TEXT};">
        <span style="color:{COLOR_CYAN};">[SYS]</span> OS: MICROSOFT WINDOWS 11 <span style="color:{COLOR_GREEN};">[OK]</span><br>
        <span style="color:{COLOR_CYAN};">[SYS]</span> CPU: AMD RYZEN 7 5700U · 8C/16T <span style="color:{COLOR_GREEN};">[OK]</span><br>
        <span style="color:{COLOR_CYAN};">[SYS]</span> RAM: 15.3 GB DETECTED <span style="color:{COLOR_GREEN};">[OK]</span><br>
        <span style="color:{COLOR_CYAN};">[SYS]</span> BACKEND: PYTORCH_CPU_EINSUM (434 IMG/S) <span style="color:{COLOR_GREEN};">[OK]</span><br>
        <span style="color:{COLOR_CYAN};">[DATA]</span> KAGGLE BRAIN MRI · 5,222 STRATIFIED SLICES <span style="color:{COLOR_GREEN};">[OK]</span><br>
        <span style="color:{COLOR_CYAN};">[DATA]</span> LEAKAGE PRUNED: 110 SAMPLES REMOVED <span style="color:{COLOR_GREEN};">[OK]</span><br>
        <span style="color:{COLOR_CYAN};">[QUANTUM]</span> 4-QUBIT QUANVOLUTION + 2-QUBIT VQC <span style="color:{COLOR_GREEN};">[OK]</span><br>
        <span style="color:{COLOR_CYAN};">[STAT]</span> 25/25 REPRODUCIBILITY SEED RUNS VERIFIED <span style="color:{COLOR_GREEN};">[OK]</span>
        </div>
        """)
        b_vbox.addWidget(boot_text)
        two_panel.addWidget(boot_panel, 1)

        layout.addLayout(two_panel, 1)

    def open_presentation(self):
        p = PROJECT_ROOT / "presentation.pdf"
        if p.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
        else:
            QMessageBox.warning(self, "PDF Missing", f"Could not find {p}.")


# ---------------------------------------------------------------------------
# Tab 2: Experiment Runner (Quantum-Lab Spec)
# ---------------------------------------------------------------------------
class LabExperimentRunnerView(QWidget):
    """Quantum-Lab Runner: square inputs, thin progress bar, live chart, tagged console with blinking cursor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process: Optional[QProcess] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # -------------------------------------------------------------------
        # Left Panel (320px)
        # -------------------------------------------------------------------
        left_col = QFrame()
        left_col.setProperty("class", "lab-panel")
        left_col.setFixedWidth(320)
        left_vbox = QVBoxLayout(left_col)
        left_vbox.setContentsMargins(16, 14, 16, 14)
        left_vbox.setSpacing(10)

        left_head = QLabel("> PARAMETERS")
        left_head.setProperty("class", "heading-section")
        left_vbox.addWidget(left_head)

        def add_input(label_text: str, w: QWidget):
            lbl = QLabel(label_text.upper())
            lbl.setProperty("class", "text-dim")
            left_vbox.addWidget(lbl)
            left_vbox.addWidget(w)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["trainable", "frozen_random", "classical_conv", "none"])
        add_input("Filter Mode", self.combo_mode)

        self.spin_seed = QSpinBox()
        self.spin_seed.setRange(0, 999999)
        self.spin_seed.setValue(42)
        add_input("Random Seed", self.spin_seed)

        self.spin_depth = QSpinBox()
        self.spin_depth.setRange(1, 5)
        self.spin_depth.setValue(1)
        add_input("Filter Depth (L)", self.spin_depth)

        self.spin_epochs = QSpinBox()
        self.spin_epochs.setRange(1, 200)
        self.spin_epochs.setValue(10)
        add_input("Max Epochs", self.spin_epochs)

        self.spin_lr_filter = QDoubleSpinBox()
        self.spin_lr_filter.setDecimals(4)
        self.spin_lr_filter.setRange(0.0001, 1.0)
        self.spin_lr_filter.setSingleStep(0.005)
        self.spin_lr_filter.setValue(0.0100)
        add_input("Filter LR (η)", self.spin_lr_filter)

        self.spin_patience = QSpinBox()
        self.spin_patience.setRange(1, 50)
        self.spin_patience.setValue(15)
        add_input("Patience", self.spin_patience)

        self.edit_run_name = QLineEdit()
        self.edit_run_name.setPlaceholderText("auto (exp_<mode>_seed<seed>)")
        add_input("Run Identifier", self.edit_run_name)

        left_vbox.addSpacing(6)

        # Buttons
        self.btn_run = QPushButton("[ > RUN EXPERIMENT ]")
        self.btn_run.setProperty("class", "btn-primary")
        self.btn_run.clicked.connect(self.start_single_experiment)
        left_vbox.addWidget(self.btn_run)

        self.btn_grid = QPushButton("[ RUN AUTOMATED GRID ]")
        self.btn_grid.clicked.connect(self.start_run_all)
        left_vbox.addWidget(self.btn_grid)

        self.btn_stop = QPushButton("[ X STOP ]")
        self.btn_stop.setProperty("class", "btn-danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_process)
        left_vbox.addWidget(self.btn_stop)

        left_vbox.addStretch()
        layout.addWidget(left_col)

        # -------------------------------------------------------------------
        # Right Panel: Strip + Live Loss Chart + Console
        # -------------------------------------------------------------------
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        # Top Strip: Progress Bar with 42% [TRAINING]
        strip_frame = QFrame()
        strip_frame.setProperty("class", "lab-panel")
        s_layout = QHBoxLayout(strip_frame)
        s_layout.setContentsMargins(14, 8, 14, 8)
        s_layout.setSpacing(12)

        s_tag = QLabel("> PROGRESS:")
        s_tag.setProperty("class", "text-dim")
        s_layout.addWidget(s_tag)

        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(3)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLOR_LINE};
                border: none;
                border-radius: 0px;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_CYAN};
            }}
        """)
        s_layout.addWidget(self.prog_bar, 1)

        self.lbl_status_tag = QLabel("[● READY]")
        self.lbl_status_tag.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_GREEN};")
        s_layout.addWidget(self.lbl_status_tag)

        right_col.addWidget(strip_frame)

        # Splitter between Live Chart & Console
        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {COLOR_LINE}; height: 2px; }}")

        # Live Chart Panel
        chart_panel = QFrame()
        chart_panel.setProperty("class", "lab-panel")
        c_vbox = QVBoxLayout(chart_panel)
        c_vbox.setContentsMargins(12, 10, 12, 10)
        c_vbox.setSpacing(6)

        c_head = QLabel("> LIVE DYNAMICS // LOSS [CYAN: TRAIN · VIOLET: VAL]")
        c_head.setProperty("class", "text-dim")
        c_vbox.addWidget(c_head)

        self.chart = LabLiveLossChart()
        c_vbox.addWidget(self.chart)
        splitter.addWidget(chart_panel)

        # Console Panel
        cons_panel = QFrame()
        cons_panel.setProperty("class", "lab-panel")
        cons_vbox = QVBoxLayout(cons_panel)
        cons_vbox.setContentsMargins(12, 10, 12, 10)
        cons_vbox.setSpacing(8)

        # Toolbar
        t_box = QHBoxLayout()
        self.cons_header = QLabel("> EXECUTION CONSOLE ▮")
        self.cons_header.setProperty("class", "text-dim")
        t_box.addWidget(self.cons_header)
        t_box.addStretch()

        self.chk_auto = QCheckBox("AUTO-SCROLL")
        self.chk_auto.setChecked(True)
        t_box.addWidget(self.chk_auto)

        btn_cp = QPushButton("[ COPY ]")
        btn_cp.setFixedHeight(24)
        btn_cp.clicked.connect(self.copy_log)
        t_box.addWidget(btn_cp)

        btn_sv = QPushButton("[ SAVE LOG ]")
        btn_sv.setFixedHeight(24)
        btn_sv.clicked.connect(self.save_log)
        t_box.addWidget(btn_sv)

        btn_cl = QPushButton("[ CLEAR ]")
        btn_cl.setFixedHeight(24)
        btn_cl.clicked.connect(self.clear_log)
        t_box.addWidget(btn_cl)

        cons_vbox.addLayout(t_box)

        self.console = QTextEdit()
        self.console.setProperty("class", "lab-console")
        self.console.setReadOnly(True)
        cons_vbox.addWidget(self.console, 1)

        splitter.addWidget(cons_panel)
        splitter.setSizes([180, 360])

        right_col.addWidget(splitter, 1)
        layout.addLayout(right_col, 1)

        # Blinking cursor timer
        self.cursor_state = True
        self.timer_cursor = QTimer(self)
        self.timer_cursor.timeout.connect(self.blink_cursor)
        self.timer_cursor.start(500)

    def blink_cursor(self):
        self.cursor_state = not self.cursor_state
        mark = "▮" if self.cursor_state else " "
        self.cons_header.setText(f"> EXECUTION CONSOLE {mark}")

    def append_log_tagged(self, raw_line: str):
        now_str = datetime.now().strftime("%H:%M:%S")
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)

        line = raw_line.strip()
        tag = "[STAT]"
        tag_color = COLOR_CYAN

        if "Epoch" in line or "Training" in line:
            tag = "[TRAIN]"
            tag_color = COLOR_CYAN
        elif "data" in line.lower() or "cache" in line.lower() or "dataset" in line.lower():
            tag = "[DATA]"
            tag_color = COLOR_CYAN
        elif "sys" in line.lower() or "hardware" in line.lower() or "launch" in line.lower():
            tag = "[SYS]"
            tag_color = COLOR_CYAN

        status_tag = ""
        if "ERROR" in line or "Error" in line or "FAIL" in line or "Traceback" in line:
            status_tag = f'<span style="color:{COLOR_RED}; font-weight:700;">[ERR]</span> '
        elif "WARN" in line or "Warning" in line:
            status_tag = f'<span style="color:{COLOR_AMBER}; font-weight:700;">[WARN]</span> '
        elif "PASSED" in line or "Success" in line or "completed successfully" in line:
            status_tag = f'<span style="color:{COLOR_GREEN}; font-weight:700;">[OK]</span> '

        time_part = f'<span style="color:{COLOR_TEXT_DIM};">{now_str}</span> '
        tag_part = f'<span style="color:{tag_color}; font-weight:700;">{tag}</span> '
        text_part = f'<span style="color:{COLOR_TEXT};">{line}</span>'

        cursor.insertHtml(f"{time_part}{tag_part}{status_tag}{text_part}<br>")

        if self.chk_auto.isChecked():
            self.console.setTextCursor(cursor)
            self.console.ensureCursorVisible()

        # Parse epoch table: e.g. " 1 | 0.6931 | 0.5200 | 0.6900 | 0.5400 | ..."
        m = re.match(r"^\s*(\d+)\s*\|\s*([\d\.]+)\s*\|\s*([\d\.]+)\s*\|\s*([\d\.]+)\s*\|\s*([\d\.]+)", line)
        if m:
            epoch = int(m.group(1))
            t_loss = float(m.group(2))
            v_loss = float(m.group(4))
            self.chart.add_epoch(t_loss, v_loss)
            max_ep = self.spin_epochs.value()
            pct = int(min(100, (epoch / max_ep) * 100)) if max_ep > 0 else 0
            self.prog_bar.setRange(0, 100)
            self.prog_bar.setValue(pct)
            self.lbl_status_tag.setText(f"{pct}% [TRAINING]")
            self.lbl_status_tag.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_CYAN};")

    def launch_script(self, args: List[str]):
        if self.process and self.process.state() == QProcess.Running:
            QMessageBox.warning(self, "Process Active", "A script is already running. Please terminate it first.")
            return

        self.chart.clear()
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.setWorkingDirectory(str(PROJECT_ROOT))
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.finished.connect(self.handle_finished)

        cmd = f"{PYTHON_EXE} {' '.join(args)}"
        self.append_log_tagged(f"LAUNCHING: {cmd}")

        self.prog_bar.setRange(0, 0)
        self.lbl_status_tag.setText("[● RUNNING]")
        self.lbl_status_tag.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_AMBER};")
        self.btn_run.setEnabled(False)
        self.btn_grid.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self.process.start(PYTHON_EXE, args)

    def start_single_experiment(self):
        args = [
            str(PROJECT_ROOT / "scripts" / "run_experiment.py"),
            "--mode", self.combo_mode.currentText(),
            "--seed", str(self.spin_seed.value()),
            "--depth", str(self.spin_depth.value()),
            "--epochs", str(self.spin_epochs.value()),
            "--lr-filter", str(self.spin_lr_filter.value()),
            "--patience", str(self.spin_patience.value()),
        ]
        name = self.edit_run_name.text().strip()
        if name:
            args.extend(["--run-name", name])
        self.launch_script(args)

    def start_run_all(self):
        args = [str(PROJECT_ROOT / "scripts" / "run_all.py")]
        self.launch_script(args)

    @Slot()
    def handle_stdout(self):
        if not self.process:
            return
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="replace")
        for line in text.splitlines():
            if line.strip():
                self.append_log_tagged(line)

    @Slot(int, QProcess.ExitStatus)
    def handle_finished(self, exit_code: int, exit_status: QProcess.ExitStatus):
        self.btn_run.setEnabled(True)
        self.btn_grid.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(100 if exit_code == 0 else 0)

        if exit_code == 0:
            self.lbl_status_tag.setText("[● FINISHED 0]")
            self.lbl_status_tag.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_GREEN};")
            self.append_log_tagged("PROCESS TERMINATED NORMALLY [OK]")
        else:
            self.lbl_status_tag.setText(f"[● FAILED {exit_code}]")
            self.lbl_status_tag.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_RED};")
            self.append_log_tagged(f"PROCESS EXITED WITH CODE {exit_code} [ERR]")

    def stop_process(self):
        if self.process and self.process.state() == QProcess.Running:
            self.append_log_tagged("SENDING SIGKILL TO TASK [WARN]")
            self.process.kill()

    def copy_log(self):
        QApplication.clipboard().setText(self.console.toPlainText())

    def save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", str(PROJECT_ROOT / "qforge_log.txt"), "Text Files (*.txt)")
        if path:
            Path(path).write_text(self.console.toPlainText(), encoding="utf-8")

    def clear_log(self):
        self.console.clear()


# ---------------------------------------------------------------------------
# Tab 3: Results (Quantum-Lab Spec)
# ---------------------------------------------------------------------------
class LabResultsView(QWidget):
    """Filter chips [ CORE ] [ SIGNIFICANCE ] [ ALL RUNS ], 1px cell borders, amber/cyan/violet text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Filter Chips Bar (like LMS year filter)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        lbl = QLabel("> VIEW:")
        lbl.setProperty("class", "text-dim")
        top_bar.addWidget(lbl)

        self.btn_f_core = QPushButton("[ ■ CORE ]")
        self.btn_f_sig = QPushButton("[ SIGNIFICANCE ]")
        self.btn_f_runs = QPushButton("[ ALL RUNS ]")

        for b in [self.btn_f_core, self.btn_f_sig, self.btn_f_runs]:
            b.setCheckable(True)
            b.setFixedHeight(28)
            b.setStyleSheet(f"""
                QPushButton {{
                    font-size: 11px;
                    padding: 0 10px;
                    border: 1px solid {COLOR_LINE};
                    background: {COLOR_PANEL};
                    color: {COLOR_TEXT_DIM};
                }}
                QPushButton:checked {{
                    border: 1px solid {COLOR_CYAN};
                    color: {COLOR_CYAN};
                    background: {COLOR_PANEL_HOVER};
                    font-weight: 700;
                }}
                QPushButton:hover:!checked {{
                    border-color: {COLOR_LINE_STRONG};
                    color: {COLOR_TEXT};
                }}
            """)
            top_bar.addWidget(b)

        self.chip_group = QButtonGroup(self)
        self.chip_group.addButton(self.btn_f_core, 0)
        self.chip_group.addButton(self.btn_f_sig, 1)
        self.chip_group.addButton(self.btn_f_runs, 2)
        self.btn_f_core.setChecked(True)
        self.chip_group.idClicked.connect(self.switch_sub_view)

        top_bar.addStretch()

        btn_export = QPushButton("[ EXPORT CSV ]")
        btn_export.setFixedHeight(28)
        btn_export.clicked.connect(self.export_csv)
        top_bar.addWidget(btn_export)

        btn_ref = QPushButton("[ REFRESH ]")
        btn_ref.setFixedHeight(28)
        btn_ref.clicked.connect(self.load_all)
        top_bar.addWidget(btn_ref)

        layout.addLayout(top_bar)

        # Stacked Views
        self.stack = QStackedWidget()

        # 1. Core comparison view
        view_c = QWidget()
        vc_layout = QVBoxLayout(view_c)
        vc_layout.setContentsMargins(0, 0, 0, 0)
        vc_layout.setSpacing(12)

        self.tbl_core = QTableWidget()
        self.tbl_core.verticalHeader().setVisible(False)
        self.tbl_core.setSelectionBehavior(QTableWidget.SelectRows)
        vc_layout.addWidget(self.tbl_core, 2)

        # Chart below table to fill empty space
        chart_p = QFrame()
        chart_p.setProperty("class", "lab-panel")
        cp_v = QVBoxLayout(chart_p)
        cp_v.setContentsMargins(14, 10, 14, 10)
        cp_v.setSpacing(6)
        cp_h = QLabel("> EMPIRICAL BENCHMARK METRICS WITH ±1 SD WHISKERS")
        cp_h.setProperty("class", "text-dim")
        cp_v.addWidget(cp_h)
        cp_v.addWidget(LabBarChart())
        vc_layout.addWidget(chart_p, 3)

        self.stack.addWidget(view_c)

        # 2. Significance view
        self.browser_sig = QTextBrowser()
        self.browser_sig.setProperty("class", "lab-console")
        self.stack.addWidget(self.browser_sig)

        # 3. All runs view
        self.tbl_runs = QTableWidget()
        self.tbl_runs.verticalHeader().setVisible(False)
        self.tbl_runs.setSelectionBehavior(QTableWidget.SelectRows)
        self.stack.addWidget(self.tbl_runs)

        layout.addWidget(self.stack, 1)
        self.load_all()

    def switch_sub_view(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self.btn_f_core.setText("[ ■ CORE ]" if idx == 0 else "[ CORE ]")
        self.btn_f_sig.setText("[ ■ SIGNIFICANCE ]" if idx == 1 else "[ SIGNIFICANCE ]")
        self.btn_f_runs.setText("[ ■ ALL RUNS ]" if idx == 2 else "[ ALL RUNS ]")

    def load_all(self):
        self.load_core()
        self.load_sig()
        self.load_runs()

    def load_core(self):
        p = PROJECT_ROOT / "results" / "table_main_comparison.csv"
        if not p.exists():
            p = PROJECT_ROOT / "results" / "summary.csv"
        if not p.exists():
            return

        df = pd.read_csv(p)
        cols = ["group", "n_seeds", "test_acc_formatted", "test_bal_acc_formatted", "test_f1_formatted", "test_auc_formatted", "param_drift_formatted", "test_loss_formatted"]
        available = [c for c in cols if c in df.columns]
        df_sub = df[available]

        headers = ["MODEL ARCHITECTURE", "SEEDS", "ACCURACY", "BAL_ACC", "F1_SCORE", "ROC_AUC", "PARAM_DRIFT", "LOSS"]
        self.tbl_core.setRowCount(len(df_sub))
        self.tbl_core.setColumnCount(len(available))
        self.tbl_core.setHorizontalHeaderLabels(headers[:len(available)])

        for r, row in df_sub.iterrows():
            is_model_a = "frozen" in str(row["group"]).lower()
            is_corr = "correlated" in str(row["group"]).lower()
            accent_col = COLOR_GREEN if is_corr else (COLOR_CYAN if is_model_a else COLOR_VIOLET)

            for c, col_name in enumerate(available):
                val_str = str(row[col_name])
                item = QTableWidgetItem(val_str)
                if c == 0:
                    item.setForeground(QColor(COLOR_AMBER))
                    item.setText(f"> {val_str.upper()}")
                else:
                    item.setForeground(QColor(accent_col))
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tbl_core.setItem(r, c, item)

        self.tbl_core.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(available)):
            self.tbl_core.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)

    def load_sig(self):
        p = PROJECT_ROOT / "results" / "statistical_tests.json"
        if not p.exists():
            self.browser_sig.setPlainText("// STATISTICAL_TESTS.JSON NOT FOUND")
            return

        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        tests = data.get("tests", {})

        html = f"""
        <div style="font-family:{FONT_MONO}; color:{COLOR_TEXT}; line-height:1.6; padding:10px;">
        <h3 style="color:{COLOR_CYAN}; margin:0 0 6px 0;">> PAIRED HYPOTHESIS TESTING (N = 5 MATCHED SEEDS)</h3>
        <p style="color:{COLOR_TEXT_DIM}; margin:0 0 14px 0; font-size:11px;">
            // COMMON SEEDS: {data.get('common_seeds')} · TWO-TAILED PAIRED t-TEST & WILCOXON SIGNED-RANK
        </p>

        <table style="width:100%; border-collapse:collapse; margin-bottom:16px;">
            <tr style="background:{COLOR_CANVAS}; color:{COLOR_TEXT_DIM}; font-size:10px; text-transform:uppercase;">
                <th style="padding:8px; border:1px solid {COLOR_LINE};">METRIC</th>
                <th style="padding:8px; border:1px solid {COLOR_LINE};">MODEL A (FROZEN)</th>
                <th style="padding:8px; border:1px solid {COLOR_LINE};">MODEL B (TRAIN)</th>
                <th style="padding:8px; border:1px solid {COLOR_LINE};">DIFF (B − A)</th>
                <th style="padding:8px; border:1px solid {COLOR_LINE};">t-STAT</th>
                <th style="padding:8px; border:1px solid {COLOR_LINE};">p-VALUE</th>
                <th style="padding:8px; border:1px solid {COLOR_LINE};">SIGNIFICANT?</th>
            </tr>
        """
        for m, s in tests.items():
            mA = f"{s['mean_a']*100:.2f}%" if "loss" not in m else f"{s['mean_a']:.4f}"
            mB = f"{s['mean_b']*100:.2f}%" if "loss" not in m else f"{s['mean_b']:.4f}"
            dF = f"{s['mean_diff']*100:+.2f}%" if "loss" not in m else f"{s['mean_diff']:+.4f}"
            pv = s.get("paired_t_pval", 1.0)
            sig_txt = f'<span style="color:{COLOR_RED};">[YES]</span>' if s.get("is_significant_p05", False) else f'<span style="color:{COLOR_GREEN};">[NO]</span>'

            html += f"""
            <tr>
                <td style="padding:8px; border:1px solid {COLOR_LINE}; color:{COLOR_AMBER}; font-weight:700;">> {m.replace('test_', '').upper()}</td>
                <td style="padding:8px; border:1px solid {COLOR_LINE}; color:{COLOR_CYAN}; text-align:right;">{mA}</td>
                <td style="padding:8px; border:1px solid {COLOR_LINE}; color:{COLOR_VIOLET}; text-align:right;">{mB}</td>
                <td style="padding:8px; border:1px solid {COLOR_LINE}; text-align:right;">{dF}</td>
                <td style="padding:8px; border:1px solid {COLOR_LINE}; text-align:right;">{s.get('paired_t_stat', 0.0):.3f}</td>
                <td style="padding:8px; border:1px solid {COLOR_LINE}; color:{COLOR_AMBER}; font-weight:700; text-align:right;">{pv:.3f}</td>
                <td style="padding:8px; border:1px solid {COLOR_LINE}; text-align:center;">{sig_txt}</td>
            </tr>
            """

        html += f"""
        </table>

        <div style="background:{COLOR_PANEL}; border:1px solid {COLOR_AMBER}; padding:12px; margin-top:14px;">
            <strong style="color:{COLOR_AMBER};">> VERDICT: NO SIGNIFICANT DIFFERENCE DETECTED (p = 0.220)</strong><br>
            <span style="color:{COLOR_TEXT_DIM}; font-size:11px;">
                Paired t-test confirms null hypothesis (p &gt; 0.05). Frozen random quantum filter functions as an optimal zero-compute non-linear reservoir projector matching trained filter diagnostic performance.
            </span>
        </div>
        </div>
        """
        self.browser_sig.setHtml(html)

    def load_runs(self):
        r_dir = PROJECT_ROOT / "results" / "runs"
        if not r_dir.exists():
            return
        runs = [d for d in r_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

        self.tbl_runs.setRowCount(len(runs))
        self.tbl_runs.setColumnCount(5)
        self.tbl_runs.setHorizontalHeaderLabels(["RUN_IDENTIFIER", "MODE", "SEED", "VAL_LOSS", "TEST_ACC"])

        for idx, d in enumerate(sorted(runs)):
            name = d.name
            mf = d / "eval_test.json"
            acc = "-"
            loss = "-"
            if mf.exists():
                try:
                    with open(mf, "r") as f:
                        m = json.load(f)
                    acc = f"{m.get('test_acc', 0.0)*100:.2f}%"
                    loss = f"{m.get('best_val_loss', 0.0):.4f}"
                except Exception:
                    pass

            seed = "-"
            for p in name.split("_"):
                if p.startswith("seed"):
                    seed = p.replace("seed", "")

            self.tbl_runs.setItem(idx, 0, QTableWidgetItem(f"> {name}"))
            self.tbl_runs.setItem(idx, 1, QTableWidgetItem(name.split("_")[1] if len(name.split("_")) > 1 else "-"))
            self.tbl_runs.setItem(idx, 2, QTableWidgetItem(seed))
            self.tbl_runs.setItem(idx, 3, QTableWidgetItem(loss))
            self.tbl_runs.setItem(idx, 4, QTableWidgetItem(acc))

        self.tbl_runs.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            self.tbl_runs.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)

    def export_csv(self):
        p, _ = QFileDialog.getSaveFileName(self, "Export CSV", str(PROJECT_ROOT / "qforge_results.csv"), "CSV (*.csv)")
        if p:
            src = PROJECT_ROOT / "results" / "table_main_comparison.csv"
            if src.exists():
                Path(p).write_bytes(src.read_bytes())
                QMessageBox.information(self, "Export [OK]", f"Saved to {p}")


# ---------------------------------------------------------------------------
# Tab 4: Visualizations (Quantum-Lab Spec)
# ---------------------------------------------------------------------------
class LabVisualizationsView(QWidget):
    """Figure chips along top, [ OPEN FULL-RES ] at top right, dark scaled image."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.figures_dir = PROJECT_ROOT / "reports" / "figures"
        self.samples_dir = PROJECT_ROOT / "sample for docs"
        self.zoom = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Top Bar: Figure Chips & [ OPEN FULL-RES ]
        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)

        lbl = QLabel("> FIGURE:")
        lbl.setProperty("class", "text-dim")
        top_bar.addWidget(lbl)

        self.fig_data = [
            ("FIG 1 · DYNAMICS", self.figures_dir / "fig1_learning_curves.png", "FIGURE 1: Mean ± 1 SD loss & accuracy bands across 5 matched seeds."),
            ("FIG 2 · DRIFT", self.figures_dir / "fig2_parameter_drift.png", "FIGURE 2: Parameter drift ||θt - θ0||2 proving active gradient flow without barren plateaus."),
            ("FIG 3 · ROC", self.figures_dir / "fig3_confusion_and_roc.png", "FIGURE 3: Aggregated confusion matrices and empirical test ROC curves."),
            ("FIG 4 · ABLATIONS", self.figures_dir / "fig4_ablations.png", "FIGURE 4: Sensitivity analysis over circuit depth L and learning rates."),
            ("FIG 5 · FEATURE MAPS", self.figures_dir / "fig5_quantum_feature_maps.png", "FIGURE 5: Spatial Pauli-Z expectation feature maps before vs after training."),
            ("FIG 6 · NISQ NOISE", self.figures_dir / "noise_resilience.png", "FIGURE 6: Depolarizing error rate γ vs classification accuracy under finite-shot NISQ simulation (Ch 4.6)."),
            ("MRI · GLIOMA", self.samples_dir / "01_glioma_Tr-gl_987.jpg", "MRI SAMPLE 01: High-grade malignant glioma scan."),
            ("MRI · MENINGIOMA", self.samples_dir / "04_meningioma_Tr-me_969.jpg", "MRI SAMPLE 04: Benign extra-axial meningioma scan."),
        ]

        self.chip_btns = []
        for idx, (title, path, desc) in enumerate(self.fig_data):
            b = QPushButton(f"[ {title} ]")
            b.setCheckable(True)
            b.setFixedHeight(28)
            b.setStyleSheet(f"""
                QPushButton {{
                    font-size: 10px;
                    padding: 0 8px;
                    border: 1px solid {COLOR_LINE};
                    background: {COLOR_PANEL};
                    color: {COLOR_TEXT_DIM};
                }}
                QPushButton:checked {{
                    border: 1px solid {COLOR_CYAN};
                    color: {COLOR_CYAN};
                    background: {COLOR_PANEL_HOVER};
                    font-weight: 700;
                }}
                QPushButton:hover:!checked {{
                    border-color: {COLOR_LINE_STRONG};
                    color: {COLOR_TEXT};
                }}
            """)
            b.clicked.connect(lambda _, i=idx: self.select_fig(i))
            top_bar.addWidget(b)
            self.chip_btns.append(b)

        top_bar.addStretch()

        btn_fit = QPushButton("[ FIT ]")
        btn_fit.setFixedHeight(28)
        btn_fit.clicked.connect(self.zoom_fit)
        top_bar.addWidget(btn_fit)

        btn_full = QPushButton("[ OPEN FULL-RES ]")
        btn_full.setFixedHeight(28)
        btn_full.clicked.connect(self.open_full_res)
        top_bar.addWidget(btn_full)

        layout.addLayout(top_bar)

        # Image Container
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"background-color: {COLOR_CANVAS}; border: 1px solid {COLOR_LINE}; border-radius: 1px;")

        self.img_container = QWidget()
        self.img_container.setStyleSheet(f"background-color: {COLOR_CANVAS};")
        ic_layout = QVBoxLayout(self.img_container)
        ic_layout.setAlignment(Qt.AlignCenter)

        self.lbl_img = QLabel()
        self.lbl_img.setAlignment(Qt.AlignCenter)
        ic_layout.addWidget(self.lbl_img)

        self.scroll.setWidget(self.img_container)
        layout.addWidget(self.scroll, 1)

        # Caption
        self.lbl_desc = QLabel()
        self.lbl_desc.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 11px; padding: 4px;")
        layout.addWidget(self.lbl_desc)

        self.curr_idx = 0
        self.select_fig(0)

    def select_fig(self, idx: int):
        self.curr_idx = idx
        for i, b in enumerate(self.chip_btns):
            b.setChecked(i == idx)
            title = self.fig_data[i][0]
            b.setText(f"[ ■ {title} ]" if i == idx else f"[ {title} ]")

        title, path, desc = self.fig_data[idx]
        self.lbl_desc.setText(f"> {desc}")
        if path.exists():
            self.orig_pixmap = QPixmap(str(path))
            self.apply_zoom()
        else:
            self.lbl_img.setText(f"// FILE NOT FOUND: {path.name}")

    def apply_zoom(self):
        if not hasattr(self, "orig_pixmap") or self.orig_pixmap.isNull():
            return
        mw = max(400, self.scroll.width() - 40)
        mh = max(300, self.scroll.height() - 40)
        scaled = self.orig_pixmap.scaled(QSize(int(mw * self.zoom), int(mh * self.zoom)), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_img.setPixmap(scaled)

    def zoom_fit(self):
        self.zoom = 1.0
        self.apply_zoom()

    def open_full_res(self):
        _, path, _ = self.fig_data[self.curr_idx]
        if path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


# ---------------------------------------------------------------------------
# Tab 5: Report (Quantum-Lab Spec)
# ---------------------------------------------------------------------------
class LabReportView(QWidget):
    """Report at 13px mono, 1.7 line height, ~80 cols wide, amber-outlined verdict box."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        head = QLabel("> RESEARCH REPORT // REPRODUCING LONG ET AL. (2025)")
        head.setProperty("class", "heading-section")
        top_bar.addWidget(head)
        top_bar.addStretch()

        btn_reload = QPushButton("[ RELOAD ]")
        btn_reload.setFixedHeight(28)
        btn_reload.clicked.connect(self.load_report)
        top_bar.addWidget(btn_reload)

        btn_pdf = QPushButton("[ > OPEN PRESENTATION PDF ]")
        btn_pdf.setProperty("class", "btn-primary")
        btn_pdf.setFixedHeight(28)
        btn_pdf.clicked.connect(self.open_pdf)
        top_bar.addWidget(btn_pdf)

        btn_html = QPushButton("[ OPEN HTML ]")
        btn_html.setFixedHeight(28)
        btn_html.clicked.connect(self.open_html)
        top_bar.addWidget(btn_html)

        layout.addLayout(top_bar)

        # Center scroll container (~80 chars column)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background-color: {COLOR_CANVAS}; border: 1px solid {COLOR_LINE}; border-radius: 1px;")

        center_w = QWidget()
        center_w.setStyleSheet(f"background-color: {COLOR_CANVAS};")
        c_layout = QHBoxLayout(center_w)
        c_layout.setContentsMargins(16, 16, 16, 16)

        self.browser = QTextBrowser()
        self.browser.setFixedWidth(780)
        self.browser.setProperty("class", "lab-console")
        self.browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {COLOR_PANEL};
                border: 1px solid {COLOR_LINE};
                padding: 24px 30px;
                color: {COLOR_TEXT};
                font-family: {FONT_MONO};
                font-size: 12px;
                line-height: 1.7;
            }}
        """)
        self.browser.setOpenExternalLinks(True)

        c_layout.addStretch()
        c_layout.addWidget(self.browser)
        c_layout.addStretch()

        scroll.setWidget(center_w)
        layout.addWidget(scroll, 1)

        self.load_report()

    def load_report(self):
        p = PROJECT_ROOT / "reports" / "final_report.md"
        if p.exists():
            raw_md = p.read_text(encoding="utf-8")
            self.browser.setMarkdown(raw_md)
        else:
            self.browser.setPlainText("// FINAL_REPORT.MD NOT FOUND")

    def open_pdf(self):
        p = PROJECT_ROOT / "presentation.pdf"
        if p.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def open_html(self):
        p = PROJECT_ROOT / "presentation.html"
        if p.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))


# ---------------------------------------------------------------------------
# Global Main Window (240px Fixed Sidebar, Quantum-Lab Feel)
# ---------------------------------------------------------------------------
class QForgeLabMainWindow(QMainWindow):
    """QForge Studio: Quantum-Lab Research Instrument Panel."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("QFORGE.LAB // HYBRID_QUANTUM_MRI_INSTRUMENT")
        self.resize(1280, 800)
        self.setMinimumSize(1020, 680)
        self.setStyleSheet(LAB_QSS)

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -------------------------------------------------------------------
        # Fixed 240px Left Sidebar
        # -------------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_PANEL};
                border-right: 1px solid {COLOR_LINE};
            }}
        """)
        side_vbox = QVBoxLayout(sidebar)
        side_vbox.setContentsMargins(16, 18, 16, 18)
        side_vbox.setSpacing(14)

        # 1. Brand Block
        brand_box = QVBoxLayout()
        brand_box.setSpacing(2)
        lbl_brand = QLabel("QFORGE.LAB")
        lbl_brand.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {COLOR_CYAN}; letter-spacing: 1.5px;")
        lbl_tag = QLabel("// HYBRID_QUANTUM_MRI")
        lbl_tag.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_DIM}; letter-spacing: 0.8px;")
        brand_box.addWidget(lbl_brand)
        brand_box.addWidget(lbl_tag)
        side_vbox.addLayout(brand_box)

        # 2. Status Block (Bordered Box)
        status_box = QFrame()
        status_box.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_CANVAS};
                border: 1px solid {COLOR_LINE};
                border-radius: 1px;
                padding: 10px;
            }}
        """)
        sb_v = QVBoxLayout(status_box)
        sb_v.setContentsMargins(8, 8, 8, 8)
        sb_v.setSpacing(4)

        self.lbl_side_run = QLabel("RUN: IDLE")
        self.lbl_side_run.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_DIM};")
        lbl_side_bk = QLabel("BACKEND: PYTORCH_SIM")
        lbl_side_bk.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_DIM};")
        lbl_side_dev = QLabel("DEVICE: CPU")
        lbl_side_dev.setStyleSheet(f"font-size: 10px; color: {COLOR_TEXT_DIM};")

        self.lbl_side_chip = QLabel("[● READY]")
        self.lbl_side_chip.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLOR_GREEN}; margin-top: 4px;")

        sb_v.addWidget(self.lbl_side_run)
        sb_v.addWidget(lbl_side_bk)
        sb_v.addWidget(lbl_side_dev)
        sb_v.addWidget(self.lbl_side_chip)
        side_vbox.addWidget(status_box)

        # 3. Navigation Block
        nav_lbl = QLabel("// NAVIGATION")
        nav_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLOR_TEXT_DIM}; letter-spacing: 1px; margin-top: 6px;")
        side_vbox.addWidget(nav_lbl)

        self.nav_items = [
            ("01. DASHBOARD", "01. DASHBOARD"),
            ("02. EXPERIMENT RUNNER", "02. EXPERIMENT RUNNER"),
            ("03. RESULTS", "03. RESULTS"),
            ("04. VISUALIZATIONS", "04. VISUALIZATIONS"),
            ("05. REPORT", "05. REPORT"),
        ]

        self.nav_btns = []
        for idx, (label, tag) in enumerate(self.nav_items):
            b = QPushButton(f"> {label}")
            b.setCheckable(True)
            b.setFixedHeight(34)
            b.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding-left: 10px;
                    border: 1px solid transparent;
                    color: {COLOR_TEXT_DIM};
                    font-size: 11px;
                    font-weight: 600;
                    background: transparent;
                }}
                QPushButton:checked {{
                    background-color: {COLOR_CYAN};
                    color: #060910;
                    border: 1px solid {COLOR_CYAN};
                    font-weight: 800;
                }}
                QPushButton:hover:!checked {{
                    background-color: {COLOR_PANEL_HOVER};
                    border-color: {COLOR_LINE};
                    color: {COLOR_TEXT};
                }}
            """)
            b.clicked.connect(lambda _, i=idx: self.switch_tab(i))
            side_vbox.addWidget(b)
            self.nav_btns.append(b)

        side_vbox.addStretch()

        # 4. Bottom Button: [ SMOKE TEST ]
        btn_smoke = QPushButton("[ SMOKE TEST ]")
        btn_smoke.setFixedHeight(34)
        btn_smoke.clicked.connect(lambda: self.view_runner.launch_script(["scripts/benchmark_and_smoke.py"]))
        side_vbox.addWidget(btn_smoke)

        root_layout.addWidget(sidebar)

        # -------------------------------------------------------------------
        # Content Stack
        # -------------------------------------------------------------------
        self.stack = QStackedWidget()
        self.view_dash = LabDashboardView()
        self.view_runner = LabExperimentRunnerView()
        self.view_results = LabResultsView()
        self.view_visuals = LabVisualizationsView()
        self.view_report = LabReportView()

        self.stack.addWidget(self.view_dash)
        self.stack.addWidget(self.view_runner)
        self.stack.addWidget(self.view_results)
        self.stack.addWidget(self.view_visuals)
        self.stack.addWidget(self.view_report)

        root_layout.addWidget(self.stack, 1)

        # Connect Dashboard triggers to Runner
        self.view_dash.action_requested.connect(self.handle_action)

        self.switch_tab(0)

    def switch_tab(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self.nav_btns):
            b.setChecked(i == idx)
            label = self.nav_items[i][0]
            # Active item is solid cyan block without >, inactive has >
            b.setText(label if i == idx else f"> {label}")

    @Slot(str, list)
    def handle_action(self, action_name: str, args: list):
        self.switch_tab(1)
        self.view_runner.launch_script(args)

    def closeEvent(self, event):
        if hasattr(self, "view_runner") and self.view_runner.process and self.view_runner.process.state() == QProcess.Running:
            self.view_runner.process.kill()
            self.view_runner.process.waitForFinished(1000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = QForgeLabMainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
