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

    def test_set_sample_rate_rejects_nonpositive(self) -> None:
        p = self.AudioProcessor()
        before = p.config.sample_rate
        p.set_sample_rate(0)
        self.assertEqual(p.config.sample_rate, before)
        p.set_sample_rate(-48000)
        self.assertEqual(p.config.sample_rate, before)

    def test_process_mono_input_becomes_stereo(self) -> None:
        p = self.AudioProcessor()
        p.config.enable_noise_reduction = False
        p.config.enable_separation = False
        p.config.enable_enhancement = False
        p.config.enable_spatial = False
        p.config.enable_depth = False
        x = np.full((128,), 0.05, dtype=np.float32)
        y = p.process(x)
        self.assertEqual(y.ndim, 2)
        self.assertEqual(y.shape, (128, 2))
        self.assertEqual(y.dtype, np.float32)

    def test_visualization_empty_audio(self) -> None:
        p = self.AudioProcessor()
        d = p.get_visualization_data(np.zeros((0, 2), dtype=np.float32))
        self.assertEqual(d["spectrum"], [])
        self.assertEqual(d["waveform"], [])
        self.assertEqual(d["stem_levels"], {})

    def test_visualization_separation_off_yields_no_stems(self) -> None:
        p = self.AudioProcessor()
        p.config.enable_separation = False
        x = np.random.randn(2048, 2).astype(np.float32) * 0.01
        d = p.get_visualization_data(x)
        self.assertEqual(d["stem_levels"], {})
        self.assertGreater(len(d["spectrum"]), 0)
        self.assertGreater(len(d["waveform"]), 0)

    def test_bypass_toggle_invokes_pipeline_flush_flags(self) -> None:
        p = self.AudioProcessor()
        p.bypass = True
        self.assertTrue(p._flush_pipeline_on_next_bypass_frame)
        self.assertTrue(p._flush_pipeline_on_next_dsp_frame)
        p.process(np.ones((32, 2), dtype=np.float32))
        self.assertFalse(p._flush_pipeline_on_next_bypass_frame)
        self.assertFalse(p._flush_pipeline_on_next_dsp_frame)

        p.bypass = False
        self.assertTrue(p._flush_pipeline_on_next_dsp_frame)
        p.process(np.ones((32, 2), dtype=np.float32))
        self.assertFalse(p._flush_pipeline_on_next_dsp_frame)

    def test_bypass_off_without_bypass_frame_still_flushes_dsp(self) -> None:
        """Rapid bypass on→off before any bypass process() must not skip DSP flush."""
        p = self.AudioProcessor()
        p.bypass = True
        self.assertTrue(p._flush_pipeline_on_next_bypass_frame)
        self.assertTrue(p._flush_pipeline_on_next_dsp_frame)
        p.bypass = False
        self.assertTrue(p._flush_pipeline_on_next_dsp_frame)
        self.assertTrue(p._flush_pipeline_on_next_bypass_frame)
        p.process(np.ones((16, 2), dtype=np.float32))
        self.assertFalse(p._flush_pipeline_on_next_dsp_frame)
        self.assertFalse(p._flush_pipeline_on_next_bypass_frame)
