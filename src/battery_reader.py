"""Joy-Con battery level reader via raw HID protocol.

Runs a background daemon thread per connected Joy-Con, reading battery
status from the standard input report (report 0x30, byte 2 high nibble).
Supports both Joy-Con L (PID 0x2006) and Joy-Con R (PID 0x2007).
Works concurrently with pygame's joystick polling.

Thread-safe: writes to shared variables protected by a threading.Lock.
The GUI reads these variables via root.after() polling.
"""

import logging
import threading

import hid

logger = logging.getLogger(__name__)

_VID = 0x057E  # Nintendo
_PID_L = 0x2006  # Joy-Con L
_PID_R = 0x2007  # Joy-Con R


def battery_label(nibble: int) -> tuple[str, int]:
    """Return (status_string, percentage) from the 4-bit battery value.

    Values 0x00-0x08: discharging, each step ~12.5%.
    Values 0x09-0x0F: charging.
    """
    if nibble <= 0x08:
        return ("discharging", min(nibble * 125 // 10, 100))
    elif nibble <= 0x0F:
        return ("charging", min((nibble & 0x0F) * 125 // 10, 100))
    return ("unknown", -1)


def _find_joycons() -> list[dict]:
    """Find all connected Joy-Con L and R HID devices."""
    results = []
    for d in hid.enumerate(_VID, _PID_L):
        d["_side"] = "L"
        results.append(d)
    for d in hid.enumerate(_VID, _PID_R):
        d["_side"] = "R"
        results.append(d)
    return results


def _safe_close(dev) -> None:
    """Close HID device, swallowing errors if already disconnected."""
    try:
        dev.close()
    except OSError:
        pass


def _read_battery_from_device(dev_info: dict, stop_event: threading.Event) -> tuple[str, int] | None:
    """Open a single Joy-Con HID device and read one battery report.

    Returns (status, pct) on success, None on failure.
    """
    dev = hid.device()
    try:
        dev.open_path(dev_info["path"])
    except OSError as e:
        logger.warning("Cannot open HID for battery (%s): %s", dev_info["_side"], e)
        return None

    # Set input report mode to 0x30
    report_mode_cmd = bytes([
        0x01, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00,
        0x03,  # subcommand: set report mode
        0x30,  # mode: standard full
    ])
    try:
        dev.write(report_mode_cmd)
    except OSError:
        _safe_close(dev)
        return None

    # Read until we get a valid battery report or give up
    for _ in range(50):
        try:
            data = dev.read(64, timeout_ms=500)
        except OSError:
            break
        if not data or len(data) < 3:
            continue
        if data[0] not in (0x30, 0x3F):
            continue
        battery_nibble = (data[2] >> 4) & 0x0F
        _safe_close(dev)
        return battery_label(battery_nibble)

    _safe_close(dev)
    return None


class BatteryReader:
    """Reads Joy-Con L and R battery levels in a background thread.

    Stores the latest readings in thread-safe shared state that the GUI
    can poll via ``get_state()``.
    """

    def __init__(self, stop_event: threading.Event) -> None:
        self._stop_event = stop_event
        self._thread: threading.Thread | None = None

        # Shared state (protected by lock) — one entry per side
        self._lock = threading.Lock()
        self._states: dict[str, tuple[str, int]] = {
            "L": ("unknown", -1),
            "R": ("unknown", -1),
        }

    # -- public API for the GUI --

    def get_state(self) -> dict[str, tuple[str, int]]:
        """Return {"L": (status, pct), "R": (status, pct)}. Thread-safe."""
        with self._lock:
            return dict(self._states)

    def start(self) -> None:
        """Start the background reading thread."""
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the thread to stop."""
        self._stop_event.set()

    def join(self, timeout: float = 2.0) -> None:
        """Wait for the background thread to finish."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    # -- internal --

    def _set_state(self, side: str, status: str, pct: int) -> None:
        with self._lock:
            self._states[side] = (status, pct)

    def _read_loop(self) -> None:
        """Main loop: enumerate Joy-Cons, read each one, sleep, repeat."""
        while not self._stop_event.is_set():
            devices = _find_joycons()

            if not devices:
                self._set_state("L", "disconnected", -1)
                self._set_state("R", "disconnected", -1)
                self._stop_event.wait(5)
                continue

            # Track which sides we found this cycle
            found_sides = set()

            for dev_info in devices:
                side = dev_info["_side"]
                found_sides.add(side)

                result = _read_battery_from_device(dev_info, self._stop_event)
                if result:
                    status, pct = result
                    self._set_state(side, status, pct)
                    logger.debug("Battery %s: %s %d%%", side, status, pct)
                else:
                    self._set_state(side, "disconnected", -1)

            # Mark missing sides as disconnected
            for side in ("L", "R"):
                if side not in found_sides:
                    self._set_state(side, "disconnected", -1)

            # Wait before next round of readings
            self._stop_event.wait(5)
