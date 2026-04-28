"""Joy-Con keep-alive via periodic zero-intensity rumble.

Sends a rumble report with intensity 0 every 5 minutes to prevent the
Joy-Con from entering sleep mode after ~30 minutes of inactivity.
Uses the same HID protocol as test_rumble_concurrent.py.
"""

from __future__ import annotations

import logging
import threading

import hid

logger = logging.getLogger(__name__)

_VID = 0x057E  # Nintendo
_PID_L = 0x2006  # Joy-Con L
_PID_R = 0x2007  # Joy-Con R

# Motor-off pattern (intensity 0)
_STOP = bytes([0x00, 0x01, 0x40, 0x40])

_KEEP_ALIVE_INTERVAL = 300  # 5 minutes


def _send_rumble(dev, right_data: bytes, counter: int = 0) -> None:
    """Send a rumble-only report (report ID 0x10)."""
    report = bytes([0x10, counter & 0xFF]) + _STOP + right_data
    dev.write(report)


class KeepAliveManager:
    """Periodically sends a zero-intensity rumble to keep Joy-Cons awake.

    Enumerates all connected Joy-Cons (L and R) and sends a rumble report
    to each one every 5 minutes.  Runs in a daemon thread.
    """

    def __init__(self, stop_event: threading.Event) -> None:
        self._stop_event = stop_event
        self._enabled = False
        self._thread: threading.Thread | None = None
        self._counter = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        """Enable or disable the keep-alive loop."""
        if value and not self._enabled:
            self._enabled = True
            if not self._thread or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._loop, daemon=True)
                self._thread.start()
                logger.info("Keep-alive started")
        elif not value and self._enabled:
            self._enabled = False
            logger.info("Keep-alive stopped")

    def _loop(self) -> None:
        """Main loop: send keep-alive rumble to every connected Joy-Con."""
        while not self._stop_event.is_set():
            if self._enabled:
                self._send_keep_alive()
            # Wait 5 minutes (or until stop)
            self._stop_event.wait(_KEEP_ALIVE_INTERVAL)

    def _send_keep_alive(self) -> None:
        """Enumerate Joy-Cons and send zero-intensity rumble to each."""
        for pid in (_PID_L, _PID_R):
            try:
                devices = hid.enumerate(_VID, pid)
            except Exception:
                logger.debug("HID enumerate failed for PID %04X", pid)
                continue

            for dev_info in devices:
                dev = hid.device()
                try:
                    dev.open_path(dev_info["path"])
                    _send_rumble(dev, _STOP, self._counter)
                    self._counter += 1
                    logger.info("Keep-alive sent to %04X", pid)
                except OSError as e:
                    logger.debug("Keep-alive HID open failed: %s", e)
                finally:
                    try:
                        dev.close()
                    except OSError:
                        pass

    def join(self, timeout: float = 2.0) -> None:
        """Wait for the background thread to finish."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
