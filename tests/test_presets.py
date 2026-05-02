"""Tests for the preset management system."""

from __future__ import annotations

import json
import os
import tempfile
from unittest import mock

import pytest

from src.presets import BUILTIN_PRESETS, EffectPreset, PresetManager


class TestEffectPreset:
    def test_default_values(self):
        preset = EffectPreset()
        assert preset.name == "Default"
        assert preset.vocal_boost == 0.3
        assert preset.soundstage_width == 0.7
        assert preset.loudness_target == -14.0
        assert preset.wiener_iterations == 3
        assert preset.transient_shape == 0.0

    def test_custom_values(self):
        preset = EffectPreset(
            name="Test",
            vocal_boost=0.9,
            bass_boost=0.8,
            loudness_target=-10.0,
        )
        assert preset.name == "Test"
        assert preset.vocal_boost == 0.9
        assert preset.bass_boost == 0.8
        assert preset.loudness_target == -10.0
        # Unchanged defaults
        assert preset.soundstage_width == 0.7


class TestBuiltinPresets:
    def test_builtin_presets_exist(self):
        assert len(BUILTIN_PRESETS) == 8

    def test_builtin_preset_names(self):
        expected = {
            "Default", "Vocal Focus", "Bass Boost", "Live Concert",
            "Studio Monitor", "Headphone Immersive", "Electronic / EDM",
            "Classical / Orchestra",
        }
        assert set(BUILTIN_PRESETS.keys()) == expected

    def test_vocal_focus_emphasizes_vocals(self):
        vf = BUILTIN_PRESETS["Vocal Focus"]
        default = BUILTIN_PRESETS["Default"]
        assert vf.vocal_boost > default.vocal_boost
        assert vf.center_focus > default.center_focus

    def test_bass_boost_emphasizes_bass(self):
        bb = BUILTIN_PRESETS["Bass Boost"]
        default = BUILTIN_PRESETS["Default"]
        assert bb.bass_boost > default.bass_boost
        assert bb.psychoacoustic_bass > default.psychoacoustic_bass

    def test_studio_monitor_minimal_processing(self):
        sm = BUILTIN_PRESETS["Studio Monitor"]
        assert sm.holographic_intensity < 0.3
        assert sm.warmth < 0.2
        assert sm.exciter < 0.1

    def test_all_presets_have_valid_ranges(self):
        for name, preset in BUILTIN_PRESETS.items():
            assert -1.0 <= preset.transient_shape <= 1.0, f"{name}: transient_shape"
            assert 0.0 <= preset.vocal_boost <= 1.0, f"{name}: vocal_boost"
            assert -24 <= preset.loudness_target <= -6, f"{name}: loudness_target"
            assert 0.0 <= preset.soundstage_width <= 1.5, f"{name}: soundstage_width"
            assert 1 <= preset.wiener_iterations <= 5, f"{name}: wiener_iterations"


class TestPresetManager:
    @pytest.fixture()
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture()
    def manager(self, temp_dir):
        with mock.patch("src.presets.PRESETS_DIR", temp_dir):
            yield PresetManager()

    def test_all_preset_names_includes_builtins(self, manager):
        names = manager.all_preset_names
        assert "Default" in names
        assert "Vocal Focus" in names
        assert len(names) >= 8

    def test_get_builtin_preset(self, manager):
        preset = manager.get_preset("Default")
        assert preset is not None
        assert preset.name == "Default"

    def test_get_nonexistent_returns_none(self, manager):
        assert manager.get_preset("NonExistent") is None

    def test_apply_preset(self, manager):
        result = manager.apply_preset("Bass Boost")
        assert result is not None
        assert result.name == "Bass Boost"
        assert manager.current_name == "Bass Boost"

    def test_apply_nonexistent_returns_none(self, manager):
        result = manager.apply_preset("FakePreset")
        assert result is None

    def test_save_and_get_user_preset(self, manager, temp_dir):
        custom = EffectPreset(name="My Custom", vocal_boost=0.9, bass_boost=0.1)
        with mock.patch("src.presets.PRESETS_DIR", temp_dir):
            manager.save_preset(custom)

        result = manager.get_preset("My Custom")
        assert result is not None
        assert result.vocal_boost == 0.9
        assert result.bass_boost == 0.1

    def test_save_persists_to_json(self, manager, temp_dir):
        custom = EffectPreset(name="Persisted", warmth=0.8)
        with mock.patch("src.presets.PRESETS_DIR", temp_dir):
            manager.save_preset(custom)

        json_path = os.path.join(temp_dir, "user_presets.json")
        assert os.path.exists(json_path)
        with open(json_path) as f:
            data = json.load(f)
        assert "Persisted" in data
        assert data["Persisted"]["warmth"] == 0.8

    def test_delete_user_preset(self, manager, temp_dir):
        custom = EffectPreset(name="ToDelete")
        with mock.patch("src.presets.PRESETS_DIR", temp_dir):
            manager.save_preset(custom)
            assert manager.get_preset("ToDelete") is not None
            assert manager.delete_preset("ToDelete") is True
            assert manager.get_preset("ToDelete") is None

    def test_cannot_delete_builtin(self, manager):
        assert manager.delete_preset("Default") is False

    def test_is_builtin(self, manager):
        assert manager.is_builtin("Default") is True
        assert manager.is_builtin("Vocal Focus") is True
        assert manager.is_builtin("NonExistent") is False

    def test_user_preset_appears_in_names(self, manager, temp_dir):
        custom = EffectPreset(name="NewPreset")
        with mock.patch("src.presets.PRESETS_DIR", temp_dir):
            manager.save_preset(custom)
        assert "NewPreset" in manager.all_preset_names

    def test_load_user_presets_from_disk(self, temp_dir):
        preset_data = {
            "Saved": {
                "name": "Saved",
                "description": "",
                "spatial_enabled": True,
                "soundstage_width": 0.5,
                "depth": 0.5,
                "height": 0.3,
                "holographic_intensity": 0.6,
                "crossfeed_level": 0.3,
                "center_focus": 0.5,
                "stereo_enhance": 0.4,
                "immersion": 0.5,
                "diffusion": 0.3,
                "separation_enabled": True,
                "vocal_boost": 0.3,
                "instrument_clarity": 0.5,
                "bass_enhance": 0.2,
                "drum_punch": 0.2,
                "wiener_iterations": 3,
                "enhancer_enabled": True,
                "warmth": 0.99,
                "clarity": 0.5,
                "presence": 0.4,
                "air": 0.3,
                "bass_boost": 0.2,
                "exciter": 0.2,
                "transient_shape": 0.0,
                "psychoacoustic_bass": 0.3,
                "multiband_compression": 0.3,
                "stereo_width": 0.0,
                "loudness_target": -14.0,
                "depth_enabled": True,
                "depth_amount": 0.5,
                "room_size": 0.4,
                "damping": 0.5,
                "damp_lo": 0.3,
                "depth_diffusion": 0.7,
                "modulation_depth": 0.3,
                "pre_delay_ms": 15.0,
                "early_reflection_mix": 0.3,
                "late_reverb_mix": 0.2,
            },
        }
        os.makedirs(temp_dir, exist_ok=True)
        with open(os.path.join(temp_dir, "user_presets.json"), "w") as f:
            json.dump(preset_data, f)

        with mock.patch("src.presets.PRESETS_DIR", temp_dir):
            mgr = PresetManager()

        preset = mgr.get_preset("Saved")
        assert preset is not None
        assert preset.warmth == 0.99
