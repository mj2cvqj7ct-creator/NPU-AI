"""
Deep Learning Recommendation Engine.

Real-time music recommendation using audio feature analysis and
collaborative filtering with NPU-accelerated feature extraction.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field

import numpy as np
from scipy.spatial.distance import cosine

logger = logging.getLogger(__name__)


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
        """Convert features to a numerical vector for similarity computation."""
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

        if self.mfcc_mean:
            base.extend(self.mfcc_mean[:13])
        else:
            base.extend([0.0] * 13)

        if self.chroma_mean:
            base.extend(self.chroma_mean[:12])
        else:
            base.extend([0.0] * 12)

        return np.array(base, dtype=np.float32)


class RecommendationEngine:
    """Real-time deep learning recommendation engine.

    Analyzes audio features in real-time using NPU-accelerated feature
    extraction and maintains a user preference model for personalized
    music recommendations across Spotify, Apple Music, and YouTube Music.
    """

    def __init__(self, data_dir: str = "data/recommender"):
        self.data_dir = data_dir
        self._npu_engine = None
        self._history: deque[TrackFeatures] = deque(maxlen=1000)
        self._preferences = np.zeros(36, dtype=np.float32)
        self._preference_momentum = np.zeros(36, dtype=np.float32)
        self._learning_rate = 0.05
        self._momentum = 0.9
        self._track_db: dict[str, TrackFeatures] = {}

        self._load_state()

    def set_npu_engine(self, engine) -> None:
        """Connect NPU engine for accelerated feature extraction."""
        self._npu_engine = engine
        logger.info("NPU engine connected to recommendation engine")

    def analyze_audio(self, audio: np.ndarray, sample_rate: int = 48000) -> TrackFeatures:
        """Extract audio features from a real-time audio buffer."""
        features = TrackFeatures(timestamp=time.time())

        if audio.ndim == 2:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio

        if len(mono) == 0:
            return features

        features.energy = float(np.sqrt(np.mean(mono**2)))

        if len(mono) >= 2048:
            spectrum = np.abs(np.fft.rfft(mono[:4096]))
            freqs = np.fft.rfftfreq(min(4096, len(mono)), 1.0 / sample_rate)

            if np.sum(spectrum) > 0:
                features.spectral_centroid = float(
                    np.sum(freqs * spectrum) / np.sum(spectrum)
                )

            cumsum = np.cumsum(spectrum)
            if cumsum[-1] > 0:
                rolloff_idx = np.searchsorted(cumsum, 0.85 * cumsum[-1])
                features.spectral_rolloff = float(freqs[min(rolloff_idx, len(freqs) - 1)])

        if self._npu_engine is not None:
            try:
                input_data = mono[:128].astype(np.float32)
                if len(input_data) < 128:
                    padded = np.zeros(128, dtype=np.float32)
                    padded[: len(input_data)] = input_data
                    input_data = padded
                input_data = input_data.reshape(1, 128)

                embedding = self._npu_engine.infer("recommender", input_data)
                if embedding is not None:
                    features.embedding = embedding.flatten()
            except Exception as e:
                logger.debug("NPU feature extraction fallback: %s", e)

        features = self._estimate_high_level_features(features, mono, sample_rate)
        return features

    def _estimate_high_level_features(
        self, features: TrackFeatures, audio: np.ndarray, sample_rate: int
    ) -> TrackFeatures:
        """Estimate high-level musical features from audio signal."""
        if len(audio) < 1024:
            return features

        features.valence = min(1.0, features.spectral_centroid / 5000.0)

        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))
        features.speechiness = min(1.0, zero_crossings * 10)

        features.acousticness = min(1.0, max(0.0, 1.0 - features.energy * 5))

        spectral_flux = 0.0
        hop = 512
        prev_spectrum = None
        for i in range(0, len(audio) - 1024, hop):
            spectrum = np.abs(np.fft.rfft(audio[i : i + 1024]))
            if prev_spectrum is not None:
                spectral_flux += np.sum((spectrum - prev_spectrum) ** 2)
            prev_spectrum = spectrum

        features.danceability = min(
            1.0, spectral_flux / (len(audio) / hop + 1) * 100
        )

        features.instrumentalness = max(0.0, 1.0 - features.speechiness * 2)

        return features

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

    def get_recommendations(self, n: int = 10) -> list[dict]:
        """Get recommended tracks based on current preferences."""
        if not self._track_db:
            return self._get_preference_summary(n)

        scored = []
        for track_id, features in self._track_db.items():
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

    def _get_preference_summary(self, n: int) -> list[dict]:
        """Return a summary of current preferences when no track DB exists."""
        feature_names = [
            "energy", "valence", "tempo", "danceability",
            "acousticness", "instrumentalness", "speechiness", "liveness",
        ]
        summary = {}
        for i, name in enumerate(feature_names):
            if i < len(self._preferences):
                summary[name] = float(self._preferences[i])

        return [{"type": "preference_profile", "features": summary}]

    def _save_state(self) -> None:
        """Persist recommendation state to disk."""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            state = {
                "preferences": self._preferences.tolist(),
                "momentum": self._preference_momentum.tolist(),
                "history_count": len(self._history),
            }
            state_path = os.path.join(self.data_dir, "state.json")
            with open(state_path, "w") as f:
                json.dump(state, f)
        except Exception as e:
            logger.debug("Failed to save recommendation state: %s", e)

    def _load_state(self) -> None:
        """Load persisted recommendation state."""
        try:
            state_path = os.path.join(self.data_dir, "state.json")
            if os.path.exists(state_path):
                with open(state_path) as f:
                    state = json.load(f)
                self._preferences = np.array(state["preferences"], dtype=np.float32)
                self._preference_momentum = np.array(state["momentum"], dtype=np.float32)
                logger.info("Recommendation state loaded")
        except Exception as e:
            logger.debug("No previous recommendation state: %s", e)

    @property
    def preference_profile(self) -> dict:
        """Get current user preference profile."""
        names = [
            "energy", "valence", "tempo", "danceability",
            "acousticness", "instrumentalness", "speechiness", "liveness",
            "spectral_centroid", "spectral_rolloff", "spectral_contrast",
        ]
        return {
            name: float(self._preferences[i])
            for i, name in enumerate(names)
            if i < len(self._preferences)
        }
