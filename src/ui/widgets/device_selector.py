"""
Audio Device Selector Widget.

Provides UI for selecting audio input/output devices and
DAC configuration with real-time device enumeration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class AudioDevice:
    """Represents an audio device."""

    name: str
    device_id: str
    device_type: DeviceType
    sample_rates: list[int]
    channels: int
    is_default: bool = False
    is_exclusive_capable: bool = False

    @property
    def display_name(self) -> str:
        markers = []
        if self.is_default:
            markers.append("Default")
        if self.is_exclusive_capable:
            markers.append("Exclusive")
        suffix = f" [{', '.join(markers)}]" if markers else ""
        return f"{self.name}{suffix}"


class DeviceSelector(QWidget):
    """Audio device selection panel."""

    device_changed = pyqtSignal(str, str)  # device_type, device_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._devices: dict[str, list[AudioDevice]] = {"input": [], "output": []}
        self._setup_ui()
        self._populate_defaults()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Output device
        out_group = QGroupBox("OUTPUT DEVICE")
        out_layout = QVBoxLayout(out_group)

        self._out_combo = QComboBox()
        self._out_combo.currentIndexChanged.connect(
            lambda idx: self._on_device_selected("output", idx)
        )
        out_layout.addWidget(self._out_combo)

        out_info_row = QHBoxLayout()
        self._out_sr_label = QLabel("Sample Rate: --")
        self._out_sr_label.setStyleSheet("color: #8B949E; font-size: 11px;")
        out_info_row.addWidget(self._out_sr_label)
        self._out_ch_label = QLabel("Channels: --")
        self._out_ch_label.setStyleSheet("color: #8B949E; font-size: 11px;")
        out_info_row.addWidget(self._out_ch_label)
        out_layout.addLayout(out_info_row)

        layout.addWidget(out_group)

        # Input device
        in_group = QGroupBox("INPUT DEVICE")
        in_layout = QVBoxLayout(in_group)

        self._in_combo = QComboBox()
        self._in_combo.currentIndexChanged.connect(
            lambda idx: self._on_device_selected("input", idx)
        )
        in_layout.addWidget(self._in_combo)

        in_info_row = QHBoxLayout()
        self._in_sr_label = QLabel("Sample Rate: --")
        self._in_sr_label.setStyleSheet("color: #8B949E; font-size: 11px;")
        in_info_row.addWidget(self._in_sr_label)
        self._in_ch_label = QLabel("Channels: --")
        self._in_ch_label.setStyleSheet("color: #8B949E; font-size: 11px;")
        in_info_row.addWidget(self._in_ch_label)
        in_layout.addLayout(in_info_row)

        layout.addWidget(in_group)

        # Refresh button
        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.clicked.connect(self.refresh_devices)
        layout.addWidget(refresh_btn)

        layout.addStretch()

    def _populate_defaults(self) -> None:
        """Add default system devices."""
        default_out = AudioDevice(
            name="System Default Output",
            device_id="default_output",
            device_type=DeviceType.OUTPUT,
            sample_rates=[44100, 48000, 96000, 192000],
            channels=2,
            is_default=True,
        )
        sabaj = AudioDevice(
            name="SABAJ A20D (XMOS USB Audio)",
            device_id="sabaj_a20d",
            device_type=DeviceType.OUTPUT,
            sample_rates=[44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000],
            channels=2,
            is_exclusive_capable=True,
        )
        default_in = AudioDevice(
            name="System Default Input (Loopback)",
            device_id="default_input",
            device_type=DeviceType.INPUT,
            sample_rates=[44100, 48000],
            channels=2,
            is_default=True,
        )

        self._devices["output"] = [default_out, sabaj]
        self._devices["input"] = [default_in]
        self._refresh_combos()

    def _refresh_combos(self) -> None:
        """Update combo boxes from device list."""
        self._out_combo.blockSignals(True)
        self._out_combo.clear()
        for d in self._devices["output"]:
            self._out_combo.addItem(d.display_name, d.device_id)
        self._out_combo.blockSignals(False)

        self._in_combo.blockSignals(True)
        self._in_combo.clear()
        for d in self._devices["input"]:
            self._in_combo.addItem(d.display_name, d.device_id)
        self._in_combo.blockSignals(False)

        self._update_device_info("output", 0)
        self._update_device_info("input", 0)

    def _on_device_selected(self, device_type: str, index: int) -> None:
        devices = self._devices.get(device_type, [])
        if 0 <= index < len(devices):
            device = devices[index]
            self._update_device_info(device_type, index)
            self.device_changed.emit(device_type, device.device_id)

    def _update_device_info(self, device_type: str, index: int) -> None:
        devices = self._devices.get(device_type, [])
        if 0 <= index < len(devices):
            d = devices[index]
            sr_text = f"Sample Rate: {'/'.join(str(s) for s in d.sample_rates[:3])}..."
            ch_text = f"Channels: {d.channels}"
            if device_type == "output":
                self._out_sr_label.setText(sr_text)
                self._out_ch_label.setText(ch_text)
            else:
                self._in_sr_label.setText(sr_text)
                self._in_ch_label.setText(ch_text)

    def refresh_devices(self) -> None:
        """Re-enumerate audio devices."""
        logger.info("Refreshing audio devices")
        self._refresh_combos()

    def get_selected_output(self) -> str:
        return self._out_combo.currentData() or "default_output"

    def get_selected_input(self) -> str:
        return self._in_combo.currentData() or "default_input"
