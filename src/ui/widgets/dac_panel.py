"""
SABAJ A20D DAC Control Panel Widget.

Provides UI for DAC configuration including sample rate, bit depth,
buffer size, latency, and NPU optimization controls.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.dac.xmos_controller import BitDepth, DACStatus, SampleRate


class DACStatusIndicator(QWidget):
    """LED-style status indicator for DAC connection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._status = DACStatus.DISCONNECTED
        self._colors = {
            DACStatus.DISCONNECTED: QColor(72, 79, 88),
            DACStatus.CONNECTED: QColor(0, 184, 148),
            DACStatus.STREAMING: QColor(108, 92, 231),
            DACStatus.ERROR: QColor(225, 112, 85),
        }

    def set_status(self, status: DACStatus) -> None:
        self._status = status
        self.update()

    def paintEvent(self, event) -> None:
        from PyQt6.QtGui import QPainter, QRadialGradient

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = self._colors[self._status]
        gradient = QRadialGradient(8, 8, 8)
        gradient.setColorAt(0, color.lighter(150))
        gradient.setColorAt(0.7, color)
        gradient.setColorAt(1, color.darker(150))

        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()


class DACControlPanel(QGroupBox):
    """Control panel for SABAJ A20D XMOS USB DAC settings."""

    config_changed = pyqtSignal(dict)
    optimize_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("SABAJ A20D USB DAC", parent)

        layout = QVBoxLayout(self)

        status_row = QHBoxLayout()
        self._status_led = DACStatusIndicator()
        self._status_label = QLabel("Disconnected")
        self._status_label.setObjectName("statusLabel")
        self._chip_label = QLabel("DAC: ES9038PRO")
        self._chip_label.setObjectName("statusLabel")
        status_row.addWidget(self._status_led)
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        status_row.addWidget(self._chip_label)
        layout.addLayout(status_row)

        config_row = QHBoxLayout()

        sr_group = QVBoxLayout()
        sr_group.addWidget(QLabel("Sample Rate"))
        self._sample_rate = QComboBox()
        for sr in SampleRate:
            self._sample_rate.addItem(f"{sr.value:,} Hz", sr.value)
        self._sample_rate.setCurrentIndex(1)
        self._sample_rate.currentIndexChanged.connect(self._emit_config)
        sr_group.addWidget(self._sample_rate)
        config_row.addLayout(sr_group)

        bd_group = QVBoxLayout()
        bd_group.addWidget(QLabel("Bit Depth"))
        self._bit_depth = QComboBox()
        for bd in BitDepth:
            self._bit_depth.addItem(f"{bd.value}-bit", bd.value)
        self._bit_depth.setCurrentIndex(2)
        self._bit_depth.currentIndexChanged.connect(self._emit_config)
        bd_group.addWidget(self._bit_depth)
        config_row.addLayout(bd_group)

        layout.addLayout(config_row)

        buffer_row = QHBoxLayout()

        buf_group = QVBoxLayout()
        buf_group.addWidget(QLabel("Buffer Size (ms)"))
        self._buffer_size = QSpinBox()
        self._buffer_size.setRange(1, 100)
        self._buffer_size.setValue(10)
        self._buffer_size.valueChanged.connect(self._emit_config)
        buf_group.addWidget(self._buffer_size)
        buffer_row.addLayout(buf_group)

        lat_group = QVBoxLayout()
        lat_group.addWidget(QLabel("Latency (ms)"))
        self._latency = QSpinBox()
        self._latency.setRange(1, 50)
        self._latency.setValue(5)
        self._latency.valueChanged.connect(self._emit_config)
        lat_group.addWidget(self._latency)
        buffer_row.addLayout(lat_group)

        layout.addLayout(buffer_row)

        btn_row = QHBoxLayout()
        self._optimize_btn = QPushButton("NPU Optimize")
        self._optimize_btn.setObjectName("primaryButton")
        self._optimize_btn.clicked.connect(self.optimize_requested.emit)
        self._optimize_btn.setToolTip(
            "Auto-optimize buffer and latency settings for NPU processing pipeline"
        )

        self._info_label = QLabel("")
        self._info_label.setObjectName("statusLabel")
        self._info_label.setWordWrap(True)

        btn_row.addWidget(self._optimize_btn)
        btn_row.addWidget(self._info_label, 1)
        layout.addLayout(btn_row)

    def _emit_config(self) -> None:
        self.config_changed.emit(self.get_config())

    def get_config(self) -> dict:
        return {
            "sample_rate": self._sample_rate.currentData(),
            "bit_depth": self._bit_depth.currentData(),
            "buffer_size_ms": self._buffer_size.value(),
            "latency_ms": self._latency.value(),
        }

    def update_status(self, status_info: dict) -> None:
        """Update DAC status display."""
        status = DACStatus(status_info.get("status", "disconnected"))
        self._status_led.set_status(status)
        self._status_label.setText(status_info.get("device_name", "Unknown"))

        if "sample_rate" in status_info:
            for i in range(self._sample_rate.count()):
                if self._sample_rate.itemData(i) == status_info["sample_rate"]:
                    self._sample_rate.setCurrentIndex(i)
                    break

    def show_optimization_result(self, settings: dict) -> None:
        """Display NPU optimization results."""
        self._buffer_size.setValue(settings.get("buffer_size_ms", 10))
        self._latency.setValue(settings.get("latency_ms", 5))
        self._info_label.setText(
            f"Optimized: buffer={settings.get('buffer_size_ms')}ms, "
            f"latency={settings.get('latency_ms')}ms, "
            f"ASIO={settings.get('asio_buffer_size', 256)}"
        )
