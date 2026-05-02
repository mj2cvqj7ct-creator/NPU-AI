"""Tests for preset import/export module."""

from __future__ import annotations

import os
import tempfile

from src.preset_io import PresetIO
from src.presets import EffectPreset


class TestPresetIO:
    def test_export_single(self):
        preset = EffectPreset(name="Test Preset")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.npu_preset")
            ok = PresetIO.export_preset(preset, path)
            assert ok is True
            assert os.path.exists(path)

    def test_import_single(self):
        preset = EffectPreset(name="Import Test", warmth=0.8)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.npu_preset")
            PresetIO.export_preset(preset, path)
            imported = PresetIO.import_presets(path)
            assert len(imported) == 1
            assert imported[0].name == "Import Test"
            assert imported[0].warmth == 0.8

    def test_export_pack(self):
        presets = [
            EffectPreset(name="A"),
            EffectPreset(name="B"),
            EffectPreset(name="C"),
        ]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pack.npu_presets")
            ok = PresetIO.export_pack(presets, path)
            assert ok is True

    def test_import_pack(self):
        presets = [
            EffectPreset(name="X", bass_boost=0.9),
            EffectPreset(name="Y", clarity=0.7),
        ]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pack.npu_presets")
            PresetIO.export_pack(presets, path)
            imported = PresetIO.import_presets(path)
            assert len(imported) == 2

    def test_import_nonexistent(self):
        result = PresetIO.import_presets("/nonexistent.json")
        assert result == []

    def test_validate_single(self):
        preset = EffectPreset(name="Valid")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "v.npu_preset")
            PresetIO.export_preset(preset, path)
            valid, msg = PresetIO.validate_file(path)
            assert valid is True
            assert "Valid" in msg

    def test_validate_pack(self):
        presets = [EffectPreset(name="P1"), EffectPreset(name="P2")]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "v.npu_presets")
            PresetIO.export_pack(presets, path)
            valid, msg = PresetIO.validate_file(path)
            assert valid is True
            assert "2 presets" in msg

    def test_validate_nonexistent(self):
        valid, msg = PresetIO.validate_file("/no.json")
        assert valid is False

    def test_validate_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w") as f:
                f.write("not json")
            valid, msg = PresetIO.validate_file(path)
            assert valid is False
