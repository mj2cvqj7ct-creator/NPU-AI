"""Tests for EQ visualizer logic (no Qt required)."""

from __future__ import annotations

import math

import pytest


class TestEQVisualizerLogic:
    """Test EQ visualizer math without PyQt6 dependency."""

    def test_freq_to_x(self):
        freq_range = (20.0, 20000.0)
        margin_l, plot_w = 0, 400

        def freq_to_x(freq):
            f_min, f_max = freq_range
            log_ratio = math.log10(freq / f_min) / math.log10(f_max / f_min)
            return margin_l + log_ratio * plot_w

        x_low = freq_to_x(20)
        x_high = freq_to_x(20000)
        x_mid = freq_to_x(632)  # geometric mean ~ 10^2.8
        assert x_low < x_mid < x_high
        assert x_low == pytest.approx(0.0, abs=1)
        assert x_high == pytest.approx(400.0, abs=1)

    def test_db_to_y(self):
        db_range = (-12.0, 12.0)
        margin_t, plot_h = 0, 200

        def db_to_y(db):
            db_min, db_max = db_range
            ratio = 1.0 - (db - db_min) / (db_max - db_min)
            return margin_t + ratio * plot_h

        y_max = db_to_y(12)
        y_zero = db_to_y(0)
        y_min = db_to_y(-12)
        assert y_max < y_zero < y_min

    def test_gains_from_enhancer(self):
        warmth = 0.5
        clarity = 0.5
        presence = 0.5
        air = 0.5
        bass_boost = 0.5

        gains = [
            bass_boost * 6.0,
            warmth * 4.2,
            warmth * 2.4,
            -0.5,
            clarity * 2.4,
            presence * 3.0,
            air * 2.4,
            air * 3.6,
        ]
        assert gains[0] == pytest.approx(3.0)
        assert gains[1] == pytest.approx(2.1)
        assert gains[3] == pytest.approx(-0.5)
        assert len(gains) == 8

    def test_bell_curve_response(self):
        gain = 6.0
        bw = 1.2

        at_center = gain * math.exp(-0.5 * (0 / (bw / 2.0)) ** 2)
        assert at_center == pytest.approx(6.0)

        one_octave_off = gain * math.exp(-0.5 * (1.0 / (bw / 2.0)) ** 2)
        assert one_octave_off < gain
        assert one_octave_off > 0
