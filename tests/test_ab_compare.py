"""Tests for A/B comparison mode in AudioProcessor."""

from __future__ import annotations

import numpy as np
import pytest

from src.audio.processor import AudioProcessor


class TestABCompare:
    @pytest.fixture()
    def processor(self):
        proc = AudioProcessor()
        proc.config.enable_separation = False
        proc.config.enable_enhancement = False
        proc.config.enable_spatial = False
        proc.config.enable_depth = False
        return proc

    def test_ab_mode_default_off(self, processor):
        assert processor.ab_mode is False

    def test_ab_mode_toggle(self, processor):
        processor.ab_mode = True
        assert processor.ab_mode is True
        processor.ab_mode = False
        assert processor.ab_mode is False

    def test_ab_mode_produces_output(self, processor):
        processor.ab_mode = True
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = processor.process(audio)
        assert result.shape == (480, 2)
        assert not np.any(np.isnan(result))

    def test_ab_position_starts_at_zero(self, processor):
        assert processor._ab_position == 0.0

    def test_crossfade_rate(self, processor):
        assert processor._ab_crossfade_rate == 0.02

    def test_ab_off_matches_normal(self, processor):
        np.random.seed(42)
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3

        processor.ab_mode = False
        result_normal = processor.process(audio.copy())

        processor2 = AudioProcessor()
        processor2.config.enable_separation = False
        processor2.config.enable_enhancement = False
        processor2.config.enable_spatial = False
        processor2.config.enable_depth = False
        processor2.ab_mode = True
        result_ab = processor2.process(audio.copy())

        # With ab_position=0 (A/wet), output should be very close to normal
        np.testing.assert_allclose(result_normal, result_ab, atol=1e-5)
