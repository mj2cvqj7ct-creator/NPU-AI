"""Regression: WASAPI failure must not leave self.config.format mutated.

When WASAPI capture fails (e.g. client.Initialize raises) and the loop falls
back to sounddevice, sd.InputStream is opened with self.config.format.channels.
If channels was mutated to a surround value (6 or 8) from the WASAPI mix
format, the sounddevice fallback will fail on most input devices that only
support 1-2 channels. The fallback must use the original (pre-WASAPI) config.
"""

from __future__ import annotations

import sys
import types
import unittest
from typing import Any
from unittest.mock import MagicMock


class TestWasapiFallbackConfigRestoration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.audio.capture import (
                AudioFormat,
                CaptureConfig,
                WASAPICapture,
            )
        except ImportError as e:
            raise unittest.SkipTest(str(e)) from e
        cls.AudioFormat = AudioFormat
        cls.CaptureConfig = CaptureConfig
        cls.WASAPICapture = WASAPICapture

    def _install_fake_modules(self) -> dict[str, Any]:
        """Stub comtypes/pycaw/sounddevice so capture.py can import them on Linux."""
        previous: dict[str, Any] = {}

        fake_comtypes = types.ModuleType("comtypes")

        def _GUID(s: str) -> str:
            return s

        fake_comtypes.GUID = _GUID
        fake_comtypes.CoInitialize = MagicMock()
        fake_comtypes.CoUninitialize = MagicMock()
        fake_comtypes.CoCreateInstance = MagicMock()
        fake_comtypes.CLSCTX_ALL = 0

        previous["comtypes"] = sys.modules.get("comtypes")
        sys.modules["comtypes"] = fake_comtypes

        fake_sd = types.ModuleType("sounddevice")
        sounddevice_streams: list[Any] = []

        class _FakeStream:
            def __init__(self, **kwargs: Any) -> None:
                self.kw = dict(kwargs)
                sounddevice_streams.append(self)

            def start(self) -> None:
                return None

            def stop(self) -> None:
                return None

            def close(self) -> None:
                return None

        fake_sd.InputStream = _FakeStream
        fake_sd.query_devices = lambda kind="input": {"name": "fake"}
        previous["sounddevice"] = sys.modules.get("sounddevice")
        sys.modules["sounddevice"] = fake_sd

        previous["_streams"] = sounddevice_streams
        return previous

    def _restore_modules(self, previous: dict[str, Any]) -> None:
        for name in ("comtypes", "sounddevice"):
            prev = previous.get(name)
            if prev is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prev

    def _make_mix_format(self, channels: int, sample_rate: int, bits: int) -> Any:
        contents = MagicMock()
        contents.nSamplesPerSec = sample_rate
        contents.nChannels = channels
        contents.wBitsPerSample = bits
        contents.nBlockAlign = channels * (bits // 8)
        mix = MagicMock()
        mix.contents = contents
        return mix

    def test_initialize_failure_restores_original_channels_for_sounddevice_fallback(
        self,
    ) -> None:
        """If client.Initialize() raises, channels must NOT leak into the fallback."""
        previous = self._install_fake_modules()
        try:
            cfg = self.CaptureConfig(format=self.AudioFormat(sample_rate=48000, channels=2))
            cap = self.WASAPICapture(cfg)

            client = MagicMock()
            client.GetMixFormat.return_value = self._make_mix_format(
                channels=8, sample_rate=44100, bits=32,
            )
            client.Initialize.side_effect = OSError("WASAPI Initialize failed")
            cap._wasapi_client = client

            cap._is_capturing = False
            cap._capture_loop_wasapi()

            self.assertEqual(cap.config.format.channels, 2)
            self.assertEqual(cap.config.format.sample_rate, 48000)
            self.assertEqual(cap.config.format.bit_depth, 32)
            self.assertEqual(cap._actual_sample_rate, 48000)

            streams = previous["_streams"]
            self.assertTrue(streams, "sounddevice fallback was not invoked")
            self.assertEqual(streams[0].kw["channels"], 2)
            self.assertEqual(streams[0].kw["samplerate"], 48000)
        finally:
            self._restore_modules(previous)

    def test_getmixformat_failure_restores_original_channels(self) -> None:
        """If GetMixFormat() raises, channels are unchanged (defense in depth)."""
        previous = self._install_fake_modules()
        try:
            cfg = self.CaptureConfig(format=self.AudioFormat(sample_rate=48000, channels=2))
            cap = self.WASAPICapture(cfg)

            client = MagicMock()
            client.GetMixFormat.side_effect = OSError("GetMixFormat failed")
            cap._wasapi_client = client

            cap._is_capturing = False
            cap._capture_loop_wasapi()

            self.assertEqual(cap.config.format.channels, 2)
            self.assertEqual(cap.config.format.sample_rate, 48000)
            self.assertEqual(cap.config.format.bit_depth, 32)

            streams = previous["_streams"]
            self.assertTrue(streams)
            self.assertEqual(streams[0].kw["channels"], 2)
        finally:
            self._restore_modules(previous)

    def test_successful_wasapi_setup_publishes_actual_format_to_config(
        self,
    ) -> None:
        """Happy path: after client.Start(), config.format reflects the mix format."""
        previous = self._install_fake_modules()
        try:
            cfg = self.CaptureConfig(format=self.AudioFormat(sample_rate=48000, channels=2))
            cap = self.WASAPICapture(cfg)

            client = MagicMock()
            client.GetMixFormat.return_value = self._make_mix_format(
                channels=6, sample_rate=44100, bits=32,
            )
            client.Initialize.return_value = None
            client.GetService.return_value = MagicMock(
                GetNextPacketSize=MagicMock(return_value=0),
            )
            client.Start.return_value = None
            client.Stop.return_value = None
            cap._wasapi_client = client

            cap._is_capturing = False
            cap._capture_loop_wasapi()

            self.assertEqual(cap.config.format.channels, 6)
            self.assertEqual(cap.config.format.sample_rate, 44100)
            self.assertEqual(cap.config.format.bit_depth, 32)
            self.assertEqual(cap._actual_sample_rate, 44100)
        finally:
            self._restore_modules(previous)


if __name__ == "__main__":
    unittest.main()
