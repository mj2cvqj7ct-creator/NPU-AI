"""
Preset Comparison Module.

Enables comparing two presets side-by-side with smooth
crossfade switching for A/B preset evaluation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.presets import EffectPreset

logger = logging.getLogger(__name__)


@dataclass
class PresetCompareState:
    """State of preset comparison mode."""

    enabled: bool = False
    preset_a_name: str = ""
    preset_b_name: str = ""
    showing_b: bool = False
    crossfade_position: float = 0.0
    crossfade_rate: float = 0.02

    @property
    def is_transitioning(self) -> bool:
        target = 1.0 if self.showing_b else 0.0
        return abs(self.crossfade_position - target) > 1e-4


class PresetComparer:
    """Manages comparing two presets in real-time."""

    def __init__(self) -> None:
        self._state = PresetCompareState()
        self._preset_a: EffectPreset | None = None
        self._preset_b: EffectPreset | None = None

    @property
    def state(self) -> PresetCompareState:
        return self._state

    def set_presets(
        self, preset_a: EffectPreset, preset_b: EffectPreset
    ) -> None:
        """Set the two presets to compare."""
        self._preset_a = preset_a
        self._preset_b = preset_b
        self._state.preset_a_name = preset_a.name
        self._state.preset_b_name = preset_b.name
        self._state.crossfade_position = 0.0
        self._state.showing_b = False
        logger.info(
            "Compare mode: %s vs %s", preset_a.name, preset_b.name
        )

    def enable(self) -> None:
        self._state.enabled = True

    def disable(self) -> None:
        self._state.enabled = False
        self._state.crossfade_position = 0.0
        self._state.showing_b = False

    def toggle(self) -> None:
        """Switch which preset is active."""
        self._state.showing_b = not self._state.showing_b

    def get_active_preset(self) -> EffectPreset | None:
        """Return the currently dominant preset."""
        if not self._state.enabled:
            return self._preset_a
        if self._state.crossfade_position > 0.5:
            return self._preset_b
        return self._preset_a

    def advance_crossfade(self) -> float:
        """Advance crossfade position toward target. Returns current position."""
        if not self._state.enabled:
            return 0.0

        target = 1.0 if self._state.showing_b else 0.0
        pos = self._state.crossfade_position

        if abs(pos - target) < 1e-4:
            self._state.crossfade_position = target
            return target

        rate = self._state.crossfade_rate
        if pos < target:
            self._state.crossfade_position = min(target, pos + rate)
        else:
            self._state.crossfade_position = max(target, pos - rate)

        return self._state.crossfade_position

    def get_mix_weights(self) -> tuple[float, float]:
        """Return (weight_a, weight_b) for blending."""
        pos = self._state.crossfade_position
        return (1.0 - pos, pos)
