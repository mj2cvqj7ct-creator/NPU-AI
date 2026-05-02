"""
SABAJ A20D DAC Control Panel Widget (v3 - Enhanced).

Provides UI for DAC configuration including sample rate, bit depth,
buffer size, latency, NPU optimization, DAC filter selection,
triple-buffering, and buffer health monitoring.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.dac.xmos_controller import BitDepth, DACFilter, DACStatus, SampleRate


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
    loopback_resync_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("SABAJ A20D ES9038PRO USB DAC", parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Status row
        status_row = QHBoxLayout()
        self._status_led = DACStatusIndicator()
        self._status_label = QLabel("Disconnected")
        self._status_label.setObjectName("statusLabel")
        self._chip_label = QLabel("DAC: ES9038PRO")
        self._chip_label.setObjectName("valueLabel")
        status_row.addWidget(self._status_led)
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        status_row.addWidget(self._chip_label)
        layout.addLayout(status_row)

        self._pipeline_rates_label = QLabel("Pipeline: loopback — → out —")
        self._pipeline_rates_label.setObjectName("statusLabel")
        self._pipeline_rates_label.setWordWrap(True)
        self._pipeline_rates_label.setToolTip(
            "Windows default playback mix (loopback) vs DAC output sample rate. "
            "Resample: polyphase in the processing path. "
            "When idle, loopback rate is re-probed about every 1.5 s.",
        )
        layout.addWidget(self._pipeline_rates_label)

        # Sample rate + bit depth
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

        # DAC filter selection
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("DAC Filter"))
        self._dac_filter = QComboBox()
        for df in DACFilter:
            self._dac_filter.addItem(df.value, df.value)
        self._dac_filter.setCurrentIndex(3)  # Slow Minimum Phase
        self._dac_filter.currentIndexChanged.connect(self._emit_config)
        filter_row.addWidget(self._dac_filter, 1)
        layout.addLayout(filter_row)

        # Buffer + latency
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

        # Triple-buffer + exclusive mode
        mode_row = QHBoxLayout()
        self._exclusive_check = QCheckBox("WASAPI Exclusive Mode")
        self._exclusive_check.setChecked(True)
        self._exclusive_check.setToolTip("Bit-perfect output via WASAPI exclusive mode")
        self._exclusive_check.toggled.connect(self._emit_config)

        self._triple_buf_check = QCheckBox("Triple Buffering")
        self._triple_buf_check.setChecked(True)
        self._triple_buf_check.setToolTip(
            "Triple-buffer for zero-dropout NPU streaming"
        )
        self._triple_buf_check.toggled.connect(self._emit_config)

        mode_row.addWidget(self._exclusive_check)
        mode_row.addWidget(self._triple_buf_check)
        layout.addLayout(mode_row)

        # NPU optimize button + health display
        btn_row = QHBoxLayout()
        self._optimize_btn = QPushButton("NPU Optimize")
        self._optimize_btn.setObjectName("primaryButton")
        self._optimize_btn.clicked.connect(self.optimize_requested.emit)
        self._optimize_btn.setToolTip(
            "Auto-optimize buffer and latency for NPU processing"
        )

        self._resync_loopback_btn = QPushButton("Resync loopback")
        self._resync_loopback_btn.setObjectName("secondaryButton")
        self._resync_loopback_btn.clicked.connect(
            self.loopback_resync_requested.emit,
        )
        self._resync_loopback_btn.setToolTip(
            "Re-probe Windows default playback mix and restart WASAPI loopback. "
            "Use if capture dropped after a driver or default-device change. "
            "Shortcut: Ctrl+Shift+R (requires processing started)."
        )
        self._resync_loopback_btn.setEnabled(False)

        self._info_label = QLabel("")
        self._info_label.setObjectName("statusLabel")
        self._info_label.setWordWrap(True)

        btn_row.addWidget(self._optimize_btn)
        btn_row.addWidget(self._resync_loopback_btn)
        btn_row.addWidget(self._info_label, 1)
        layout.addLayout(btn_row)

        # Health monitoring
        health_row = QHBoxLayout()
        self._health_label = QLabel("Buffer Health: 100%")
        self._health_label.setObjectName("valueLabel")
        self._dropout_label = QLabel("Dropouts: 0")
        self._dropout_label.setObjectName("statusLabel")
        self._npu_time_label = QLabel("NPU: -- ms")
        self._npu_time_label.setObjectName("statusLabel")
        health_row.addWidget(self._health_label)
        health_row.addWidget(self._dropout_label)
        health_row.addWidget(self._npu_time_label)
        layout.addLayout(health_row)

    def set_loopback_resync_enabled(self, enabled: bool) -> None:
        self._resync_loopback_btn.setEnabled(enabled)

    def update_pipeline_rates(self, info: dict[str, int | bool]) -> None:
        """Show loopback vs output rates from AudioEnhancerApp.pipeline_rate_info()."""
        lb = int(info["loopback_hz"])
        out = int(info["output_hz"])
        if info["resampling"]:
            self._pipeline_rates_label.setText(
                f"Pipeline: loopback {lb} Hz → out {out} Hz (resample)",
            )
            self._pipeline_rates_label.setStyleSheet("color: #FDCB6E;")
        else:
            self._pipeline_rates_label.setText(
                f"Pipeline: loopback {lb} Hz — matched to out {out} Hz",
            )
            self._pipeline_rates_label.setStyleSheet("color: #55EFC4;")

    def _emit_config(self) -> None:
        self.config_changed.emit(self.get_config())

    def get_config(self) -> dict:
        return {
            "sample_rate": self._sample_rate.currentData(),
            "bit_depth": self._bit_depth.currentData(),
            "buffer_size_ms": self._buffer_size.value(),
            "latency_ms": self._latency.value(),
            "exclusive_mode": self._exclusive_check.isChecked(),
            "triple_buffer": self._triple_buf_check.isChecked(),
            "dac_filter": self._dac_filter.currentData(),
        }

    def update_status(self, status_info: dict) -> None:
        """Update DAC status display."""
        status = DACStatus(status_info.get("status", "disconnected"))
        self._status_led.set_status(status)
        self._status_label.setText(status_info.get("device_name", "Unknown"))

        if "sample_rate" in status_info:
            for w in (
                self._sample_rate,
                self._bit_depth,
                self._dac_filter,
                self._buffer_size,
                self._latency,
                self._exclusive_check,
                self._triple_buf_check,
            ):
                w.blockSignals(True)
            try:
                for i in range(self._sample_rate.count()):
                    if self._sample_rate.itemData(i) == status_info["sample_rate"]:
                        self._sample_rate.setCurrentIndex(i)
                        break
            finally:
                for w in (
                    self._sample_rate,
                    self._bit_depth,
                    self._dac_filter,
                    self._buffer_size,
                    self._latency,
                    self._exclusive_check,
                    self._triple_buf_check,
                ):
                    w.blockSignals(False)

        # Health monitoring
        health = status_info.get("buffer_health", 1.0)
        self._health_label.setText(f"Buffer Health: {health * 100:.0f}%")
        if health >= 0.8:
            self._health_label.setStyleSheet("color: #00B894;")
        elif health >= 0.5:
            self._health_label.setStyleSheet("color: #FDCB6E;")
        else:
            self._health_label.setStyleSheet("color: #E17055;")

        dropouts = status_info.get("dropout_count", 0)
        self._dropout_label.setText(f"Dropouts: {dropouts}")

        npu_ms = status_info.get("npu_processing_ms", 0)
        npu_peak = status_info.get("npu_peak_ms", 0)
        self._npu_time_label.setText(
            f"NPU: {npu_ms:.1f}ms (peak: {npu_peak:.1f}ms)"
        )

    def show_optimization_result(self, settings: dict) -> None:
        """Display NPU optimization results."""
        for w in (self._buffer_size, self._latency):
            w.blockSignals(True)
        try:
            self._buffer_size.setValue(settings.get("buffer_size_ms", 10))
            self._latency.setValue(settings.get("latency_ms", 5))
        finally:
            for w in (self._buffer_size, self._latency):
                w.blockSignals(False)
        self._info_label.setText(
            f"Optimized: buffer={settings.get('buffer_size_ms')}ms, "
            f"latency={settings.get('latency_ms')}ms, "
            f"ASIO={settings.get('asio_buffer_size', 256)}, "
            f"filter={settings.get('dac_filter', 'N/A')}"
        )
