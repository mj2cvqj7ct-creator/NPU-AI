"""
User Profile Manager.

Manages multiple user profiles with saved presets, settings,
hotkeys, and processing preferences. Enables quick switching
between different use cases (headphone, speaker, studio, etc).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)

PROFILES_DIR = os.path.join(
    os.path.expanduser("~"), ".npu_audio_enhancer", "profiles"
)


@dataclass
class UserProfile:
    """A named user profile."""

    name: str = "Default"
    description: str = ""
    preset_name: str = "Flat / Default"
    master_volume: float = 0.85
    bypass: bool = False
    active_tab: int = 0

    # Enhancement params
    warmth: float = 0.4
    clarity: float = 0.5
    presence: float = 0.4
    air: float = 0.3
    bass_boost: float = 0.3
    stereo_width: float = 0.5

    # Output config
    sample_rate: int = 48000
    bit_depth: int = 24
    buffer_size: int = 480

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> UserProfile:
        valid_fields = {f.name for f in UserProfile.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return UserProfile(**filtered)


class ProfileManager:
    """Manages saving, loading, and switching user profiles."""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}
        self._active_name: str = "Default"
        os.makedirs(PROFILES_DIR, exist_ok=True)
        self._load_all()

    def _load_all(self) -> None:
        """Load all profiles from disk."""
        if not os.path.isdir(PROFILES_DIR):
            return

        for fname in os.listdir(PROFILES_DIR):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(PROFILES_DIR, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                profile = UserProfile.from_dict(data)
                self._profiles[profile.name] = profile
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load profile %s: %s", fname, e)

        # Ensure default exists
        if "Default" not in self._profiles:
            self._profiles["Default"] = UserProfile()

    @property
    def active(self) -> UserProfile:
        if self._active_name not in self._profiles:
            self._active_name = "Default"
        return self._profiles[self._active_name]

    @property
    def active_name(self) -> str:
        return self._active_name

    @property
    def profile_names(self) -> list[str]:
        return sorted(self._profiles.keys())

    def switch(self, name: str) -> bool:
        """Switch to a different profile."""
        if name not in self._profiles:
            logger.warning("Profile not found: %s", name)
            return False
        self._active_name = name
        logger.info("Switched to profile: %s", name)
        return True

    def create(self, name: str, description: str = "") -> UserProfile:
        """Create a new profile (copies from active)."""
        profile = UserProfile.from_dict(self.active.to_dict())
        profile.name = name
        profile.description = description
        self._profiles[name] = profile
        self.save(name)
        logger.info("Created profile: %s", name)
        return profile

    def delete(self, name: str) -> bool:
        """Delete a profile (cannot delete Default)."""
        if name == "Default":
            logger.warning("Cannot delete Default profile")
            return False
        if name not in self._profiles:
            return False

        del self._profiles[name]
        path = os.path.join(PROFILES_DIR, f"{self._safe_filename(name)}.json")
        if os.path.exists(path):
            os.remove(path)

        if self._active_name == name:
            self._active_name = "Default"

        logger.info("Deleted profile: %s", name)
        return True

    def save(self, name: str | None = None) -> None:
        """Save a profile (or active) to disk."""
        if name is None:
            name = self._active_name
        if name not in self._profiles:
            return

        path = os.path.join(PROFILES_DIR, f"{self._safe_filename(name)}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._profiles[name].to_dict(), f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("Failed to save profile %s: %s", name, e)

    def update_active(self, **kwargs: Any) -> None:
        """Update fields on the active profile."""
        profile = self.active
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Convert profile name to safe filename."""
        return name.replace(" ", "_").replace("/", "_").replace("\\", "_")
