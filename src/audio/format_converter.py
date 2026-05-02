"""
Multi-Format Audio Converter Module.

Extends audio I/O with support for FLAC, OGG, and additional
WAV sub-formats via soundfile library fallback. Provides
format-specific encoding options.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class AudioFormat(Enum):
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"


@dataclass
class FormatOptions:
    """Encoding options for audio export."""

    format: AudioFormat = AudioFormat.WAV
    bit_depth: int = 24
    sample_rate: int = 48000
    flac_compression: int = 5  # 0-8, higher = smaller
    ogg_quality: float = 0.5  # 0.0-1.0
    normalize: bool = False

    @property
    def extension(self) -> str:
        return f".{self.format.value}"

    @staticmethod
    def supported_formats() -> list[str]:
        return [f.value.upper() for f in AudioFormat]


class FormatConverter:
    """Converts and exports audio to multiple formats."""

    # soundfile subtype mapping
    _SF_SUBTYPES = {
        (AudioFormat.WAV, 16): "PCM_16",
        (AudioFormat.WAV, 24): "PCM_24",
        (AudioFormat.WAV, 32): "FLOAT",
        (AudioFormat.FLAC, 16): "PCM_16",
        (AudioFormat.FLAC, 24): "PCM_24",
        (AudioFormat.OGG, 16): "VORBIS",
        (AudioFormat.OGG, 24): "VORBIS",
    }

    @staticmethod
    def can_use_soundfile() -> bool:
        """Check if soundfile library is available."""
        try:
            import soundfile  # noqa: F401

            return True
        except ImportError:
            return False

    @staticmethod
    def export(
        audio: np.ndarray,
        path: str,
        options: FormatOptions | None = None,
    ) -> bool:
        """Export audio to the specified format.

        Falls back to scipy wavfile for WAV if soundfile unavailable.
        """
        if options is None:
            options = FormatOptions()

        if options.normalize:
            peak = np.max(np.abs(audio))
            if peak > 0:
                audio = audio / peak * 0.99

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        if options.format == AudioFormat.WAV and not FormatConverter.can_use_soundfile():
            return FormatConverter._export_wav_scipy(audio, path, options)

        return FormatConverter._export_soundfile(audio, path, options)

    @staticmethod
    def _export_soundfile(
        audio: np.ndarray, path: str, options: FormatOptions
    ) -> bool:
        """Export using soundfile library."""
        try:
            import soundfile as sf

            fmt = options.format.value.upper()
            subtype = FormatConverter._SF_SUBTYPES.get(
                (options.format, options.bit_depth), "PCM_24"
            )

            sf.write(
                path,
                audio,
                options.sample_rate,
                format=fmt,
                subtype=subtype,
            )
            size = os.path.getsize(path)
            logger.info(
                "Exported %s: %s (%dHz, %s, %.1f MB)",
                options.format.value.upper(),
                os.path.basename(path),
                options.sample_rate,
                subtype,
                size / 1_048_576,
            )
            return True
        except ImportError:
            logger.error("soundfile not installed, cannot export %s", options.format.value)
            return False
        except Exception as e:
            logger.error("Export failed: %s", e)
            return False

    @staticmethod
    def _export_wav_scipy(
        audio: np.ndarray, path: str, options: FormatOptions
    ) -> bool:
        """Fallback WAV export using scipy."""
        try:
            from scipy.io import wavfile

            if options.bit_depth == 16:
                data = np.clip(audio * 32768.0, -32768, 32767).astype(np.int16)
            elif options.bit_depth == 24:
                scaled = audio.astype(np.float64) * 2147483648.0
                data = np.clip(scaled, -2147483648.0, 2147483647.0).astype(np.int32)
            else:
                data = audio.astype(np.float32)

            wavfile.write(path, options.sample_rate, data)
            logger.info("Exported WAV (scipy): %s", os.path.basename(path))
            return True
        except Exception as e:
            logger.error("WAV export failed: %s", e)
            return False

    @staticmethod
    def get_format_from_path(path: str) -> AudioFormat:
        """Determine format from file extension."""
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        for fmt in AudioFormat:
            if fmt.value == ext:
                return fmt
        return AudioFormat.WAV
