"""
Session History Module.

Persists processing statistics, preset changes, genre detections,
and other session events to a JSON log file for review.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)

HISTORY_DIR = os.path.join(
    os.path.expanduser("~"), ".npu_audio_enhancer"
)
HISTORY_FILE = os.path.join(HISTORY_DIR, "session_history.json")
MAX_ENTRIES = 500


@dataclass
class SessionEvent:
    """Single session event record."""

    timestamp: float = 0.0
    event_type: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> SessionEvent:
        return SessionEvent(
            timestamp=d.get("timestamp", 0.0),
            event_type=d.get("event_type", ""),
            details=d.get("details", {}),
        )


@dataclass
class SessionStats:
    """Aggregate statistics for the current session."""

    start_time: float = 0.0
    total_frames_processed: int = 0
    total_processing_time_ms: float = 0.0
    preset_changes: int = 0
    genre_detections: int = 0
    files_imported: int = 0
    files_exported: int = 0
    ab_comparisons: int = 0

    @property
    def session_duration_sec(self) -> float:
        if self.start_time == 0.0:
            return 0.0
        return time.time() - self.start_time

    @property
    def avg_processing_ms(self) -> float:
        if self.total_frames_processed == 0:
            return 0.0
        return self.total_processing_time_ms / max(1, self.preset_changes + 1)


class SessionHistory:
    """Manages session event logging and persistence."""

    def __init__(self) -> None:
        self._events: list[SessionEvent] = []
        self._stats = SessionStats(start_time=time.time())
        self._load()

    def _load(self) -> None:
        if not os.path.exists(HISTORY_FILE):
            return
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._events = [SessionEvent.from_dict(d) for d in data]
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load session history: %s", e)

    def save(self) -> None:
        """Persist events to disk."""
        os.makedirs(HISTORY_DIR, exist_ok=True)
        # Keep only recent entries
        recent = self._events[-MAX_ENTRIES:]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([e.to_dict() for e in recent], f, indent=2)
        except OSError as e:
            logger.error("Failed to save session history: %s", e)

    def log_event(self, event_type: str, **details: object) -> None:
        """Record a session event."""
        event = SessionEvent(
            timestamp=time.time(),
            event_type=event_type,
            details=dict(details),
        )
        self._events.append(event)
        self._update_stats(event)

    def _update_stats(self, event: SessionEvent) -> None:
        if event.event_type == "preset_change":
            self._stats.preset_changes += 1
        elif event.event_type == "genre_detected":
            self._stats.genre_detections += 1
        elif event.event_type == "file_import":
            self._stats.files_imported += 1
        elif event.event_type == "file_export":
            self._stats.files_exported += 1
        elif event.event_type == "ab_toggle":
            self._stats.ab_comparisons += 1

    @property
    def stats(self) -> SessionStats:
        return self._stats

    @property
    def events(self) -> list[SessionEvent]:
        return list(self._events)

    def get_recent(self, count: int = 20) -> list[SessionEvent]:
        """Return the most recent events."""
        return self._events[-count:]

    def clear(self) -> None:
        """Clear all history."""
        self._events.clear()
        self._stats = SessionStats(start_time=time.time())
