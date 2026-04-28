"""Keyboard simulation wrapper — cross-platform.

On Windows: uses the `keyboard` library (requires administrator).
On macOS:   uses `pynput` (requires Accessibility permission).

Provides press/release/tap/combination operations with state tracking
to prevent double-press and ensure cleanup.
"""

from __future__ import annotations

import sys
import time
import logging

logger = logging.getLogger(__name__)

_held_keys: set[str] = set()

# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

if sys.platform == "darwin":
    from pynput.keyboard import Controller as _Controller, Key as _Key

    _kb = _Controller()

    _SPECIAL_KEYS: dict[str, _Key] = {
        "ctrl": _Key.ctrl,
        "control": _Key.ctrl,
        "ctrl_l": _Key.ctrl,
        "ctrl_r": _Key.ctrl_r,
        "alt": _Key.alt,
        "alt_l": _Key.alt,
        "alt_r": _Key.alt_r,
        "option": _Key.alt,
        "shift": _Key.shift,
        "shift_l": _Key.shift,
        "shift_r": _Key.shift_r,
        "cmd": _Key.cmd,
        "command": _Key.cmd,
        "cmd_l": _Key.cmd,
        "cmd_r": _Key.cmd_r,
        "windows": _Key.cmd,
        "win": _Key.cmd,
        "super": _Key.cmd,
        "enter": _Key.enter,
        "return": _Key.enter,
        "tab": _Key.tab,
        "space": _Key.space,
        "backspace": _Key.backspace,
        "delete": _Key.delete,
        "escape": _Key.esc,
        "esc": _Key.esc,
        "up": _Key.up,
        "down": _Key.down,
        "left": _Key.left,
        "right": _Key.right,
        "home": _Key.home,
        "end": _Key.end,
        "page_up": _Key.page_up,
        "page_down": _Key.page_down,
        "caps_lock": _Key.caps_lock,
        "f1": _Key.f1,
        "f2": _Key.f2,
        "f3": _Key.f3,
        "f4": _Key.f4,
        "f5": _Key.f5,
        "f6": _Key.f6,
        "f7": _Key.f7,
        "f8": _Key.f8,
        "f9": _Key.f9,
        "f10": _Key.f10,
        "f11": _Key.f11,
        "f12": _Key.f12,
        "f13": _Key.f13,
        "f14": _Key.f14,
        "f15": _Key.f15,
        "f16": _Key.f16,
        "f17": _Key.f17,
        "f18": _Key.f18,
        "f19": _Key.f19,
        "f20": _Key.f20,
    }

    # Keys that exist on Windows but not macOS — map to closest equivalents
    _FALLBACK_KEYS: dict[str, str] = {
        "print_screen": "f13",
        "insert": "f14",
        "menu": "f15",
        "num_lock": "f16",
        "pause": "f17",
        "scroll_lock": "f18",
    }

    def _resolve_key(key_name: str):
        """Convert a key name string to a pynput key object."""
        lower = key_name.lower().strip()
        if lower in _SPECIAL_KEYS:
            return _SPECIAL_KEYS[lower]
        if lower in _FALLBACK_KEYS:
            fallback = _FALLBACK_KEYS[lower]
            return _SPECIAL_KEYS.get(fallback, fallback)
        if len(lower) == 1:
            return lower
        return lower

    def _do_press(key_name: str) -> None:
        _kb.press(_resolve_key(key_name))

    def _do_release(key_name: str) -> None:
        _kb.release(_resolve_key(key_name))

    def _do_type_text(text: str) -> None:
        _kb.type(text)

    def is_valid_key(key_name: str) -> bool:
        """Check if a key name is recognized."""
        lower = key_name.lower().strip()
        if lower in _SPECIAL_KEYS:
            return True
        if lower in _FALLBACK_KEYS:
            return True
        if len(lower) == 1:
            return True
        return False

else:
    import keyboard as _keyboard

    def _do_press(key_name: str) -> None:
        _keyboard.press(key_name)

    def _do_release(key_name: str) -> None:
        _keyboard.release(key_name)

    def _do_type_text(text: str) -> None:
        _keyboard.write(text)

    def is_valid_key(key_name: str) -> bool:
        """Check if a key name is recognized by the keyboard library."""
        try:
            codes = _keyboard.key_to_scan_codes(key_name)
            return len(codes) > 0
        except (ValueError, KeyError):
            return False


# ---------------------------------------------------------------------------
# Public API (unchanged interface)
# ---------------------------------------------------------------------------

def press(key: str) -> None:
    """Hold a key down. No-op if already held."""
    if key in _held_keys:
        return
    _do_press(key)
    _held_keys.add(key)
    logger.debug("pressed: %s", key)


def release(key: str) -> None:
    """Release a held key. No-op if not currently held."""
    if key not in _held_keys:
        return
    _do_release(key)
    _held_keys.discard(key)
    logger.debug("released: %s", key)


def tap(key: str, duration: float = 0.02) -> None:
    """Press and release a key immediately.

    If the key is currently held (tracked in _held_keys), temporarily
    release it, re-tap, then restore the held state.
    """
    was_held = key in _held_keys
    if was_held:
        _do_release(key)
        _held_keys.discard(key)

    _do_press(key)
    time.sleep(duration)
    _do_release(key)

    if was_held:
        _do_press(key)
        _held_keys.add(key)

    logger.debug("tapped: %s (was_held=%s)", key, was_held)


def send_combination(keys: list[str], hold: float = 0.05) -> None:
    """Press multiple keys simultaneously, then release in reverse order.

    Example: send_combination(["ctrl", "c"]) -> Ctrl+C

    Keys that are currently held via press() are temporarily released,
    then restored after the combination completes.

    Args:
        keys: Key names in press order.
        hold: Duration to hold all keys before releasing (seconds).
    """
    held_in_combo = [k for k in keys if k in _held_keys]
    for k in held_in_combo:
        _do_release(k)
        _held_keys.discard(k)

    for key in keys:
        _do_press(key)
        time.sleep(0.01)

    time.sleep(hold)

    for key in reversed(keys):
        _do_release(key)

    for k in held_in_combo:
        _do_press(k)
        _held_keys.add(k)

    logger.debug("combination: %s", "+".join(keys))


def release_all() -> None:
    """Release every currently held key. Used for cleanup on exit or disconnect."""
    for key in list(_held_keys):
        _do_release(key)
        logger.debug("cleanup released: %s", key)
    _held_keys.clear()


def is_held(key: str) -> bool:
    """Check if a key is currently being held."""
    return key in _held_keys


def type_text(text: str) -> None:
    """Type a string."""
    _do_type_text(text)
    logger.debug("typed: %s", text)
