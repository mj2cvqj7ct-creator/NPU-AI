"""
WASAPI Loopback Audio Capture Module.

Captures system audio output in real-time using WASAPI loopback mode on Windows.
Supports exclusive mode for minimum latency with the SABAJ A20D USB DAC.
"""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)


def probe_default_render_mix_sample_rate() -> int | None:
    """Read the mix-format sample rate of the default playback device (Windows)."""
    try:
        import comtypes
        from pycaw.pycaw import IAudioClient, IMMDeviceEnumerator

        comtypes.CoInitialize()
        enumerator = comtypes.CoCreateInstance(
            comtypes.GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}"),
            IMMDeviceEnumerator,
            comtypes.CLSCTX_ALL,
        )
        device = enumerator.GetDefaultAudioEndpoint(0, 1)
        client = device.Activate(IAudioClient._iid_, comtypes.CLSCTX_ALL, None)
        mix = client.GetMixFormat()
        rate = int(mix.contents.nSamplesPerSec)
        logger.info("Default render mix sample rate: %d Hz", rate)
        return rate
    except Exception as e:
        logger.debug("Could not probe mix sample rate: %s", e)
        return None


class CaptureMode(Enum):
    SHARED = "shared"
    EXCLUSIVE = "exclusive"


@dataclass
class AudioFormat:
    sample_rate: int = 48000
    channels: int = 2
    bit_depth: int = 32
    is_float: bool = True

    @property
    def dtype(self) -> np.dtype:
        if self.is_float:
            return np.float32 if self.bit_depth == 32 else np.float64
        return np.dtype(f"int{self.bit_depth}")

    @property
    def bytes_per_sample(self) -> int:
        return self.bit_depth // 8

    @property
    def bytes_per_frame(self) -> int:
        return self.bytes_per_sample * self.channels


@dataclass
class CaptureConfig:
    format: AudioFormat = field(default_factory=AudioFormat)
    mode: CaptureMode = CaptureMode.EXCLUSIVE
    buffer_size_ms: int = 10
    device_name: str | None = None

    @property
    def buffer_frames(self) -> int:
        return int(self.format.sample_rate * self.buffer_size_ms / 1000)


