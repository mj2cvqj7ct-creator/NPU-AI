"""
Main Audio DSP Processing Pipeline.

Orchestrates all audio effects in the correct order for optimal quality:
Source Separation → Enhancement → Spatial → Depth → Output Normalization.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from src.audio.effects.depth import DepthProcessor
from src.audio.effects.enhancer import AudioEnhancer
from src.audio.effects.separator import SourceSeparator
from src.audio.effects.spatial import SpatialProcessor

logger = logging.getLogger(__name__)


@dataclass
class ProcessorStats:
    processing_time_ms: float = 0.0
    peak_level: float = 0.0
    rms_level: float = 0.0
    frames_processed: int = 0
    buffer_underruns: int = 0


@dataclass
class ProcessorConfig:
    sample_rate: int = 48000
    channels: int = 2
    buffer_size: int = 480
    enable_separation: bool = True
    enable_enhancement: bool = True
    enable_spatial: bool = True
    enable_depth: bool = True


class AudioProcessor:
    """Main DSP pipeline orchestrator.

    Processing chain:
    1. Input normalization
    2. Source separation (vocals, drums, bass, instruments)
    3. Per-stem enhancement
    4. Spatial audio & holographic processing
    5. Depth & soundstage
    6. Output normalization & limiting
    """

    def __init__(self, config: ProcessorConfig | None = None):
        self.config = config or ProcessorConfig()
        self._separator = SourceSeparator(self.config.sample_rate)
        self._enhancer = AudioEnhancer(self.config.sample_rate)
        self._spatial = SpatialProcessor(self.config.sample_rate)
        self._depth = DepthProcessor(self.config.sample_rate)
        self._stats = ProcessorStats()
        self._bypass = False
        self._master_gain = 1.0

    @property
    def separator(self) -> SourceSeparator:
        return self._separator

    @property
    def enhancer(self) -> AudioEnhancer:
        return self._enhancer

    @property
    def spatial(self) -> SpatialProcessor:
        return self._spatial

    @property
    def depth(self) -> DepthProcessor:
        return self._depth

    @property
    def stats(self) -> ProcessorStats:
        return self._stats

    @property
    def bypass(self) -> bool:
        return self._bypass

    @bypass.setter
    def bypass(self, value: bool) -> None:
        self._bypass = value

    @property
    def master_gain(self) -> float:
        return self._master_gain

    @master_gain.setter
    def master_gain(self, value: float) -> None:
        self._master_gain = max(0.0, min(2.0, value))

    def set_npu_engine(self, engine: Any) -> None:
        """Connect NPU engine for AI-accelerated processing."""
        self._separator.set_npu_engine(engine)
        logger.info("NPU engine connected to audio processor")

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Process audio through the full DSP chain."""
        if self._bypass or audio.shape[0] == 0:
            return audio

        start_time = time.perf_counter()

        if audio.ndim == 1:
            audio = np.column_stack([audio, audio])

        audio = self._normalize_input(audio)

        if self.config.enable_separation:
            audio = self._separator.process(audio)

        if self.config.enable_enhancement:
            audio = self._enhancer.process(audio)

        if self.config.enable_spatial:
            audio = self._spatial.process(audio)

        if self.config.enable_depth:
            audio = self._depth.process(audio)

        audio = audio * self._master_gain
        audio = self._limit_output(audio)

        elapsed = (time.perf_counter() - start_time) * 1000
        self._update_stats(audio, elapsed)

        return audio.astype(np.float32)

    def _normalize_input(self, audio: np.ndarray) -> np.ndarray:
        """Normalize input to prevent clipping in the processing chain."""
        peak = np.max(np.abs(audio))
        if peak > 0.95:
            audio = audio * (0.95 / peak)
        return audio

    def _limit_output(self, audio: np.ndarray) -> np.ndarray:
        """Apply brick-wall limiter to prevent clipping."""
        threshold = 0.98
        peak = np.max(np.abs(audio))
        if peak > threshold:
            ratio = threshold / peak
            audio = np.tanh(audio * (1.0 / threshold)) * threshold * ratio
        return audio

    def _update_stats(self, audio: np.ndarray, processing_time_ms: float) -> None:
        """Update processing statistics."""
        self._stats.processing_time_ms = processing_time_ms
        self._stats.peak_level = float(np.max(np.abs(audio)))
        self._stats.rms_level = float(np.sqrt(np.mean(audio**2)))
        self._stats.frames_processed += audio.shape[0]

    def get_visualization_data(self, audio: np.ndarray) -> dict:
        """Get data for UI visualization."""
        if audio.shape[0] == 0:
            return {"spectrum": [], "waveform": [], "stem_levels": {}}

        mono = np.mean(audio, axis=1) if audio.ndim == 2 else audio

        n_fft = min(2048, len(mono))
        windowed = mono[:n_fft] * np.hanning(n_fft)
        spectrum = np.abs(np.fft.rfft(windowed))
        spectrum_db = 20 * np.log10(spectrum + 1e-10)

        waveform_decimated = mono[:: max(1, len(mono) // 256)]

        stem_levels = self._separator.get_stem_levels(audio)

        return {
            "spectrum": spectrum_db.tolist(),
            "waveform": waveform_decimated.tolist(),
            "stem_levels": stem_levels,
        }
