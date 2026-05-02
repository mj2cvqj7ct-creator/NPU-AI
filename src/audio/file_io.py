"""
Audio File I/O Module.

Provides import/export for WAV and FLAC audio files with
format conversion, metadata extraction, and progress reporting.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.io import wavfile

logger = logging.getLogger(__name__)


@dataclass
class AudioFileInfo:
    path: str
    filename: str
    format: str
    sample_rate: int
    channels: int
    duration_sec: float
    bit_depth: int
    size_bytes: int


class AudioFileIO:
    """Handles import/export of WAV and FLAC audio files."""

    SUPPORTED_IMPORT = (".wav", ".flac")
    SUPPORTED_EXPORT = (".wav", ".flac")

    @staticmethod
    def get_file_info(path: str) -> AudioFileInfo | None:
        """Read metadata from an audio file without loading full data."""
        if not os.path.exists(path):
            logger.error("File not found: %s", path)
            return None

        ext = os.path.splitext(path)[1].lower()
        if ext not in AudioFileIO.SUPPORTED_IMPORT:
            logger.error("Unsupported format: %s", ext)
            return None

        try:
            sr, data = wavfile.read(path)
            channels = 1 if data.ndim == 1 else data.shape[1]
            duration = data.shape[0] / sr
            bit_depth = data.dtype.itemsize * 8
            return AudioFileInfo(
                path=path,
                filename=os.path.basename(path),
                format=ext.lstrip(".").upper(),
                sample_rate=sr,
                channels=channels,
                duration_sec=duration,
                bit_depth=bit_depth,
                size_bytes=os.path.getsize(path),
            )
        except Exception as e:
            logger.error("Failed to read file info: %s", e)
            return None

    @staticmethod
    def import_audio(
        path: str,
        target_sample_rate: int = 48000,
        progress_callback: Callable[[float], None] | None = None,
    ) -> tuple[np.ndarray, int] | None:
        """Import audio file and convert to float32 stereo.

        Returns (audio_data, sample_rate) or None on failure.
        """
        if not os.path.exists(path):
            logger.error("File not found: %s", path)
            return None

        ext = os.path.splitext(path)[1].lower()
        if ext not in AudioFileIO.SUPPORTED_IMPORT:
            logger.error("Unsupported import format: %s", ext)
            return None

        try:
            if progress_callback:
                progress_callback(0.1)

            sr, data = wavfile.read(path)

            if progress_callback:
                progress_callback(0.4)

            # Convert to float32
            if data.dtype == np.int16:
                audio = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                audio = data.astype(np.float32) / 2147483648.0
            elif data.dtype == np.float64:
                audio = data.astype(np.float32)
            else:
                audio = data.astype(np.float32)
                peak = np.max(np.abs(audio))
                if peak > 1.0:
                    audio /= peak

            if progress_callback:
                progress_callback(0.6)

            # Convert mono to stereo
            if audio.ndim == 1:
                audio = np.column_stack([audio, audio])

            # Resample if needed
            if sr != target_sample_rate:
                audio = AudioFileIO._resample(audio, sr, target_sample_rate)
                sr = target_sample_rate

            if progress_callback:
                progress_callback(1.0)

            logger.info(
                "Imported: %s (%dHz, %dch, %.1fs)",
                os.path.basename(path),
                sr,
                audio.shape[1],
                audio.shape[0] / sr,
            )
            return audio, sr

        except Exception as e:
            logger.error("Failed to import audio: %s", e)
            return None

    @staticmethod
    def export_audio(
        audio: np.ndarray,
        path: str,
        sample_rate: int = 48000,
        bit_depth: int = 24,
        progress_callback: Callable[[float], None] | None = None,
    ) -> bool:
        """Export audio data to WAV or FLAC file.

        Returns True on success.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext not in AudioFileIO.SUPPORTED_EXPORT:
            logger.error("Unsupported export format: %s", ext)
            return False

        try:
            if progress_callback:
                progress_callback(0.1)

            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

            # Convert to target bit depth
            if bit_depth == 16:
                data = np.clip(audio * 32768.0, -32768, 32767).astype(np.int16)
            elif bit_depth == 24:
                # scipy wavfile writes int32 for 24-bit; scale to 24-bit range
                data = np.clip(audio * 8388608.0, -8388608, 8388607).astype(np.int32)
            elif bit_depth == 32:
                data = audio.astype(np.float32)
            else:
                data = audio.astype(np.float32)

            if progress_callback:
                progress_callback(0.5)

            wavfile.write(path, sample_rate, data)

            if progress_callback:
                progress_callback(1.0)

            size = os.path.getsize(path)
            logger.info(
                "Exported: %s (%dHz, %d-bit, %.1f MB)",
                os.path.basename(path),
                sample_rate,
                bit_depth,
                size / 1_048_576,
            )
            return True

        except Exception as e:
            logger.error("Failed to export audio: %s", e)
            return False

    @staticmethod
    def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Resample audio using scipy."""
        from scipy.signal import resample

        ratio = target_sr / orig_sr
        new_length = int(audio.shape[0] * ratio)
        resampled = np.zeros((new_length, audio.shape[1]), dtype=np.float32)
        for ch in range(audio.shape[1]):
            resampled[:, ch] = resample(audio[:, ch], new_length).astype(np.float32)
        return resampled
