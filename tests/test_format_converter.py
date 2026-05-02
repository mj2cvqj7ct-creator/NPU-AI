"""Tests for multi-format audio converter."""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from src.audio.format_converter import AudioFormat, FormatConverter, FormatOptions


class TestFormatOptions:
    def test_defaults(self):
        opts = FormatOptions()
        assert opts.format == AudioFormat.WAV
        assert opts.bit_depth == 24
        assert opts.extension == ".wav"

    def test_flac_extension(self):
        opts = FormatOptions(format=AudioFormat.FLAC)
        assert opts.extension == ".flac"

    def test_supported_formats(self):
        fmts = FormatOptions.supported_formats()
        assert "WAV" in fmts
        assert "FLAC" in fmts
        assert "OGG" in fmts


class TestFormatConverter:
    @pytest.fixture()
    def sample_audio(self):
        return np.random.randn(48000, 2).astype(np.float32) * 0.3

    def test_export_wav_scipy_fallback(self, sample_audio):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.wav")
            opts = FormatOptions(format=AudioFormat.WAV, bit_depth=16)
            ok = FormatConverter._export_wav_scipy(sample_audio, path, opts)
            assert ok is True
            assert os.path.exists(path)

    def test_export_wav_16bit(self, sample_audio):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test16.wav")
            opts = FormatOptions(format=AudioFormat.WAV, bit_depth=16)
            ok = FormatConverter.export(sample_audio, path, opts)
            assert ok is True

    def test_export_wav_24bit(self, sample_audio):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test24.wav")
            opts = FormatOptions(format=AudioFormat.WAV, bit_depth=24)
            ok = FormatConverter.export(sample_audio, path, opts)
            assert ok is True

    def test_export_with_normalize(self, sample_audio):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "norm.wav")
            opts = FormatOptions(normalize=True)
            ok = FormatConverter.export(sample_audio, path, opts)
            assert ok is True

    def test_get_format_from_path(self):
        assert FormatConverter.get_format_from_path("test.wav") == AudioFormat.WAV
        assert FormatConverter.get_format_from_path("test.flac") == AudioFormat.FLAC
        assert FormatConverter.get_format_from_path("test.ogg") == AudioFormat.OGG
        assert FormatConverter.get_format_from_path("test.xyz") == AudioFormat.WAV
