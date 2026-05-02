"""Tests for user profile manager."""

from __future__ import annotations

import tempfile
from unittest import mock

from src.profiles import ProfileManager, UserProfile


class TestUserProfile:
    def test_defaults(self):
        p = UserProfile()
        assert p.name == "Default"
        assert p.master_volume == 0.85

    def test_to_dict(self):
        p = UserProfile(name="Test", warmth=0.7)
        d = p.to_dict()
        assert d["name"] == "Test"
        assert d["warmth"] == 0.7

    def test_from_dict(self):
        p = UserProfile.from_dict({"name": "Studio", "bass_boost": 0.8})
        assert p.name == "Studio"
        assert p.bass_boost == 0.8

    def test_from_dict_extra_keys(self):
        p = UserProfile.from_dict({"name": "X", "unknown_field": 42})
        assert p.name == "X"


class TestProfileManager:
    def test_default_profile_exists(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("src.profiles.PROFILES_DIR", d):
                mgr = ProfileManager()
                assert "Default" in mgr.profile_names

    def test_create_profile(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("src.profiles.PROFILES_DIR", d):
                mgr = ProfileManager()
                p = mgr.create("Headphone", "For headphone listening")
                assert p.name == "Headphone"
                assert "Headphone" in mgr.profile_names

    def test_switch_profile(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("src.profiles.PROFILES_DIR", d):
                mgr = ProfileManager()
                mgr.create("Studio")
                ok = mgr.switch("Studio")
                assert ok is True
                assert mgr.active_name == "Studio"

    def test_switch_nonexistent(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("src.profiles.PROFILES_DIR", d):
                mgr = ProfileManager()
                ok = mgr.switch("NonExistent")
                assert ok is False

    def test_delete_profile(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("src.profiles.PROFILES_DIR", d):
                mgr = ProfileManager()
                mgr.create("ToDelete")
                ok = mgr.delete("ToDelete")
                assert ok is True
                assert "ToDelete" not in mgr.profile_names

    def test_cannot_delete_default(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("src.profiles.PROFILES_DIR", d):
                mgr = ProfileManager()
                ok = mgr.delete("Default")
                assert ok is False

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("src.profiles.PROFILES_DIR", d):
                mgr = ProfileManager()
                mgr.create("Saved")
                mgr.switch("Saved")
                mgr.update_active(warmth=0.9)
                mgr.save()

                mgr2 = ProfileManager()
                assert "Saved" in mgr2.profile_names

    def test_update_active(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("src.profiles.PROFILES_DIR", d):
                mgr = ProfileManager()
                mgr.update_active(clarity=0.9, bass_boost=0.7)
                assert mgr.active.clarity == 0.9
                assert mgr.active.bass_boost == 0.7
