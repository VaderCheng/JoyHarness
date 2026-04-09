"""Keyboard simulation wrapper using the keyboard library.

Provides press/release/tap/combination operations with state tracking
to prevent double-press and ensure cleanup.
"""

import time
import logging

import keyboard

logger = logging.getLogger(__name__)

# Currently held keys — prevents double-press and enables release_all cleanup
_held_keys: set[str] = set()


def press(key: str) -> None:
    """Hold a key down. No-op if already held."""
    if key in _held_keys:
        return
    keyboard.press(key)
    _held_keys.add(key)
    logger.debug("pressed: %s", key)


def release(key: str) -> None:
    """Release a held key. No-op if not currently held."""
    if key not in _held_keys:
        return
    keyboard.release(key)
    _held_keys.discard(key)
    logger.debug("released: %s", key)


def tap(key: str, duration: float = 0.02) -> None:
    """Press and release a key immediately."""
    keyboard.press(key)
    time.sleep(duration)
    keyboard.release(key)
    logger.debug("tapped: %s", key)


def send_combination(keys: list[str], hold: float = 0.05) -> None:
    """Press multiple keys simultaneously, then release in reverse order.

    Example: send_combination(["ctrl", "c"]) → Ctrl+C

    Args:
        keys: Key names in press order.
        hold: Duration to hold all keys before releasing (seconds).
    """
    for key in keys:
        keyboard.press(key)
        time.sleep(0.01)

    time.sleep(hold)

    for key in reversed(keys):
        keyboard.release(key)

    logger.debug("combination: %s", "+".join(keys))


def release_all() -> None:
    """Release every currently held key. Used for cleanup on exit or disconnect."""
    for key in list(_held_keys):
        keyboard.release(key)
        logger.debug("cleanup released: %s", key)
    _held_keys.clear()


def is_held(key: str) -> bool:
    """Check if a key is currently being held."""
    return key in _held_keys
