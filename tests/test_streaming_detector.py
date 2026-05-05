"""Tests for the streaming detector source classification and snapshot logic."""

from __future__ import annotations

import unittest

from src.recommender.streaming_detector import (
    SOURCE_APPLE_MUSIC,
    SOURCE_SPOTIFY,
    SOURCE_UNKNOWN,
    SOURCE_YOUTUBE_MUSIC,
    NowPlaying,
    StreamingDetector,
    _classify,
)


class TestClassify(unittest.TestCase):
    def test_spotify_app_id(self) -> None:
        self.assertEqual(
            _classify("Spotify.exe"),
            SOURCE_SPOTIFY,
        )
        self.assertEqual(
            _classify("SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify"),
            SOURCE_SPOTIFY,
        )

    def test_apple_music(self) -> None:
        self.assertEqual(
            _classify("AppleInc.AppleMusic_nzyj5cx40ttqa"),
            SOURCE_APPLE_MUSIC,
        )
        self.assertEqual(_classify("iTunes"), SOURCE_APPLE_MUSIC)

    def test_youtube_music(self) -> None:
        self.assertEqual(
            _classify("Some Song · Artist - YouTube Music — Google Chrome"),
            SOURCE_YOUTUBE_MUSIC,
        )
        self.assertEqual(
            _classify("music.youtube.com tab"),
            SOURCE_YOUTUBE_MUSIC,
        )

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(_classify("notepad.exe"))
        self.assertIsNone(_classify(""))


class TestNowPlaying(unittest.TestCase):
    def test_track_id_combines_source_artist_title(self) -> None:
        np_ = NowPlaying(
            source=SOURCE_SPOTIFY, title="Lithium", artist="Nirvana",
        )
        self.assertEqual(np_.track_id, "spotify::nirvana::lithium")

    def test_track_id_blank_when_no_metadata(self) -> None:
        self.assertEqual(NowPlaying().track_id, "")

    def test_display_label_handles_partials(self) -> None:
        self.assertEqual(
            NowPlaying(title="X", artist="Y").display_label, "X — Y",
        )
        self.assertEqual(NowPlaying(title="X").display_label, "X")
        self.assertEqual(NowPlaying(artist="Y").display_label, "Y")
        self.assertEqual(NowPlaying().display_label, "")


class TestStreamingDetectorListener(unittest.TestCase):
    def test_poll_once_publishes_only_on_track_change(self) -> None:
        d = StreamingDetector()
        events: list[NowPlaying] = []
        d.add_listener(events.append)

        first = NowPlaying(
            source=SOURCE_SPOTIFY, title="A", artist="B", is_playing=True,
        )
        d._publish(first)
        self.assertEqual(len(events), 1)

        # Same track again — no callback.
        d._publish(first)
        self.assertEqual(len(events), 1)

        # Different track — callback fires.
        second = NowPlaying(
            source=SOURCE_YOUTUBE_MUSIC, title="C", artist="D",
            is_playing=True,
        )
        d._publish(second)
        self.assertEqual(len(events), 2)

    def test_remove_listener_silences_callbacks(self) -> None:
        d = StreamingDetector()
        events: list[NowPlaying] = []
        d.add_listener(events.append)
        d.remove_listener(events.append)
        d._publish(
            NowPlaying(source=SOURCE_APPLE_MUSIC, title="x", artist="y"),
        )
        self.assertEqual(events, [])

    def test_poll_once_returns_unknown_on_silent_host(self) -> None:
        d = StreamingDetector()
        snap = d.poll_once()
        # On non-Windows / silent CI host both backends are inert.
        self.assertEqual(snap.source, SOURCE_UNKNOWN)
        self.assertFalse(snap.is_playing)


if __name__ == "__main__":
    unittest.main()
