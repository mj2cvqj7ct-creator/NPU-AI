"""Tests for audio profiler and genre detection."""

from __future__ import annotations

import numpy as np
import pytest

from src.audio.profiler import AudioProfile, AudioProfiler


class TestAudioProfile:
    def test_defaults(self):
        p = AudioProfile()
        assert p.rms_level == 0.0
        assert p.detected_genre == "Unknown"
        assert p.recommended_preset == "Default"


class TestAudioProfiler:
    @pytest.fixture()
    def profiler(self):
        return AudioProfiler(sample_rate=48000)

    def test_analyze_silence(self, profiler):
        audio = np.zeros((4800, 2), dtype=np.float32)
        profile = profiler.analyze(audio)
        assert profile.rms_level < 1e-8
        assert profile.peak_level < 1e-8

    def test_analyze_sine(self, profiler):
        t = np.linspace(0, 1, 48000, dtype=np.float32)
        sine = np.sin(2 * np.pi * 440 * t) * 0.5
        audio = np.column_stack([sine, sine])
        profile = profiler.analyze(audio)
        assert profile.rms_level > 0.1
        assert profile.peak_level > 0.4
        assert profile.spectral_centroid > 200

    def test_analyze_mono(self, profiler):
        mono = np.random.randn(4800).astype(np.float32) * 0.3
        profile = profiler.analyze(mono)
        assert profile.rms_level > 0.0

    def test_analyze_empty(self, profiler):
        audio = np.zeros((0, 2), dtype=np.float32)
        profile = profiler.analyze(audio)
        assert profile.rms_level == 0.0

    def test_band_ratios_sum_to_one(self, profiler):
        np.random.seed(42)
        audio = np.random.randn(48000, 2).astype(np.float32) * 0.3
        profile = profiler.analyze(audio)
        total = profile.bass_energy_ratio + profile.mid_energy_ratio + profile.high_energy_ratio
        assert total == pytest.approx(1.0, abs=0.01)

    def test_crest_factor(self, profiler):
        np.random.seed(42)
        audio = np.random.randn(48000, 2).astype(np.float32) * 0.3
        profile = profiler.analyze(audio)
        assert profile.crest_factor > 1.0

    def test_genre_detection_bass_heavy(self, profiler):
        # Create bass-heavy signal (low frequency)
        t = np.linspace(0, 1, 48000, dtype=np.float32)
        bass = np.sin(2 * np.pi * 60 * t) * 0.8
        audio = np.column_stack([bass, bass])
        profile = profiler.analyze(audio)
        # Should detect some genre; centroid will be low
        assert profile.spectral_centroid < 1000

    def test_history_accumulates(self, profiler):
        audio = np.random.randn(4800, 2).astype(np.float32) * 0.3
        for _ in range(5):
            profiler.analyze(audio)
        assert len(profiler._history) == 5

    def test_smoothed_profile(self, profiler):
        audio = np.random.randn(4800, 2).astype(np.float32) * 0.3
        for _ in range(5):
            profiler.analyze(audio)
        smoothed = profiler.get_smoothed_profile()
        assert smoothed is not None
        assert smoothed.rms_level > 0.0

    def test_smoothed_empty(self, profiler):
        assert profiler.get_smoothed_profile() is None

    def test_dynamic_range(self, profiler):
        np.random.seed(42)
        audio = np.random.randn(48000, 2).astype(np.float32) * 0.3
        profile = profiler.analyze(audio)
        assert profile.dynamic_range_db >= 0.0

    def test_zero_crossing_rate(self, profiler):
        np.random.seed(42)
        audio = np.random.randn(48000, 2).astype(np.float32) * 0.3
        profile = profiler.analyze(audio)
        assert 0.0 < profile.zero_crossing_rate < 1.0
