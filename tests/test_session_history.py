"""Tests for session history module."""

from __future__ import annotations

import os
import tempfile
from unittest import mock

from src.session_history import SessionEvent, SessionHistory, SessionStats


class TestSessionEvent:
    def test_to_dict(self):
        e = SessionEvent(timestamp=1.0, event_type="test", details={"k": "v"})
        d = e.to_dict()
        assert d["event_type"] == "test"
        assert d["details"]["k"] == "v"

    def test_from_dict(self):
        e = SessionEvent.from_dict(
            {"timestamp": 2.0, "event_type": "preset_change", "details": {}}
        )
        assert e.event_type == "preset_change"
        assert e.timestamp == 2.0

    def test_from_dict_defaults(self):
        e = SessionEvent.from_dict({})
        assert e.event_type == ""
        assert e.timestamp == 0.0


class TestSessionStats:
    def test_defaults(self):
        s = SessionStats()
        assert s.total_frames_processed == 0
        assert s.preset_changes == 0

    def test_avg_processing_zero(self):
        s = SessionStats()
        assert s.avg_processing_ms == 0.0


class TestSessionHistory:
    def test_log_event(self):
        with mock.patch("src.session_history.HISTORY_FILE", "/tmp/test_hist.json"):
            h = SessionHistory()
            h.log_event("preset_change", preset="Bass Boost")
            assert h.stats.preset_changes == 1
            assert len(h.events) >= 1

    def test_get_recent(self):
        with mock.patch("src.session_history.HISTORY_FILE", "/tmp/test_hist2.json"):
            h = SessionHistory()
            for i in range(5):
                h.log_event("test", index=i)
            recent = h.get_recent(3)
            assert len(recent) == 3

    def test_clear(self):
        with mock.patch("src.session_history.HISTORY_FILE", "/tmp/test_hist3.json"):
            h = SessionHistory()
            h.log_event("test")
            h.clear()
            assert len(h.events) == 0
            assert h.stats.preset_changes == 0

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "history.json")
            with mock.patch("src.session_history.HISTORY_FILE", path):
                h = SessionHistory()
                h.log_event("file_import", filename="test.wav")
                h.save()

                # Reload
                h2 = SessionHistory()
                assert len(h2.events) >= 1

    def test_stats_tracking(self):
        with mock.patch("src.session_history.HISTORY_FILE", "/tmp/test_hist4.json"):
            h = SessionHistory()
            h.log_event("genre_detected", genre="Electronic")
            h.log_event("file_export", path="/tmp/out.wav")
            h.log_event("ab_toggle")
            assert h.stats.genre_detections == 1
            assert h.stats.files_exported == 1
            assert h.stats.ab_comparisons == 1