class WASAPICapture:
    """WASAPI loopback audio capture for real-time system audio interception."""

    def __init__(self, config: CaptureConfig | None = None):
        self.config = config or CaptureConfig()
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=256)
        self._is_capturing = False
        self._capture_thread: threading.Thread | None = None
        self._callbacks: list[Callable[[np.ndarray], None]] = []
        self._lock = threading.Lock()
        self._stream = None
        self._wasapi_client = None
        # Set by WASAPI thread from IAudioClient.GetMixFormat (authoritative)
        self._actual_sample_rate: int | None = None

    def add_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _initialize_wasapi(self) -> bool:
        """Initialize WASAPI loopback capture via comtypes/pycaw."""
        try:
            import comtypes
            from pycaw.pycaw import AudioUtilities, IAudioClient, IMMDeviceEnumerator

            comtypes.CoInitialize()

            enumerator = comtypes.CoCreateInstance(
                comtypes.GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}"),
                IMMDeviceEnumerator,
                comtypes.CLSCTX_ALL,
            )

            if self.config.device_name:
                devices = AudioUtilities.GetAllDevices()
                device = None
                for d in devices:
                    if self.config.device_name.lower() in d.FriendlyName.lower():
                        device = d
                        break
                if device is None:
                    logger.warning(
                        "Device '%s' not found, using default", self.config.device_name
                    )
                    device = enumerator.GetDefaultAudioEndpoint(0, 1)
                else:
                    device = device._dev
            else:
                device = enumerator.GetDefaultAudioEndpoint(0, 1)

            self._wasapi_client = device.Activate(IAudioClient._iid_, comtypes.CLSCTX_ALL, None)
            logger.info("WASAPI loopback initialized successfully")
            return True

        except ImportError:
            logger.info("WASAPI not available (non-Windows platform), using sounddevice fallback")
            return False
        except Exception as e:
            logger.warning("WASAPI initialization failed: %s, using sounddevice fallback", e)
            return False

    def _initialize_sounddevice(self) -> None:
        """Fallback: initialize sounddevice for audio capture."""
        import sounddevice as sd

        device_info = sd.query_devices(kind="input")
        logger.info("Using sounddevice capture: %s", device_info.get("name", "default"))

    def start(self) -> None:
        if self._is_capturing:
            return

        self._is_capturing = True
        wasapi_ok = self._initialize_wasapi()

        if not wasapi_ok:
            self._initialize_sounddevice()

        self._capture_thread = threading.Thread(
            target=self._capture_loop_sounddevice if not wasapi_ok else self._capture_loop_wasapi,
            daemon=True,
            name="AudioCapture",
        )
        self._capture_thread.start()
        logger.info(
            "Audio capture started: %dHz, %dch, %dbit, buffer=%dms",
            self.config.format.sample_rate,
            self.config.format.channels,
            self.config.format.bit_depth,
            self.config.buffer_size_ms,
        )

    @property
    def effective_sample_rate(self) -> int:
        """Sample rate of captured PCM (WASAPI mix rate or config)."""
        if self._actual_sample_rate is not None:
            return self._actual_sample_rate
        return self.config.format.sample_rate

    def stop(self) -> None:
        self._is_capturing = False
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._actual_sample_rate = None
        logger.info("Audio capture stopped")

    def _capture_loop_wasapi(self) -> None:
        """Main WASAPI capture loop using COM audio capture client."""
        try:
            import ctypes
            import time

            from comtypes import GUID

            AUDCLNT_SHAREMODE_SHARED = 0
            AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000
            REFTIMES_PER_SEC = 10_000_000

            client = self._wasapi_client
            mix_format = client.GetMixFormat()
            mix_rate = int(mix_format.contents.nSamplesPerSec)
            mix_ch = int(mix_format.contents.nChannels)
            with self._lock:
                self._actual_sample_rate = mix_rate
            self.config.format.sample_rate = mix_rate
            logger.info("WASAPI mix format: %d Hz, %d ch", mix_rate, mix_ch)
            buffer_duration_hns = int(
                REFTIMES_PER_SEC * self.config.buffer_size_ms / 1000
            )

            client.Initialize(
                AUDCLNT_SHAREMODE_SHARED,
                AUDCLNT_STREAMFLAGS_LOOPBACK,
                buffer_duration_hns,
                0,
                mix_format,
                None,
            )

            IID_IAudioCaptureClient = GUID("{C8ADBD64-E71E-48a0-A4DE-185C395CD317}")
            capture_client = client.GetService(IID_IAudioCaptureClient)

            client.Start()
            logger.info("WASAPI loopback capture started via COM")

            channels = mix_format.contents.nChannels

            while self._is_capturing:
                try:
                    packet_length = capture_client.GetNextPacketSize()
                    while packet_length > 0:
                        data_ptr, num_frames, flags, _, _ = capture_client.GetBuffer()

                        if num_frames > 0 and data_ptr:
                            byte_count = num_frames * channels * 4  # float32
                            raw = (ctypes.c_byte * byte_count).from_address(data_ptr)
                            audio_data = np.frombuffer(raw, dtype=np.float32).reshape(
                                num_frames, channels
                            ).copy()
                            if channels > 2:
                                audio_data = audio_data[:, :2]
                            elif channels == 1:
                                c0 = audio_data[:, 0]
                                audio_data = np.column_stack([c0, c0])
                            self._dispatch_audio(audio_data)

                        capture_client.ReleaseBuffer(num_frames)
                        packet_length = capture_client.GetNextPacketSize()

                    time.sleep(self.config.buffer_size_ms / 2000.0)

                except Exception as e:
                    logger.error("WASAPI capture error: %s", e)
                    time.sleep(0.001)

            client.Stop()

        except Exception as e:
            logger.warning("WASAPI COM capture failed, falling back to sounddevice: %s", e)
            self._capture_loop_sounddevice()

    def _capture_loop_sounddevice(self) -> None:
        """Sounddevice fallback capture loop."""
        import sounddevice as sd

        def audio_callback(indata: np.ndarray, frames: int, time_info, status) -> None:
            if status:
                logger.debug("Sounddevice status: %s", status)
            audio_copy = indata.copy()
            self._dispatch_audio(audio_copy)

        try:
            self._stream = sd.InputStream(
                samplerate=self.config.format.sample_rate,
                channels=self.config.format.channels,
                dtype="float32",
                blocksize=self.config.buffer_frames,
                callback=audio_callback,
            )
            self._stream.start()
            with self._lock:
                self._actual_sample_rate = int(self.config.format.sample_rate)

            while self._is_capturing:
                import time

                time.sleep(0.01)

        except Exception as e:
            logger.error("Sounddevice capture error: %s", e)
            self._is_capturing = False

    def _dispatch_audio(self, audio_data: np.ndarray) -> None:
        """Send captured audio to all registered callbacks."""
        try:
            self._audio_queue.put_nowait(audio_data)
        except queue.Full:
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.put_nowait(audio_data)
            except queue.Empty:
                pass

        with self._lock:
            for callback in self._callbacks:
                try:
                    callback(audio_data)
                except Exception as e:
                    logger.error("Audio callback error: %s", e)

    def get_audio(self, timeout: float = 0.1) -> np.ndarray | None:
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_capturing(self) -> bool:
        return self._is_capturing

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio capture devices."""
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            result = []
            for i, dev in enumerate(devices):
                if dev["max_input_channels"] > 0 or dev.get("hostapi", -1) >= 0:
                    result.append(
                        {
                            "index": i,
                            "name": dev["name"],
                            "channels": dev["max_input_channels"],
                            "sample_rate": dev["default_samplerate"],
                        }
                    )
            return result
        except Exception:
            return []
