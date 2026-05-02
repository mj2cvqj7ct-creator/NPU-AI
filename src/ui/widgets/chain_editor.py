"""
Effect Chain Editor Widget.

Provides a visual drag-and-drop interface for reordering the
audio processing chain. Each effect stage can be enabled/disabled
and reordered by dragging.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDrag
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from PyQt6.QtCore import QPoint
    from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QMouseEvent


class EffectStageItem(QWidget):
    """Single draggable effect stage in the chain."""

    toggled = pyqtSignal(str, bool)

    def __init__(
        self,
        name: str,
        display_name: str,
        color: QColor,
        enabled: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.effect_name = name
        self._display_name = display_name
        self._color = color
        self._enabled = enabled
        self._drag_start: QPoint | None = None

        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(10)

        # Drag handle indicator
        self._handle = QLabel("⋮⋮")
        self._handle.setStyleSheet("color: #484F58; font-size: 16px;")
        layout.addWidget(self._handle)

        # Color indicator
        self._indicator = QWidget()
        self._indicator.setFixedSize(8, 28)
        self._indicator.setStyleSheet(
            f"background-color: {color.name()}; border-radius: 4px;"
        )
        layout.addWidget(self._indicator)

        # Stage name
        self._name_label = QLabel(display_name)
        self._name_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        layout.addWidget(self._name_label, 1)

        # Enable/disable toggle
        self._toggle = QPushButton("ON" if enabled else "OFF")
        self._toggle.setCheckable(True)
        self._toggle.setChecked(enabled)
        self._toggle.setFixedSize(50, 28)
        self._toggle.clicked.connect(self._on_toggle)
        layout.addWidget(self._toggle)

        self._update_style()

    def _on_toggle(self) -> None:
        self._enabled = self._toggle.isChecked()
        self._toggle.setText("ON" if self._enabled else "OFF")
        self._update_style()
        self.toggled.emit(self.effect_name, self._enabled)

    def _update_style(self) -> None:
        alpha = "FF" if self._enabled else "60"
        self.setStyleSheet(
            f"EffectStageItem {{"
            f"  background-color: #161D28;"
            f"  border: 1px solid {self._color.name()}{alpha};"
            f"  border-radius: 10px;"
            f"}}"
        )
        self._name_label.setEnabled(self._enabled)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is None:
            return
        distance = (event.pos() - self._drag_start).manhattanLength()
        if distance < 20:
            return

        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.effect_name)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_start = None

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start = None
        super().mouseReleaseEvent(event)


class EffectChainEditor(QWidget):
    """Drag-and-drop effect chain reorder panel."""

    chain_changed = pyqtSignal(list)  # emits list of effect names in new order
    effect_toggled = pyqtSignal(str, bool)

    DEFAULT_CHAIN = [
        ("separation", "Source Separation", QColor(253, 121, 168)),
        ("enhancement", "Audio Enhancement", QColor(108, 92, 231)),
        ("spatial", "Spatial / Holographic", QColor(0, 206, 201)),
        ("depth", "Depth / Reverb", QColor(85, 239, 196)),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._items: list[EffectStageItem] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(6)
        self._layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("EFFECT CHAIN ORDER")
        self._chain_layout = QVBoxLayout(group)
        self._chain_layout.setSpacing(4)

        for name, display, color in self.DEFAULT_CHAIN:
            item = EffectStageItem(name, display, color)
            item.toggled.connect(self._on_item_toggled)
            self._items.append(item)
            self._chain_layout.addWidget(item)

        # Reset button
        reset_btn = QPushButton("Reset to Default Order")
        reset_btn.setObjectName("dangerButton")
        reset_btn.clicked.connect(self._reset_chain)
        self._chain_layout.addWidget(reset_btn)

        self._layout.addWidget(group)

    def _on_item_toggled(self, name: str, enabled: bool) -> None:
        self.effect_toggled.emit(name, enabled)

    def _reset_chain(self) -> None:
        """Restore default effect order."""
        for item in self._items:
            self._chain_layout.removeWidget(item)
            item.deleteLater()

        self._items.clear()
        for name, display, color in self.DEFAULT_CHAIN:
            item = EffectStageItem(name, display, color)
            item.toggled.connect(self._on_item_toggled)
            self._items.append(item)
            self._chain_layout.insertWidget(self._chain_layout.count() - 1, item)

        self.chain_changed.emit(self.get_chain_order())

    def get_chain_order(self) -> list[str]:
        return [item.effect_name for item in self._items]

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        source_name = event.mimeData().text()
        drop_pos = event.position().toPoint()

        source_idx = None
        for i, item in enumerate(self._items):
            if item.effect_name == source_name:
                source_idx = i
                break

        if source_idx is None:
            return

        # Find target position
        target_idx = len(self._items) - 1
        for i, item in enumerate(self._items):
            item_center = item.pos().y() + item.height() // 2
            if drop_pos.y() < item_center:
                target_idx = i
                break

        if source_idx == target_idx:
            return

        # Reorder
        item = self._items.pop(source_idx)
        self._chain_layout.removeWidget(item)
        self._items.insert(target_idx, item)
        # -1 because reset button is last widget
        self._chain_layout.insertWidget(target_idx, item)

        self.chain_changed.emit(self.get_chain_order())
        event.acceptProposedAction()
