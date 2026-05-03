"""Tests for XMOSController sounddevice-based detection."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


def test_detect_via_default_output_when_no_keyword_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.dac.xmos_controller import XMOSController

    devices: list[dict[str, Any]] = [
        {
            "name": "Speakers (Realtek(R) Audio)",
            "default_samplerate": 48000.0,
        },
    ]

    fake_sd = ModuleType("sounddevice")
    fake_sd.query_devices = lambda: devices  # noqa: ARG005
    fake_sd.default = SimpleNamespace(device={"input": None, "output": 0})
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)

    c = XMOSController()
    assert c.is_connected
    assert "Realtek" in c.info.name


def test_detect_usb_dac_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.dac.xmos_controller import XMOSController

    devices: list[dict[str, Any]] = [
        {"name": "Speakers", "default_samplerate": 44100.0},
        {"name": "SABAJ A20D USB Audio", "default_samplerate": 48000.0},
    ]

    fake_sd = ModuleType("sounddevice")
    fake_sd.query_devices = lambda: devices  # noqa: ARG005
    fake_sd.default = SimpleNamespace(device={"input": None, "output": 0})
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)

    c = XMOSController()
    assert c.is_connected
    assert "SABAJ" in c.info.name


def test_refresh_detection_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.dac.xmos_controller import XMOSController

    devices: list[dict[str, Any]] = [
        {"name": "Headphones", "default_samplerate": 48000.0},
    ]
    fake_sd = ModuleType("sounddevice")
    fake_sd.query_devices = lambda: devices  # noqa: ARG005
    fake_sd.default = SimpleNamespace(device={"input": None, "output": 0})
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)

    c = XMOSController()
    assert c.is_connected
    c.refresh_detection()
    assert c.is_connected
