"""
Real-time Clipping Indicator Widget.

Displays peak and true-peak levels with visual warning
when audio exceeds 0 dBFS. Shows clip count and
auto-resets after timeout.
"""

from __future__ import annotations

import time

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget


class ClipIndicator(QWidget):
    """Real-time clipping/true-peak warning display."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(28)

        self._peak_db = -96.0
        self._true_peak_db = -96.0
        self._clip_count = 0
        self._last_clip_time = 0.0
        self._clip_active = False
        self._clip_threshold_db = 0.0
        self._warning_threshold_db = -1.0
        self._reset_timeout = 3.0

        self._setup_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_reset)
        self._timer.start(500)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        self._peak_label = QLabel("Peak: ---")
        self._peak_label.setStyleSheet("color: #8B949E; font-size: 11px;")
        layout.addWidget(self._peak_label)

        self._tp_label = QLabel("TP: ---")
        self._tp_label.setStyleSheet("color: #8B949E; font-size: 11px;")
        layout.addWidget(self._tp_label)

        self._clip_led = QLabel("CLIP")
        self._clip_led.setFixedWidth(40)
        self._clip_led.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._clip_led.setStyleSheet(
            "background-color: #21262D; color: #484F58; "
            "font-size: 10px; font-weight: bold; border-radius: 3px;"
        )
        layout.addWidget(self._clip_led)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: #FD7978; font-size: 10px;")
        layout.addWidget(self._count_label)

        layout.addStretch()

    def update_levels(self, audio: np.ndarray) -> None:
        """Analyze audio chunk for peak and clipping."""
        if audio.size == 0:
            return

        peak = float(np.max(np.abs(audio)))
        peak_db = 20.0 * np.log10(max(peak, 1e-10))
        self._peak_db = peak_db

        # True peak approximation (4x oversampled peak)
        tp = self._compute_true_peak(audio)
        self._true_peak_db = tp

        # Update display
        self._update_display(peak_db, tp)

        # Check clipping
        if peak_db >= self._clip_threshold_db or tp >= self._clip_threshold_db:
            self._clip_count += 1
            self._clip_active = True
            self._last_clip_time = time.time()
            self._clip_led.setStyleSheet(
                "background-color: #DA3633; color: white; "
                "font-size: 10px; font-weight: bold; border-radius: 3px;"
            )
            self._count_label.setText(f"x{self._clip_count}")
        elif peak_db >= self._warning_threshold_db:
            self._clip_led.setStyleSheet(
                "background-color: #D29922; color: white; "
                "font-size: 10px; font-weight: bold; border-radius: 3px;"
            )

    def _update_display(self, peak_db: float, tp_db: float) -> None:
        color = "#E6EDF3"
        if peak_db >= -1.0:
            color = "#FD7978"
        elif peak_db >= -3.0:
            color = "#D29922"
        elif peak_db >= -6.0:
            color = "#FECA57"

        self._peak_label.setText(f"Peak: {peak_db:.1f} dB")
        self._peak_label.setStyleSheet(f"color: {color}; font-size: 11px;")

        tp_color = "#FD7978" if tp_db >= -0.5 else "#8B949E"
        self._tp_label.setText(f"TP: {tp_db:.1f} dB")
        self._tp_label.setStyleSheet(f"color: {tp_color}; font-size: 11px;")

    @staticmethod
    def _compute_true_peak(audio: np.ndarray) -> float:
        """Approximate true peak via 4x oversampling."""
        if audio.shape[0] < 4:
            peak = float(np.max(np.abs(audio)))
            return 20.0 * np.log10(max(peak, 1e-10))

        # Simple 4x linear interpolation for true peak estimation
        n = audio.shape[0]
        if audio.ndim == 2:
            mono = audio.mean(axis=1)
        else:
            mono = audio

        # Upsample 4x via linear interpolation
        x_orig = np.arange(n)
        x_up = np.linspace(0, n - 1, n * 4)
        upsampled = np.interp(x_up, x_orig, mono)

        tp = float(np.max(np.abs(upsampled)))
        return 20.0 * np.log10(max(tp, 1e-10))

    def _check_reset(self) -> None:
        """Auto-reset clip indicator after timeout."""
        if self._clip_active and (time.time() - self._last_clip_time > self._reset_timeout):
            self._clip_active = False
            self._clip_led.setStyleSheet(
                "background-color: #21262D; color: #484F58; "
                "font-size: 10px; font-weight: bold; border-radius: 3px;"
            )

    def reset(self) -> None:
        """Manually reset clip counter and indicator."""
        self._clip_count = 0
        self._clip_active = False
        self._count_label.setText("")
        self._clip_led.setStyleSheet(
            "background-color: #21262D; color: #484F58; "
            "font-size: 10px; font-weight: bold; border-radius: 3px;"
        )
