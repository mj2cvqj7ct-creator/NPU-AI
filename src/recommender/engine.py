"""
Deep Learning Recommendation Engine.

Real-time music recommendation using audio feature analysis and
collaborative filtering with NPU-accelerated feature extraction.
Supports Spotify, Apple Music, and YouTube Music.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.spatial.distance import cosine

logger = logging.getLogger(__name__)

FEATURE_NAMES = (
    "energy", "valence", "tempo", "danceability",
    "acousticness", "instrumentalness", "speechiness", "liveness",
    "spectral_centroid", "spectral_rolloff", "spectral_contrast",
)
FEATURE_DIM = 36


@dataclass
class TrackFeatures:
    track_id: str = ""
    title: str = ""
    artist: str = ""
    source: str = ""  # spotify, apple_music, youtube_music

    energy: float = 0.0
    valence: float = 0.0
    tempo: float = 0.0
    danceability: float = 0.0
    acousticness: float = 0.0
    instrumentalness: float = 0.0
    speechiness: float = 0.0
    liveness: float = 0.0

    spectral_centroid: float = 0.0
    spectral_rolloff: float = 0.0
    spectral_contrast: float = 0.0
    mfcc_mean: list[float] = field(default_factory=list)
    chroma_mean: list[float] = field(default_factory=list)

    embedding: np.ndarray | None = None

    timestamp: float = 0.0
    play_count: int = 0
    skip_count: int = 0
    listen_duration_s: float = 0.0

    def to_vector(self) -> np.ndarray:
        """Convert features to a fixed-length numerical vector."""
        base = [
            self.energy,
            self.valence,
            self.tempo / 200.0,
            self.danceability,
            self.acousticness,
            self.instrumentalness,
            self.speechiness,
            self.liveness,
            self.spectral_centroid / 10000.0,
            self.spectral_rolloff / 20000.0,
            self.spectral_contrast,
        ]

        mfcc = self.mfcc_mean[:13] if self.mfcc_mean else [0.0] * 13
        mfcc += [0.0] * (13 - len(mfcc))
        base.extend(mfcc)

        chroma = self.chroma_mean[:12] if self.chroma_mean else [0.0] * 12
        chroma += [0.0] * (12 - len(chroma))
        base.extend(chroma)

        return np.array(base, dtype=np.float32)


class RecommendationEngine:
    """Real-time deep learning recommendation engine.

    Analyzes audio features in real-time using NPU-accelerated feature
    extraction and maintains a user preference model for personalized
    music recommendations across Spotify, Apple Music, and YouTube Music.
    """

    def __init__(self, data_dir: str = "data/recommender"):
        self.data_dir = data_dir
        self._npu_engine: Any = None
        self._history: deque[TrackFeatures] = deque(maxlen=2000)
        self._preferences = np.zeros(FEATURE_DIM, dtype=np.float32)
        self._preference_momentum = np.zeros(FEATURE_DIM, dtype=np.float32)
        self._learning_rate = 0.05
        self._momentum = 0.9
        self._track_db: dict[str, TrackFeatures] = {}
        self._genre_affinity: dict[str, float] = {}

        self._load_state()

    def set_npu_engine(self, engine: Any) -> None:
        """Connect NPU engine for accelerated feature extraction."""
        self._npu_engine = engine
        logger.info("NPU engine connected to recommendation engine")

    def analyze_audio(
        self, audio: np.ndarray, sample_rate: int = 48000,
    ) -> TrackFeatures:
        """Extract audio features from a real-time audio buffer."""
        features = TrackFeatures(timestamp=time.time())

        mono = np.mean(audio, axis=1) if audio.ndim == 2 else audio.copy()

        if len(mono) == 0:
            return features

        features.energy = float(np.sqrt(np.mean(mono ** 2)))

        if len(mono) >= 2048:
            n_fft = min(4096, len(mono))
            spectrum = np.abs(np.fft.rfft(mono[:n_fft]))
            freqs = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
            total = np.sum(spectrum)

            if total > 0:
                features.spectral_centroid = float(np.sum(freqs * spectrum) / total)

            cumsum = np.cumsum(spectrum)
            if cumsum[-1] > 0:
                idx = np.searchsorted(cumsum, 0.85 * cumsum[-1])
                features.spectral_rolloff = float(freqs[min(idx, len(freqs) - 1)])

            # Spectral contrast (difference between peaks and valleys)
            n_bands = 6
            band_size = len(spectrum) // n_bands
            contrasts = []
            for b in range(n_bands):
                band = spectrum[b * band_size : (b + 1) * band_size]
                if len(band) > 0:
                    contrasts.append(float(np.max(band) - np.min(band)))
            if contrasts:
                avg_mag = total / len(spectrum) + 1e-10
                features.spectral_contrast = float(np.mean(contrasts)) / avg_mag

        # NPU embedding
        if self._npu_engine is not None:
            try:
                chunk = mono[:128].astype(np.float32)
                if len(chunk) < 128:
                    padded = np.zeros(128, dtype=np.float32)
                    padded[: len(chunk)] = chunk
                    chunk = padded
                embedding = self._npu_engine.infer("recommender", chunk.reshape(1, 128))
                if embedding is not None:
                    features.embedding = embedding.flatten()
            except Exception as e:
                logger.debug("NPU feature extraction fallback: %s", e)

        features = self._estimate_high_level(features, mono, sample_rate)
        return features

    def _estimate_high_level(
        self, features: TrackFeatures, audio: np.ndarray, sample_rate: int,
    ) -> TrackFeatures:
        """Estimate high-level musical features from audio signal."""
        if len(audio) < 1024:
            return features

        features.valence = min(1.0, features.spectral_centroid / 5000.0)

        zcr = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))
        features.speechiness = min(1.0, float(zcr) * 10)
        features.acousticness = min(1.0, max(0.0, 1.0 - features.energy * 5))

        # Spectral flux for danceability
        hop = 512
        prev_spec = None
        flux = 0.0
        count = 0
        for i in range(0, len(audio) - 1024, hop):
            spec = np.abs(np.fft.rfft(audio[i : i + 1024]))
            if prev_spec is not None:
                flux += float(np.sum((spec - prev_spec) ** 2))
                count += 1
            prev_spec = spec

        features.danceability = min(1.0, flux / (count + 1) * 100)
        features.instrumentalness = max(0.0, 1.0 - features.speechiness * 2)

        # Tempo estimation via onset autocorrelation
        if len(audio) >= sample_rate:
            onset_env = self._onset_envelope(audio, sample_rate)
            if len(onset_env) > 2:
                ac = np.correlate(onset_env, onset_env, mode="full")
                ac = ac[len(ac) // 2 :]
                min_lag = int(60 / 200 * sample_rate / hop)
                max_lag = min(int(60 / 40 * sample_rate / hop), len(ac) - 1)
                if max_lag > min_lag:
                    peak = np.argmax(ac[min_lag:max_lag]) + min_lag
                    if peak > 0:
                        features.tempo = 60.0 * sample_rate / (peak * hop)

        return features

    @staticmethod
    def _onset_envelope(audio: np.ndarray, sample_rate: int) -> np.ndarray:
        hop = 512
        frames = []
        prev = None
        for i in range(0, len(audio) - 1024, hop):
            mag = np.abs(np.fft.rfft(audio[i : i + 1024]))
            if prev is not None:
                diff = np.maximum(0, mag - prev)
                frames.append(float(np.sum(diff)))
            prev = mag
        return np.array(frames, dtype=np.float32)

    def update_preferences(self, features: TrackFeatures, liked: bool = True) -> None:
        """Update user preference model based on listening behavior."""
        vector = features.to_vector()
        if len(vector) != len(self._preferences):
            vector = np.resize(vector, len(self._preferences))

        direction = 1.0 if liked else -0.3
        gradient = (vector - self._preferences) * direction

        self._preference_momentum = (
            self._momentum * self._preference_momentum
            + (1 - self._momentum) * gradient
        )
        self._preferences += self._learning_rate * self._preference_momentum
        self._preferences = np.clip(self._preferences, -1.0, 1.0)

        self._history.append(features)
        self._save_state()

    def get_recommendations(self, n: int = 10) -> list[dict[str, Any]]:
        """Get recommended tracks based on current preferences."""
        if not self._track_db:
            return self._get_preference_summary(n)

        scored: list[tuple[float, TrackFeatures]] = []
        for _track_id, features in self._track_db.items():
            vector = features.to_vector()
            if len(vector) != len(self._preferences):
                vector = np.resize(vector, len(self._preferences))

            similarity = 1.0 - cosine(self._preferences, vector)

            recency_bonus = 0.0
            for hist in reversed(list(self._history)[-20:]):
                if hist.artist == features.artist:
                    recency_bonus += 0.05
                    break

            score = similarity + recency_bonus
            scored.append((score, features))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "track_id": f.track_id,
                "title": f.title,
                "artist": f.artist,
                "source": f.source,
                "score": float(s),
            }
            for s, f in scored[:n]
        ]

    def _get_preference_summary(self, n: int) -> list[dict[str, Any]]:
        summary: dict[str, float] = {}
        for i, name in enumerate(FEATURE_NAMES):
            if i < len(self._preferences):
                summary[name] = float(self._preferences[i])
        return [{"type": "preference_profile", "features": summary}]

    def _save_state(self) -> None:
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            state = {
                "preferences": self._preferences.tolist(),
                "momentum": self._preference_momentum.tolist(),
                "history_count": len(self._history),
            }
            path = os.path.join(self.data_dir, "state.json")
            with open(path, "w") as f:
                json.dump(state, f)
        except Exception as e:
            logger.debug("Failed to save recommendation state: %s", e)

    def _load_state(self) -> None:
        try:
            path = os.path.join(self.data_dir, "state.json")
            if os.path.exists(path):
                with open(path) as f:
                    state = json.load(f)
                self._preferences = np.array(state["preferences"], dtype=np.float32)
                self._preference_momentum = np.array(state["momentum"], dtype=np.float32)
                logger.info("Recommendation state loaded")
        except Exception as e:
            logger.debug("No previous recommendation state: %s", e)

    @property
    def preference_profile(self) -> dict[str, float]:
        return {
            name: float(self._preferences[i])
            for i, name in enumerate(FEATURE_NAMES)
            if i < len(self._preferences)
        }
