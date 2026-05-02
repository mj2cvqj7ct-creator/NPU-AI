"""
Parametric EQ Curve Visualizer Widget.

Displays the 8-band parametric EQ frequency response as an
interactive curve overlay on a logarithmic frequency grid.
"""

from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QWidget

# EQ band definitions: (name, center_freq_hz, color)
EQ_BANDS = [
    ("Sub Bass", 35, QColor(253, 121, 168)),
    ("Bass", 100, QColor(255, 159, 67)),
    ("Upper Bass", 225, QColor(254, 202, 87)),
    ("Low Mid", 550, QColor(85, 239, 196)),
    ("Mid", 1650, QColor(0, 206, 201)),
    ("Presence", 3750, QColor(108, 92, 231)),
    ("Brilliance", 7500, QColor(162, 155, 254)),
    ("Air", 15000, QColor(253, 203, 110)),
]


class EQVisualizer(QWidget):
    """Interactive parametric EQ frequency response display."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._gains: list[float] = [0.0] * 8
        self._freq_range = (20.0, 20000.0)
        self._db_range = (-12.0, 12.0)

    def set_gains(self, gains: list[float]) -> None:
        """Set EQ band gains in dB (length must match band count)."""
        if len(gains) == len(self._gains):
            self._gains = list(gains)
            self.update()

    def set_gains_from_enhancer(
        self,
        warmth: float,
        clarity: float,
        presence: float,
        air: float,
        bass_boost: float,
    ) -> None:
        """Convert enhancer parameters to approximate dB gains."""
        self._gains = [
            bass_boost * 6.0,        # Sub Bass
            warmth * 4.2,            # Bass
            warmth * 2.4,            # Upper Bass
            -0.5,                    # Low Mid (slight cut)
            clarity * 2.4,           # Mid
            presence * 3.0,          # Presence
            air * 2.4,               # Brilliance
            air * 3.6,               # Air
        ]
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin_l, margin_r, margin_t, margin_b = 45, 15, 10, 25
        plot_w = w - margin_l - margin_r
        plot_h = h - margin_t - margin_b

        # Background
        painter.fillRect(self.rect(), QColor(10, 14, 20))

        # Grid
        self._draw_grid(painter, margin_l, margin_t, plot_w, plot_h)

        # EQ curve
        self._draw_curve(painter, margin_l, margin_t, plot_w, plot_h)

        # Band markers
        self._draw_band_markers(painter, margin_l, margin_t, plot_w, plot_h)

        painter.end()

    def _freq_to_x(self, freq: float, margin_l: int, plot_w: int) -> float:
        f_min, f_max = self._freq_range
        log_ratio = math.log10(freq / f_min) / math.log10(f_max / f_min)
        return margin_l + log_ratio * plot_w

    def _db_to_y(self, db: float, margin_t: int, plot_h: int) -> float:
        db_min, db_max = self._db_range
        ratio = 1.0 - (db - db_min) / (db_max - db_min)
        return margin_t + ratio * plot_h

    def _draw_grid(
        self, painter: QPainter, ml: int, mt: int, pw: int, ph: int
    ) -> None:
        grid_pen = QPen(QColor(42, 48, 64), 1)
        text_pen = QPen(QColor(139, 148, 158), 1)

        # Frequency grid lines
        freq_marks = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
        for f in freq_marks:
            x = self._freq_to_x(f, ml, pw)
            painter.setPen(grid_pen)
            painter.drawLine(int(x), mt, int(x), mt + ph)
            painter.setPen(text_pen)
            label = f"{f // 1000}k" if f >= 1000 else str(f)
            painter.drawText(int(x) - 12, mt + ph + 14, label)

        # dB grid lines
        for db in range(-12, 13, 3):
            y = self._db_to_y(db, mt, ph)
            painter.setPen(grid_pen)
            painter.drawLine(ml, int(y), ml + pw, int(y))
            if db % 6 == 0:
                painter.setPen(text_pen)
                lbl = f"{db:+d}" if db != 0 else " 0"
                painter.drawText(4, int(y) + 4, lbl)

        # 0 dB line highlighted
        y0 = self._db_to_y(0, mt, ph)
        painter.setPen(QPen(QColor(72, 79, 88), 1, Qt.PenStyle.DashLine))
        painter.drawLine(ml, int(y0), ml + pw, int(y0))

    def _draw_curve(
        self, painter: QPainter, ml: int, mt: int, pw: int, ph: int
    ) -> None:
        # Generate smooth curve through band gains
        n_points = 200
        freqs = np.logspace(
            math.log10(self._freq_range[0]),
            math.log10(self._freq_range[1]),
            n_points,
        )
        response = np.zeros(n_points)

        for i, (_, center, _) in enumerate(EQ_BANDS):
            gain = self._gains[i]
            if abs(gain) < 0.01:
                continue
            bw = 1.2  # bandwidth in octaves
            for j, f in enumerate(freqs):
                octave_dist = abs(math.log2(f / center))
                bell = math.exp(-0.5 * (octave_dist / (bw / 2.0)) ** 2)
                response[j] += gain * bell

        # Build path
        path = QPainterPath()
        for j in range(n_points):
            x = self._freq_to_x(freqs[j], ml, pw)
            y = self._db_to_y(float(response[j]), mt, ph)
            if j == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        # Fill under curve
        fill_path = QPainterPath(path)
        y_zero = self._db_to_y(0, mt, ph)
        fill_path.lineTo(self._freq_to_x(freqs[-1], ml, pw), y_zero)
        fill_path.lineTo(self._freq_to_x(freqs[0], ml, pw), y_zero)
        fill_path.closeSubpath()

        gradient = QLinearGradient(0, mt, 0, mt + ph)
        gradient.setColorAt(0.0, QColor(108, 92, 231, 60))
        gradient.setColorAt(0.5, QColor(108, 92, 231, 20))
        gradient.setColorAt(1.0, QColor(108, 92, 231, 60))
        painter.fillPath(fill_path, gradient)

        # Curve line
        painter.setPen(QPen(QColor(162, 155, 254), 2))
        painter.drawPath(path)

    def _draw_band_markers(
        self, painter: QPainter, ml: int, mt: int, pw: int, ph: int
    ) -> None:
        for i, (name, center, color) in enumerate(EQ_BANDS):
            gain = self._gains[i]
            x = self._freq_to_x(center, ml, pw)
            y = self._db_to_y(gain, mt, ph)

            # Dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(int(x) - 5, int(y) - 5, 10, 10)

            # Label on hover position
            painter.setPen(QPen(color, 1))
            font = painter.font()
            font.setPointSize(7)
            painter.setFont(font)
            label_y = int(y) - 10 if gain >= 0 else int(y) + 16
            painter.drawText(int(x) - 15, label_y, name[:4])
