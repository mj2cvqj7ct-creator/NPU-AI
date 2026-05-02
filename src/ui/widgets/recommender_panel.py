"""
Recommendation Panel Widget.

Displays real-time music recommendations and user preference profile
with interactive controls for the deep learning recommendation engine.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PreferenceBar(QWidget):
    """Individual preference bar for feature visualization."""

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(4)

        self._label = QLabel(name)
        self._label.setMinimumWidth(100)
        self._label.setMaximumWidth(100)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(50)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(10)

        self._value_label = QLabel("0.00")
        self._value_label.setObjectName("valueLabel")
        self._value_label.setMinimumWidth(50)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self._label)
        layout.addWidget(self._bar, 1)
        layout.addWidget(self._value_label)

    def set_value(self, value: float) -> None:
        normalized = int((value + 1.0) / 2.0 * 100)
        self._bar.setValue(max(0, min(100, normalized)))
        self._value_label.setText(f"{value:.2f}")


class RecommenderPanel(QGroupBox):
    """Panel displaying recommendations and user preference profile."""

    track_liked = pyqtSignal()
    track_skipped = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("AI Recommendations", parent)

        layout = QVBoxLayout(self)

        profile_label = QLabel("Preference Profile")
        profile_label.setObjectName("sectionTitle")
        layout.addWidget(profile_label)

        self._preference_bars: dict[str, PreferenceBar] = {}
        feature_names = [
            "Energy", "Valence", "Tempo", "Danceability",
            "Acousticness", "Instrumentalness", "Speechiness", "Liveness",
        ]
        for name in feature_names:
            bar = PreferenceBar(name)
            self._preference_bars[name.lower()] = bar
            layout.addWidget(bar)

        btn_row = QHBoxLayout()
        self._like_btn = QPushButton("Like")
        self._like_btn.setObjectName("primaryButton")
        self._like_btn.clicked.connect(self.track_liked.emit)

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.clicked.connect(self.track_skipped.emit)

        btn_row.addWidget(self._like_btn)
        btn_row.addWidget(self._skip_btn)
        layout.addLayout(btn_row)

        rec_label = QLabel("Recommended Tracks")
        rec_label.setObjectName("sectionTitle")
        layout.addWidget(rec_label)

        self._rec_list = QListWidget()
        self._rec_list.setMaximumHeight(200)
        self._rec_list.setAlternatingRowColors(True)
        layout.addWidget(self._rec_list)

        self._learning_label = QLabel("Learning from your listening...")
        self._learning_label.setObjectName("statusLabel")
        self._learning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._learning_label)

    def update_preferences(self, profile: dict[str, float]) -> None:
        """Update preference profile display."""
        for name, value in profile.items():
            if name in self._preference_bars:
                self._preference_bars[name].set_value(value)

    def update_recommendations(self, recommendations: list[dict[str, Any]]) -> None:
        """Update recommendation list."""
        self._rec_list.clear()
        for rec in recommendations:
            if rec.get("type") == "preference_profile":
                continue
            title = rec.get("title", "Unknown")
            artist = rec.get("artist", "Unknown")
            source = rec.get("source", "")
            score = rec.get("score", 0)
            text = f"{title} - {artist}"
            if source:
                text += f" [{source}]"
            item = QListWidgetItem(text)
            item.setToolTip(f"Match score: {score:.2f}")
            self._rec_list.addItem(item)

        if not recommendations:
            self._learning_label.setText("Play music to start learning your preferences...")
        else:
            self._learning_label.setText(
                f"Analyzed {len(recommendations)} tracks | Learning active"
            )
