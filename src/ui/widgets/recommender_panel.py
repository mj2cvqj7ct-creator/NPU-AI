"""
Recommendation Panel Widget (v3 - Enhanced).

Displays real-time music recommendations and user preference profile
with MFCC/chroma feature visualization, source diversity indicators,
and Adam optimizer learning status.
"""

from __future__ import annotations

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

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(4)

        self._label = QLabel(name)
        self._label.setMinimumWidth(110)
        self._label.setMaximumWidth(110)

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

    def __init__(self, parent=None):
        super().__init__("AI Recommendations (Adam Optimizer)", parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Preference profile section
        profile_label = QLabel("Preference Profile")
        profile_label.setObjectName("sectionTitle")
        layout.addWidget(profile_label)

        self._preference_bars: dict[str, PreferenceBar] = {}
        feature_names = [
            "Energy", "Valence", "Tempo", "Danceability",
            "Acousticness", "Instrumentalness", "Speechiness", "Liveness",
            "Spectral Centroid", "Spectral Rolloff", "Spectral Contrast",
        ]
        for name in feature_names:
            bar = PreferenceBar(name)
            key = name.lower().replace(" ", "_")
            self._preference_bars[key] = bar
            layout.addWidget(bar)

        # Action buttons
        btn_row = QHBoxLayout()
        self._like_btn = QPushButton("Like")
        self._like_btn.setObjectName("successButton")
        self._like_btn.clicked.connect(self.track_liked.emit)
        self._like_btn.setToolTip("Reinforce current audio preference vector")

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.clicked.connect(self.track_skipped.emit)
        self._skip_btn.setToolTip("Penalize current audio in preference learning")

        btn_row.addWidget(self._like_btn)
        btn_row.addWidget(self._skip_btn)
        layout.addLayout(btn_row)

        # Source diversity
        source_row = QHBoxLayout()
        source_label = QLabel("Source Diversity")
        source_label.setObjectName("statusLabel")
        self._spotify_count = QLabel("Spotify: 0")
        self._spotify_count.setObjectName("statusLabel")
        self._apple_count = QLabel("Apple: 0")
        self._apple_count.setObjectName("statusLabel")
        self._youtube_count = QLabel("YouTube: 0")
        self._youtube_count.setObjectName("statusLabel")
        source_row.addWidget(source_label)
        source_row.addWidget(self._spotify_count)
        source_row.addWidget(self._apple_count)
        source_row.addWidget(self._youtube_count)
        layout.addLayout(source_row)

        # Optimizer stats
        opt_row = QHBoxLayout()
        self._lr_label = QLabel("LR: 0.010")
        self._lr_label.setObjectName("statusLabel")
        self._step_label = QLabel("Steps: 0")
        self._step_label.setObjectName("statusLabel")
        self._tracks_label = QLabel("Tracks: 0/5000")
        self._tracks_label.setObjectName("statusLabel")
        opt_row.addWidget(self._lr_label)
        opt_row.addWidget(self._step_label)
        opt_row.addWidget(self._tracks_label)
        layout.addLayout(opt_row)

        # Recommendations list
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

    def update_preferences(self, profile: dict) -> None:
        """Update preference profile display."""
        for name, value in profile.items():
            key = name.lower().replace(" ", "_")
            if key in self._preference_bars:
                self._preference_bars[key].set_value(value)

    def update_optimizer_stats(self, stats: dict) -> None:
        """Update optimizer statistics."""
        self._lr_label.setText(f"LR: {stats.get('learning_rate', 0.01):.4f}")
        self._step_label.setText(f"Steps: {stats.get('step', 0)}")
        tracks = stats.get("history_size", 0)
        self._tracks_label.setText(f"Tracks: {tracks}/5000")

    def update_source_counts(self, counts: dict) -> None:
        """Update source diversity counters."""
        self._spotify_count.setText(
            f"Spotify: {counts.get('spotify', 0)}"
        )
        self._apple_count.setText(
            f"Apple: {counts.get('apple_music', 0)}"
        )
        self._youtube_count.setText(
            f"YouTube: {counts.get('youtube_music', 0)}"
        )

    def update_recommendations(self, recommendations: list[dict]) -> None:
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
                source_icon = {
                    "spotify": "S",
                    "apple_music": "A",
                    "youtube_music": "Y",
                }.get(source, source[0].upper())
                text += f" [{source_icon}]"
            item = QListWidgetItem(text)
            item.setToolTip(
                f"Score: {score:.3f} | Source: {source}"
            )
            self._rec_list.addItem(item)

        if not recommendations:
            self._learning_label.setText(
                "Play music to start learning your preferences..."
            )
        else:
            self._learning_label.setText(
                f"Analyzed {len(recommendations)} tracks | "
                f"Adam optimizer active"
            )
