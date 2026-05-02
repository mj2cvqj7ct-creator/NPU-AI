"""
System Tray Integration.

Provides minimize-to-tray functionality with playback controls
and status indicators in the system notification area.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def _create_tray_icon() -> QIcon:
    """Generate a simple circular icon for the system tray."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QBrush(QColor(108, 92, 231)))
    painter.setPen(QColor(162, 155, 254))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    painter.setBrush(QBrush(QColor(255, 255, 255)))
    painter.setPen(QColor(255, 255, 255))
    points = [
        (24, 16),
        (24, 48),
        (46, 32),
    ]
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QPolygonF

    poly = QPolygonF([QPointF(x, y) for x, y in points])
    painter.drawPolygon(poly)
    painter.end()

    return QIcon(pixmap)


class SystemTrayManager:
    """Manages system tray icon and its context menu."""

    def __init__(self, main_window: MainWindow) -> None:
        self._window = main_window
        self._tray = QSystemTrayIcon(main_window)
        self._tray.setIcon(_create_tray_icon())
        self._tray.setToolTip("NPU Audio Enhancer")

        self._setup_menu()
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()
        logger.info("System tray icon initialized")

    def _setup_menu(self) -> None:
        menu = QMenu()

        self._show_action = QAction("Show Window", self._window)
        self._show_action.triggered.connect(self._show_window)
        menu.addAction(self._show_action)

        menu.addSeparator()

        self._play_action = QAction("Play / Stop", self._window)
        self._play_action.triggered.connect(
            lambda: self._window._master_bar._play_btn.toggle()
        )
        menu.addAction(self._play_action)

        self._bypass_action = QAction("Toggle Bypass", self._window)
        self._bypass_action.triggered.connect(
            lambda: self._window._master_bar._bypass_btn.toggle()
        )
        menu.addAction(self._bypass_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self._window)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self) -> None:
        self._window.showNormal()
        self._window.activateWindow()
        self._window.raise_()

    def _quit_app(self) -> None:
        self._tray.hide()
        self._window.close()

    def show_notification(self, title: str, message: str) -> None:
        self._tray.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )
