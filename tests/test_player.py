"""Tests for audio player module."""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from src.audio.file_io import AudioFileIO
from src.audio.player import AudioPlayer, PlaybackState


class TestPlaybackState:
    def test_defaults(self):
        state = PlaybackState()
        assert state.is_playing is False
        assert state.position_sec == 0.0
        assert state.progress == 0.0

    def test_duration(self):
        state = PlaybackState(total_samples=48000, sample_rate=48000)
        assert state.duration_sec == pytest.approx(1.0)

    def test_progress(self):
        state = PlaybackState(
            position_samples=24000, total_samples=48000, sample_rate=48000
        )
        assert state.progress == pytest.approx(0.5)


class TestAudioPlayer:
    @pytest.fixture()
    def temp_wav(self):
        audio = np.random.randn(48000, 2).astype(np.float32) * 0.3
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.wav")
            AudioFileIO.export_audio(audio, path, sample_rate=48000, bit_depth=16)
            yield path

    def test_load(self, temp_wav):
        player = AudioPlayer()
        ok = player.load(temp_wav)
        assert ok is True
        assert player.state.total_samples == 48000

    def test_load_nonexistent(self):
        player = AudioPlayer()
        ok = player.load("/nonexistent.wav")
        assert ok is False

    def test_play_without_load(self):
        player = AudioPlayer()
        player.play()
        assert player.state.is_playing is False

    def test_seek(self, temp_wav):
        player = AudioPlayer()
        player.load(temp_wav)
        player.seek(0.5)
        assert player.state.position_samples == 24000

    def test_stop_resets_position(self, temp_wav):
        player = AudioPlayer()
        player.load(temp_wav)
        player.seek(0.5)
        player.stop()
        assert player.state.position_samples == 0

    def test_get_current_chunk(self, temp_wav):
        player = AudioPlayer()
        player.load(temp_wav)
        chunk = player.get_current_chunk()
        assert chunk is not None
        assert chunk.shape[0] == player.chunk_size

    def test_pause(self, temp_wav):
        player = AudioPlayer()
        player.load(temp_wav)
        player.play()
        player.pause()
        assert player.state.is_paused is True
        player.stop()
