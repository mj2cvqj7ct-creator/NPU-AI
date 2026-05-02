"""
Real-time Audio Statistics Dashboard Widget.

Displays RMS level, peak level, LUFS estimate, dynamic range,
spectral centroid, band energy distribution, and genre detection
with auto-preset recommendation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.audio.profiler import AudioProfile


class StatMeter(QWidget):
    """Compact horizontal meter with label and value."""

    def __init__(self, label: str, unit: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label_text = label
        self._unit = unit
        self._value = 0.0
        self._max_val = 1.0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)

        self._label = QLabel(label)
        self._label.setMinimumWidth(100)
        self._label.setMaximumWidth(120)

        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setMaximumHeight(14)

        self._value_label = QLabel("0.0")
        self._value_label.setMinimumWidth(70)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self._label)
        layout.addWidget(self._bar, 1)
        layout.addWidget(self._value_label)

    def set_value(self, value: float, max_val: float = 1.0) -> None:
        self._value = value
        self._max_val = max_val
        ratio = max(0.0, min(1.0, value / max_val)) if max_val > 0 else 0.0
        self._bar.setValue(int(ratio * 1000))
        self._value_label.setText(f"{value:.1f}{self._unit}")


class BandDistribution(QWidget):
    """Horizontal bar chart showing bass/mid/high energy distribution."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(30)
        self.setMaximumHeight(40)
        self._bass = 0.33
        self._mid = 0.34
        self._high = 0.33

    def set_distribution(self, bass: float, mid: float, high: float) -> None:
        total = bass + mid + high
        if total > 0:
            self._bass = bass / total
            self._mid = mid / total
            self._high = high / total
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width() - 4
        h = self.height() - 4

        # Bass (warm orange)
        bass_w = int(w * self._bass)
        painter.setBrush(QColor(225, 112, 85, 200))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawRoundedRect(2, 2, bass_w, h, 4, 4)

        # Mid (purple)
        mid_w = int(w * self._mid)
        painter.setBrush(QColor(108, 92, 231, 200))
        painter.drawRoundedRect(2 + bass_w, 2, mid_w, h, 4, 4)

        # High (teal)
        high_w = w - bass_w - mid_w
        painter.setBrush(QColor(0, 206, 201, 200))
        painter.drawRoundedRect(2 + bass_w + mid_w, 2, high_w, h, 4, 4)

        # Labels
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1))
        font = painter.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)

        if bass_w > 30:
            txt = f"Bass {self._bass:.0%}"
            painter.drawText(4, 2, bass_w, h, Qt.AlignmentFlag.AlignCenter, txt)
        if mid_w > 30:
            txt = f"Mid {self._mid:.0%}"
            painter.drawText(2 + bass_w, 2, mid_w, h, Qt.AlignmentFlag.AlignCenter, txt)
        if high_w > 30:
            x = 2 + bass_w + mid_w
            txt = f"High {self._high:.0%}"
            painter.drawText(x, 2, high_w, h, Qt.AlignmentFlag.AlignCenter, txt)

        painter.end()


class AudioStatsPanel(QWidget):
    """Real-time audio statistics dashboard."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Level meters group
        level_group = QGroupBox("LEVELS")
        level_layout = QVBoxLayout(level_group)
        level_layout.setSpacing(4)

        self._rms_meter = StatMeter("RMS Level", " dB")
        self._peak_meter = StatMeter("Peak Level", " dB")
        self._lufs_meter = StatMeter("LUFS Est.", " LUFS")
        self._dr_meter = StatMeter("Dynamic Range", " dB")
        self._crest_meter = StatMeter("Crest Factor", "")

        level_layout.addWidget(self._rms_meter)
        level_layout.addWidget(self._peak_meter)
        level_layout.addWidget(self._lufs_meter)
        level_layout.addWidget(self._dr_meter)
        level_layout.addWidget(self._crest_meter)

        layout.addWidget(level_group)

        # Spectral group
        spectral_group = QGroupBox("SPECTRAL ANALYSIS")
        spectral_layout = QVBoxLayout(spectral_group)
        spectral_layout.setSpacing(4)

        self._centroid_meter = StatMeter("Centroid", " Hz")
        self._rolloff_meter = StatMeter("Rolloff (85%)", " Hz")
        self._zcr_meter = StatMeter("Zero Crossing", "")

        spectral_layout.addWidget(self._centroid_meter)
        spectral_layout.addWidget(self._rolloff_meter)
        spectral_layout.addWidget(self._zcr_meter)

        # Band distribution
        band_label = QLabel("Band Energy Distribution")
        band_label.setObjectName("statusLabel")
        spectral_layout.addWidget(band_label)

        self._band_dist = BandDistribution()
        spectral_layout.addWidget(self._band_dist)

        layout.addWidget(spectral_group)

        # Genre detection group
        genre_group = QGroupBox("AUTO PROFILE")
        genre_layout = QVBoxLayout(genre_group)
        genre_layout.setSpacing(6)

        genre_row = QHBoxLayout()
        genre_row.addWidget(QLabel("Detected Genre:"))
        self._genre_label = QLabel("—")
        self._genre_label.setObjectName("valueLabel")
        genre_row.addWidget(self._genre_label)
        genre_layout.addLayout(genre_row)

        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("Confidence:"))
        self._conf_label = QLabel("—")
        self._conf_label.setObjectName("valueLabel")
        conf_row.addWidget(self._conf_label)
        genre_layout.addLayout(conf_row)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Recommended:"))
        self._preset_label = QLabel("—")
        self._preset_label.setObjectName("valueLabel")
        preset_row.addWidget(self._preset_label)
        genre_layout.addLayout(preset_row)

        layout.addWidget(genre_group)
        layout.addStretch()

    def update_profile(self, profile: AudioProfile) -> None:
        """Update all stats from an AudioProfile."""
        import numpy as np

        rms_db = 20 * np.log10(max(profile.rms_level, 1e-10))
        peak_db = 20 * np.log10(max(profile.peak_level, 1e-10))
        lufs_est = rms_db - 0.691  # approximate K-weighted

        self._rms_meter.set_value(rms_db + 60, 60)
        self._peak_meter.set_value(peak_db + 60, 60)
        self._lufs_meter.set_value(lufs_est + 60, 60)
        self._dr_meter.set_value(profile.dynamic_range_db, 30)
        self._crest_meter.set_value(profile.crest_factor, 15)

        self._centroid_meter.set_value(profile.spectral_centroid, 10000)
        self._rolloff_meter.set_value(profile.spectral_rolloff, 20000)
        self._zcr_meter.set_value(profile.zero_crossing_rate, 0.5)

        self._band_dist.set_distribution(
            profile.bass_energy_ratio,
            profile.mid_energy_ratio,
            profile.high_energy_ratio,
        )

        self._genre_label.setText(profile.detected_genre)
        self._conf_label.setText(f"{profile.confidence:.0%}")
        self._preset_label.setText(profile.recommended_preset)
