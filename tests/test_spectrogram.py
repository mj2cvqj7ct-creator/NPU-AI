"""Tests for spectrogram logic (no Qt required)."""

from __future__ import annotations

import numpy as np
import pytest


class TestSpectrogramLogic:
    """Test spectrogram FFT analysis without PyQt6 dependency."""

    def test_fft_magnitude(self):
        """Verify FFT produces expected shape."""
        fft_size = 512
        n_bins = fft_size // 2
        window = np.hanning(fft_size).astype(np.float32)
        signal = np.sin(2 * np.pi * 440 * np.arange(fft_size) / 48000)
        frame = signal * window
        spectrum = np.abs(np.fft.rfft(frame))[:n_bins]
        assert spectrum.shape == (n_bins,)
        assert np.max(spectrum) > 0

    def test_db_conversion(self):
        """Verify linear to dB conversion."""
        spectrum = np.array([1.0, 0.1, 0.01, 0.001])
        db = 20.0 * np.log10(np.maximum(spectrum, 1e-10))
        assert db[0] == pytest.approx(0.0, abs=0.01)
        assert db[1] == pytest.approx(-20.0, abs=0.01)
        assert db[2] == pytest.approx(-40.0, abs=0.01)

    def test_mono_from_stereo(self):
        """Verify stereo to mono conversion."""
        stereo = np.random.randn(1024, 2).astype(np.float32)
        mono = stereo.mean(axis=1)
        assert mono.shape == (1024,)

    def test_colormap_build(self):
        """Test viridis-like colormap generation."""
        anchors = [
            (0.0, (10, 14, 20)),
            (0.5, (30, 155, 138)),
            (1.0, (253, 231, 37)),
        ]
        cmap = []
        for i in range(256):
            t = i / 255.0
            for k in range(len(anchors) - 1):
                t0, c0 = anchors[k]
                t1, c1 = anchors[k + 1]
                if t0 <= t <= t1:
                    f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
                    r = int(c0[0] + (c1[0] - c0[0]) * f)
                    g = int(c0[1] + (c1[1] - c0[1]) * f)
                    b = int(c0[2] + (c1[2] - c0[2]) * f)
                    cmap.append((r, g, b))
                    break

        assert len(cmap) == 256
        assert cmap[0] == (10, 14, 20)
        assert cmap[255] == (253, 231, 37)

    def test_hop_windowing(self):
        """Verify hop-based windowing produces correct frame count."""
        fft_size = 512
        hop = fft_size // 2
        audio_len = 4096
        frame_count = 0
        pos = 0
        while pos + fft_size <= audio_len:
            frame_count += 1
            pos += hop
        expected = (audio_len - fft_size) // hop + 1
        assert frame_count == expected
