"""
AI-Powered Source Separation Module.

Separates audio into individual stems (vocals, drums, bass, other instruments)
using NPU-accelerated neural networks for real-time processing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)


@dataclass
class SeparationConfig:
    enabled: bool = True
    vocal_boost: float = 0.3
    instrument_clarity: float = 0.5
    bass_enhance: float = 0.2
    drum_punch: float = 0.2
    fft_size: int = 4096
    hop_size: int = 1024
    num_stems: int = 4  # vocals, drums, bass, other


class SourceSeparator:
    """Real-time source separation with NPU acceleration.

    Uses spectral masking and NPU-inferred separation masks to isolate
    individual audio sources for independent enhancement.
    """

    def __init__(self, sample_rate: int = 48000, config: SeparationConfig | None = None):
        self.sample_rate = sample_rate
        self.config = config or SeparationConfig()
        self._npu_engine = None
        self._window = signal.windows.hann(self.config.fft_size, sym=False).astype(np.float32)
        self._prev_phase = None
        self._stft_buffer = np.zeros(self.config.fft_size, dtype=np.float32)

        self._band_filters = self._create_band_filters()

    def set_npu_engine(self, engine) -> None:
        """Set the NPU inference engine for AI-based separation."""
        self._npu_engine = engine
        logger.info("NPU engine connected to source separator")

    def _create_band_filters(self) -> dict[str, tuple]:
        """Create bandpass filters for frequency-based stem estimation."""
        nyq = self.sample_rate / 2.0
        filters = {}

        bass_sos = signal.butter(4, 250 / nyq, btype="low", output="sos")
        filters["bass"] = bass_sos

        vocal_low = max(300, 1) / nyq
        vocal_high = min(4000, nyq - 1) / nyq
        vocal_sos = signal.butter(4, [vocal_low, vocal_high], btype="band", output="sos")
        filters["vocals"] = vocal_sos

        drum_low = max(60, 1) / nyq
        drum_high = min(8000, nyq - 1) / nyq
        drum_sos = signal.butter(3, [drum_low, drum_high], btype="band", output="sos")
        filters["drums"] = drum_sos

        other_sos = signal.butter(2, 5000 / nyq, btype="high", output="sos")
        filters["other"] = other_sos

        return filters

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Separate and re-mix audio with per-stem enhancements."""
        if not self.config.enabled or audio.shape[0] == 0:
            return audio

        if audio.ndim == 1:
            audio = np.column_stack([audio, audio])

        if self._npu_engine is not None:
            stems = self._npu_separate(audio)
        else:
            stems = self._spectral_separate(audio)

        return self._remix_stems(stems, audio)

    def _npu_separate(self, audio: np.ndarray) -> dict[str, np.ndarray]:
        """Use NPU-accelerated model for source separation."""
        try:
            mono = np.mean(audio, axis=1)
            stft = np.fft.rfft(
                mono[: self.config.fft_size] * self._window[: len(mono[: self.config.fft_size])]
            )
            magnitude = np.abs(stft)

            input_data = magnitude.reshape(1, 1, -1).astype(np.float32)
            masks = self._npu_engine.infer("source_separation", input_data)

            if masks is not None and len(masks) >= self.config.num_stems:
                stems = {}
                stem_names = ["vocals", "drums", "bass", "other"]
                for i, name in enumerate(stem_names):
                    mask = masks[i] if i < len(masks) else np.ones_like(magnitude)
                    stem_stft = stft * mask.flatten()[: len(stft)]
                    stem_mono = np.fft.irfft(stem_stft, n=len(mono))
                    stems[name] = np.column_stack([stem_mono, stem_mono])
                return stems
        except Exception as e:
            logger.debug("NPU separation fallback: %s", e)

        return self._spectral_separate(audio)

    def _spectral_separate(self, audio: np.ndarray) -> dict[str, np.ndarray]:
        """Spectral-based source separation using frequency band analysis."""
        stems = {}

        for stem_name, sos in self._band_filters.items():
            stem_data = np.zeros_like(audio)
            for ch in range(audio.shape[1]):
                stem_data[:, ch] = signal.sosfilt(sos, audio[:, ch])
            stems[stem_name] = stem_data

        mid = (audio[:, 0] + audio[:, 1]) * 0.5
        side = (audio[:, 0] - audio[:, 1]) * 0.5

        vocal_mid = signal.sosfilt(self._band_filters["vocals"], mid)
        center_energy = np.mean(vocal_mid**2) + 1e-10
        side_energy = np.mean(side**2) + 1e-10
        center_ratio = center_energy / (center_energy + side_energy)

        vocals_enhanced = stems["vocals"] * (0.5 + center_ratio * 0.5)
        stems["vocals"] = vocals_enhanced

        return stems

    def _remix_stems(self, stems: dict[str, np.ndarray], original: np.ndarray) -> np.ndarray:
        """Re-mix separated stems with individual enhancements."""
        target_len = original.shape[0]
        output = np.zeros_like(original)

        stem_gains = {
            "vocals": 1.0 + self.config.vocal_boost,
            "drums": 1.0 + self.config.drum_punch,
            "bass": 1.0 + self.config.bass_enhance,
            "other": 1.0 + self.config.instrument_clarity * 0.5,
        }

        for stem_name, stem_data in stems.items():
            gain = stem_gains.get(stem_name, 1.0)
            if stem_data.shape[0] >= target_len:
                output += stem_data[:target_len] * gain
            else:
                output[: stem_data.shape[0]] += stem_data * gain

        rms_original = np.sqrt(np.mean(original**2)) + 1e-10
        rms_output = np.sqrt(np.mean(output**2)) + 1e-10
        output *= rms_original / rms_output

        return output.astype(np.float32)

    def get_stem_levels(self, audio: np.ndarray) -> dict[str, float]:
        """Get current RMS levels for each stem (for visualization)."""
        if audio.shape[0] == 0:
            return {name: 0.0 for name in ["vocals", "drums", "bass", "other"]}

        stereo = audio if audio.ndim == 2 else np.column_stack([audio, audio])
        stems = self._spectral_separate(stereo)
        levels = {}
        for name, data in stems.items():
            rms = float(np.sqrt(np.mean(data**2)))
            levels[name] = min(1.0, rms * 10)
        return levels
