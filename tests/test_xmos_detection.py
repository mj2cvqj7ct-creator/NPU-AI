"""Tests for XMOSController sounddevice-based detection (unittest for CI)."""

from __future__ import annotations

import sys
import unittest
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import patch


def _fake_sounddevice(
    devices: list[dict[str, Any]],
    default_output_idx: int,
) -> ModuleType:
    fake_sd = ModuleType("sounddevice")
    fake_sd.query_devices = lambda: devices  # noqa: ARG005
    fake_sd.default = SimpleNamespace(
        device={"input": None, "output": default_output_idx},
    )
    return fake_sd


class TestXmosDetection(unittest.TestCase):
    def test_detect_via_default_output_when_no_keyword_match(self) -> None:
        from src.dac.xmos_controller import XMOSController

        devices: list[dict[str, Any]] = [
            {
                "name": "Speakers (Realtek(R) Audio)",
                "default_samplerate": 48000.0,
            },
        ]
        fake_sd = _fake_sounddevice(devices, 0)
        with patch.dict(sys.modules, {"sounddevice": fake_sd}):
            c = XMOSController()
        self.assertTrue(c.is_connected)
        self.assertIn("Realtek", c.info.name)

    def test_detect_usb_dac_keyword(self) -> None:
        from src.dac.xmos_controller import XMOSController

        devices: list[dict[str, Any]] = [
            {"name": "Speakers", "default_samplerate": 44100.0},
            {"name": "SABAJ A20D USB Audio", "default_samplerate": 48000.0},
        ]
        fake_sd = _fake_sounddevice(devices, 0)
        with patch.dict(sys.modules, {"sounddevice": fake_sd}):
            c = XMOSController()
        self.assertTrue(c.is_connected)
        self.assertIn("SABAJ", c.info.name)

    def test_refresh_detection_runs(self) -> None:
        from src.dac.xmos_controller import XMOSController

        devices: list[dict[str, Any]] = [
            {"name": "Headphones", "default_samplerate": 48000.0},
        ]
        fake_sd = _fake_sounddevice(devices, 0)
        with patch.dict(sys.modules, {"sounddevice": fake_sd}):
            c = XMOSController()
            self.assertTrue(c.is_connected)
            c.refresh_detection()
            self.assertTrue(c.is_connected)


if __name__ == "__main__":
    unittest.main()
