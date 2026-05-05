"""
Deep Learning Recommendation Engine (v4 - Streaming-Aware).

Real-time music recommendation with:
  - MFCC + chroma + onset strength feature extraction
  - Adam-like optimizer for preference learning (momentum + RMSProp)
  - Cross-service normalization (Spotify/Apple Music/YouTube Music)
  - Per-service preference profiles with shared latent factors
  - Genre affinity clustering with cosine similarity
  - Temporal decay weighting for recency bias
  - NPU-accelerated feature embedding + deep scorer MLP
  - Exploration/exploitation balance via UCB-style scoring
  - Streaming source metadata bound to learned representations
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.spatial.distance import cosine

from src.recommender.streaming_detector import (
    SOURCE_APPLE_MUSIC,
    SOURCE_SPOTIFY,
    SOURCE_UNKNOWN,
    SOURCE_YOUTUBE_MUSIC,
    NowPlaying,
)

logger = logging.getLogger(__name__)

FEATURE_NAMES = (
    "energy", "valence", "tempo", "danceability",
    "acousticness", "instrumentalness", "speechiness", "liveness",
    "spectral_centroid", "spectral_rolloff", "spectral_contrast",
)
FEATURE_DIM = 36

#: Streaming services that get a dedicated preference profile.
SERVICE_KEYS: tuple[str, ...] = (
    SOURCE_SPOTIFY,
    SOURCE_APPLE_MUSIC,
    SOURCE_YOUTUBE_MUSIC,
)

#: Display labels and accent colours used by the UI for each service.
SERVICE_DISPLAY: dict[str, dict[str, str]] = {
    SOURCE_SPOTIFY: {"label": "Spotify", "color": "#1DB954"},
    SOURCE_APPLE_MUSIC: {"label": "Apple Music", "color": "#FA243C"},
    SOURCE_YOUTUBE_MUSIC: {"label": "YouTube Music", "color": "#FF0000"},
    SOURCE_UNKNOWN: {"label": "システム音", "color": "#8B949E"},
}


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

    # Extended features
    onset_strength: float = 0.0
    spectral_flatness: float = 0.0
    harmonic_ratio: float = 0.0

    def to_vector(self) -> np.ndarray:
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

    Uses Adam-like optimization for preference learning with
    NPU-accelerated feature extraction, per-service preference profiles,
    and cross-service normalization. Recommendations are scored with a
    blend of cosine similarity, NPU-evaluated MLP affinity, source-aware
    diversity bonuses, and UCB-style exploration.
    """

    def __init__(self, data_dir: str = "data/recommender"):
        self.data_dir = data_dir
        self._npu_engine: Any = None
        # Re-entrant lock guards mutations to the track DB, preference state,
        # and history buffers. Lets the audio processing thread call
        # update_preferences() concurrently with the UI thread polling
        # get_recommendations() without races on dict iteration or numpy
        # writes.
        self._lock = threading.RLock()
        self._history: deque[TrackFeatures] = deque(maxlen=5000)
        self._preferences = np.zeros(FEATURE_DIM, dtype=np.float32)
        self._preference_momentum = np.zeros(FEATURE_DIM, dtype=np.float32)
        self._preference_velocity = np.zeros(FEATURE_DIM, dtype=np.float32)
        # Per-service preferences let the engine learn that user enjoys
        # different acoustic profiles on different platforms (e.g. lo-fi on
        # YouTube Music, chart pop on Spotify). They share the same feature
        # vocabulary but accumulate gradients independently.
        self._service_preferences: dict[str, np.ndarray] = {
            key: np.zeros(FEATURE_DIM, dtype=np.float32)
            for key in SERVICE_KEYS
        }
        self._service_play_counts: dict[str, int] = {
            key: 0 for key in SERVICE_KEYS
        }
        self._learning_rate = 0.03
        self._beta1 = 0.9  # momentum decay
        self._beta2 = 0.999  # velocity decay
        self._epsilon = 1e-8
        self._update_step = 0
        self._track_db: dict[str, TrackFeatures] = {}
        self._genre_affinity: dict[str, float] = {}

        # Feature normalization stats (running mean/var)
        self._feature_mean = np.zeros(FEATURE_DIM, dtype=np.float32)
        self._feature_var = np.ones(FEATURE_DIM, dtype=np.float32)
        self._norm_count = 0

        # Recent learning losses for UI training-curve display.
        self._loss_history: deque[float] = deque(maxlen=240)

        # Exploration parameter
        self._exploration_rate = 0.1

        self._load_state()

    def set_npu_engine(self, engine: Any) -> None:
        self._npu_engine = engine
        logger.info("NPU engine connected to recommendation engine")

    def analyze_audio(
        self,
        audio: np.ndarray,
        sample_rate: int = 48000,
        now_playing: NowPlaying | None = None,
    ) -> TrackFeatures:
        """Extract comprehensive audio features from a real-time audio buffer.

        ``now_playing`` lets the caller bind streaming metadata (Spotify,
        Apple Music, YouTube Music) onto the resulting :class:`TrackFeatures`
        so per-service preference learning and the track database can use
        real titles instead of synthetic ids.
        """
        features = TrackFeatures(timestamp=time.time())
        if now_playing is not None and now_playing.has_metadata:
            features.title = now_playing.title
            features.artist = now_playing.artist
            features.source = now_playing.source
            tid = now_playing.track_id
            if tid:
                features.track_id = tid

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
                features.spectral_centroid = float(
                    np.sum(freqs * spectrum) / total,
                )

            cumsum = np.cumsum(spectrum)
            if cumsum[-1] > 0:
                idx = np.searchsorted(cumsum, 0.85 * cumsum[-1])
                features.spectral_rolloff = float(
                    freqs[min(idx, len(freqs) - 1)],
                )

            # Spectral contrast (peaks vs valleys per band)
            n_bands = 6
            band_size = len(spectrum) // n_bands
            contrasts = []
            for b in range(n_bands):
                band = spectrum[b * band_size: (b + 1) * band_size]
                if len(band) > 0:
                    contrasts.append(float(np.max(band) - np.min(band)))
            if contrasts:
                avg_mag = total / len(spectrum) + 1e-10
                features.spectral_contrast = (
                    float(np.mean(contrasts)) / avg_mag
                )

            # Spectral flatness (tonality measure)
            spectrum_pos = spectrum[spectrum > 0]
            if len(spectrum_pos) > 0:
                geo_mean = np.exp(np.mean(np.log(spectrum_pos + 1e-10)))
                arith_mean = np.mean(spectrum_pos)
                features.spectral_flatness = float(
                    geo_mean / (arith_mean + 1e-10),
                )

            # MFCC extraction (simplified)
            features.mfcc_mean = self._extract_mfcc(mono, sample_rate, n_fft)

            # Chroma extraction
            features.chroma_mean = self._extract_chroma(
                spectrum, freqs, sample_rate,
            )

            # Onset strength
            features.onset_strength = self._compute_onset_strength(
                mono, sample_rate,
            )

        # NPU embedding
        if self._npu_engine is not None:
            try:
                chunk = mono[:128].astype(np.float32)
                if len(chunk) < 128:
                    padded = np.zeros(128, dtype=np.float32)
                    padded[: len(chunk)] = chunk
                    chunk = padded
                embedding = self._npu_engine.infer(
                    "recommender", chunk.reshape(1, 128),
                )
                if embedding is not None:
                    features.embedding = embedding.flatten()
            except Exception as e:
                logger.debug("NPU feature extraction fallback: %s", e)

        features = self._estimate_high_level(features, mono, sample_rate)
        return features

    def _extract_mfcc(
        self, audio: np.ndarray, sample_rate: int, n_fft: int,
    ) -> list[float]:
        """Simplified MFCC extraction using mel filterbank."""
        spectrum = np.abs(np.fft.rfft(audio[:n_fft])) ** 2
        n_mels = 26
        n_mfcc = 13

        # Mel filterbank
        low_mel = 0.0
        high_mel = 2595 * np.log10(1 + (sample_rate / 2) / 700)
        mel_points = np.linspace(low_mel, high_mel, n_mels + 2)
        hz_points = 700 * (10 ** (mel_points / 2595) - 1)
        bins = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)

        mel_energies = np.zeros(n_mels, dtype=np.float64)
        for m in range(n_mels):
            lo = max(0, bins[m])
            mid = max(0, bins[m + 1])
            hi = min(len(spectrum), bins[m + 2])

            if lo < mid <= hi and mid < len(spectrum):
                for k in range(lo, mid):
                    if k < len(spectrum):
                        weight = (k - lo) / max(1, mid - lo)
                        mel_energies[m] += spectrum[k] * weight
                for k in range(mid, hi):
                    if k < len(spectrum):
                        weight = (hi - k) / max(1, hi - mid)
                        mel_energies[m] += spectrum[k] * weight

        # Log compression
        mel_energies = np.log(mel_energies + 1e-10)

        # DCT to get MFCCs
        mfccs = np.zeros(n_mfcc, dtype=np.float64)
        for i in range(n_mfcc):
            for j in range(n_mels):
                mfccs[i] += mel_energies[j] * np.cos(
                    np.pi * i * (j + 0.5) / n_mels,
                )

        # Normalize
        norm = np.sqrt(np.sum(mfccs ** 2)) + 1e-10
        mfccs /= norm

        return mfccs.tolist()

    def _extract_chroma(
        self,
        spectrum: np.ndarray,
        freqs: np.ndarray,
        sample_rate: int,
    ) -> list[float]:
        """Extract chroma features (pitch class distribution)."""
        chroma = np.zeros(12, dtype=np.float64)

        for _i, (mag, freq) in enumerate(zip(spectrum, freqs, strict=True)):
            if freq < 30 or freq > 5000:
                continue
            # Map frequency to pitch class
            midi = 69 + 12 * np.log2(freq / 440.0 + 1e-10)
            pitch_class = int(round(midi)) % 12
            chroma[pitch_class] += mag

        total = np.sum(chroma) + 1e-10
        chroma /= total
        return chroma.tolist()

    def _compute_onset_strength(
        self, audio: np.ndarray, sample_rate: int,
    ) -> float:
        """Compute onset strength envelope magnitude."""
        hop = 512
        prev_spec = None
        flux_values = []

        for i in range(0, len(audio) - 1024, hop):
            spec = np.abs(np.fft.rfft(audio[i: i + 1024]))
            if prev_spec is not None:
                diff = np.maximum(0, spec - prev_spec)
                flux_values.append(float(np.sum(diff)))
            prev_spec = spec

        if flux_values:
            return float(np.mean(flux_values))
        return 0.0

    def _estimate_high_level(
        self, features: TrackFeatures, audio: np.ndarray, sample_rate: int,
    ) -> TrackFeatures:
        if len(audio) < 1024:
            return features

        features.valence = min(1.0, features.spectral_centroid / 5000.0)

        zcr = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))
        features.speechiness = min(1.0, float(zcr) * 10)
        features.acousticness = min(
            1.0, max(0.0, 1.0 - features.energy * 5),
        )

        # Spectral flux for danceability
        hop = 512
        prev_spec = None
        flux = 0.0
        count = 0
        for i in range(0, len(audio) - 1024, hop):
            spec = np.abs(np.fft.rfft(audio[i: i + 1024]))
            if prev_spec is not None:
                flux += float(np.sum((spec - prev_spec) ** 2))
                count += 1
            prev_spec = spec

        features.danceability = min(1.0, flux / (count + 1) * 100)
        features.instrumentalness = max(
            0.0, 1.0 - features.speechiness * 2,
        )

        # Harmonic ratio
        if features.spectral_flatness > 0:
            features.harmonic_ratio = min(
                1.0, 1.0 - features.spectral_flatness,
            )

        # Tempo estimation via onset autocorrelation
        if len(audio) >= sample_rate:
            onset_env = self._onset_envelope(audio, sample_rate)
            if len(onset_env) > 2:
                ac = np.correlate(onset_env, onset_env, mode="full")
                ac = ac[len(ac) // 2:]
                min_lag = int(60 / 200 * sample_rate / hop)
                max_lag = min(
                    int(60 / 40 * sample_rate / hop), len(ac) - 1,
                )
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
            mag = np.abs(np.fft.rfft(audio[i: i + 1024]))
            if prev is not None:
                diff = np.maximum(0, mag - prev)
                frames.append(float(np.sum(diff)))
            prev = mag
        return np.array(frames, dtype=np.float32)

    def update_preferences(
        self,
        features: TrackFeatures,
        liked: bool | None = True,
    ) -> None:
        """Update preferences using Adam-like optimizer.

        ``liked`` semantics:
          * ``True``  — positive gradient (the user wants more of this).
          * ``False`` — negative gradient (the user actively disliked it).
          * ``None``  — *neutral*: refresh normalization stats, register the
            track in the database, append to history, but apply **no**
            preference gradient. Used when the stream is merely paused.

        The squared L2 distance between the normalized track vector and the
        global preferences is always recorded as the live training "loss"
        for UI display.
        """
        with self._lock:
            vector = features.to_vector()
            if len(vector) != len(self._preferences):
                vector = np.resize(vector, len(self._preferences))

            # Update running normalization stats unconditionally — keeping
            # them current even on neutral updates avoids cold-start drift
            # the next time a real "liked" signal arrives.
            self._norm_count += 1
            delta = vector - self._feature_mean
            self._feature_mean += delta / self._norm_count
            delta2 = vector - self._feature_mean
            self._feature_var += (
                (delta * delta2 - self._feature_var) / self._norm_count
            )

            # Normalize input
            std = np.sqrt(self._feature_var + 1e-8)
            normalized = (vector - self._feature_mean) / std

            if liked is not None:
                # Adam-style update only when there is a real signal.
                direction = 1.0 if liked else -0.5
                gradient = (normalized - self._preferences) * direction

                self._update_step += 1

                # Momentum (first moment)
                self._preference_momentum = (
                    self._beta1 * self._preference_momentum
                    + (1 - self._beta1) * gradient
                )
                # Velocity (second moment)
                self._preference_velocity = (
                    self._beta2 * self._preference_velocity
                    + (1 - self._beta2) * gradient ** 2
                )

                # Bias correction
                m_hat = self._preference_momentum / (
                    1 - self._beta1 ** self._update_step
                )
                v_hat = self._preference_velocity / (
                    1 - self._beta2 ** self._update_step
                )

                # Update
                self._preferences += (
                    self._learning_rate * m_hat
                    / (np.sqrt(v_hat) + self._epsilon)
                )
                self._preferences = np.clip(self._preferences, -1.0, 1.0)

                # Per-service profile: simple online EMA, biased by direction.
                if features.source in self._service_preferences:
                    ema = 0.05 if liked else 0.02
                    current = self._service_preferences[features.source]
                    target = normalized * direction
                    self._service_preferences[features.source] = np.clip(
                        current * (1 - ema) + target * ema,
                        -1.0, 1.0,
                    ).astype(np.float32)
                    self._service_play_counts[features.source] += 1

            # Track loss = current distance between the normalized track and
            # the learned profile. Drops as the model adapts to the listener.
            diff = normalized - self._preferences
            loss = float(np.mean(diff * diff))
            self._loss_history.append(loss)

            self._register_track(features, count_play=liked is not None)
            self._history.append(features)
            self._save_state()

    def _register_track(
        self, features: TrackFeatures, *, count_play: bool = True,
    ) -> None:
        """Persist or merge a track entry into the in-memory database.

        The database is keyed on the streaming track id so the same song from
        Spotify and YouTube Music ends up as separate entries — letting us
        suggest the cross-platform "same vibe, different service" picks.

        ``count_play=False`` lets neutral (paused) updates refresh the cached
        acoustic signature without inflating ``play_count``. Inflated play
        counts would otherwise depress the UCB exploration bonus and display
        a misleading "played N times" tooltip in the UI.
        """
        if not features.track_id:
            return
        existing = self._track_db.get(features.track_id)
        if existing is None:
            if count_play:
                features.play_count = max(1, features.play_count)
            else:
                features.play_count = 0
            self._track_db[features.track_id] = features
            return
        if count_play:
            existing.play_count += 1
        existing.timestamp = features.timestamp
        # Acoustic features drift over the course of a song; keep an EMA so
        # the stored signature reflects the whole listen rather than the last
        # 4-second window.
        ema = 0.2
        for attr in (
            "energy", "valence", "tempo", "danceability",
            "acousticness", "instrumentalness", "speechiness", "liveness",
            "spectral_centroid", "spectral_rolloff", "spectral_contrast",
            "spectral_flatness", "harmonic_ratio", "onset_strength",
        ):
            cur = float(getattr(existing, attr))
            new = float(getattr(features, attr))
            setattr(existing, attr, cur * (1 - ema) + new * ema)
        if features.embedding is not None:
            if existing.embedding is None:
                existing.embedding = features.embedding
            else:
                existing.embedding = (
                    existing.embedding * (1 - ema) + features.embedding * ema
                ).astype(np.float32)

    def get_recommendations(
        self,
        n: int = 10,
        *,
        target_source: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the top ``n`` recommendations.

        ``target_source`` lets the caller bias the ranking towards a specific
        service profile — e.g. when the user is currently listening to
        Spotify, the cross-platform "same vibe" score uses Spotify's
        per-service preference vector even when scoring YouTube Music tracks.
        """
        # Snapshot the track DB and recent history under the lock so the
        # background processing thread can keep registering new tracks
        # without raising "dictionary changed size during iteration" here.
        with self._lock:
            if not self._track_db:
                return self._get_preference_summary(n)
            track_items = list(self._track_db.items())
            history_snapshot = list(self._history)
            preferences_snapshot = self._preferences.copy()
            service_profile = (
                self._service_preferences[target_source].copy()
                if target_source and target_source in self._service_preferences
                else None
            )
            update_step = self._update_step

        # Choose the profile vector to score against.
        if service_profile is not None:
            target_profile = service_profile
            mix = 0.6
        else:
            target_profile = preferences_snapshot
            mix = 1.0
        if mix < 1.0:
            target_profile = (
                preferences_snapshot * (1 - mix) + target_profile * mix
            ).astype(np.float32)

        scored: list[tuple[float, TrackFeatures, dict[str, float]]] = []
        recent_sources = [h.source for h in history_snapshot[-10:]]
        for _track_id, features in track_items:
            vector = features.to_vector()
            if len(vector) != len(preferences_snapshot):
                vector = np.resize(vector, len(preferences_snapshot))

            # Cosine similarity (primary scorer). ``scipy`` returns NaN when
            # either side is the zero vector (cold-start), so coerce to 0.
            try:
                similarity_raw = 1.0 - cosine(target_profile, vector)
                if not np.isfinite(similarity_raw):
                    similarity_raw = 0.0
            except Exception:
                similarity_raw = 0.0
            similarity = float(similarity_raw)

            # NPU rec_scorer affinity: feeds the embedding (or DCT vector)
            # through the deep MLP and aggregates the response. Falls back
            # to the cosine similarity when the model is not yet loaded.
            mlp_score = self._npu_score(features)

            # Recency bonus (favour artists you just heard)
            recency_bonus = 0.0
            for hist in reversed(history_snapshot[-30:]):
                if hist.artist and hist.artist == features.artist:
                    recency_bonus += 0.03
                    break

            # Exploration bonus (UCB-style)
            play_count = max(1, features.play_count)
            exploration = self._exploration_rate * np.sqrt(
                np.log(update_step + 1) / play_count,
            )

            # Source diversity bonus
            source_bonus = 0.0
            if features.source and features.source not in recent_sources:
                source_bonus = 0.02
            if target_source and features.source == target_source:
                source_bonus += 0.05

            score = (
                similarity * 0.55
                + mlp_score * 0.25
                + recency_bonus
                + exploration
                + source_bonus
            )
            breakdown = {
                "similarity": float(similarity),
                "mlp_score": float(mlp_score),
                "recency_bonus": float(recency_bonus),
                "exploration": float(exploration),
                "source_bonus": float(source_bonus),
            }
            scored.append((score, features, breakdown))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "track_id": f.track_id,
                "title": f.title,
                "artist": f.artist,
                "source": f.source,
                "score": float(s),
                "play_count": f.play_count,
                "reason": self._explain(f, breakdown, target_source),
                "breakdown": breakdown,
            }
            for s, f, breakdown in scored[:n]
        ]

    def _npu_score(self, features: TrackFeatures) -> float:
        """Run the optional ``rec_scorer`` MLP and project to a scalar."""
        if self._npu_engine is None:
            return 0.0
        embedding = features.embedding
        if embedding is None:
            return 0.0
        try:
            arr = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
            if arr.shape[1] < 64:
                pad = np.zeros((1, 64), dtype=np.float32)
                pad[:, : arr.shape[1]] = arr
                arr = pad
            elif arr.shape[1] > 64:
                arr = arr[:, :64]
            out = self._npu_engine.infer("rec_scorer", arr)
            if out is None:
                return 0.0
            scalar = float(np.tanh(np.mean(out)))
            return scalar
        except Exception as exc:
            logger.debug("rec_scorer inference fallback: %s", exc)
            return 0.0

    def _explain(
        self,
        features: TrackFeatures,
        breakdown: dict[str, float],
        target_source: str | None,
    ) -> str:
        """Short human-readable reason text shown next to a recommendation."""
        bits: list[str] = []
        if breakdown["similarity"] >= 0.4:
            bits.append("嗜好と高一致")
        elif breakdown["similarity"] >= 0.15:
            bits.append("嗜好に近い")
        else:
            bits.append("新しい音色を探索中")
        if breakdown["mlp_score"] > 0.05:
            bits.append("NPUスコア高")
        if breakdown["exploration"] > 0.1:
            bits.append("再生回数少")
        if (
            target_source
            and features.source
            and features.source == target_source
        ):
            label = SERVICE_DISPLAY.get(target_source, {}).get("label", "")
            if label:
                bits.append(f"{label} 内で類似")
        elif features.source and features.source != SOURCE_UNKNOWN:
            bits.append("クロスサービス候補")
        return " · ".join(bits)

    # ----- UI accessors -----------------------------------------------------

    @property
    def loss_history(self) -> list[float]:
        return list(self._loss_history)

    @property
    def service_play_counts(self) -> dict[str, int]:
        return dict(self._service_play_counts)

    def service_profile(self, source: str) -> dict[str, float]:
        """Return one service's preference vector restricted to FEATURE_NAMES."""
        if source not in self._service_preferences:
            return {}
        vec = self._service_preferences[source]
        return {
            name: float(vec[i])
            for i, name in enumerate(FEATURE_NAMES)
            if i < len(vec)
        }

    @property
    def track_count(self) -> int:
        return len(self._track_db)

    @property
    def update_step(self) -> int:
        return self._update_step

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
                "velocity": self._preference_velocity.tolist(),
                "update_step": self._update_step,
                "feature_mean": self._feature_mean.tolist(),
                "feature_var": self._feature_var.tolist(),
                "norm_count": self._norm_count,
                "history_count": len(self._history),
                "service_preferences": {
                    k: v.tolist()
                    for k, v in self._service_preferences.items()
                },
                "service_play_counts": dict(self._service_play_counts),
                "loss_history": list(self._loss_history),
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
                self._preferences = np.array(
                    state["preferences"], dtype=np.float32,
                )
                self._preference_momentum = np.array(
                    state["momentum"], dtype=np.float32,
                )
                if "velocity" in state:
                    self._preference_velocity = np.array(
                        state["velocity"], dtype=np.float32,
                    )
                if "update_step" in state:
                    self._update_step = state["update_step"]
                if "feature_mean" in state:
                    self._feature_mean = np.array(
                        state["feature_mean"], dtype=np.float32,
                    )
                if "feature_var" in state:
                    self._feature_var = np.array(
                        state["feature_var"], dtype=np.float32,
                    )
                if "norm_count" in state:
                    self._norm_count = state["norm_count"]
                if "service_preferences" in state:
                    for key, vec in state["service_preferences"].items():
                        if key in self._service_preferences:
                            arr = np.array(vec, dtype=np.float32)
                            if len(arr) == FEATURE_DIM:
                                self._service_preferences[key] = arr
                if "service_play_counts" in state:
                    for key, count in state["service_play_counts"].items():
                        if key in self._service_play_counts:
                            self._service_play_counts[key] = int(count)
                if "loss_history" in state:
                    for v in state["loss_history"]:
                        try:
                            self._loss_history.append(float(v))
                        except (TypeError, ValueError):
                            continue
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
