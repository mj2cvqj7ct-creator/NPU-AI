"""
Preset Import/Export Module.

Enables sharing presets between users via JSON files.
Supports single preset and preset pack (multiple presets) export.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from typing import Any

from src.presets import EffectPreset

logger = logging.getLogger(__name__)

PRESET_FILE_EXT = ".npu_preset"
PRESET_PACK_EXT = ".npu_presets"


class PresetIO:
    """Import/export presets to/from JSON files."""

    @staticmethod
    def export_preset(preset: EffectPreset, path: str) -> bool:
        """Export a single preset to a JSON file."""
        try:
            data = {
                "version": "1.0",
                "type": "single",
                "preset": asdict(preset),
            }
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("Exported preset: %s -> %s", preset.name, path)
            return True
        except (OSError, TypeError) as e:
            logger.error("Failed to export preset: %s", e)
            return False

    @staticmethod
    def export_pack(presets: list[EffectPreset], path: str) -> bool:
        """Export multiple presets as a preset pack."""
        try:
            data = {
                "version": "1.0",
                "type": "pack",
                "count": len(presets),
                "presets": [asdict(p) for p in presets],
            }
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("Exported preset pack: %d presets -> %s", len(presets), path)
            return True
        except (OSError, TypeError) as e:
            logger.error("Failed to export preset pack: %s", e)
            return False

    @staticmethod
    def import_presets(path: str) -> list[EffectPreset]:
        """Import presets from a JSON file (single or pack)."""
        if not os.path.exists(path):
            logger.error("Preset file not found: %s", path)
            return []

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read preset file: %s", e)
            return []

        if not isinstance(data, dict):
            logger.error("Invalid preset file format")
            return []

        file_type = data.get("type", "single")
        presets: list[EffectPreset] = []

        if file_type == "pack":
            for item in data.get("presets", []):
                preset = PresetIO._dict_to_preset(item)
                if preset:
                    presets.append(preset)
        else:
            preset = PresetIO._dict_to_preset(data.get("preset", {}))
            if preset:
                presets.append(preset)

        logger.info("Imported %d preset(s) from %s", len(presets), path)
        return presets

    @staticmethod
    def _dict_to_preset(data: dict[str, Any]) -> EffectPreset | None:
        """Convert a dict to an EffectPreset."""
        if not data or "name" not in data:
            return None

        try:
            valid_fields = {f.name for f in EffectPreset.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            return EffectPreset(**filtered)
        except (TypeError, KeyError) as e:
            logger.warning("Invalid preset data: %s", e)
            return None

    @staticmethod
    def validate_file(path: str) -> tuple[bool, str]:
        """Validate a preset file. Returns (valid, message)."""
        if not os.path.exists(path):
            return False, "File not found"

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            return False, "Invalid JSON"
        except OSError as e:
            return False, f"Read error: {e}"

        if not isinstance(data, dict):
            return False, "Not a valid preset file"

        version = data.get("version", "")
        file_type = data.get("type", "")

        if file_type == "pack":
            count = len(data.get("presets", []))
            return True, f"Preset pack v{version}: {count} presets"
        elif file_type == "single":
            name = data.get("preset", {}).get("name", "Unknown")
            return True, f"Single preset v{version}: {name}"

        return False, "Unknown preset file type"
