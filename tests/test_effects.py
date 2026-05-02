"""Tests for audio effect processors."""

from __future__ import annotations

import numpy as np
import pytest

from src.audio.effects.depth import DepthProcessor
from src.audio.effects.enhancer import AudioEnhancer
from src.audio.effects.separator import STEM_NAMES, SeparationConfig, SourceSeparator
from src.audio.effects.spatial import SpatialProcessor


class TestAudioEnhancer:
    @pytest.fixture()
    def enhancer(self):
        return AudioEnhancer(sample_rate=48000)

    def test_init_defaults(self, enhancer):
        assert enhancer.enabled is True
        assert enhancer.transient_shape == 0.0
        assert enhancer.psychoacoustic_bass == 0.3
        assert enhancer.multiband_compression == 0.3

    def test_disabled_passthrough(self, enhancer):
        enhancer.enabled = False
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = enhancer.process(audio)
        np.testing.assert_array_equal(result, audio)

    def test_process_stereo(self, enhancer):
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = enhancer.process(audio)
        assert result.shape == (480, 2)
        assert not np.any(np.isnan(result))

    def test_process_does_not_explode(self, enhancer):
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = enhancer.process(audio)
        assert np.max(np.abs(result)) < 10.0

    def test_transient_shape_extreme_values(self, enhancer):
        enhancer.transient_shape = 1.0
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = enhancer.process(audio)
        assert not np.any(np.isnan(result))

        enhancer.transient_shape = -1.0
        result = enhancer.process(audio)
        assert not np.any(np.isnan(result))
        # Gain should never invert audio (clamped at 0.1)
        assert np.max(np.abs(result)) < 10.0

    def test_update_parameters(self, enhancer):
        enhancer.update_parameters(warmth=0.8, clarity=0.9)
        assert enhancer.warmth == 0.8
        assert enhancer.clarity == 0.9


class TestDepthProcessor:
    @pytest.fixture()
    def depth(self):
        return DepthProcessor(sample_rate=48000)

    def test_init_defaults(self, depth):
        assert depth.enabled is True
        assert depth.damp_lo == 0.3
        assert depth.modulation_depth == 0.3
        assert depth.room_size == 0.4

    def test_disabled_passthrough(self, depth):
        depth.enabled = False
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = depth.process(audio)
        np.testing.assert_array_equal(result, audio)

    def test_process_stereo(self, depth):
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = depth.process(audio)
        assert result.shape == (480, 2)
        assert not np.any(np.isnan(result))

    def test_process_does_not_explode(self, depth):
        audio = np.random.randn(480, 2).astype(np.float32) * 0.1
        result = depth.process(audio)
        assert np.max(np.abs(result)) < 10.0


class TestSpatialProcessor:
    @pytest.fixture()
    def spatial(self):
        return SpatialProcessor(sample_rate=48000)

    def test_init_defaults(self, spatial):
        assert spatial.enabled is True
        assert spatial.diffusion == 0.3

    def test_disabled_passthrough(self, spatial):
        spatial.enabled = False
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = spatial.process(audio)
        np.testing.assert_array_equal(result, audio)

    def test_process_stereo(self, spatial):
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = spatial.process(audio)
        assert result.shape == (480, 2)
        assert not np.any(np.isnan(result))


class TestSourceSeparator:
    @pytest.fixture()
    def separator(self):
        return SourceSeparator(sample_rate=48000)

    def test_init(self, separator):
        assert separator.config.enabled is True
        assert separator.config.num_stems == 4
        assert separator.config.wiener_iterations == 3

    def test_stem_names(self):
        assert STEM_NAMES == ("vocals", "drums", "bass", "other")

    def test_disabled_passthrough(self, separator):
        separator.config.enabled = False
        audio = np.random.randn(4096, 2).astype(np.float32) * 0.3
        result = separator.process(audio)
        np.testing.assert_array_equal(result, audio)

    def test_process_produces_output(self, separator):
        audio = np.random.randn(4096, 2).astype(np.float32) * 0.3
        result = separator.process(audio)
        assert result.shape == audio.shape
        assert not np.any(np.isnan(result))

    def test_stem_levels_updated(self, separator):
        audio = np.random.randn(4096, 2).astype(np.float32) * 0.3
        separator.process(audio)
        for name in STEM_NAMES:
            assert name in separator._stem_levels
            assert separator._stem_levels[name] >= 0.0

    def test_separation_config_custom(self):
        cfg = SeparationConfig(
            vocal_boost=0.8,
            wiener_iterations=5,
            fft_size=2048,
        )
        sep = SourceSeparator(config=cfg)
        assert sep.config.vocal_boost == 0.8
        assert sep.config.wiener_iterations == 5
        assert sep.config.fft_size == 2048

    def test_mono_input(self, separator):
        mono = np.random.randn(4096).astype(np.float32) * 0.3
        result = separator.process(mono)
        assert result.ndim == 2
        assert result.shape[1] == 2
