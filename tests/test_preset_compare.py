"""Tests for preset comparison module."""

from __future__ import annotations

import pytest

from src.preset_compare import PresetComparer, PresetCompareState
from src.presets import EffectPreset


class TestPresetCompareState:
    def test_defaults(self):
        state = PresetCompareState()
        assert state.enabled is False
        assert state.showing_b is False
        assert state.crossfade_position == 0.0

    def test_not_transitioning_at_target(self):
        state = PresetCompareState(showing_b=False, crossfade_position=0.0)
        assert state.is_transitioning is False

    def test_transitioning(self):
        state = PresetCompareState(showing_b=True, crossfade_position=0.3)
        assert state.is_transitioning is True


class TestPresetComparer:
    @pytest.fixture()
    def comparer(self):
        c = PresetComparer()
        a = EffectPreset(name="Preset A")
        b = EffectPreset(name="Preset B")
        c.set_presets(a, b)
        return c

    def test_set_presets(self, comparer):
        assert comparer.state.preset_a_name == "Preset A"
        assert comparer.state.preset_b_name == "Preset B"

    def test_enable_disable(self, comparer):
        comparer.enable()
        assert comparer.state.enabled is True
        comparer.disable()
        assert comparer.state.enabled is False

    def test_toggle(self, comparer):
        comparer.enable()
        assert comparer.state.showing_b is False
        comparer.toggle()
        assert comparer.state.showing_b is True
        comparer.toggle()
        assert comparer.state.showing_b is False

    def test_advance_crossfade(self, comparer):
        comparer.enable()
        comparer.toggle()  # target = 1.0
        for _ in range(100):
            comparer.advance_crossfade()
        assert comparer.state.crossfade_position == pytest.approx(1.0, abs=0.01)

    def test_mix_weights(self, comparer):
        comparer.enable()
        w_a, w_b = comparer.get_mix_weights()
        assert w_a == pytest.approx(1.0)
        assert w_b == pytest.approx(0.0)

    def test_active_preset(self, comparer):
        comparer.enable()
        p = comparer.get_active_preset()
        assert p is not None
        assert p.name == "Preset A"

    def test_crossfade_disabled(self, comparer):
        pos = comparer.advance_crossfade()
        assert pos == 0.0
