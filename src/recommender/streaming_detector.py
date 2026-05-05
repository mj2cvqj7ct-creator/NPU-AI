"""
Streaming Source Detector.

Detects what is currently playing on Spotify, Apple Music, and YouTube Music
on Windows 11 ARM64 by combining:

  1. Windows Global System Media Transport Controls (GSMTC) via ``winsdk``
     - first-class metadata: title, artist, album, source app id, playback
       state. Works for any app that registers an SMTC session, including
       Spotify, Apple Music (Microsoft Store), and YouTube Music in Chrome /
       Edge / the YT Music desktop wrapper.
  2. Process / window enumeration via ``psutil`` and ``ctypes`` as a low-cost
     fallback when SMTC metadata is unavailable (e.g. PWA without full
     metadata, or when ``winsdk`` is missing).

The detector is non-blocking: a background thread polls every ``poll_interval``
seconds and exposes a snapshot through :py:meth:`current_track`. Listeners can
subscribe via :py:meth:`add_listener` to be notified of track-change events.

Designed to run inside the audio processing app on Snapdragon X (Windows 11
ARM64) with negligible overhead — the SMTC bridge is event-light and the
fallback enumeration only runs when SMTC is silent.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


SOURCE_SPOTIFY = "spotify"
SOURCE_APPLE_MUSIC = "apple_music"
SOURCE_YOUTUBE_MUSIC = "youtube_music"
SOURCE_UNKNOWN = "unknown"

#: Lower-cased substrings used to map an SMTC session source app id or a
#: process/window name to one of the supported services.
_SOURCE_FINGERPRINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        SOURCE_SPOTIFY,
        ("spotify", "spotifyab.spotifymusic"),
    ),
    (
        SOURCE_APPLE_MUSIC,
        ("apple.music", "applemusic", "appleinc.applemusic", "itunes"),
    ),
    (
        SOURCE_YOUTUBE_MUSIC,
        (
            "youtube music",
            "ytmusic",
            "music.youtube.com",
            "youtubemusic",
            "youtube_music",
        ),
    ),
)


@dataclass(frozen=True)
class NowPlaying:
    """Snapshot of the currently detected streaming track."""

    source: str = SOURCE_UNKNOWN
    title: str = ""
    artist: str = ""
    album: str = ""
    is_playing: bool = False
    detected_at: float = 0.0
    detail: str = ""

    @property
    def track_id(self) -> str:
        """Stable identifier for the (source, title, artist) triple."""
        if not (self.title or self.artist):
            return ""
        return f"{self.source}::{self.artist}::{self.title}".lower()

    @property
    def display_label(self) -> str:
        """Human-readable label for UI Now-Playing strips."""
        if self.title and self.artist:
            return f"{self.title} — {self.artist}"
        if self.title:
            return self.title
        if self.artist:
            return self.artist
        return ""

    @property
    def has_metadata(self) -> bool:
        return bool(self.title or self.artist)


def _classify(text: str) -> str | None:
    """Map an arbitrary text fragment to a known streaming source."""
    if not text:
        return None
    haystack = text.lower()
    for source, needles in _SOURCE_FINGERPRINTS:
        for needle in needles:
            if needle in haystack:
                return source
    return None


# --- SMTC backend -------------------------------------------------------------

class _SMTCBackend:
    """Bridge to Windows Global System Media Transport Controls.

    Uses ``winsdk`` (preferred) or ``winrt`` (legacy) lazily so the module
    can be imported on non-Windows platforms (CI) without crashing.
    """

    def __init__(self) -> None:
        self._available = False
        self._manager: Any = None
        self._asyncio: Any = None
        self._mc_module: Any = None
        if sys.platform != "win32":
            return
        try:
            self._mc_module, self._asyncio = self._import_smtc()
        except Exception as exc:  # pragma: no cover - depends on host
            # Log at WARNING — when the bridge fails, the UI silently falls
            # back to "待機中" and we want this visible in the log file.
            logger.warning(
                "SMTC backend unavailable (winsdk/winrt import failed): %s",
                exc,
            )
            return
        try:
            self._manager = self._asyncio.run(
                self._mc_module.GlobalSystemMediaTransportControlsSessionManager
                .request_async(),
            )
            self._available = True
            logger.info("SMTC backend initialised — Now Playing detection active")
        except Exception as exc:  # pragma: no cover - depends on host
            logger.warning("SMTC manager init failed: %s", exc)

    @staticmethod
    def _import_smtc() -> tuple[Any, Any]:
        import asyncio
        import importlib

        mc: Any
        try:
            mc = importlib.import_module("winsdk.windows.media.control")
        except Exception:
            mc = importlib.import_module("winrt.windows.media.control")
        # Sanity-check that the manager exists; raises AttributeError if
        # the module is hollow.
        _ = mc.GlobalSystemMediaTransportControlsSessionManager
        return mc, asyncio

    @property
    def available(self) -> bool:
        return self._available

    def snapshot(self) -> NowPlaying | None:
        """Return the active SMTC session as a NowPlaying snapshot."""
        if not self._available or self._manager is None:
            return None
        try:
            session = self._manager.get_current_session()
            if session is None:
                return None
            try:
                props = self._asyncio.run(
                    session.try_get_media_properties_async(),
                )
            except Exception as exc:  # pragma: no cover
                logger.debug("SMTC properties fetch failed: %s", exc)
                return None
            playback_info = session.get_playback_info()
            try:
                # PlaybackStatus enum: 0=Closed, 1=Opened, 2=Changing,
                # 3=Stopped, 4=Playing, 5=Paused
                status_val = int(playback_info.playback_status)
            except Exception:
                status_val = 0
            is_playing = status_val == 4
            app_id = (session.source_app_user_model_id or "").strip()
            title = (props.title or "").strip() if props is not None else ""
            artist = (props.artist or "").strip() if props is not None else ""
            album = (
                (props.album_title or "").strip() if props is not None else ""
            )
            source = _classify(app_id) or _classify(title) or SOURCE_UNKNOWN
            return NowPlaying(
                source=source,
                title=title,
                artist=artist,
                album=album,
                is_playing=is_playing,
                detected_at=time.time(),
                detail=app_id,
            )
        except Exception as exc:  # pragma: no cover - SMTC can race
            logger.debug("SMTC snapshot error: %s", exc)
            return None


# --- Process / window fallback -----------------------------------------------

class _WindowFallback:
    """Lightweight detector based on process and window-title enumeration.

    Cannot read song metadata from Spotify (no public API), but it can answer
    "which streaming app is foreground / running?" on its own without
    ``winsdk``. For YouTube Music in a browser, the page title typically reads
    ``Some Song · Artist - YouTube Music`` — enough to surface a label.
    """

    def __init__(self) -> None:
        self._psutil: Any = None
        self._ctypes: Any = None
        if sys.platform != "win32":
            return
        try:
            import psutil

            self._psutil = psutil
        except Exception as exc:  # pragma: no cover
            logger.debug("psutil unavailable: %s", exc)
        try:
            import ctypes
            from ctypes import wintypes  # noqa: F401

            self._ctypes = ctypes
        except Exception as exc:  # pragma: no cover
            logger.debug("ctypes unavailable: %s", exc)

    def snapshot(self) -> NowPlaying | None:
        title = self._foreground_window_title()
        source = self._classify_from_processes()
        title_source = _classify(title) if title else None
        if title_source:
            source = source or title_source
        if source is None and not title:
            return None
        parsed_title, parsed_artist = self._parse_window_title(title, source)
        return NowPlaying(
            source=source or SOURCE_UNKNOWN,
            title=parsed_title,
            artist=parsed_artist,
            album="",
            is_playing=bool(source),
            detected_at=time.time(),
            detail=title or "",
        )

    def _classify_from_processes(self) -> str | None:
        if self._psutil is None:
            return None
        try:
            for proc in self._psutil.process_iter(("name", "exe")):
                try:
                    name = (proc.info.get("name") or "").lower()
                except Exception:
                    continue
                hit = _classify(name)
                if hit:
                    return hit
        except Exception:  # pragma: no cover
            return None
        return None

    def _foreground_window_title(self) -> str:
        if self._ctypes is None or sys.platform != "win32":
            return ""
        try:
            user32 = self._ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return ""
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return ""
            buf = self._ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value or ""
        except Exception:  # pragma: no cover
            return ""

    @staticmethod
    def _parse_window_title(
        raw: str, source: str | None,
    ) -> tuple[str, str]:
        if not raw:
            return ("", "")
        text = raw.strip()
        # Spotify pattern: "Title - Artist" (in main window).
        # YT Music browser tab: "Title · Artist - YouTube Music".
        # Apple Music: "Title — Artist" or "Apple Music".
        for sep in (" · ", " — ", " - "):
            if sep in text:
                left, right = text.split(sep, 1)
                left, right = left.strip(), right.strip()
                lower_right = right.lower()
                if any(
                    needle in lower_right
                    for needle in (
                        "youtube music",
                        "spotify",
                        "apple music",
                    )
                ):
                    return (left, "")
                if source == SOURCE_SPOTIFY:
                    return (left, right)
                return (left, right)
        return (text, "")


# --- Public detector ---------------------------------------------------------

ListenerFn = Callable[[NowPlaying], None]


class StreamingDetector:
    """High-level detector combining SMTC and window-title fallback.

    Polling cadence is deliberately conservative (default 2 s) — track changes
    on streaming services typically happen on a 2-5 minute timescale, so the
    overhead is negligible while still feeling instantaneous in the UI.
    """

    def __init__(self, poll_interval: float = 2.0) -> None:
        self.poll_interval = max(0.25, float(poll_interval))
        self._smtc = _SMTCBackend()
        self._fallback = _WindowFallback()
        if sys.platform == "win32" and not self._smtc.available:
            logger.warning(
                "StreamingDetector: SMTC unavailable — falling back to "
                "process/window enumeration only. Title/artist will be "
                "limited unless winsdk is bundled correctly.",
            )
        self._lock = threading.RLock()
        self._current = NowPlaying()
        self._last_track_id = ""
        self._listeners: list[ListenerFn] = []
        self._thread: threading.Thread | None = None
        self._stop_evt = threading.Event()

    # ----- Lifecycle --------------------------------------------------------

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_evt.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="StreamingDetector",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=1.5)
        self._thread = None

    # ----- Snapshot / listeners --------------------------------------------

    def current_track(self) -> NowPlaying:
        with self._lock:
            return self._current

    def add_listener(self, listener: ListenerFn) -> None:
        with self._lock:
            self._listeners.append(listener)

    def remove_listener(self, listener: ListenerFn) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    @property
    def smtc_available(self) -> bool:
        return self._smtc.available

    # ----- Snapshot acquisition (test-friendly) ----------------------------

    def poll_once(self) -> NowPlaying:
        """Run a single detection pass and return the resulting snapshot."""
        snap = self._smtc.snapshot()
        if snap is None or not (snap.title or snap.artist or snap.is_playing):
            fallback = self._fallback.snapshot()
            if fallback is not None and (
                fallback.has_metadata or fallback.is_playing
            ):
                snap = fallback
        if snap is None:
            snap = NowPlaying(detected_at=time.time())
        self._publish(snap)
        return snap

    # ----- Internal --------------------------------------------------------

    def _publish(self, snap: NowPlaying) -> None:
        listeners: list[ListenerFn]
        changed = False
        with self._lock:
            self._current = snap
            tid = snap.track_id
            if tid and tid != self._last_track_id:
                self._last_track_id = tid
                changed = True
            listeners = list(self._listeners) if changed else []
        for listener in listeners:
            try:
                listener(snap)
            except Exception as exc:  # pragma: no cover - listener-specific
                logger.debug("Streaming listener failed: %s", exc)

    def _run(self) -> None:
        # Honour CI / non-Windows tests: do nothing if no backend available.
        if not (self._smtc.available or sys.platform == "win32"):
            return
        while not self._stop_evt.is_set():
            try:
                self.poll_once()
            except Exception:  # pragma: no cover - never let thread die
                logger.exception("StreamingDetector poll failed")
            self._stop_evt.wait(self.poll_interval)


__all__ = [
    "NowPlaying",
    "SOURCE_APPLE_MUSIC",
    "SOURCE_SPOTIFY",
    "SOURCE_UNKNOWN",
    "SOURCE_YOUTUBE_MUSIC",
    "StreamingDetector",
]
