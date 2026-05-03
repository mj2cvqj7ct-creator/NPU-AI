"""Regression tests for audio effect processors (no GUI)."""

from __future__ import annotations

import unittest


class TestDepthProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.audio.effects.depth import DepthProcessor
        except ImportError as e:
            raise unittest.SkipTest(str(e)) from e
        cls.DepthProcessor = DepthProcessor

    def test_init_has_distance_sos(self) -> None:
        d = self.DepthProcessor(48000)
        self.assertIsNotNone(d._distance_sos)
        self.assertEqual(len(d._zi_dist), 2)

    def test_update_parameters_ignores_foreign_keys(self) -> None:
        d = self.DepthProcessor(48000)
        orig_sr = d.sample_rate
        d.update_parameters(
            enabled=False,
            depth=999.0,
            sample_rate=12000,
            vocal_boost=0.9,
            depth_amount=0.2,
        )
        self.assertEqual(d.sample_rate, orig_sr)
        self.assertEqual(d.depth_amount, 0.2)

    def test_reset_streaming_state_does_not_crash(self) -> None:
        d = self.DepthProcessor(48000)
        d.reset_streaming_state()


class TestSpatialProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.audio.effects.spatial import SpatialProcessor
        except ImportError as e:
            raise unittest.SkipTest(str(e)) from e
        cls.SpatialProcessor = SpatialProcessor

    def test_update_parameters_whitelist(self) -> None:
        s = self.SpatialProcessor(48000)
        orig_sr = s.sample_rate
        orig_depth = s.depth
        s.update_parameters(
            pre_delay_ms=50.0,
            depth_amount=0.99,
            room_size=0.9,
            sample_rate=8000,
            enabled=False,
            vocal_boost=1.0,
        )
        self.assertEqual(s.sample_rate, orig_sr)
        self.assertEqual(s.depth, orig_depth)
        s.update_parameters(soundstage_width=0.88)
        self.assertAlmostEqual(s.soundstage_width, 0.88)


class TestEnhancerWhitelist(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.audio.effects.enhancer import AudioEnhancer
        except ImportError as e:
            raise unittest.SkipTest(str(e)) from e
        cls.AudioEnhancer = AudioEnhancer

    def test_update_parameters_ignores_sample_rate(self) -> None:
        e = self.AudioEnhancer(48000)
        orig = e.sample_rate
        e.update_parameters(sample_rate=8000, warmth=0.9, enabled=False)
        self.assertEqual(e.sample_rate, orig)
        self.assertAlmostEqual(e.warmth, 0.9)


class TestNoiseReducerWhitelist(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.audio.effects.noise_reducer import NPUNoiseReducer
        except ImportError as e:
            raise unittest.SkipTest(str(e)) from e
        cls.NPUNoiseReducer = NPUNoiseReducer

    def test_only_npu_blend_tunable(self) -> None:
        n = self.NPUNoiseReducer(48000)
        orig = n.sample_rate
        n.update_parameters(enabled=True, npu_blend=0.4, sample_rate=16000)
        self.assertEqual(n.sample_rate, orig)
        self.assertAlmostEqual(n.npu_blend, 0.4)


if __name__ == "__main__":
    unittest.main()
