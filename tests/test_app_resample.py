"""AudioEnhancerApp._resample_audio edge cases (no app instance)."""

from __future__ import annotations

import unittest

import numpy as np


class TestResampleAudio(unittest.TestCase):
    def test_invalid_sample_rates_returns_audio_unchanged_shape(self) -> None:
        from src.app import AudioEnhancerApp

        x = np.linspace(-1, 1, 20, dtype=np.float32).reshape(10, 2)
        y0 = AudioEnhancerApp._resample_audio(x, 0, 48000)
        self.assertEqual(y0.shape, x.shape)
        self.assertEqual(y0.dtype, np.float32)
        np.testing.assert_array_equal(y0, x.astype(np.float32))

        y1 = AudioEnhancerApp._resample_audio(x, 48000, -1)
        np.testing.assert_array_equal(y1, x.astype(np.float32))


if __name__ == "__main__":
    unittest.main()
