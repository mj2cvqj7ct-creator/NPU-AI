"""
Hotkey Customization Module.

Allows users to define and persist custom keyboard shortcuts.
Stores mappings in settings JSON alongside other user preferences.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

HOTKEY_FILE = os.path.join(
    os.path.expanduser("~"), ".npu_audio_enhancer", "hotkeys.json"
)

# Default hotkey mappings: action -> key sequence
DEFAULT_HOTKEYS: dict[str, str] = {
    "play_pause": "Space",
    "bypass": "B",
    "ab_compare": "A",
    "import_file": "Ctrl+O",
    "export_file": "Ctrl+E",
    "save_preset": "Ctrl+S",
    "tab_1": "Ctrl+1",
    "tab_2": "Ctrl+2",
    "tab_3": "Ctrl+3",
    "tab_4": "Ctrl+4",
    "tab_5": "Ctrl+5",
    "volume_up": "Ctrl+Up",
    "volume_down": "Ctrl+Down",
    "help": "F1",
    "preset_compare": "Ctrl+Shift+A",
}

# Human-readable labels for each action
ACTION_LABELS: dict[str, str] = {
    "play_pause": "再生 / 停止",
    "bypass": "バイパス",
    "ab_compare": "A/B 比較",
    "import_file": "ファイルインポート",
    "export_file": "ファイルエクスポート",
    "save_preset": "プリセット保存",
    "tab_1": "タブ 1 (Effects)",
    "tab_2": "タブ 2 (DAC)",
    "tab_3": "タブ 3 (Recommend)",
    "tab_4": "タブ 4 (Stats)",
    "tab_5": "タブ 5 (Debug)",
    "volume_up": "音量アップ",
    "volume_down": "音量ダウン",
    "help": "ヘルプ / ガイド",
    "preset_compare": "プリセット比較",
}


@dataclass
class HotkeyManager:
    """Manages user-customizable keyboard shortcuts."""

    _mappings: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._mappings = dict(DEFAULT_HOTKEYS)
        self._load()

    def _load(self) -> None:
        if not os.path.exists(HOTKEY_FILE):
            return
        try:
            with open(HOTKEY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for action, key in data.items():
                    if action in DEFAULT_HOTKEYS and isinstance(key, str):
                        self._mappings[action] = key
                logger.info("Loaded custom hotkeys from %s", HOTKEY_FILE)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load hotkeys: %s", e)

    def save(self) -> None:
        """Persist custom hotkeys to disk."""
        os.makedirs(os.path.dirname(HOTKEY_FILE), exist_ok=True)
        # Only save non-default mappings
        custom = {
            k: v
            for k, v in self._mappings.items()
            if v != DEFAULT_HOTKEYS.get(k)
        }
        try:
            with open(HOTKEY_FILE, "w", encoding="utf-8") as f:
                json.dump(custom, f, indent=2)
        except OSError as e:
            logger.error("Failed to save hotkeys: %s", e)

    def get(self, action: str) -> str:
        """Get the key sequence for an action."""
        return self._mappings.get(action, "")

    def set(self, action: str, key_sequence: str) -> None:
        """Set a custom key sequence for an action."""
        if action in DEFAULT_HOTKEYS:
            self._mappings[action] = key_sequence

    def reset(self, action: str) -> None:
        """Reset an action to its default hotkey."""
        if action in DEFAULT_HOTKEYS:
            self._mappings[action] = DEFAULT_HOTKEYS[action]

    def reset_all(self) -> None:
        """Reset all hotkeys to defaults."""
        self._mappings = dict(DEFAULT_HOTKEYS)

    def get_all(self) -> dict[str, str]:
        """Return all current mappings."""
        return dict(self._mappings)

    def get_conflicts(self) -> list[tuple[str, str, str]]:
        """Find hotkey conflicts. Returns list of (key, action1, action2)."""
        conflicts: list[tuple[str, str, str]] = []
        seen: dict[str, str] = {}
        for action, key in self._mappings.items():
            if key in seen:
                conflicts.append((key, seen[key], action))
            else:
                seen[key] = action
        return conflicts

    @staticmethod
    def get_label(action: str) -> str:
        """Get human-readable label for an action."""
        return ACTION_LABELS.get(action, action)
