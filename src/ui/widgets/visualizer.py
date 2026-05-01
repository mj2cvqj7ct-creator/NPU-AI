"""
Real-time Audio Visualizer Widget.

Displays spectrum analyzer, waveform, and stem level meters
with smooth animations and gradient rendering.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np
from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget


class SpectrumVisualizer(QWidget):
    """Real-time spectrum analyzer with gradient bars."""

    BAR_COUNT = 64
    SMOOTHING = 0.3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self._spectrum = np.zeros(self.BAR_COUNT, dtype=np.float32)
        self._peak_hold = np.zeros(self.BAR_COUNT, dtype=np.float32)
        self._peak_decay = 0.995

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._decay_peaks)
        self._timer.start(16)

    def update_spectrum(self, spectrum_data: list[float] | np.ndarray) -> None:
        """Update spectrum data from FFT analysis."""
        if len(spectrum_data) == 0:
            return

        data = np.array(spectrum_data, dtype=np.float32)

        if len(data) != self.BAR_COUNT:
            indices = np.linspace(0, len(data) - 1, self.BAR_COUNT).astype(int)
            data = data[indices]

        data = np.clip((data + 60) / 60, 0, 1)

        self._spectrum = self._spectrum * self.SMOOTHING + data * (1 - self.SMOOTHING)

        self._peak_hold = np.maximum(self._peak_hold, self._spectrum)
        self.update()

    def _decay_peaks(self) -> None:
        self._peak_hold *= self._peak_decay
        self._spectrum *= 0.97
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_width = max(2, (w - self.BAR_COUNT * 2) / self.BAR_COUNT)
        gap = 2

        for i in range(self.BAR_COUNT):
            x = i * (bar_width + gap)
            bar_height = self._spectrum[i] * h * 0.9

            gradient = QLinearGradient(x, h, x, h - bar_height)
            gradient.setColorAt(0.0, QColor(108, 92, 231))
            gradient.setColorAt(0.5, QColor(0, 206, 201))
            gradient.setColorAt(1.0, QColor(0, 184, 148))

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)

            rect = QRectF(x, h - bar_height, bar_width, bar_height)
            painter.drawRoundedRect(rect, 2, 2)

            peak_y = h - self._peak_hold[i] * h * 0.9
            painter.setPen(QPen(QColor(253, 203, 110), 2))
            painter.drawLine(int(x), int(peak_y), int(x + bar_width), int(peak_y))

        painter.end()


class WaveformVisualizer(QWidget):
    """Real-time waveform display with gradient fill."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self._waveform: deque[float] = deque(maxlen=512)
        self._waveform.extend([0.0] * 512)

    def update_waveform(self, waveform_data: list[float] | np.ndarray) -> None:
        """Update waveform display data."""
        self._waveform.extend(waveform_data)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        mid_y = h / 2
        data = list(self._waveform)

        if not data:
            painter.end()
            return

        path_top = QPainterPath()
        path_bottom = QPainterPath()
        path_top.moveTo(0, mid_y)
        path_bottom.moveTo(0, mid_y)

        step = max(1, len(data) / w)
        for i in range(int(w)):
            idx = min(int(i * step), len(data) - 1)
            val = data[idx]
            y_top = mid_y - val * mid_y * 0.8
            y_bottom = mid_y + val * mid_y * 0.8
            path_top.lineTo(i, y_top)
            path_bottom.lineTo(i, y_bottom)

        path_top.lineTo(w, mid_y)
        path_bottom.lineTo(w, mid_y)

        gradient_top = QLinearGradient(0, 0, 0, mid_y)
        gradient_top.setColorAt(0, QColor(108, 92, 231, 100))
        gradient_top.setColorAt(1, QColor(108, 92, 231, 20))

        gradient_bottom = QLinearGradient(0, mid_y, 0, h)
        gradient_bottom.setColorAt(0, QColor(0, 206, 201, 20))
        gradient_bottom.setColorAt(1, QColor(0, 206, 201, 100))

        painter.setBrush(QBrush(gradient_top))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path_top)

        painter.setBrush(QBrush(gradient_bottom))
        painter.drawPath(path_bottom)

        pen = QPen(QColor(108, 92, 231, 200), 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path_top)

        painter.end()


class StemMeter(QWidget):
    """Individual stem level meter with label."""

    def __init__(self, name: str, color: QColor, parent=None):
        super().__init__(parent)
        self.name = name
        self.color = color
        self.level = 0.0
        self.peak = 0.0
        self.setMinimumHeight(24)
        self.setMinimumWidth(200)

    def set_level(self, level: float) -> None:
        self.level = self.level * 0.7 + level * 0.3
        self.peak = max(self.peak * 0.99, self.level)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        painter.setPen(QPen(QColor(139, 148, 158), 1))
        painter.setFont(painter.font())
        label_width = 70
        painter.drawText(0, 0, label_width, h, Qt.AlignmentFlag.AlignVCenter, self.name)

        bar_x = label_width + 4
        bar_width = w - bar_x - 40
        bar_height = max(4, h - 8)

        painter.setBrush(QBrush(QColor(33, 38, 45)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bar_x, (h - bar_height) / 2, bar_width, bar_height), 3, 3)

        level_width = bar_width * min(1.0, self.level)
        if level_width > 0:
            gradient = QLinearGradient(bar_x, 0, bar_x + level_width, 0)
            gradient.setColorAt(0, self.color)
            fade = QColor(self.color.red(), self.color.green(), self.color.blue(), 180)
            gradient.setColorAt(1, fade)
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(
                QRectF(bar_x, (h - bar_height) / 2, level_width, bar_height), 3, 3
            )

        db = 20 * math.log10(self.level + 1e-10)
        db_str = f"{db:.0f} dB"
        painter.setPen(QPen(QColor(0, 206, 201), 1))
        painter.drawText(
            int(bar_x + bar_width + 4), 0, 40, h, Qt.AlignmentFlag.AlignVCenter, db_str
        )

        painter.end()


class StemLevelMeters(QWidget):
    """Collection of stem level meters for source separation visualization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        self.meters = {
            "vocals": StemMeter("Vocals", QColor(108, 92, 231)),
            "drums": StemMeter("Drums", QColor(225, 112, 85)),
            "bass": StemMeter("Bass", QColor(0, 206, 201)),
            "other": StemMeter("Other", QColor(0, 184, 148)),
        }

        for meter in self.meters.values():
            layout.addWidget(meter)

    def update_levels(self, levels: dict[str, float]) -> None:
        for name, level in levels.items():
            if name in self.meters:
                self.meters[name].set_level(level)
