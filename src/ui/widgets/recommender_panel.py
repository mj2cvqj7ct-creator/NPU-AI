"""
Recommendation Panel Widget (v2 - Streaming-Aware).

Displays:
  * a Now-Playing card driven by Spotify / Apple Music / YouTube Music
    metadata captured by :class:`StreamingDetector`
  * per-service preference profiles with coloured service badges
  * a live deep-learning loss curve so the user can watch the model adapt
  * recommendation cards with score, reason, and source pill

The panel is purely declarative — it never reaches into the recommender
engine state. Updates flow in via :py:meth:`update_now_playing`,
:py:meth:`update_preferences`, :py:meth:`update_service_profiles`, and
:py:meth:`update_recommendations`.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPolygonF,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.recommender.engine import (
    SERVICE_DISPLAY,
    SERVICE_KEYS,
)
from src.recommender.streaming_detector import (
    SOURCE_UNKNOWN,
    NowPlaying,
)


def _service_color(source: str) -> str:
    return SERVICE_DISPLAY.get(source, SERVICE_DISPLAY[SOURCE_UNKNOWN])["color"]


def _service_label(source: str) -> str:
    return SERVICE_DISPLAY.get(source, SERVICE_DISPLAY[SOURCE_UNKNOWN])["label"]


class _ServiceBadge(QLabel):
    """Pill label that recolours itself based on the streaming source."""

    def __init__(self, source: str = SOURCE_UNKNOWN) -> None:
        super().__init__()
        self.setObjectName("serviceBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(22)
        self.setMaximumHeight(22)
        self.set_source(source)

    def set_source(self, source: str) -> None:
        color = _service_color(source)
        label = _service_label(source)
        self.setText(label)
        self.setStyleSheet(
            "QLabel#serviceBadge {"
            f"background-color: {color}26;"
            f"color: {color};"
            f"border: 1px solid {color}80;"
            "border-radius: 11px;"
            "padding: 2px 12px;"
            "font-weight: 700;"
            "font-size: 11px;"
            "letter-spacing: 0.6px;"
            "}"
        )


class _LossSparkline(QFrame):
    """Tiny canvas showing the recent deep-learning loss curve.

    The y-axis is auto-scaled to ``[0, max(history) * 1.1]``. We avoid
    bringing in QtCharts to keep the EXE small, so this is a hand-rolled
    QPainter widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._values: list[float] = []
        self.setMinimumHeight(42)
        self.setMaximumHeight(60)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed,
        )
        self.setObjectName("lossSparkline")
        self.setStyleSheet(
            "QFrame#lossSparkline {"
            "background-color: #0F1620;"
            "border: 1px solid #2A3040;"
            "border-radius: 8px;"
            "}",
        )

    def update_values(self, values: list[float]) -> None:
        # Keep at most 240 points (~the loss_history maxlen on the engine).
        self._values = values[-240:]
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            rect = self.rect().adjusted(8, 6, -8, -6)
            if not self._values or rect.width() <= 0 or rect.height() <= 0:
                self._draw_placeholder(painter, rect)
                return
            v_max = max(self._values) or 1e-6
            v_min = min(self._values)
            span = max(1e-6, v_max - v_min)
            n = len(self._values)
            if n < 2:
                self._draw_placeholder(painter, rect)
                return
            grad = QLinearGradient(
                QPointF(0, rect.top()),
                QPointF(0, rect.bottom()),
            )
            grad.setColorAt(0.0, QColor("#A29BFE"))
            grad.setColorAt(1.0, QColor("#6C5CE7"))
            pen = QPen(QBrush(grad), 2.0)
            painter.setPen(pen)
            step = rect.width() / (n - 1)
            prev_x: float = float(rect.left())
            prev_y: float = float(
                rect.bottom() - ((self._values[0] - v_min) / span)
                * rect.height(),
            )
            for i in range(1, n):
                x = float(rect.left()) + step * i
                y = float(rect.bottom()) - (
                    (self._values[i] - v_min) / span
                ) * rect.height()
                painter.drawLine(QPointF(prev_x, prev_y), QPointF(x, y))
                prev_x, prev_y = x, y
            # Fill underneath the line for a soft glow.
            fill_grad = QLinearGradient(
                QPointF(0, rect.top()), QPointF(0, rect.bottom()),
            )
            fill_grad.setColorAt(0.0, QColor(108, 92, 231, 90))
            fill_grad.setColorAt(1.0, QColor(108, 92, 231, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(fill_grad))
            polygon = QPolygonF()
            polygon.append(QPointF(rect.left(), rect.bottom()))
            for i, v in enumerate(self._values):
                x = rect.left() + step * i
                y = rect.bottom() - ((v - v_min) / span) * rect.height()
                polygon.append(QPointF(x, y))
            polygon.append(QPointF(rect.right(), rect.bottom()))
            painter.drawPolygon(polygon)
        finally:
            painter.end()

    @staticmethod
    def _draw_placeholder(painter: QPainter, rect: Any) -> None:
        painter.setPen(QPen(QColor("#484F58")))
        painter.drawText(
            rect, Qt.AlignmentFlag.AlignCenter,
            "学習データを収集中…",
        )


class _NowPlayingCard(QFrame):
    """Header card showing the detected streaming track."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("nowPlayingCard")
        self.setStyleSheet(
            "QFrame#nowPlayingCard {"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            " stop:0 #1A2030, stop:1 #131A26);"
            "border: 1px solid #2A3040;"
            "border-radius: 14px;"
            "}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        self._artwork = QLabel("♪")
        self._artwork.setFixedSize(56, 56)
        self._artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._artwork.setStyleSheet(
            "QLabel {"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            " stop:0 #6C5CE7, stop:1 #00CEC9);"
            "color: white; border-radius: 12px; font-size: 26px;"
            "font-weight: 700;}"
        )

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._title = QLabel("音楽を再生してください")
        self._title.setStyleSheet(
            "font-weight: 700; font-size: 15px; color: #E6EDF3;",
        )
        self._artist = QLabel("Spotify / Apple Music / YouTube Music を検出します")
        self._artist.setStyleSheet("color: #8B949E; font-size: 12px;")
        self._badge = _ServiceBadge(SOURCE_UNKNOWN)
        self._state = QLabel("待機中")
        self._state.setStyleSheet("color: #8B949E; font-size: 11px;")

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        meta_row.addWidget(self._badge)
        meta_row.addWidget(self._state)
        meta_row.addStretch()

        text_col.addWidget(self._title)
        text_col.addWidget(self._artist)
        text_col.addLayout(meta_row)

        layout.addWidget(self._artwork)
        layout.addLayout(text_col, 1)

    def update_now_playing(self, now: NowPlaying) -> None:
        title = now.title or "音楽を再生してください"
        artist = now.artist or _service_label(now.source)
        if not now.has_metadata and now.source == SOURCE_UNKNOWN:
            artist = "Spotify / Apple Music / YouTube Music を検出します"
        self._title.setText(title)
        self._artist.setText(artist)
        self._badge.set_source(now.source)
        if now.is_playing and now.has_metadata:
            self._state.setText("再生中 — 学習更新")
            self._state.setStyleSheet("color: #00B894; font-size: 11px;")
        elif now.has_metadata:
            self._state.setText("一時停止 — 学習なし")
            self._state.setStyleSheet("color: #FDCB6E; font-size: 11px;")
        else:
            self._state.setText("待機中")
            self._state.setStyleSheet("color: #8B949E; font-size: 11px;")
        # Use the first letter of the title as a tiny “artwork”.
        glyph = (title or "♪")[:1].upper()
        self._artwork.setText(glyph or "♪")


class _ServiceProfileRow(QWidget):
    """One row showing the service badge plus its play count."""

    def __init__(self, source: str) -> None:
        super().__init__()
        self._source = source
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        self._badge = _ServiceBadge(source)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)
        color = _service_color(source)
        self._bar.setStyleSheet(
            "QProgressBar {"
            "background: #0F1620; border-radius: 4px; border: 0;"
            "}"
            "QProgressBar::chunk {"
            f"background-color: {color}; border-radius: 4px;"
            "}",
        )
        self._count = QLabel("0 曲")
        self._count.setStyleSheet("color: #8B949E; font-size: 11px;")
        self._count.setFixedWidth(60)
        self._count.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addWidget(self._badge)
        layout.addWidget(self._bar, 1)
        layout.addWidget(self._count)

    def update_state(self, profile_strength: float, play_count: int) -> None:
        self._bar.setValue(int(max(0.0, min(1.0, profile_strength)) * 100))
        self._count.setText(f"{play_count} 曲")


class PreferenceBar(QWidget):
    """Individual preference bar for global feature visualization."""

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(4)

        self._label = QLabel(name)
        self._label.setMinimumWidth(100)
        self._label.setMaximumWidth(120)

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
    """Panel displaying recommendations and per-service preference profiles."""

    track_liked = pyqtSignal()
    track_skipped = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("AI おすすめ", parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self._now_playing_card = _NowPlayingCard()
        layout.addWidget(self._now_playing_card)

        services_label = QLabel("ストリーミングサービス別 学習進捗")
        services_label.setObjectName("sectionTitle")
        layout.addWidget(services_label)
        self._service_rows: dict[str, _ServiceProfileRow] = {}
        for source in SERVICE_KEYS:
            row = _ServiceProfileRow(source)
            self._service_rows[source] = row
            layout.addWidget(row)

        learning_label = QLabel("ディープラーニング学習曲線（NPU推論）")
        learning_label.setObjectName("sectionTitle")
        layout.addWidget(learning_label)
        self._loss_chart = _LossSparkline()
        layout.addWidget(self._loss_chart)
        self._learning_summary = QLabel("学習ステップ: 0  ·  曲データベース: 0")
        self._learning_summary.setStyleSheet(
            "color: #8B949E; font-size: 11px;",
        )
        layout.addWidget(self._learning_summary)

        profile_label = QLabel("グローバル嗜好プロファイル")
        profile_label.setObjectName("sectionTitle")
        layout.addWidget(profile_label)

        self._preference_bars: dict[str, PreferenceBar] = {}
        feature_rows = [
            ("energy", "エネルギー"),
            ("valence", "ポジティブさ"),
            ("tempo", "テンポ"),
            ("danceability", "ダンス性"),
            ("acousticness", "アコースティック性"),
            ("instrumentalness", "インストゥルメンタル性"),
            ("speechiness", "スピーチ性"),
            ("liveness", "ライブ感"),
        ]
        for key, label in feature_rows:
            bar = PreferenceBar(label)
            self._preference_bars[key] = bar
            layout.addWidget(bar)

        btn_row = QHBoxLayout()
        self._like_btn = QPushButton("好き")
        self._like_btn.setObjectName("primaryButton")
        self._like_btn.clicked.connect(self.track_liked.emit)

        self._skip_btn = QPushButton("スキップ")
        self._skip_btn.clicked.connect(self.track_skipped.emit)

        btn_row.addWidget(self._like_btn)
        btn_row.addWidget(self._skip_btn)
        layout.addLayout(btn_row)

        rec_label = QLabel("クロスプラットフォームおすすめ")
        rec_label.setObjectName("sectionTitle")
        layout.addWidget(rec_label)

        self._rec_list = QListWidget()
        self._rec_list.setMinimumHeight(140)
        self._rec_list.setMaximumHeight(260)
        self._rec_list.setAlternatingRowColors(True)
        self._rec_list.setWordWrap(True)
        layout.addWidget(self._rec_list)

        self._learning_label = QLabel("再生中の音楽から学習しています…")
        self._learning_label.setObjectName("statusLabel")
        self._learning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._learning_label)

    # ----- Public update API -----------------------------------------------

    def update_now_playing(self, now: NowPlaying) -> None:
        self._now_playing_card.update_now_playing(now)

    def update_preferences(self, profile: dict[str, float]) -> None:
        """Update the global preference bars."""
        for name, value in profile.items():
            if name in self._preference_bars:
                self._preference_bars[name].set_value(value)

    def update_service_profiles(
        self,
        profiles: dict[str, dict[str, float]],
        play_counts: dict[str, int],
    ) -> None:
        """Update per-service progress bars."""
        max_count = max([1, *play_counts.values()])
        for source, row in self._service_rows.items():
            profile = profiles.get(source, {})
            # "Strength" = mean absolute value of the per-service vector,
            # i.e. how distinct that service's profile is from the cold-start
            # zero baseline. Combine with relative play share.
            if profile:
                strength = sum(abs(v) for v in profile.values())
                strength /= max(1, len(profile))
            else:
                strength = 0.0
            share = play_counts.get(source, 0) / max_count
            row.update_state(0.5 * strength + 0.5 * share, play_counts.get(source, 0))

    def update_learning_curve(
        self,
        loss_history: list[float],
        update_step: int,
        track_count: int,
    ) -> None:
        self._loss_chart.update_values(loss_history)
        self._learning_summary.setText(
            f"学習ステップ: {update_step}  ·  曲データベース: {track_count}",
        )

    def update_recommendations(self, recommendations: list[dict[str, Any]]) -> None:
        """Update recommendation list with structured rich items."""
        self._rec_list.clear()
        for rec in recommendations:
            if rec.get("type") == "preference_profile":
                continue
            title = rec.get("title", "不明")
            artist = rec.get("artist", "不明")
            source = rec.get("source", "")
            score = rec.get("score", 0)
            reason = rec.get("reason", "")
            label = _service_label(source) if source else ""
            text_lines = [f"{title} — {artist}"]
            if label:
                text_lines.append(f"[{label}] {reason}".strip())
            elif reason:
                text_lines.append(reason)
            text_lines.append(f"スコア: {score:+.2f}")
            item = QListWidgetItem("\n".join(text_lines))
            item.setData(Qt.ItemDataRole.UserRole, rec)
            color = QColor(_service_color(source))
            item.setForeground(QColor("#E6EDF3"))
            font = QFont()
            font.setPointSize(10)
            item.setFont(font)
            # Subtle stripe by setting background of the item to a tint.
            item.setBackground(QColor(color.red(), color.green(), color.blue(), 22))
            item.setToolTip(self._format_breakdown(rec))
            self._rec_list.addItem(item)

        if not recommendations:
            self._learning_label.setText(
                "音楽を再生すると嗜好の学習が始まります…",
            )
        else:
            self._learning_label.setText(
                f"{len(recommendations)} トラックを解析 — 学習中",
            )

    @staticmethod
    def _format_breakdown(rec: dict[str, Any]) -> str:
        breakdown = rec.get("breakdown") or {}
        if not breakdown:
            return str(rec.get("reason", ""))
        order = ("similarity", "mlp_score", "recency_bonus",
                 "exploration", "source_bonus")
        labels = {
            "similarity": "嗜好類似度",
            "mlp_score": "NPU MLPスコア",
            "recency_bonus": "最近の再生",
            "exploration": "探索ボーナス",
            "source_bonus": "サービス多様性",
        }
        lines: list[str] = []
        for key in order:
            if key in breakdown:
                lines.append(f"{labels[key]}: {breakdown[key]:+.3f}")
        play_count = rec.get("play_count")
        if play_count is not None:
            lines.append(f"再生回数: {play_count}")
        return "\n".join(lines)
