"""Regression: AudioOutput callback must not drop samples when chunk > blocksize."""

from __future__ import annotations

import sys
import time
import types
import unittest
from collections.abc import Callable
from typing import Any, cast

import numpy as np


class TestAudioOutputCarry(unittest.TestCase):
    """sounddevice invokes callbacks with fixed blocksize; large writes use _carry_buf."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.audio.output import AudioOutput, OutputConfig
        except ImportError as e:
            raise unittest.SkipTest(str(e)) from e
        cls.AudioOutput = AudioOutput
        cls.OutputConfig = OutputConfig

    def test_large_write_spans_callbacks_without_loss(self) -> None:
        """25-frame stereo chunk with blocksize 10 → 50 scalar samples, no gaps."""
        cfg = self.OutputConfig(
            sample_rate=1000,
            channels=2,
            buffer_size_ms=10,
        )
        self.assertEqual(cfg.buffer_frames, 10)

        collected: list[np.ndarray] = []
        stream_holder: list[object] = []

        class MockStream:
            def __init__(self, **kwargs: object) -> None:
                self.kw = dict(kwargs)
                orig_cb = self.kw["callback"]

                def wrapped(
                    outdata: np.ndarray,
                    frames: int,
                    time_info: object,
                    status: object,
                ) -> None:
                    orig_cb(outdata, frames, time_info, status)
                    collected.append(outdata.copy())

                self.kw["callback"] = wrapped
                stream_holder.append(self)

            def start(self) -> None:
                return None

            def stop(self) -> None:
                return None

            def close(self) -> None:
                return None

        fake_sd = types.ModuleType("sounddevice")
        fake_sd.OutputStream = MockStream
        prev_sd = sys.modules.get("sounddevice")
        sys.modules["sounddevice"] = fake_sd
        try:
            ao = self.AudioOutput(cfg)
            ao.start()
            deadline = time.monotonic() + 2.0
            while not stream_holder and time.monotonic() < deadline:
                time.sleep(0.005)
            self.assertTrue(stream_holder, "OutputStream was not constructed")

            chunk = np.ones((25, 2), dtype=np.float32)
            ao.write(chunk)

            for _ in range(6):
                out = np.zeros((cfg.buffer_frames, cfg.channels), dtype=np.float32)
                stream = cast(Any, stream_holder[0])
                callback = cast(
                    Callable[[np.ndarray, int, object, object], None],
                    stream.kw["callback"],
                )
                callback(out, cfg.buffer_frames, None, None)

            ao.stop()
        finally:
            if prev_sd is not None:
                sys.modules["sounddevice"] = prev_sd
            else:
                sys.modules.pop("sounddevice", None)

        if not collected:
            self.fail("callback never captured output")

        flat = np.vstack(collected).reshape(-1)
        self.assertGreaterEqual(flat.shape[0], 50)
        np.testing.assert_allclose(flat[:50], 1.0, rtol=0, atol=1e-6)
        if flat.shape[0] > 50:
            np.testing.assert_allclose(flat[50:60], 0.0, rtol=0, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
