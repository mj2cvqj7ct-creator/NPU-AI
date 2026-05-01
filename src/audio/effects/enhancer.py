"""
Audio Quality Enhancement Module.

Advanced multi-band dynamics, harmonic exciter, psychoacoustic bass
enhancement, air-band sparkle, and LUFS-aware loudness normalization
for dramatically improved audio quality.
"""

from __future__ import annotations

import numpy as np
from scipy import signal


class AudioEnhancer:
    """Multi-stage audio quality enhancer with psychoacoustic optimization."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = True

        # Enhancement parameters
        self.warmth = 0.3
        self.clarity = 0.5
        self.presence = 0.4
        self.air = 0.3
        self.bass_boost = 0.2
        self.exciter = 0.2
        self.stereo_width = 0.0
        self.loudness_target = -14.0  # LUFS

        self._build_processing_chain()

    def _build_processing_chain(self) -> None:
        self._multiband = self._create_multiband_filters()
        self._harmonic = HarmonicExciter(self.sample_rate, self.exciter)
        self._dynamics = MultibandCompressor(self.sample_rate)
        self._bass_enhancer = PsychoacousticBass(self.sample_rate)

    def _create_multiband_filters(
        self,
    ) -> list[tuple[str, np.ndarray, float]]:
        """Create 6-band parametric EQ."""
        nyq = self.sample_rate / 2.0
        bands: list[tuple[str, np.ndarray, float]] = []

        # Sub-bass (20-60 Hz)
        if 60.0 / nyq < 1.0:
            sos = signal.butter(3, 60.0 / nyq, btype="low", output="sos")
            bands.append(("sub_bass", sos, 1.0 + self.bass_boost * 0.8))

        # Bass (60-250 Hz)
        lo, hi = 60.0 / nyq, min(250.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(3, [lo, hi], btype="band", output="sos")
            bands.append(("bass", sos, 1.0 + self.warmth * 0.6))

        # Low-mid (250-1000 Hz) — slight cut to reduce muddiness
        lo, hi = 250.0 / nyq, min(1000.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(3, [lo, hi], btype="band", output="sos")
            bands.append(("low_mid", sos, 1.0 - 0.05))

        # Mid (1-4 kHz) — clarity
        lo, hi = 1000.0 / nyq, min(4000.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(3, [lo, hi], btype="band", output="sos")
            bands.append(("mid", sos, 1.0 + self.clarity * 0.35))

        # Presence (4-8 kHz)
        lo, hi = 4000.0 / nyq, min(8000.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(3, [lo, hi], btype="band", output="sos")
            bands.append(("presence", sos, 1.0 + self.presence * 0.45))

        # Air (8-16 kHz)
        lo, hi = 8000.0 / nyq, min(16000.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(2, [lo, hi], btype="band", output="sos")
            bands.append(("air", sos, 1.0 + self.air * 0.55))

        return bands

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply full enhancement chain."""
        if not self.enabled or audio.shape[0] == 0:
            return audio

        # 1. Psychoacoustic bass
        if self.bass_boost > 0:
            audio = self._bass_enhancer.process(audio, self.bass_boost)

        # 2. Multi-band EQ
        audio = self._apply_multiband_eq(audio)

        # 3. Harmonic exciter
        audio = self._harmonic.process(audio)

        # 4. Multi-band compression
        audio = self._dynamics.process(audio)

        # 5. Stereo width adjustment
        if self.stereo_width != 0.0 and audio.ndim == 2:
            audio = self._adjust_stereo_width(audio)

        # 6. LUFS normalization
        audio = self._apply_loudness_normalization(audio)

        return audio.astype(np.float32)

    def _apply_multiband_eq(self, audio: np.ndarray) -> np.ndarray:
        output = np.zeros_like(audio, dtype=np.float64)
        for _name, sos, gain in self._multiband:
            if audio.ndim == 2:
                for ch in range(audio.shape[1]):
                    output[:, ch] += signal.sosfilt(sos, audio[:, ch]) * gain
            else:
                output += signal.sosfilt(sos, audio) * gain
        return output.astype(audio.dtype)

    def _adjust_stereo_width(self, audio: np.ndarray) -> np.ndarray:
        mid = (audio[:, 0] + audio[:, 1]) * 0.5
        side = (audio[:, 0] - audio[:, 1]) * 0.5
        width = 1.0 + self.stereo_width
        return np.column_stack([
            mid + side * width,
            mid - side * width,
        ])

    def _apply_loudness_normalization(self, audio: np.ndarray) -> np.ndarray:
        rms = np.sqrt(np.mean(audio ** 2)) + 1e-10
        current_lufs = 20 * np.log10(rms) - 0.691
        gain_db = np.clip(self.loudness_target - current_lufs, -8.0, 8.0)
        return audio * (10 ** (gain_db / 20.0))

    def update_parameters(self, **kwargs: float) -> None:
        changed = False
        for key, value in kwargs.items():
            if hasattr(self, key) and getattr(self, key) != value:
                setattr(self, key, value)
                changed = True
        if changed:
            self._build_processing_chain()


