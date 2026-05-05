"""Recommender engine: streaming metadata + per-service preference learning."""

from __future__ import annotations

import os
import tempfile
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


if __name__ == "__main__":
    unittest.main()
