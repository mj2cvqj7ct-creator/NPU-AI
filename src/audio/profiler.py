"""
Audio Profile & Genre Detection Module.

Analyzes audio characteristics to auto-detect music genre and
automatically select the best-matching preset for optimal processing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from scipy.signal import welch

logger = logging.getLogger(__name__)


@dataclass
class AudioProfile:
    """Acoustic characteristics extracted from audio."""

    rms_level: float = 0.0
    peak_level: float = 0.0
    dynamic_range_db: float = 0.0
    spectral_centroid: float = 0.0
    spectral_rolloff: float = 0.0
    bass_energy_ratio: float = 0.0
    mid_energy_ratio: float = 0.0
    high_energy_ratio: float = 0.0
    zero_crossing_rate: float = 0.0
    crest_factor: float = 0.0
    detected_genre: str = "Unknown"
    confidence: float = 0.0
    recommended_preset: str = "Default"


# Genre detection thresholds based on spectral and dynamic features
GENRE_RULES: list[tuple[str, str, dict[str, tuple[float, float]]]] = [
    (
        "Electronic/EDM",
        "Electronic/EDM",
        {
            "bass_energy_ratio": (0.35, 1.0),
            "crest_factor": (1.0, 6.0),
            "spectral_centroid": (500, 3000),
        },
    ),
    (
        "Classical/Orchestra",
        "Classical/Orchestra",
        {
            "dynamic_range_db": (15.0, 80.0),
            "crest_factor": (6.0, 30.0),
            "spectral_centroid": (800, 4000),
        },
    ),
    (
        "Vocal/Pop",
        "Vocal Focus",
        {
            "mid_energy_ratio": (0.35, 1.0),
            "spectral_centroid": (1500, 5000),
        },
    ),
    (
        "Bass Heavy",
        "Bass Boost",
        {
            "bass_energy_ratio": (0.40, 1.0),
            "spectral_centroid": (200, 2000),
        },
    ),
    (
        "Live/Concert",
        "Live Concert",
        {
            "dynamic_range_db": (10.0, 25.0),
            "high_energy_ratio": (0.15, 1.0),
            "crest_factor": (4.0, 12.0),
        },
    ),
    (
        "Studio/Reference",
        "Studio Monitor",
        {
            "dynamic_range_db": (8.0, 18.0),
            "crest_factor": (3.0, 8.0),
        },
    ),
]


class AudioProfiler:
    """Analyzes audio to extract profile and recommend optimal preset."""

    SAMPLE_RATE = 48000

    def __init__(self, sample_rate: int = 48000) -> None:
        self.SAMPLE_RATE = sample_rate
        self._history: list[AudioProfile] = []

    def analyze(self, audio: np.ndarray) -> AudioProfile:
        """Analyze audio block and return acoustic profile."""
        if audio.ndim == 2:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio.copy()

        if len(mono) == 0:
            return AudioProfile()

        profile = AudioProfile()

        # Level analysis
        profile.rms_level = float(np.sqrt(np.mean(mono**2)))
        profile.peak_level = float(np.max(np.abs(mono)))

        if profile.rms_level > 1e-10:
            profile.crest_factor = profile.peak_level / profile.rms_level
        else:
            profile.crest_factor = 1.0

        # Dynamic range
        if profile.rms_level > 1e-10 and profile.peak_level > 1e-10:
            rms_db = 20 * np.log10(max(profile.rms_level, 1e-10))
            peak_db = 20 * np.log10(max(profile.peak_level, 1e-10))
            profile.dynamic_range_db = max(0.0, peak_db - rms_db)
        else:
            profile.dynamic_range_db = 0.0

        # Spectral analysis
        nperseg = min(2048, len(mono))
        if nperseg >= 16:
            freqs, psd = welch(mono, fs=self.SAMPLE_RATE, nperseg=nperseg)

            total_power = np.sum(psd) + 1e-20

            # Spectral centroid
            profile.spectral_centroid = float(np.sum(freqs * psd) / total_power)

            # Spectral rolloff (85th percentile)
            cumsum = np.cumsum(psd)
            rolloff_idx = np.searchsorted(cumsum, 0.85 * cumsum[-1])
            profile.spectral_rolloff = float(freqs[min(rolloff_idx, len(freqs) - 1)])

            # Band energy ratios
            bass_mask = freqs < 250
            mid_mask = (freqs >= 250) & (freqs < 4000)
            high_mask = freqs >= 4000

            profile.bass_energy_ratio = float(np.sum(psd[bass_mask]) / total_power)
            profile.mid_energy_ratio = float(np.sum(psd[mid_mask]) / total_power)
            profile.high_energy_ratio = float(np.sum(psd[high_mask]) / total_power)

        # Zero crossing rate
        signs = np.sign(mono)
        sign_changes = np.abs(np.diff(signs))
        profile.zero_crossing_rate = float(np.mean(sign_changes > 0))

        # Genre detection
        self._detect_genre(profile)

        self._history.append(profile)
        if len(self._history) > 100:
            self._history.pop(0)

        return profile

    def _detect_genre(self, profile: AudioProfile) -> None:
        """Rule-based genre detection from audio profile."""
        best_genre = "Unknown"
        best_preset = "Default"
        best_score = 0.0

        for genre_name, preset_name, rules in GENRE_RULES:
            matches = 0
            total = len(rules)

            for feature_name, (low, high) in rules.items():
                value = getattr(profile, feature_name, 0.0)
                if low <= value <= high:
                    matches += 1

            score = matches / total if total > 0 else 0.0
            if score > best_score:
                best_score = score
                best_genre = genre_name
                best_preset = preset_name

        if best_score >= 0.5:
            profile.detected_genre = best_genre
            profile.confidence = best_score
            profile.recommended_preset = best_preset
        else:
            profile.detected_genre = "Unknown"
            profile.confidence = best_score
            profile.recommended_preset = "Default"

    def get_smoothed_profile(self) -> AudioProfile | None:
        """Get averaged profile from recent history."""
        if not self._history:
            return None

        recent = self._history[-10:]
        avg = AudioProfile()
        n = len(recent)
        avg.rms_level = sum(p.rms_level for p in recent) / n
        avg.peak_level = max(p.peak_level for p in recent)
        avg.dynamic_range_db = sum(p.dynamic_range_db for p in recent) / n
        avg.spectral_centroid = sum(p.spectral_centroid for p in recent) / n
        avg.spectral_rolloff = sum(p.spectral_rolloff for p in recent) / n
        avg.bass_energy_ratio = sum(p.bass_energy_ratio for p in recent) / n
        avg.mid_energy_ratio = sum(p.mid_energy_ratio for p in recent) / n
        avg.high_energy_ratio = sum(p.high_energy_ratio for p in recent) / n
        avg.zero_crossing_rate = sum(p.zero_crossing_rate for p in recent) / n
        avg.crest_factor = sum(p.crest_factor for p in recent) / n

        # Genre from most recent
        avg.detected_genre = recent[-1].detected_genre
        avg.confidence = recent[-1].confidence
        avg.recommended_preset = recent[-1].recommended_preset

        return avg
