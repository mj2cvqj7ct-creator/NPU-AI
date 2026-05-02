"""
Audio Player Control Bar Widget.

Provides transport controls (play/pause/stop), seek slider,
time display, loop toggle, and file info for the audio player.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.audio.player import PlaybackState


class PlayerControlBar(QWidget):
    """Transport control bar for audio player."""

    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    seek_requested = pyqtSignal(float)  # 0.0-1.0
    loop_toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_playing = False
        self._is_looping = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # File info
        self._file_label = QLabel("No file loaded")
        self._file_label.setStyleSheet("color: #8B949E; font-size: 11px;")
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._file_label)

        # Seek slider
        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setValue(0)
        self._seek_slider.setEnabled(False)
        self._seek_slider.sliderReleased.connect(self._on_seek)
        layout.addWidget(self._seek_slider)

        # Time display + controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setStyleSheet("color: #E6EDF3; font-size: 12px;")
        self._time_label.setFixedWidth(100)
        controls_row.addWidget(self._time_label)

        controls_row.addStretch()

        # Transport buttons
        self._stop_btn = QPushButton("⏹")
        self._stop_btn.setFixedSize(36, 28)
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        controls_row.addWidget(self._stop_btn)

        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedSize(40, 28)
        self._play_btn.setStyleSheet(
            "QPushButton { background-color: #238636; font-size: 16px; }"
        )
        self._play_btn.clicked.connect(self._on_play_pause)
        controls_row.addWidget(self._play_btn)

        self._loop_btn = QPushButton("🔁")
        self._loop_btn.setFixedSize(36, 28)
        self._loop_btn.setCheckable(True)
        self._loop_btn.clicked.connect(self._on_loop_toggle)
        controls_row.addWidget(self._loop_btn)

        controls_row.addStretch()

        # Spacer for symmetry
        spacer = QLabel()
        spacer.setFixedWidth(100)
        controls_row.addWidget(spacer)

        layout.addLayout(controls_row)

    def _on_play_pause(self) -> None:
        if self._is_playing:
            self.pause_clicked.emit()
        else:
            self.play_clicked.emit()

    def _on_seek(self) -> None:
        val = self._seek_slider.value() / 1000.0
        self.seek_requested.emit(val)

    def _on_loop_toggle(self) -> None:
        self._is_looping = self._loop_btn.isChecked()
        self.loop_toggled.emit(self._is_looping)

    def update_state(self, state: PlaybackState) -> None:
        """Update UI from playback state."""
        self._is_playing = state.is_playing and not state.is_paused
        self._play_btn.setText("⏸" if self._is_playing else "▶")

        # Update seek slider
        if not self._seek_slider.isSliderDown():
            self._seek_slider.setValue(int(state.progress * 1000))
        self._seek_slider.setEnabled(state.total_samples > 0)

        # Time display
        pos = state.position_sec
        dur = state.duration_sec
        self._time_label.setText(
            f"{self._fmt_time(pos)} / {self._fmt_time(dur)}"
        )

        # File label
        if state.filename:
            self._file_label.setText(state.filename)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"

    def reset(self) -> None:
        """Reset to default state."""
        self._is_playing = False
        self._play_btn.setText("▶")
        self._seek_slider.setValue(0)
        self._seek_slider.setEnabled(False)
        self._time_label.setText("0:00 / 0:00")
        self._file_label.setText("No file loaded")
