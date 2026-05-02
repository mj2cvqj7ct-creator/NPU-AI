"""
Audio Player Module.

Provides offline audio playback with real-time DSP processing.
Loads WAV files via file_io, processes through the audio pipeline,
and streams to output device.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

import numpy as np

from src.audio.file_io import AudioFileIO

if TYPE_CHECKING:
    from src.audio.processor import AudioProcessor

logger = logging.getLogger(__name__)


@dataclass
class PlaybackState:
    """Current playback information."""

    is_playing: bool = False
    is_paused: bool = False
    position_samples: int = 0
    total_samples: int = 0
    sample_rate: int = 48000
    filename: str = ""
    loop: bool = False

    @property
    def position_sec(self) -> float:
        if self.sample_rate == 0:
            return 0.0
        return self.position_samples / self.sample_rate

    @property
    def duration_sec(self) -> float:
        if self.sample_rate == 0:
            return 0.0
        return self.total_samples / self.sample_rate

    @property
    def progress(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.position_samples / self.total_samples


@dataclass
class AudioPlayer:
    """Offline audio file player with DSP processing."""

    processor: AudioProcessor | None = None
    chunk_size: int = 2048
    _audio_data: np.ndarray | None = field(default=None, repr=False)
    _state: PlaybackState = field(default_factory=PlaybackState)
    _thread: threading.Thread | None = field(default=None, repr=False)
    _stop_event: threading.Event = field(
        default_factory=threading.Event, repr=False
    )
    _on_chunk: Callable[[np.ndarray], None] | None = field(
        default=None, repr=False
    )
    _on_position_changed: Callable[[PlaybackState], None] | None = field(
        default=None, repr=False
    )

    @property
    def state(self) -> PlaybackState:
        return self._state

    def load(self, path: str, target_sr: int = 48000) -> bool:
        """Load an audio file for playback."""
        self.stop()
        result = AudioFileIO.import_audio(path, target_sample_rate=target_sr)
        if result is None:
            logger.error("Failed to load: %s", path)
            return False

        audio, sr = result
        self._audio_data = audio
        self._state = PlaybackState(
            total_samples=audio.shape[0],
            sample_rate=sr,
            filename=path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
        )
        logger.info(
            "Loaded: %s (%.1fs, %dHz)",
            self._state.filename,
            self._state.duration_sec,
            sr,
        )
        return True

    def play(self) -> None:
        """Start or resume playback."""
        if self._audio_data is None:
            return
        if self._state.is_paused:
            self._state.is_paused = False
            return
        if self._state.is_playing:
            return

        self._stop_event.clear()
        self._state.is_playing = True
        self._state.is_paused = False
        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        """Pause playback (resume with play())."""
        if self._state.is_playing:
            self._state.is_paused = True

    def stop(self) -> None:
        """Stop playback and reset position."""
        self._stop_event.set()
        self._state.is_playing = False
        self._state.is_paused = False
        self._state.position_samples = 0
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def seek(self, position_ratio: float) -> None:
        """Seek to position (0.0 to 1.0)."""
        if self._audio_data is None:
            return
        pos = int(position_ratio * self._state.total_samples)
        self._state.position_samples = max(0, min(pos, self._state.total_samples))

    def get_current_chunk(self) -> np.ndarray | None:
        """Get the current chunk of audio around playback position."""
        if self._audio_data is None:
            return None
        pos = self._state.position_samples
        end = min(pos + self.chunk_size, self._state.total_samples)
        if pos >= end:
            return None
        return self._audio_data[pos:end].copy()

    def _playback_loop(self) -> None:
        """Main playback thread loop."""
        while not self._stop_event.is_set():
            if self._state.is_paused:
                self._stop_event.wait(0.05)
                continue

            chunk = self.get_current_chunk()
            if chunk is None:
                if self._state.loop:
                    self._state.position_samples = 0
                    continue
                break

            # Apply DSP processing
            if self.processor:
                chunk = self.processor.process(chunk)

            if self._on_chunk:
                self._on_chunk(chunk)

            actual_len = chunk.shape[0]
            self._state.position_samples += actual_len

            if self._on_position_changed:
                self._on_position_changed(self._state)

            # Sleep to approximate real-time playback
            sleep_time = actual_len / self._state.sample_rate
            self._stop_event.wait(sleep_time)

        self._state.is_playing = False
        self._state.is_paused = False
