"""
Application Settings Persistence.

Saves and restores user preferences (window geometry, last preset,
DAC configuration, UI state) across sessions using JSON storage.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)

SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".npu_audio_enhancer")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")


@dataclass
class AppSettings:
    """Persistent application settings."""

    # Window geometry
    window_x: int = 100
    window_y: int = 100
    window_width: int = 1500
    window_height: int = 950
    window_maximized: bool = False

    # Last preset
    last_preset: str = "Default"

    # Audio
    master_volume: float = 1.0
    bypass_enabled: bool = False

    # DAC
    dac_buffer_size_ms: int = 10
    dac_latency_ms: int = 5
    dac_exclusive_mode: bool = True
    dac_filter_mode: int = 0

    # UI state
    active_tab: int = 0
    always_on_top: bool = False
    minimize_to_tray: bool = True

    # Processing toggles
    spatial_enabled: bool = True
    separation_enabled: bool = True
    enhancer_enabled: bool = True
    depth_enabled: bool = True


class SettingsManager:
    """Loads and saves application settings to disk."""

    def __init__(self) -> None:
        self._settings = AppSettings()
        self.load()

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def load(self) -> None:
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            for key, value in data.items():
                if hasattr(self._settings, key):
                    setattr(self._settings, key, value)
            logger.info("Settings loaded from %s", SETTINGS_FILE)
        except Exception as e:
            logger.warning("Failed to load settings: %s", e)

    def save(self) -> None:
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self._settings), f, indent=2)
            logger.debug("Settings saved to %s", SETTINGS_FILE)
        except Exception as e:
            logger.error("Failed to save settings: %s", e)
