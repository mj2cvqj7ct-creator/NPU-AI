"""Tests for audio file I/O module."""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from src.audio.file_io import AudioFileIO


class TestAudioFileIO:
    @pytest.fixture()
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture()
    def sample_audio(self):
        np.random.seed(42)
        return np.random.randn(48000, 2).astype(np.float32) * 0.5

    def test_export_wav(self, temp_dir, sample_audio):
        path = os.path.join(temp_dir, "test.wav")
        ok = AudioFileIO.export_audio(sample_audio, path, sample_rate=48000, bit_depth=16)
        assert ok is True
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_import_wav(self, temp_dir, sample_audio):
        path = os.path.join(temp_dir, "test.wav")
        AudioFileIO.export_audio(sample_audio, path, sample_rate=48000, bit_depth=16)

        result = AudioFileIO.import_audio(path, target_sample_rate=48000)
        assert result is not None
        audio, sr = result
        assert sr == 48000
        assert audio.shape[1] == 2
        assert audio.shape[0] == 48000

    def test_import_nonexistent(self):
        result = AudioFileIO.import_audio("/nonexistent/path.wav")
        assert result is None

    def test_import_unsupported_format(self, temp_dir):
        path = os.path.join(temp_dir, "test.mp3")
        with open(path, "w") as f:
            f.write("fake")
        result = AudioFileIO.import_audio(path)
        assert result is None

    def test_export_unsupported_format(self, temp_dir, sample_audio):
        path = os.path.join(temp_dir, "test.ogg")
        ok = AudioFileIO.export_audio(sample_audio, path)
        assert ok is False

    def test_get_file_info(self, temp_dir, sample_audio):
        path = os.path.join(temp_dir, "test.wav")
        AudioFileIO.export_audio(sample_audio, path, sample_rate=48000, bit_depth=16)

        info = AudioFileIO.get_file_info(path)
        assert info is not None
        assert info.sample_rate == 48000
        assert info.channels == 2
        assert info.format == "WAV"
        assert info.duration_sec == pytest.approx(1.0, abs=0.1)

    def test_get_file_info_nonexistent(self):
        info = AudioFileIO.get_file_info("/nonexistent.wav")
        assert info is None

    def test_export_24bit(self, temp_dir, sample_audio):
        path = os.path.join(temp_dir, "test24.wav")
        ok = AudioFileIO.export_audio(sample_audio, path, bit_depth=24)
        assert ok is True
        assert os.path.exists(path)

    def test_export_32bit_float(self, temp_dir, sample_audio):
        path = os.path.join(temp_dir, "test32.wav")
        ok = AudioFileIO.export_audio(sample_audio, path, bit_depth=32)
        assert ok is True

    def test_roundtrip_preserves_length(self, temp_dir, sample_audio):
        path = os.path.join(temp_dir, "roundtrip.wav")
        AudioFileIO.export_audio(sample_audio, path, sample_rate=48000, bit_depth=32)
        result = AudioFileIO.import_audio(path, target_sample_rate=48000)
        assert result is not None
        audio, _ = result
        assert audio.shape[0] == sample_audio.shape[0]

    def test_progress_callback(self, temp_dir, sample_audio):
        path = os.path.join(temp_dir, "progress.wav")
        progress_values = []
        AudioFileIO.export_audio(
            sample_audio, path, progress_callback=lambda p: progress_values.append(p)
        )
        assert len(progress_values) > 0
        assert progress_values[-1] == 1.0
