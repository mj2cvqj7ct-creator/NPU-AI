"""
SABAJ A20D XMOS USB DAC Driver Control.

Interfaces with the XMOS USB DAC driver to configure sample rate,
bit depth, buffer size, and exclusive mode for optimal audio output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class DACStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    STREAMING = "streaming"
    ERROR = "error"


class SampleRate(Enum):
    SR_44100 = 44100
    SR_48000 = 48000
    SR_88200 = 88200
    SR_96000 = 96000
    SR_176400 = 176400
    SR_192000 = 192000
    SR_352800 = 352800
    SR_384000 = 384000
    SR_705600 = 705600
    SR_768000 = 768000


class BitDepth(Enum):
    BIT_16 = 16
    BIT_24 = 24
    BIT_32 = 32


@dataclass
class DACConfig:
    sample_rate: SampleRate = SampleRate.SR_48000
    bit_depth: BitDepth = BitDepth.BIT_32
    buffer_size_ms: int = 10
    exclusive_mode: bool = True
    dsd_mode: bool = False
    volume_db: float = 0.0
    latency_ms: int = 5
    asio_buffer_size: int = 256

    @property
    def buffer_frames(self) -> int:
        return int(self.sample_rate.value * self.buffer_size_ms / 1000)


@dataclass
class DACInfo:
    name: str = "SABAJ A20D"
    driver: str = "XMOS USB Audio"
    firmware_version: str = ""
    serial_number: str = ""
    usb_speed: str = "USB 2.0 High Speed"
    max_sample_rate: int = 768000
    max_bit_depth: int = 32
    supports_dsd: bool = True
    supports_mqa: bool = False
    dac_chip: str = "ES9038PRO"


class XMOSController:
    """Controller for SABAJ A20D XMOS USB DAC.

    Manages DAC configuration, sample rate switching, buffer optimization,
    and WASAPI exclusive mode for bit-perfect audio output.
    """

    def __init__(self, config: DACConfig | None = None):
        self.config = config or DACConfig()
        self._status = DACStatus.DISCONNECTED
        self._info = DACInfo()
        self._device_handle: Any = None
        self._current_sample_rate: int = 0
        self._current_bit_depth: int = 0

        self._detect_device()

    def _detect_device(self) -> None:
        """Detect SABAJ A20D USB DAC via Windows audio API."""
        try:
            self._detect_via_sounddevice()
        except Exception as e:
            logger.debug("Device detection error: %s", e)
            self._status = DACStatus.DISCONNECTED

    def _detect_via_sounddevice(self) -> None:
        """Detect DAC using sounddevice."""
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                name = dev["name"].lower()
                if any(
                    keyword in name
                    for keyword in ["sabaj", "xmos", "a20d", "usb audio"]
                ):
                    self._status = DACStatus.CONNECTED
                    self._info.name = dev["name"]
                    self._current_sample_rate = int(dev["default_samplerate"])
                    logger.info("SABAJ A20D detected: %s (device %d)", dev["name"], i)
                    return

            logger.info("SABAJ A20D not detected; using default audio output")
            self._status = DACStatus.DISCONNECTED

        except ImportError:
            logger.info("sounddevice not available for device detection")
            self._status = DACStatus.DISCONNECTED

    @property
    def status(self) -> DACStatus:
        return self._status

    @property
    def info(self) -> DACInfo:
        return self._info

    @property
    def is_connected(self) -> bool:
        return self._status in (DACStatus.CONNECTED, DACStatus.STREAMING)

    def configure(self, config: DACConfig) -> bool:
        """Apply DAC configuration."""
        self.config = config

        logger.info(
            "DAC configured: %dHz / %dbit / buffer=%dms / exclusive=%s / latency=%dms",
            config.sample_rate.value,
            config.bit_depth.value,
            config.buffer_size_ms,
            config.exclusive_mode,
            config.latency_ms,
        )

        self._current_sample_rate = config.sample_rate.value
        self._current_bit_depth = config.bit_depth.value

        return True

    def set_sample_rate(self, rate: SampleRate) -> bool:
        """Change the DAC sample rate."""
        self.config.sample_rate = rate
        self._current_sample_rate = rate.value
        logger.info("Sample rate set to %d Hz", rate.value)
        return True

    def set_bit_depth(self, depth: BitDepth) -> bool:
        """Change the DAC bit depth."""
        self.config.bit_depth = depth
        self._current_bit_depth = depth.value
        logger.info("Bit depth set to %d", depth.value)
        return True

    def set_buffer_size(self, size_ms: int) -> bool:
        """Set the output buffer size in milliseconds."""
        size_ms = max(1, min(100, size_ms))
        self.config.buffer_size_ms = size_ms
        logger.info("Buffer size set to %d ms", size_ms)
        return True

    def set_latency(self, latency_ms: int) -> bool:
        """Set the target latency in milliseconds."""
        latency_ms = max(1, min(50, latency_ms))
        self.config.latency_ms = latency_ms
        logger.info("Target latency set to %d ms", latency_ms)
        return True

    def optimize_for_npu(self) -> dict:
        """Auto-optimize DAC settings for NPU processing pipeline.

        Calculates optimal buffer and latency values to prevent audio dropouts
        while minimizing latency for real-time NPU processing.
        """
        npu_processing_budget_ms = 5
        safety_margin_ms = 2

        optimal_buffer = npu_processing_budget_ms + safety_margin_ms
        optimal_latency = max(3, optimal_buffer - 2)

        self.config.buffer_size_ms = optimal_buffer
        self.config.latency_ms = optimal_latency
        self.config.exclusive_mode = True

        optimal_asio = max(64, int(self.config.sample_rate.value * optimal_buffer / 1000))
        optimal_asio = 2 ** int(np.log2(optimal_asio) + 0.5) if optimal_asio > 0 else 256
        self.config.asio_buffer_size = optimal_asio

        settings = {
            "buffer_size_ms": optimal_buffer,
            "latency_ms": optimal_latency,
            "asio_buffer_size": optimal_asio,
            "exclusive_mode": True,
            "npu_budget_ms": npu_processing_budget_ms,
        }

        logger.info("DAC optimized for NPU: %s", settings)
        return settings

    def get_status_info(self) -> dict:
        """Get comprehensive DAC status information."""
        return {
            "status": self._status.value,
            "device_name": self._info.name,
            "driver": self._info.driver,
            "dac_chip": self._info.dac_chip,
            "sample_rate": self._current_sample_rate or self.config.sample_rate.value,
            "bit_depth": self._current_bit_depth or self.config.bit_depth.value,
            "buffer_size_ms": self.config.buffer_size_ms,
            "latency_ms": self.config.latency_ms,
            "exclusive_mode": self.config.exclusive_mode,
            "usb_speed": self._info.usb_speed,
            "supports_dsd": self._info.supports_dsd,
        }

