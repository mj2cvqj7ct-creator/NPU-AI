"""Tests for hotkey customization module."""

from __future__ import annotations

import os
import tempfile
from unittest import mock

from src.hotkeys import ACTION_LABELS, DEFAULT_HOTKEYS, HotkeyManager


class TestHotkeyManager:
    def test_defaults(self):
        with mock.patch("src.hotkeys.HOTKEY_FILE", "/tmp/hk_test_1.json"):
            mgr = HotkeyManager()
            assert mgr.get("play_pause") == "Space"
            assert mgr.get("bypass") == "B"
            assert mgr.get("help") == "F1"

    def test_set_custom(self):
        with mock.patch("src.hotkeys.HOTKEY_FILE", "/tmp/hk_test_2.json"):
            mgr = HotkeyManager()
            mgr.set("bypass", "Ctrl+B")
            assert mgr.get("bypass") == "Ctrl+B"

    def test_reset_single(self):
        with mock.patch("src.hotkeys.HOTKEY_FILE", "/tmp/hk_test_3.json"):
            mgr = HotkeyManager()
            mgr.set("bypass", "Ctrl+B")
            mgr.reset("bypass")
            assert mgr.get("bypass") == "B"

    def test_reset_all(self):
        with mock.patch("src.hotkeys.HOTKEY_FILE", "/tmp/hk_test_4.json"):
            mgr = HotkeyManager()
            mgr.set("bypass", "X")
            mgr.set("help", "F2")
            mgr.reset_all()
            assert mgr.get("bypass") == "B"
            assert mgr.get("help") == "F1"

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hotkeys.json")
            with mock.patch("src.hotkeys.HOTKEY_FILE", path):
                mgr = HotkeyManager()
                mgr.set("bypass", "Ctrl+B")
                mgr.save()

                mgr2 = HotkeyManager()
                assert mgr2.get("bypass") == "Ctrl+B"

    def test_get_conflicts(self):
        with mock.patch("src.hotkeys.HOTKEY_FILE", "/tmp/hk_test_5.json"):
            mgr = HotkeyManager()
            mgr.set("bypass", "Space")  # Conflict with play_pause
            conflicts = mgr.get_conflicts()
            assert len(conflicts) >= 1
            keys = [c[0] for c in conflicts]
            assert "Space" in keys

    def test_get_label(self):
        assert HotkeyManager.get_label("play_pause") == "再生 / 停止"
        assert HotkeyManager.get_label("unknown") == "unknown"

    def test_get_all(self):
        with mock.patch("src.hotkeys.HOTKEY_FILE", "/tmp/hk_test_6.json"):
            mgr = HotkeyManager()
            all_keys = mgr.get_all()
            assert len(all_keys) == len(DEFAULT_HOTKEYS)

    def test_invalid_action_ignored(self):
        with mock.patch("src.hotkeys.HOTKEY_FILE", "/tmp/hk_test_7.json"):
            mgr = HotkeyManager()
            mgr.set("nonexistent_action", "X")
            assert mgr.get("nonexistent_action") == ""

    def test_action_labels_complete(self):
        for action in DEFAULT_HOTKEYS:
            assert action in ACTION_LABELS
