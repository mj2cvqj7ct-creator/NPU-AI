"""
Spatial Audio & Holographic Sound Processing.

Implements HRTF-based spatial positioning, cross-feed processing,
and holographic soundstage expansion for immersive 3D audio.
"""

from __future__ import annotations

import numpy as np
from scipy import signal


class SpatialProcessor:
    """HRTF-based spatial audio processor with holographic soundstage."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = True

        self.soundstage_width = 0.7
        self.depth = 0.5
        self.height = 0.3
        self.holographic_intensity = 0.6
        self.crossfeed_level = 0.3

        self._hrtf_filters_l: np.ndarray | None = None
        self._hrtf_filters_r: np.ndarray | None = None
        self._early_reflection_delays: list[int] = []
        self._early_reflection_gains: list[float] = []
        self._late_reverb_filter: np.ndarray | None = None
        self._crossfeed_filter: np.ndarray | None = None
        self._prev_left = np.zeros(512, dtype=np.float32)
        self._prev_right = np.zeros(512, dtype=np.float32)

        self._initialize_filters()

    def _initialize_filters(self) -> None:
        """Generate HRTF approximation filters and spatial processing chains."""
        filter_len = 128
        self._generate_hrtf_filters(filter_len)
        self._generate_early_reflections()
        self._generate_crossfeed_filter()
        self._generate_holographic_filter()

    def _generate_hrtf_filters(self, filter_len: int) -> None:
        """Generate simplified HRTF filters for left and right ears."""
        t = np.arange(filter_len) / self.sample_rate

        itd_samples = int(0.00065 * self.sample_rate * self.soundstage_width)

        left_hrtf = np.zeros(filter_len, dtype=np.float32)
        right_hrtf = np.zeros(filter_len, dtype=np.float32)

        for i in range(filter_len):
            decay = np.exp(-i / (filter_len * 0.3))
            left_hrtf[i] = decay * np.sin(2 * np.pi * 1200 * t[i]) * 0.5
            right_hrtf[i] = decay * np.sin(2 * np.pi * 1100 * t[i]) * 0.5

        left_hrtf[0] = 1.0
        if itd_samples < filter_len:
            right_hrtf[itd_samples] = 1.0

        head_shadow_freq = 1500.0
        sos = signal.butter(2, head_shadow_freq / (self.sample_rate / 2), btype="low", output="sos")
        shadow = signal.sosfilt(sos, np.eye(1, filter_len, 0).flatten())

        contralateral_scale = 0.7 * self.soundstage_width
        self._hrtf_filters_l = left_hrtf + shadow * (1.0 - contralateral_scale) * 0.3
        self._hrtf_filters_r = right_hrtf + shadow * contralateral_scale * 0.3

        self._hrtf_filters_l = self._hrtf_filters_l.astype(np.float32)
        self._hrtf_filters_r = self._hrtf_filters_r.astype(np.float32)

    def _generate_early_reflections(self) -> None:
        """Generate early reflection pattern for room simulation."""
        base_delays_ms = [5.2, 8.7, 12.3, 18.1, 25.6, 33.4, 42.8]
        base_gains = [0.65, 0.52, 0.43, 0.35, 0.28, 0.22, 0.17]

        self._early_reflection_delays = [
            int(d * self.sample_rate / 1000 * (0.5 + self.depth)) for d in base_delays_ms
        ]
        self._early_reflection_gains = [g * self.depth for g in base_gains]

    def _generate_crossfeed_filter(self) -> None:
        """Generate crossfeed filter for natural speaker-like presentation."""
        crossfeed_freq = 700.0
        sos = signal.butter(
            1, crossfeed_freq / (self.sample_rate / 2), btype="low", output="sos"
        )
        impulse = np.zeros(64, dtype=np.float32)
        impulse[0] = 1.0
        self._crossfeed_filter = signal.sosfilt(sos, impulse).astype(np.float32)

    def _generate_holographic_filter(self) -> None:
        """Generate holographic ambience extraction filter."""
        nyq = self.sample_rate / 2.0

        bands = [
            (200, 800, 0.4),
            (800, 3000, 0.6),
            (3000, 8000, 0.8),
            (8000, min(16000, nyq - 1), 0.5),
        ]

        self._holographic_bands = []
        for low, high, gain in bands:
            if low >= nyq or high >= nyq:
                continue
            sos = signal.butter(
                2, [low / nyq, high / nyq], btype="band", output="sos"
            )
            self._holographic_bands.append((sos, gain))

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply full spatial processing chain."""
        if not self.enabled or audio.shape[0] == 0:
            return audio

        if audio.ndim == 1:
            audio = np.column_stack([audio, audio])

        left = audio[:, 0].copy()
        right = audio[:, 1].copy()

        mid = (left + right) * 0.5
        side = (left - right) * 0.5

        side *= 1.0 + self.soundstage_width * 1.5

        left, right = self._apply_crossfeed(left, right)
        left, right = self._apply_hrtf(left, right)
        left, right = self._apply_early_reflections(left, right)
        left, right = self._apply_holographic(left, right, mid, side)

        output = np.column_stack([left, right]).astype(np.float32)
        return self._soft_clip(output)

    def _apply_crossfeed(
        self, left: np.ndarray, right: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Apply crossfeed for natural imaging."""
        if self._crossfeed_filter is None or self.crossfeed_level <= 0:
            return left, right

        cross_l = np.convolve(left, self._crossfeed_filter, mode="same") * self.crossfeed_level
        cross_r = np.convolve(right, self._crossfeed_filter, mode="same") * self.crossfeed_level

        left_out = left * (1.0 - self.crossfeed_level * 0.5) + cross_r
        right_out = right * (1.0 - self.crossfeed_level * 0.5) + cross_l

        return left_out, right_out

    def _apply_hrtf(
        self, left: np.ndarray, right: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Apply HRTF filters for spatial positioning."""
        if self._hrtf_filters_l is None:
            return left, right

        left_out = np.convolve(left, self._hrtf_filters_l, mode="same")
        right_out = np.convolve(right, self._hrtf_filters_r, mode="same")

        blend = 0.3 * self.soundstage_width
        left = left * (1.0 - blend) + left_out * blend
        right = right * (1.0 - blend) + right_out * blend

        return left, right

    def _apply_early_reflections(
        self, left: np.ndarray, right: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Add early reflections for depth perception."""
        if not self._early_reflection_delays:
            return left, right

        n = len(left)
        for delay, gain in zip(self._early_reflection_delays, self._early_reflection_gains):
            if delay >= n:
                continue
            left[delay:] += left[:-delay] if delay > 0 else left
            right[delay:] += right[:-delay] if delay > 0 else right
            left[delay:] *= (1.0 + gain * 0.1)
            right[delay:] *= (1.0 + gain * 0.1)

        return left, right

    def _apply_holographic(
        self,
        left: np.ndarray,
        right: np.ndarray,
        mid: np.ndarray,
        side: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Apply holographic ambience enhancement."""
        if self.holographic_intensity <= 0 or not hasattr(self, "_holographic_bands"):
            return left, right

        ambience_l = np.zeros_like(left)
        ambience_r = np.zeros_like(right)

        for sos, gain in self._holographic_bands:
            band_side = signal.sosfilt(sos, side)
            phase_shift = np.roll(band_side, int(self.sample_rate * 0.002))
            ambience_l += band_side * gain
            ambience_r -= phase_shift * gain

        intensity = self.holographic_intensity * 0.4
        left += ambience_l * intensity
        right += ambience_r * intensity

        return left, right

    @staticmethod
    def _soft_clip(audio: np.ndarray) -> np.ndarray:
        """Apply soft clipping to prevent harsh distortion."""
        return np.tanh(audio * 0.95) / 0.95
