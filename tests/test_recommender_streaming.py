"""Recommender engine: streaming metadata + per-service preference learning."""

from __future__ import annotations

import os
import tempfile
import threading
import unittest

import numpy as np

from src.recommender.engine import (
    SERVICE_KEYS,
    RecommendationEngine,
)
from src.recommender.streaming_detector import (
    SOURCE_APPLE_MUSIC,
    SOURCE_SPOTIFY,
    SOURCE_YOUTUBE_MUSIC,
    NowPlaying,
)


def _make_audio(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(48000).astype(np.float32) * 0.1


class TestRecommenderStreaming(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.engine = RecommendationEngine(data_dir=self._tmp.name)

    def test_analyze_audio_binds_now_playing_metadata(self) -> None:
        now = NowPlaying(
            source=SOURCE_SPOTIFY, title="Test", artist="Demo",
            is_playing=True,
        )
        feats = self.engine.analyze_audio(_make_audio(1), now_playing=now)
        self.assertEqual(feats.source, SOURCE_SPOTIFY)
        self.assertEqual(feats.title, "Test")
        self.assertEqual(feats.artist, "Demo")
        self.assertEqual(feats.track_id, now.track_id)

    def test_update_preferences_grows_per_service_profile(self) -> None:
        for source in (SOURCE_SPOTIFY, SOURCE_APPLE_MUSIC):
            now = NowPlaying(
                source=source, title=f"{source}-song", artist="A",
                is_playing=True,
            )
            feats = self.engine.analyze_audio(_make_audio(2), now_playing=now)
            self.engine.update_preferences(feats, liked=True)
        # Service we never touched should remain at the zero baseline.
        ytm = self.engine.service_profile(SOURCE_YOUTUBE_MUSIC)
        self.assertTrue(all(abs(v) < 1e-6 for v in ytm.values()))
        # Touched services should record a positive play count.
        self.assertEqual(self.engine.service_play_counts[SOURCE_SPOTIFY], 1)
        self.assertEqual(
            self.engine.service_play_counts[SOURCE_APPLE_MUSIC], 1,
        )
        self.assertEqual(
            self.engine.service_play_counts[SOURCE_YOUTUBE_MUSIC], 0,
        )

    def test_recommendations_include_reason_and_breakdown(self) -> None:
        now = NowPlaying(
            source=SOURCE_SPOTIFY, title="Reasoned", artist="Engine",
            is_playing=True,
        )
        feats = self.engine.analyze_audio(_make_audio(3), now_playing=now)
        self.engine.update_preferences(feats, liked=True)
        recs = self.engine.get_recommendations(
            n=3, target_source=SOURCE_SPOTIFY,
        )
        self.assertTrue(recs)
        rec = recs[0]
        self.assertIn("reason", rec)
        self.assertIn("breakdown", rec)
        self.assertIn("similarity", rec["breakdown"])
        self.assertEqual(rec["source"], SOURCE_SPOTIFY)

    def test_loss_history_populates(self) -> None:
        for i in range(3):
            now = NowPlaying(
                source=SOURCE_YOUTUBE_MUSIC, title=f"t{i}", artist="A",
                is_playing=True,
            )
            feats = self.engine.analyze_audio(_make_audio(i), now_playing=now)
            self.engine.update_preferences(feats, liked=True)
        history = self.engine.loss_history
        self.assertEqual(len(history), 3)
        self.assertTrue(all(v >= 0.0 for v in history))

    def test_state_persists_per_service_profile(self) -> None:
        now = NowPlaying(
            source=SOURCE_APPLE_MUSIC, title="Persist", artist="X",
            is_playing=True,
        )
        feats = self.engine.analyze_audio(_make_audio(7), now_playing=now)
        self.engine.update_preferences(feats, liked=True)

        reborn = RecommendationEngine(data_dir=self._tmp.name)
        self.assertEqual(
            reborn.service_play_counts[SOURCE_APPLE_MUSIC], 1,
        )
        self.assertGreater(len(reborn.loss_history), 0)

    def test_service_keys_match_engine_constants(self) -> None:
        self.assertIn(SOURCE_SPOTIFY, SERVICE_KEYS)
        self.assertIn(SOURCE_APPLE_MUSIC, SERVICE_KEYS)
        self.assertIn(SOURCE_YOUTUBE_MUSIC, SERVICE_KEYS)

    def test_state_file_round_trip(self) -> None:
        now = NowPlaying(
            source=SOURCE_SPOTIFY, title="Save", artist="Test",
            is_playing=True,
        )
        feats = self.engine.analyze_audio(_make_audio(11), now_playing=now)
        self.engine.update_preferences(feats, liked=True)
        path = os.path.join(self._tmp.name, "state.json")
        self.assertTrue(os.path.exists(path))

    def test_neutral_update_does_not_apply_gradient(self) -> None:
        """liked=None must not push the preference vector either way."""
        # First, build up a non-zero preference profile via a positive signal.
        now_playing = NowPlaying(
            source=SOURCE_SPOTIFY, title="A", artist="B", is_playing=True,
        )
        seeded = self.engine.analyze_audio(
            _make_audio(20), now_playing=now_playing,
        )
        self.engine.update_preferences(seeded, liked=True)
        prefs_before = self.engine.preference_profile.copy()
        service_before = self.engine.service_profile(SOURCE_SPOTIFY).copy()
        play_count_before = self.engine.service_play_counts[SOURCE_SPOTIFY]

        # Apply a *neutral* update (e.g. user paused the streaming track).
        # The preference and service vectors must NOT change, but the track
        # database and history should still grow so the model has memory of
        # the song.
        track_count_before = self.engine.track_count
        paused_now = NowPlaying(
            source=SOURCE_SPOTIFY, title="C", artist="D",
            is_playing=False,
        )
        paused_feats = self.engine.analyze_audio(
            _make_audio(21), now_playing=paused_now,
        )
        self.engine.update_preferences(paused_feats, liked=None)

        prefs_after = self.engine.preference_profile
        service_after = self.engine.service_profile(SOURCE_SPOTIFY)
        for k, v in prefs_before.items():
            self.assertAlmostEqual(prefs_after[k], v, places=6)
        for k, v in service_before.items():
            self.assertAlmostEqual(service_after[k], v, places=6)
        self.assertEqual(
            self.engine.service_play_counts[SOURCE_SPOTIFY],
            play_count_before,
        )
        self.assertGreater(self.engine.track_count, track_count_before)

    def test_get_recommendations_thread_safe(self) -> None:
        """get_recommendations must not raise while another thread updates."""
        # Seed the database with one entry so the snapshot path runs.
        seed_now = NowPlaying(
            source=SOURCE_SPOTIFY, title="Seed", artist="X", is_playing=True,
        )
        feats = self.engine.analyze_audio(_make_audio(31), now_playing=seed_now)
        self.engine.update_preferences(feats, liked=True)

        stop = threading.Event()
        errors: list[BaseException] = []

        def writer() -> None:
            for i in range(40):
                if stop.is_set():
                    return
                np_now = NowPlaying(
                    source=SOURCE_YOUTUBE_MUSIC,
                    title=f"writer-{i}",
                    artist=f"author-{i}",
                    is_playing=True,
                )
                f = self.engine.analyze_audio(
                    _make_audio(40 + i), now_playing=np_now,
                )
                try:
                    self.engine.update_preferences(f, liked=True)
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)
                    return

        def reader() -> None:
            for _ in range(80):
                if stop.is_set():
                    return
                try:
                    self.engine.get_recommendations(
                        n=4, target_source=SOURCE_SPOTIFY,
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)
                    return

        threads = [threading.Thread(target=writer) for _ in range(2)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        stop.set()
        self.assertFalse(errors, f"Concurrency errors: {errors}")


if __name__ == "__main__":
    unittest.main()
