"""
Help & Tutorial Overlay Widget.

Shows a first-run guided tour and keyboard shortcut reference
as a translucent overlay on the main window.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

TUTORIAL_STEPS = [
    {
        "title": "NPU Audio Enhancer へようこそ",
        "text": (
            "このアプリはSnapdragon X NPUを使って、"
            "リアルタイムで音質を劇的に向上させます。\n\n"
            "スペースキーで処理開始・停止できます。"
        ),
    },
    {
        "title": "エフェクトチェーン",
        "text": (
            "Effectsタブで4つの処理ステージを制御:\n"
            "• Source Separation - 楽器・ボーカル分離\n"
            "• Audio Enhancement - EQ・コンプ・エキサイター\n"
            "• Spatial / Holographic - 3D音場拡張\n"
            "• Depth / Reverb - リバーブ・奥行き\n\n"
            "ドラッグ＆ドロップで処理順序を変更できます。"
        ),
    },
    {
        "title": "プリセット & ジャンル検出",
        "text": (
            "8種のビルトインプリセットから選択、\n"
            "またはCtrl+Sでカスタムプリセット保存。\n\n"
            "Statsタブでジャンル自動検出結果と\n"
            "推薦プリセットが表示されます。"
        ),
    },
    {
        "title": "キーボードショートカット",
        "text": (
            "Space - 再生/停止\n"
            "B - バイパス\n"
            "A - A/B比較\n"
            "Ctrl+O - ファイルインポート\n"
            "Ctrl+E - エクスポート\n"
            "Ctrl+S - プリセット保存\n"
            "Ctrl+1~5 - タブ切替\n"
            "Ctrl+Up/Down - ボリューム"
        ),
    },
]


class HelpOverlay(QWidget):
    """Translucent overlay for guided tour and help."""

    closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._step = 0
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Content card
        self._card = QWidget()
        self._card.setStyleSheet(
            "QWidget {"
            "  background-color: rgba(22, 29, 40, 240);"
            "  border: 1px solid #6C5CE7;"
            "  border-radius: 16px;"
            "  padding: 24px;"
            "}"
        )
        card_layout = QVBoxLayout(self._card)
        card_layout.setSpacing(12)

        self._title_label = QLabel()
        self._title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._title_label.setStyleSheet("color: #A29BFE; border: none;")
        card_layout.addWidget(self._title_label)

        self._text_label = QLabel()
        self._text_label.setWordWrap(True)
        self._text_label.setStyleSheet(
            "color: #E6EDF3; font-size: 13px; border: none; line-height: 1.5;"
        )
        card_layout.addWidget(self._text_label)

        # Step indicator
        self._step_label = QLabel()
        self._step_label.setStyleSheet("color: #8B949E; border: none;")
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._step_label)

        # Buttons
        btn_row = QHBoxLayout()

        self._prev_btn = QPushButton("← 前へ")
        self._prev_btn.clicked.connect(self._prev_step)
        btn_row.addWidget(self._prev_btn)

        btn_row.addStretch()

        self._next_btn = QPushButton("次へ →")
        self._next_btn.clicked.connect(self._next_step)
        btn_row.addWidget(self._next_btn)

        self._close_btn = QPushButton("閉じる")
        self._close_btn.setObjectName("dangerButton")
        self._close_btn.clicked.connect(self._close)
        btn_row.addWidget(self._close_btn)

        card_layout.addLayout(btn_row)
        layout.addWidget(self._card)

        self._update_content()

    def _update_content(self) -> None:
        step = TUTORIAL_STEPS[self._step]
        self._title_label.setText(step["title"])
        self._text_label.setText(step["text"])
        total = len(TUTORIAL_STEPS)
        self._step_label.setText(f"{self._step + 1} / {total}")
        self._prev_btn.setEnabled(self._step > 0)
        self._next_btn.setEnabled(self._step < total - 1)

    def _next_step(self) -> None:
        if self._step < len(TUTORIAL_STEPS) - 1:
            self._step += 1
            self._update_content()

    def _prev_step(self) -> None:
        if self._step > 0:
            self._step -= 1
            self._update_content()

    def _close(self) -> None:
        self.hide()
        self.closed.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        painter.end()
        super().paintEvent(event)

    def show_at_center(self, parent: QWidget) -> None:
        """Show overlay centered on parent widget."""
        self.setFixedSize(480, 360)
        px = parent.x() + (parent.width() - 480) // 2
        py = parent.y() + (parent.height() - 360) // 2
        self.move(px, py)
        self._step = 0
        self._update_content()
        self.show()
