"""Tests for the settings persistence system."""

from __future__ import annotations

import json
import os
import tempfile
from unittest import mock

import pytest

from src.settings import AppSettings, SettingsManager


class TestAppSettings:
    def test_defaults(self):
        s = AppSettings()
        assert s.window_width == 1500
        assert s.window_height == 950
        assert s.last_preset == "Default"
        assert s.master_volume == 1.0
        assert s.minimize_to_tray is True
        assert s.dac_exclusive_mode is True
        assert s.active_tab == 0

    def test_custom(self):
        s = AppSettings(window_width=1920, last_preset="Bass Boost", master_volume=0.8)
        assert s.window_width == 1920
        assert s.last_preset == "Bass Boost"
        assert s.master_volume == 0.8


class TestSettingsManager:
    @pytest.fixture()
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_load_nonexistent(self, temp_dir):
        settings_file = os.path.join(temp_dir, "settings.json")
        with mock.patch("src.settings.SETTINGS_FILE", settings_file):
            mgr = SettingsManager()
        assert mgr.settings.last_preset == "Default"

    def test_save_and_load(self, temp_dir):
        settings_file = os.path.join(temp_dir, "settings.json")
        with mock.patch("src.settings.SETTINGS_FILE", settings_file), \
             mock.patch("src.settings.SETTINGS_DIR", temp_dir):
            mgr = SettingsManager()
            mgr.settings.last_preset = "Vocal Focus"
            mgr.settings.window_width = 1920
            mgr.settings.master_volume = 0.75
            mgr.save()

        assert os.path.exists(settings_file)
        with open(settings_file) as f:
            data = json.load(f)
        assert data["last_preset"] == "Vocal Focus"
        assert data["window_width"] == 1920
        assert data["master_volume"] == 0.75

        # Re-load
        with mock.patch("src.settings.SETTINGS_FILE", settings_file):
            mgr2 = SettingsManager()
        assert mgr2.settings.last_preset == "Vocal Focus"
        assert mgr2.settings.window_width == 1920

    def test_load_partial_data(self, temp_dir):
        settings_file = os.path.join(temp_dir, "settings.json")
        with open(settings_file, "w") as f:
            json.dump({"last_preset": "Live Concert"}, f)

        with mock.patch("src.settings.SETTINGS_FILE", settings_file):
            mgr = SettingsManager()
        assert mgr.settings.last_preset == "Live Concert"
        assert mgr.settings.window_width == 1500  # default

    def test_load_corrupt_json(self, temp_dir):
        settings_file = os.path.join(temp_dir, "settings.json")
        with open(settings_file, "w") as f:
            f.write("{invalid json!!!}")

        with mock.patch("src.settings.SETTINGS_FILE", settings_file):
            mgr = SettingsManager()
        # Should fall back to defaults
        assert mgr.settings.last_preset == "Default"

    def test_unknown_keys_ignored(self, temp_dir):
        settings_file = os.path.join(temp_dir, "settings.json")
        with open(settings_file, "w") as f:
            json.dump({"unknown_key": "value", "last_preset": "Bass Boost"}, f)

        with mock.patch("src.settings.SETTINGS_FILE", settings_file):
            mgr = SettingsManager()
        assert mgr.settings.last_preset == "Bass Boost"
