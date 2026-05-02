"""
Real-time Spectrogram Widget.

Displays a scrolling time-frequency heatmap (spectrogram)
using short-time FFT analysis with color-mapped intensity.
"""

from __future__ import annotations

from collections import deque

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QWidget

# Viridis-inspired color map (dark → blue → green → yellow)
_COLORMAP: list[tuple[int, int, int]] = []


def _build_colormap() -> list[tuple[int, int, int]]:
    """Build a 256-entry viridis-like color map."""
    if _COLORMAP:
        return _COLORMAP

    anchors = [
        (0.00, (10, 14, 20)),
        (0.15, (48, 18, 59)),
        (0.30, (67, 62, 133)),
        (0.45, (56, 111, 165)),
        (0.60, (30, 155, 138)),
        (0.75, (86, 198, 103)),
        (0.90, (194, 223, 35)),
        (1.00, (253, 231, 37)),
    ]
    for i in range(256):
        t = i / 255.0
        # Find anchor pair
        for k in range(len(anchors) - 1):
            t0, c0 = anchors[k]
            t1, c1 = anchors[k + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
                r = int(c0[0] + (c1[0] - c0[0]) * f)
                g = int(c0[1] + (c1[1] - c0[1]) * f)
                b = int(c0[2] + (c1[2] - c0[2]) * f)
                _COLORMAP.append((r, g, b))
                break
        else:
            _COLORMAP.append(anchors[-1][1])

    return _COLORMAP


class SpectrogramWidget(QWidget):
    """Scrolling spectrogram display with FFT analysis."""

    def __init__(
        self,
        fft_size: int = 512,
        history_length: int = 200,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(120)
        self._fft_size = fft_size
        self._n_bins = fft_size // 2
        self._history_length = history_length
        self._columns: deque[np.ndarray] = deque(maxlen=history_length)
        self._db_floor = -80.0
        self._db_ceil = 0.0
        self._sample_rate = 48000
        self._window = np.hanning(fft_size).astype(np.float32)

    def set_sample_rate(self, sr: int) -> None:
        self._sample_rate = sr

    def push_audio(self, audio: np.ndarray) -> None:
        """Analyze a chunk of audio and add to spectrogram history."""
        if audio.shape[0] == 0:
            return

        # Mix to mono if stereo
        if audio.ndim == 2:
            mono = audio.mean(axis=1)
        else:
            mono = audio

        # Process in fft_size windows
        n = len(mono)
        pos = 0
        hop = self._fft_size // 2
        while pos + self._fft_size <= n:
            frame = mono[pos : pos + self._fft_size] * self._window
            spectrum = np.abs(np.fft.rfft(frame))[: self._n_bins]
            # Convert to dB
            spectrum = np.maximum(spectrum, 1e-10)
            db = 20.0 * np.log10(spectrum)
            self._columns.append(db.astype(np.float32))
            pos += hop

        self.update()

    def paintEvent(self, event) -> None:
        if not self._columns:
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(10, 14, 20))
            painter.setPen(QColor(139, 148, 158))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, "Spectrogram"
            )
            painter.end()
            return

        cmap = _build_colormap()
        w = self.width()
        h = self.height()
        n_cols = len(self._columns)

        # Build image
        img = QImage(n_cols, self._n_bins, QImage.Format.Format_RGB32)
        db_range = self._db_ceil - self._db_floor

        for x, col in enumerate(self._columns):
            for y in range(self._n_bins):
                # Flip y: low freq at bottom
                freq_idx = self._n_bins - 1 - y
                if freq_idx < len(col):
                    val = (col[freq_idx] - self._db_floor) / db_range
                else:
                    val = 0.0
                val = max(0.0, min(1.0, val))
                idx = int(val * 255)
                r, g, b = cmap[idx]
                img.setPixelColor(x, y, QColor(r, g, b))

        painter = QPainter(self)
        # Scale image to widget size
        scaled = img.scaled(
            w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawImage(0, 0, scaled)

        # Frequency labels
        painter.setPen(QColor(255, 255, 255, 160))
        font = painter.font()
        font.setPointSize(7)
        painter.setFont(font)
        nyq = self._sample_rate / 2
        for freq in [100, 500, 1000, 5000, 10000]:
            if freq > nyq:
                continue
            y_ratio = 1.0 - (freq / nyq)
            y_pos = int(y_ratio * h)
            label = f"{freq // 1000}k" if freq >= 1000 else str(freq)
            painter.drawText(4, y_pos + 4, label)

        painter.end()

    def clear(self) -> None:
        """Clear spectrogram history."""
        self._columns.clear()
        self.update()
