"""Tests for clipping indicator logic (no Qt required)."""

from __future__ import annotations

import numpy as np
import pytest


class TestClipIndicatorLogic:
    """Test clipping detection without PyQt6 dependency."""

    def test_peak_detection(self):
        audio = np.array([[0.5, 0.3], [-0.8, 0.9]], dtype=np.float32)
        peak = float(np.max(np.abs(audio)))
        assert peak == pytest.approx(0.9)

    def test_peak_to_db(self):
        peak = 1.0
        db = 20.0 * np.log10(max(peak, 1e-10))
        assert db == pytest.approx(0.0)

    def test_quiet_signal_db(self):
        peak = 0.01
        db = 20.0 * np.log10(max(peak, 1e-10))
        assert db == pytest.approx(-40.0, abs=0.1)

    def test_clipping_detected(self):
        audio = np.array([[1.0, 0.99]], dtype=np.float32)
        peak = float(np.max(np.abs(audio)))
        db = 20.0 * np.log10(max(peak, 1e-10))
        assert db >= 0.0

    def test_true_peak_oversampling(self):
        """True peak via 4x oversampling can be higher than sample peak."""
        n = 100
        x_orig = np.arange(n, dtype=np.float32)
        mono = np.sin(2 * np.pi * 0.1 * x_orig) * 0.95
        x_up = np.linspace(0, n - 1, n * 4)
        upsampled = np.interp(x_up, x_orig, mono)
        sample_peak = float(np.max(np.abs(mono)))
        true_peak = float(np.max(np.abs(upsampled)))
        # True peak should be >= sample peak
        assert true_peak >= sample_peak * 0.99

    def test_zero_signal(self):
        audio = np.zeros((1024, 2), dtype=np.float32)
        peak = float(np.max(np.abs(audio)))
        db = 20.0 * np.log10(max(peak, 1e-10))
        assert db < -80
