"""
Windows MMDevice API notifications for default render endpoint changes.

Uses pycaw's MMNotificationClient so loopback capture can resync without
relying only on polling. Callbacks run on a COM worker thread; the caller
must schedule work on the UI thread (e.g. QTimer.singleShot).
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

ScheduleFn = Callable[[str], None]


class NotificationHandle:
    """Keeps COM enumerator + client alive; call close() to unregister."""

    def __init__(self, enumerator: Any, client: Any) -> None:
        self._enumerator = enumerator
        self._client = client

    def close(self) -> None:
        try:
            self._enumerator.UnregisterEndpointNotificationCallback(self._client)
            logger.info("MMDevice endpoint notification unregistered")
        except Exception as e:
            logger.debug("UnregisterEndpointNotificationCallback: %s", e)
        finally:
            self._enumerator = None
            self._client = None


def start_render_endpoint_notifier(schedule: ScheduleFn) -> NotificationHandle | None:
    """Register for render-device / property notifications.

    `schedule(reason)` is invoked from a COM thread for each relevant event;
    use a thread-safe delegate (e.g. ``lambda r: QTimer.singleShot(0, lambda: slot(r))``).
    """
    try:
        from pycaw.callbacks import MMNotificationClient
        from pycaw.utils import AudioUtilities
    except ImportError:
        logger.debug("pycaw not available; MMDevice notifications disabled")
        return None

    class _Client(MMNotificationClient):
        """eRender == flow_id 0 (pycaw DataFlow order)."""

        def __init__(self, fire: ScheduleFn) -> None:
            super().__init__()
            self._fire = fire

        def on_default_device_changed(
            self,
            flow: str,
            flow_id: int,
            role: str,
            role_id: int,
            default_device_id: str,
        ) -> None:
            if flow_id == 0:
                self._fire("default_render_device")

        def on_device_state_changed(
            self,
            device_id: str,
            new_state: str,
            new_state_id: int,
        ) -> None:
            self._fire("device_state")

        def on_property_value_changed(
            self,
            device_id: str,
            property_struct: object,
            fmtid: object,
            pid: int,
        ) -> None:
            self._fire("device_property")

    try:
        enumerator = AudioUtilities.GetDeviceEnumerator()
        client = _Client(schedule)
        enumerator.RegisterEndpointNotificationCallback(client)
        logger.info("MMDevice endpoint notification registered")
        return NotificationHandle(enumerator, client)
    except Exception as e:
        logger.warning("MMDevice notification registration failed: %s", e)
        return None
