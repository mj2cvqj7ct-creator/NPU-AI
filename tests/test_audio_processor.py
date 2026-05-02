"""Tests for AudioProcessor pipeline (no PyQt / no audio device)."""

from __future__ import annotations

import unittest

import numpy as np


class TestAudioProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.audio.processor import AudioProcessor
        except ImportError as e:
            raise unittest.SkipTest(str(e)) from e
        cls.AudioProcessor = AudioProcessor

    def test_bypass_applies_master_gain(self) -> None:
        p = self.AudioProcessor()
        p.master_gain = 0.5
        p.bypass = True
        x = np.ones((64, 2), dtype=np.float32) * 0.4
        y = p.process(x)
        np.testing.assert_allclose(y, x * 0.5, rtol=1e-5, atol=1e-5)
        self.assertEqual(y.dtype, np.float32)

    def test_empty_input_returns_empty(self) -> None:
        p = self.AudioProcessor()
        z = np.zeros((0, 2), dtype=np.float32)
        out = p.process(z)
        self.assertEqual(out.shape, (0, 2))

    def test_set_sample_rate_preserves_stage_flags(self) -> None:
        p = self.AudioProcessor()
        p.config.enable_spatial = False
        p.config.enable_depth = False
        p.set_sample_rate(96000)
        self.assertFalse(p.config.enable_spatial)
        self.assertFalse(p.spatial.enabled)
        self.assertFalse(p.depth.enabled)