class HarmonicExciter:
    """Tube-style harmonic saturation for warmth and presence."""

    def __init__(self, sample_rate: int = 48000, intensity: float = 0.2):
        self.sample_rate = sample_rate
        self.intensity = intensity
        self.even_ratio = 0.65
        self.odd_ratio = 0.35

    def process(self, audio: np.ndarray) -> np.ndarray:
        if self.intensity <= 0:
            return audio

        # Soft-clip saturation (tube-like)
        x = audio * (1.0 + self.intensity)
        even = np.tanh(x * 1.5) * 0.5  # 2nd harmonic
        odd = (np.tanh(x * 2.5) - np.tanh(x)) * 0.3  # 3rd harmonic

        harmonics = even * self.even_ratio + odd * self.odd_ratio
        return audio + harmonics * self.intensity * 0.5


class PsychoacousticBass:
    """Generate missing fundamental harmonics for perceived bass boost."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        nyq = sample_rate / 2.0
        fc = min(120.0, nyq - 1)
        if fc > 0:
            self._bass_sos = signal.butter(3, fc / nyq, btype="low", output="sos")
        else:
            self._bass_sos = None

    def process(self, audio: np.ndarray, amount: float = 0.2) -> np.ndarray:
        if self._bass_sos is None or amount <= 0:
            return audio

        if audio.ndim == 2:
            bass = np.zeros_like(audio)
            for ch in range(audio.shape[1]):
                bass[:, ch] = signal.sosfilt(self._bass_sos, audio[:, ch])
        else:
            bass = signal.sosfilt(self._bass_sos, audio)

        # Generate 2nd and 3rd harmonics of bass content
        harmonics = np.tanh(bass * 3.0) * 0.4 + np.tanh(bass * 5.0) * 0.2
        return audio + harmonics * amount


class MultibandCompressor:
    """4-band dynamics compressor for consistent loudness across frequency ranges."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.threshold_db = -18.0
        self.ratio = 3.0
        self.attack_ms = 5.0
        self.release_ms = 50.0

        nyq = sample_rate / 2.0
        self._bands: list[tuple[str, np.ndarray | None]] = []

        # Low (< 250 Hz)
        fc = min(250.0, nyq - 1) / nyq
        self._bands.append(("low", signal.butter(3, fc, btype="low", output="sos")))

        # Low-mid (250-1000 Hz)
        lo, hi = 250.0 / nyq, min(1000.0, nyq - 1) / nyq
        if lo < hi:
            self._bands.append(("low_mid", signal.butter(3, [lo, hi], btype="band", output="sos")))

        # High-mid (1000-4000 Hz)
        lo, hi = 1000.0 / nyq, min(4000.0, nyq - 1) / nyq
        if lo < hi:
            self._bands.append(("high_mid", signal.butter(3, [lo, hi], btype="band", output="sos")))

        # High (> 4000 Hz)
        fc = min(4000.0, nyq - 1) / nyq
        self._bands.append(("high", signal.butter(3, fc, btype="high", output="sos")))

        # Envelope followers per band
        self._envelopes = [0.0] * len(self._bands)

        attack_coeff = 1.0 - np.exp(-1.0 / (self.attack_ms * sample_rate / 1000))
        release_coeff = 1.0 - np.exp(-1.0 / (self.release_ms * sample_rate / 1000))
        self._attack = float(attack_coeff)
        self._release = float(release_coeff)

    def process(self, audio: np.ndarray) -> np.ndarray:
        output = np.zeros_like(audio, dtype=np.float64)
        threshold_lin = 10 ** (self.threshold_db / 20.0)

        for i, (_name, sos) in enumerate(self._bands):
            if sos is None:
                continue
            if audio.ndim == 2:
                band = np.zeros_like(audio)
                for ch in range(audio.shape[1]):
                    band[:, ch] = signal.sosfilt(sos, audio[:, ch])
            else:
                band = signal.sosfilt(sos, audio)

            rms = np.sqrt(np.mean(band ** 2)) + 1e-10
            if rms > self._envelopes[i]:
                self._envelopes[i] += (rms - self._envelopes[i]) * self._attack
            else:
                self._envelopes[i] += (rms - self._envelopes[i]) * self._release

            env = self._envelopes[i]
            if env > threshold_lin:
                gain_db = self.threshold_db + (20 * np.log10(env) - self.threshold_db) / self.ratio
                gain = 10 ** (gain_db / 20.0) / env
            else:
                gain = 1.0

            output += band * gain

        return output.astype(audio.dtype)
