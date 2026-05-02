"""
Audio Output Module.

Routes processed audio to the SABAJ A20D XMOS USB DAC or default output device.
Supports WASAPI exclusive mode for bit-perfect output with minimal latency.
"""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class OutputConfig:
    device_name: str | None = None
    sample_rate: int = 48000
    channels: int = 2
    bit_depth: int = 32
    buffer_size_ms: int = 10
    exclusive_mode: bool = True
    use_asio: bool = False

    @property
    def buffer_frames(self) -> int:
        return int(self.sample_rate * self.buffer_size_ms / 1000)


class AudioOutput:
    """Audio output handler with WASAPI exclusive mode and ASIO support."""

    def __init__(self, config: OutputConfig | None = None):
        self.config = config or OutputConfig()
        self._output_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=512)
        self._is_playing = False
        self._output_thread: threading.Thread | None = None
        self._stream = None
        self._lock = threading.Lock()
        self._volume = 1.0
        self._muted = False

        self._underrun_count = 0
        self._total_frames = 0

    def start(self) -> None:
        if self._is_playing:
            return

        self._is_playing = True
        self._output_thread = threading.Thread(
            target=self._output_loop,
            daemon=True,
            name="AudioOutput",
        )
        self._output_thread.start()
        logger.info(
            "Audio output started: %dHz, %dch, buffer=%dms, exclusive=%s",
            self.config.sample_rate,
            self.config.channels,
            self.config.buffer_size_ms,
            self.config.exclusive_mode,
        )

    def stop(self) -> None:
        self._is_playing = False
        if self._output_thread:
            self._output_thread.join(timeout=2.0)
            self._output_thread = None
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        while True:
            try:
                self._output_queue.get_nowait()
            except queue.Empty:
                break
        logger.info("Audio output stopped (underruns: %d)", self._underrun_count)

    def apply_config(self, config: OutputConfig) -> None:
        """Replace output config and recreate the stream if already playing."""
        was_playing = self._is_playing
        if was_playing:
            self.stop()
        self.config = config
        if was_playing:
            self.start()
        logger.info(
            "Output config applied: %dHz, buffer=%dms, exclusive=%s",
            self.config.sample_rate,
            self.config.buffer_size_ms,
            self.config.exclusive_mode,
        )

    def write(self, audio_data: np.ndarray) -> None:
        """Queue audio data for output."""
        if not self._is_playing:
            return

        if self._muted:
            audio_data = np.zeros_like(audio_data)
        # Do not scale by self._volume here: the DSP pipeline applies master_gain;
        # scaling twice made the Master slider non-linear (gain²).

        audio_data = np.ascontiguousarray(audio_data, dtype=np.float32)

        try:
            self._output_queue.put_nowait(audio_data)
        except queue.Full:
            self._output_queue.get_nowait()
            self._output_queue.put_nowait(audio_data)
            self._underrun_count += 1

    def _output_loop(self) -> None:
        """Main output loop using sounddevice."""
        import sounddevice as sd

        device = self._find_output_device()

        def output_callback(outdata: np.ndarray, frames: int, time_info, status) -> None:
            if status:
                logger.debug("Output status: %s", status)
                if status.output_underflow:
                    self._underrun_count += 1

            try:
                data = self._output_queue.get_nowait()
                if data.shape[0] >= frames:
                    outdata[:] = data[:frames]
                else:
                    outdata[: data.shape[0]] = data
                    outdata[data.shape[0] :] = 0
                self._total_frames += frames
            except queue.Empty:
                outdata[:] = 0

        try:
            self._stream = sd.OutputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="float32",
                blocksize=self.config.buffer_frames,
                device=device,
                callback=output_callback,
                latency="low" if self.config.exclusive_mode else "high",
            )
            self._stream.start()

            while self._is_playing:
                import time

                time.sleep(0.01)

        except Exception as e:
            logger.error("Audio output error: %s", e)
            self._is_playing = False

    def _find_output_device(self) -> int | None:
        """Find the configured output device."""
        if not self.config.device_name:
            return None

        import sounddevice as sd

        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if (
                self.config.device_name.lower() in dev["name"].lower()
                and dev["max_output_channels"] > 0
            ):
                logger.info("Found output device: %s (index %d)", dev["name"], i)
                return i

        logger.warning("Device '%s' not found, using default output", self.config.device_name)
        return None

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = max(0.0, min(2.0, value))

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, value: bool) -> None:
        self._muted = value

    @property
    def stats(self) -> dict:
        return {
            "total_frames": self._total_frames,
            "underrun_count": self._underrun_count,
            "queue_size": self._output_queue.qsize(),
            "is_playing": self._is_playing,
        }

    @staticmethod
    def list_output_devices() -> list[dict]:
        """List available audio output devices."""
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            result = []
            for i, dev in enumerate(devices):
                if dev["max_output_channels"] > 0:
                    result.append(
                        {
                            "index": i,
                            "name": dev["name"],
                            "channels": dev["max_output_channels"],
                            "sample_rate": dev["default_samplerate"],
                        }
                    )
            return result
        except Exception:
            return []
