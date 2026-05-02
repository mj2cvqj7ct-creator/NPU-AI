"""Tests for the main audio DSP pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from src.audio.processor import AudioProcessor, ProcessorConfig, ProcessorStats


class TestProcessorConfig:
    def test_defaults(self):
        cfg = ProcessorConfig()
        assert cfg.sample_rate == 48000
        assert cfg.channels == 2
        assert cfg.buffer_size == 480
        assert cfg.headroom_db == -1.0

    def test_custom_config(self):
        cfg = ProcessorConfig(sample_rate=44100, buffer_size=256)
        assert cfg.sample_rate == 44100
        assert cfg.buffer_size == 256


class TestProcessorStats:
    def test_defaults(self):
        s = ProcessorStats()
        assert s.processing_time_ms == 0.0
        assert s.peak_level == 0.0
        assert s.lufs == -70.0
        assert s.buffer_underruns == 0


class TestAudioProcessor:
    @pytest.fixture()
    def processor(self):
        return AudioProcessor()

    def test_init(self, processor):
        assert processor.config.sample_rate == 48000
        assert processor.bypass is False
        assert processor.master_gain == 1.0

    def test_bypass_passthrough(self, processor):
        processor.bypass = True
        audio = np.random.randn(480, 2).astype(np.float32)
        result = processor.process(audio)
        np.testing.assert_array_equal(result, audio)

    def test_empty_audio_passthrough(self, processor):
        audio = np.zeros((0, 2), dtype=np.float32)
        result = processor.process(audio)
        assert result.shape[0] == 0

    def test_mono_to_stereo_conversion(self, processor):
        # Disable all effects for simpler testing
        processor.config.enable_separation = False
        processor.config.enable_enhancement = False
        processor.config.enable_spatial = False
        processor.config.enable_depth = False

        mono = np.random.randn(480).astype(np.float32) * 0.1
        result = processor.process(mono)
        assert result.ndim == 2
        assert result.shape[1] == 2

    def test_master_gain_clamp(self, processor):
        processor.master_gain = 3.0
        assert processor.master_gain == 2.0

        processor.master_gain = -1.0
        assert processor.master_gain == 0.0

    def test_process_output_float32(self, processor):
        processor.config.enable_separation = False
        processor.config.enable_enhancement = False
        processor.config.enable_spatial = False
        processor.config.enable_depth = False

        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        result = processor.process(audio)
        assert result.dtype == np.float32

    def test_process_updates_stats(self, processor):
        processor.config.enable_separation = False
        processor.config.enable_enhancement = False
        processor.config.enable_spatial = False
        processor.config.enable_depth = False

        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        processor.process(audio)
        assert processor.stats.processing_time_ms > 0
        assert processor.stats.peak_level > 0
        assert processor.stats.frames_processed > 0

    def test_normalization_clips_loud_input(self, processor):
        processor.config.enable_separation = False
        processor.config.enable_enhancement = False
        processor.config.enable_spatial = False
        processor.config.enable_depth = False

        audio = np.ones((480, 2), dtype=np.float32) * 2.0
        result = processor.process(audio)
        assert np.max(np.abs(result)) <= 1.0

    def test_visualization_data(self, processor):
        audio = np.random.randn(480, 2).astype(np.float32) * 0.3
        viz = processor.get_visualization_data(audio)
        assert "spectrum" in viz
        assert "waveform" in viz
        assert "stem_levels" in viz
        assert len(viz["spectrum"]) > 0
        assert len(viz["waveform"]) > 0

    def test_visualization_empty_audio(self, processor):
        audio = np.zeros((0, 2), dtype=np.float32)
        viz = processor.get_visualization_data(audio)
        assert viz["spectrum"] == []
        assert viz["waveform"] == []

    def test_limiter_prevents_clipping(self, processor):
        processor.config.enable_separation = False
        processor.config.enable_enhancement = False
        processor.config.enable_spatial = False
        processor.config.enable_depth = False
        processor.master_gain = 2.0

        audio = np.ones((480, 2), dtype=np.float32) * 0.8
        result = processor.process(audio)
        headroom = 10 ** (processor.config.headroom_db / 20.0)
        assert np.max(np.abs(result)) <= headroom + 0.01

    def test_properties(self, processor):
        assert processor.separator is not None
        assert processor.enhancer is not None
        assert processor.spatial is not None
        assert processor.depth is not None
