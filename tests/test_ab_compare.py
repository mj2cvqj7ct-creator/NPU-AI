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

    def test_ab_showing_dry_default(self, processor):
        assert processor.ab_showing_dry is False

    def test_ab_showing_dry_crossfades_toward_dry(self, processor):
        processor.ab_mode = True
        processor.ab_showing_dry = True
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        # Process multiple frames so crossfade advances
        for _ in range(60):
            processor.process(audio.copy())
        # After 60 frames (> 50 needed), position should be ~1.0 (dry)
        assert processor._ab_position > 0.9

    def test_ab_showing_dry_false_crossfades_back(self, processor):
        processor.ab_mode = True
        processor.ab_showing_dry = True
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        for _ in range(60):
            processor.process(audio.copy())
        # Now switch back to processed
        processor.ab_showing_dry = False
        for _ in range(60):
            processor.process(audio.copy())
        assert processor._ab_position < 0.1

    def test_bypass_still_works_without_ab(self, processor):
        processor.bypass = True
        processor.ab_mode = False
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = processor.process(audio)
        np.testing.assert_array_equal(result, audio)

    def test_ab_limiter_state_preserved(self, processor):
        processor.ab_mode = True
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        processor.process(audio.copy())
        state_after_wet = processor._limiter_state
        # Limiter state should reflect the wet signal, not the dry
        processor.process(audio.copy())
        # State should remain consistent (not corrupted by dry path)
        assert abs(processor._limiter_state - state_after_wet) < 0.5
