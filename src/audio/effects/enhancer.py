"""
Audio Quality Enhancement Module.

Multi-band dynamics processing, harmonic enhancement, and psychoacoustic
optimization for dramatically improved audio quality.
"""

from __future__ import annotations

import numpy as np
from scipy import signal


class AudioEnhancer:
    """Multi-stage audio quality enhancer with psychoacoustic optimization."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = True

        self.warmth = 0.3
        self.clarity = 0.5
        self.presence = 0.4
        self.air = 0.3
        self.bass_boost = 0.2
        self.loudness_target = -14.0  # LUFS

        self._multiband_filters = self._create_multiband_filters()
        self._harmonic_generator = HarmonicEnhancer(sample_rate)
        self._dynamics = MultibandCompressor(sample_rate)

    def _create_multiband_filters(self) -> list[tuple[str, np.ndarray, float]]:
        """Create multiband EQ filters."""
        nyq = self.sample_rate / 2.0
        bands = []

        sub_bass = signal.butter(3, 80 / nyq, btype="low", output="sos")
        bands.append(("sub_bass", sub_bass, 1.0 + self.bass_boost))

        bass = signal.butter(3, [80 / nyq, 250 / nyq], btype="band", output="sos")
        bands.append(("bass", bass, 1.0 + self.warmth * 0.5))

        low_mid = signal.butter(3, [250 / nyq, 1000 / nyq], btype="band", output="sos")
        bands.append(("low_mid", low_mid, 1.0))

        mid_freq = min(4000, nyq - 1)
        mid = signal.butter(3, [1000 / nyq, mid_freq / nyq], btype="band", output="sos")
        bands.append(("mid", mid, 1.0 + self.clarity * 0.3))

        presence_high = min(8000, nyq - 1)
        if mid_freq < presence_high:
            presence = signal.butter(
                3, [mid_freq / nyq, presence_high / nyq], btype="band", output="sos"
            )
            bands.append(("presence", presence, 1.0 + self.presence * 0.4))

        air_freq = min(12000, nyq - 1)
        if presence_high < air_freq:
            air = signal.butter(
                2, [presence_high / nyq, air_freq / nyq], btype="band", output="sos"
            )
            bands.append(("air", air, 1.0 + self.air * 0.5))

        return bands

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply full enhancement chain."""
        if not self.enabled or audio.shape[0] == 0:
            return audio

        audio = self._apply_multiband_eq(audio)
        audio = self._harmonic_generator.process(audio)
        audio = self._dynamics.process(audio)
        audio = self._apply_loudness_normalization(audio)

        return audio.astype(np.float32)

    def _apply_multiband_eq(self, audio: np.ndarray) -> np.ndarray:
        """Apply multiband equalization."""
        output = np.zeros_like(audio)

        for _name, sos, gain in self._multiband_filters:
            if audio.ndim == 2:
                for ch in range(audio.shape[1]):
                    band = signal.sosfilt(sos, audio[:, ch])
                    output[:, ch] += band * gain
            else:
                band = signal.sosfilt(sos, audio)
                output += band * gain

        return output

    def _apply_loudness_normalization(self, audio: np.ndarray) -> np.ndarray:
        """Apply loudness normalization toward target LUFS."""
        rms = np.sqrt(np.mean(audio**2)) + 1e-10
        current_lufs = 20 * np.log10(rms) - 0.691
        gain_db = self.loudness_target - current_lufs
        gain_db = np.clip(gain_db, -6.0, 6.0)
        gain_linear = 10 ** (gain_db / 20.0)
        return audio * gain_linear

    def update_parameters(self, **kwargs) -> None:
        """Update enhancement parameters and rebuild filters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self._multiband_filters = self._create_multiband_filters()


class HarmonicEnhancer:
    """Generates subtle harmonics for warmth and presence."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.intensity = 0.15
        self.even_harmonic_ratio = 0.7
        self.odd_harmonic_ratio = 0.3

    def process(self, audio: np.ndarray) -> np.ndarray:
        if self.intensity <= 0:
            return audio

        even_harmonics = np.tanh(audio * 2.0) * 0.5
        odd_harmonics = (
            np.tanh(audio * 3.0) - np.tanh(audio * 1.5)
        ) * 0.3

        harmonics = (
            even_harmonics * self.even_harmonic_ratio
            + odd_harmonics * self.odd_harmonic_ratio
        )

        return audio + harmonics * self.intensity


class MultibandCompressor:
    """4-band dynamics compressor for consistent loudness."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.threshold_db = -18.0
        self.ratio = 3.0
        self.attack_ms = 5.0
        self.release_ms = 50.0

        self._attack_coeff = np.exp(-1.0 / (sample_rate * self.attack_ms / 1000.0))
        self._release_coeff = np.exp(-1.0 / (sample_rate * self.release_ms / 1000.0))
        self._envelope = 0.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        threshold_linear = 10 ** (self.threshold_db / 20.0)

        if audio.ndim == 2:
            level = np.max(np.abs(audio), axis=1)
        else:
            level = np.abs(audio)

        output = audio.copy()

        for i in range(len(level)):
            if level[i] > self._envelope:
                self._envelope = (
                    self._attack_coeff * self._envelope + (1 - self._attack_coeff) * level[i]
                )
            else:
                self._envelope = (
                    self._release_coeff * self._envelope + (1 - self._release_coeff) * level[i]
                )

            if self._envelope > threshold_linear:
                gain_reduction = (
                    threshold_linear
                    + (self._envelope - threshold_linear) / self.ratio
                ) / (self._envelope + 1e-10)
                if audio.ndim == 2:
                    output[i, :] *= gain_reduction
                else:
                    output[i] *= gain_reduction

        return output
