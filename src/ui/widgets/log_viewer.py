"""
Log Viewer & Debug Panel Widget.

Displays application logs in real-time with filtering,
NPU/DAC status details, and performance metrics.
"""

from __future__ import annotations

import logging
from collections import deque

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor, QTextCharFormat
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogHandler(logging.Handler):
    """Custom logging handler that stores records for the viewer."""

    def __init__(self, max_records: int = 2000) -> None:
        super().__init__()
        self._records: deque[logging.LogRecord] = deque(maxlen=max_records)

    def emit(self, record: logging.LogRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> deque[logging.LogRecord]:
        return self._records

    def clear(self) -> None:
        self._records.clear()


# Singleton handler registered once
_log_handler = LogHandler()


def get_log_handler() -> LogHandler:
    return _log_handler


def install_log_handler() -> None:
    """Install the log handler on the root logger."""
    root = logging.getLogger()
    if _log_handler not in root.handlers:
        _log_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
        )
        root.addHandler(_log_handler)


_LEVEL_COLORS = {
    "DEBUG": QColor(139, 148, 158),
    "INFO": QColor(85, 239, 196),
    "WARNING": QColor(253, 203, 110),
    "ERROR": QColor(225, 112, 85),
    "CRITICAL": QColor(253, 121, 168),
}


class LogViewer(QWidget):
    """Real-time application log viewer with level filtering."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        install_log_handler()
        self._last_count = 0
        self._setup_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(500)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Level:"))
        self._level_filter = QComboBox()
        self._level_filter.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self._level_filter.setCurrentText("INFO")
        self._level_filter.currentTextChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._level_filter)

        toolbar.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self._clear_logs)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        # Log text area
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet(
            "QTextEdit {"
            "  background-color: #0A0E14;"
            "  color: #E6EDF3;"
            "  font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;"
            "  font-size: 11px;"
            "  border: 1px solid #2A3040;"
            "  border-radius: 8px;"
            "  padding: 8px;"
            "}"
        )
        layout.addWidget(self._text)

    def _on_filter_changed(self) -> None:
        self._last_count = 0
        self._text.clear()
        self._refresh()

    def _clear_logs(self) -> None:
        get_log_handler().clear()
        self._text.clear()
        self._last_count = 0

    def _refresh(self) -> None:
        handler = get_log_handler()
        records = list(handler.records)

        level_text = self._level_filter.currentText()
        min_level = getattr(logging, level_text, 0) if level_text != "ALL" else 0

        filtered = [r for r in records if r.levelno >= min_level]

        if len(filtered) == self._last_count:
            return

        # Only append new records
        new_records = filtered[self._last_count:]
        self._last_count = len(filtered)

        cursor = self._text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        for record in new_records:
            fmt = QTextCharFormat()
            level_name = record.levelname
            color = _LEVEL_COLORS.get(level_name, QColor(230, 237, 243))
            fmt.setForeground(color)

            text = handler.format(record)
            cursor.insertText(text + "\n", fmt)

        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()


class DebugPanel(QWidget):
    """Combined debug panel with log viewer and system status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Status group
        status_group = QGroupBox("SYSTEM STATUS")
        status_layout = QVBoxLayout(status_group)

        self._npu_status = QLabel("NPU: —")
        self._npu_status.setObjectName("statusLabel")
        self._dac_status = QLabel("DAC: —")
        self._dac_status.setObjectName("statusLabel")
        self._pipeline_status = QLabel("Pipeline: Stopped")
        self._pipeline_status.setObjectName("statusLabel")
        self._memory_status = QLabel("Memory: —")
        self._memory_status.setObjectName("statusLabel")

        status_layout.addWidget(self._npu_status)
        status_layout.addWidget(self._dac_status)
        status_layout.addWidget(self._pipeline_status)
        status_layout.addWidget(self._memory_status)

        layout.addWidget(status_group)

        # Log viewer
        log_group = QGroupBox("APPLICATION LOG")
        log_layout = QVBoxLayout(log_group)
        self._log_viewer = LogViewer()
        log_layout.addWidget(self._log_viewer)

        layout.addWidget(log_group, 1)

    def update_npu_status(self, info: dict) -> None:
        provider = info.get("provider", "Unknown")
        is_npu = info.get("is_npu", False)
        badge = "NPU" if is_npu else "CPU"
        self._npu_status.setText(f"NPU: {badge} ({provider})")

    def update_dac_status(self, connected: bool, name: str = "") -> None:
        if connected:
            self._dac_status.setText(f"DAC: Connected ({name})")
        else:
            self._dac_status.setText("DAC: Not Connected")

    def update_pipeline_status(self, running: bool) -> None:
        self._pipeline_status.setText(f"Pipeline: {'Running' if running else 'Stopped'}")

    def update_memory(self, mb: float) -> None:
        self._memory_status.setText(f"Memory: {mb:.0f} MB")
