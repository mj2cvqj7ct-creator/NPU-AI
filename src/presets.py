"""
Preset Management System.

Provides built-in audio effect presets and user-defined preset
save/load functionality with JSON persistence.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

PRESETS_DIR = os.path.join(os.path.expanduser("~"), ".npu_audio_enhancer", "presets")


@dataclass
class EffectPreset:
    """Complete snapshot of all effect parameters."""

    name: str = "Default"
    description: str = ""

    # Spatial
    spatial_enabled: bool = True
    soundstage_width: float = 0.7
    depth: float = 0.5
    height: float = 0.3
    holographic_intensity: float = 0.6
    crossfeed_level: float = 0.3
    center_focus: float = 0.5
    stereo_enhance: float = 0.4
    immersion: float = 0.5
    diffusion: float = 0.3

    # Separation
    separation_enabled: bool = True
    vocal_boost: float = 0.3
    instrument_clarity: float = 0.5
    bass_enhance: float = 0.2
    drum_punch: float = 0.2
    wiener_iterations: int = 3

    # Enhancer
    enhancer_enabled: bool = True
    warmth: float = 0.3
    clarity: float = 0.5
    presence: float = 0.4
    air: float = 0.3
    bass_boost: float = 0.2
    exciter: float = 0.2
    transient_shape: float = 0.0
    psychoacoustic_bass: float = 0.3
    multiband_compression: float = 0.3
    stereo_width: float = 0.0
    loudness_target: float = -14.0

    # Depth
    depth_enabled: bool = True
    depth_amount: float = 0.5
    room_size: float = 0.4
    damping: float = 0.5
    damp_lo: float = 0.3
    depth_diffusion: float = 0.7
    modulation_depth: float = 0.3
    pre_delay_ms: float = 15.0
    early_reflection_mix: float = 0.3
    late_reverb_mix: float = 0.2


# Built-in presets
BUILTIN_PRESETS: dict[str, EffectPreset] = {
    "Default": EffectPreset(
        name="Default",
        description="Balanced settings for general listening",
    ),
    "Vocal Focus": EffectPreset(
        name="Vocal Focus",
        description="Emphasize vocals with clarity and presence",
        vocal_boost=0.7,
        center_focus=0.8,
        clarity=0.7,
        presence=0.6,
        transient_shape=0.2,
        psychoacoustic_bass=0.1,
        soundstage_width=0.5,
        depth_amount=0.3,
    ),
    "Bass Boost": EffectPreset(
        name="Bass Boost",
        description="Deep bass with psychoacoustic enhancement",
        bass_boost=0.6,
        psychoacoustic_bass=0.7,
        bass_enhance=0.5,
        warmth=0.5,
        depth_amount=0.4,
        multiband_compression=0.4,
        loudness_target=-12.0,
    ),
    "Live Concert": EffectPreset(
        name="Live Concert",
        description="Wide soundstage with reverb for concert feel",
        soundstage_width=0.9,
        holographic_intensity=0.8,
        immersion=0.8,
        diffusion=0.6,
        depth_amount=0.7,
        room_size=0.7,
        early_reflection_mix=0.5,
        late_reverb_mix=0.4,
        pre_delay_ms=25.0,
        modulation_depth=0.5,
        stereo_enhance=0.6,
    ),
    "Studio Monitor": EffectPreset(
        name="Studio Monitor",
        description="Flat, accurate reproduction with minimal processing",
        soundstage_width=0.5,
        holographic_intensity=0.2,
        crossfeed_level=0.4,
        immersion=0.3,
        diffusion=0.1,
        clarity=0.6,
        presence=0.5,
        warmth=0.1,
        exciter=0.05,
        transient_shape=0.0,
        psychoacoustic_bass=0.0,
        multiband_compression=0.1,
        depth_amount=0.2,
        loudness_target=-16.0,
    ),
    "Headphone Immersive": EffectPreset(
        name="Headphone Immersive",
        description="Optimized for headphones with 3D spatial audio",
        soundstage_width=0.8,
        height=0.5,
        holographic_intensity=0.7,
        crossfeed_level=0.5,
        immersion=0.7,
        diffusion=0.5,
        stereo_enhance=0.5,
        depth_amount=0.5,
        room_size=0.5,
        early_reflection_mix=0.4,
        depth_diffusion=0.8,
    ),
    "Electronic / EDM": EffectPreset(
        name="Electronic / EDM",
        description="Punchy bass, crisp highs for electronic music",
        bass_boost=0.5,
        psychoacoustic_bass=0.5,
        drum_punch=0.5,
        transient_shape=0.5,
        multiband_compression=0.5,
        exciter=0.3,
        air=0.4,
        soundstage_width=0.8,
        holographic_intensity=0.5,
        loudness_target=-10.0,
    ),
    "Classical / Orchestra": EffectPreset(
        name="Classical / Orchestra",
        description="Natural room acoustics for classical music",
        soundstage_width=0.9,
        height=0.6,
        holographic_intensity=0.4,
        depth_amount=0.6,
        room_size=0.6,
        damping=0.3,
        early_reflection_mix=0.5,
        late_reverb_mix=0.3,
        pre_delay_ms=20.0,
        warmth=0.4,
        clarity=0.5,
        instrument_clarity=0.7,
        transient_shape=-0.2,
        loudness_target=-18.0,
    ),
}


@dataclass
class PresetManager:
    """Manages built-in and user-defined presets."""

    _user_presets: dict[str, EffectPreset] = field(default_factory=dict)
    _current_preset: str = "Default"

    def __post_init__(self) -> None:
        self._load_user_presets()

    @property
    def current_name(self) -> str:
        return self._current_preset

    @property
    def all_preset_names(self) -> list[str]:
        names = list(BUILTIN_PRESETS.keys())
        for name in self._user_presets:
            if name not in names:
                names.append(name)
        return names

    def get_preset(self, name: str) -> EffectPreset | None:
        if name in self._user_presets:
            return self._user_presets[name]
        return BUILTIN_PRESETS.get(name)

    def apply_preset(self, name: str) -> EffectPreset | None:
        preset = self.get_preset(name)
        if preset:
            self._current_preset = name
        return preset

    def save_preset(self, preset: EffectPreset) -> None:
        self._user_presets[preset.name] = preset
        self._persist_user_presets()
        logger.info("Saved user preset: %s", preset.name)

    def delete_preset(self, name: str) -> bool:
        if name in BUILTIN_PRESETS:
            return False
        if name in self._user_presets:
            del self._user_presets[name]
            self._persist_user_presets()
            return True
        return False

    def is_builtin(self, name: str) -> bool:
        return name in BUILTIN_PRESETS

    def _load_user_presets(self) -> None:
        preset_file = os.path.join(PRESETS_DIR, "user_presets.json")
        if not os.path.exists(preset_file):
            return
        try:
            with open(preset_file, encoding="utf-8") as f:
                data = json.load(f)
            for name, values in data.items():
                self._user_presets[name] = EffectPreset(**values)
            logger.info("Loaded %d user presets", len(self._user_presets))
        except Exception as e:
            logger.warning("Failed to load user presets: %s", e)

    def _persist_user_presets(self) -> None:
        os.makedirs(PRESETS_DIR, exist_ok=True)
        preset_file = os.path.join(PRESETS_DIR, "user_presets.json")
        try:
            data: dict[str, Any] = {}
            for name, preset in self._user_presets.items():
                data[name] = asdict(preset)
            with open(preset_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save user presets: %s", e)
