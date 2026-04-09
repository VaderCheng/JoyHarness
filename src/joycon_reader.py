"""pygame-based Joy-Con R detection and polling loop.

Handles controller discovery, button state polling, axis reading,
disconnection detection, and automatic reconnection.
"""

from __future__ import annotations

import threading
import time
import logging

import pygame

from .constants import (
    AXIS_RSTICK_X,
    AXIS_RSTICK_Y,
    BUTTON_NAMES,
    SNAPBACK_FRAMES,
)
from .joystick_handler import apply_deadzone, get_direction
from .key_mapper import KeyMapper

logger = logging.getLogger(__name__)

# Reconnection scan interval in seconds
RECONNECT_INTERVAL = 2.0


def find_joycon(joystick_index: int | None = None) -> pygame.joystick.Joystick | None:
    """Find and return a Joy-Con R joystick instance.

    Args:
        joystick_index: Specific device index to use. None for auto-detection.

    Returns:
        pygame Joystick instance, or None if not found.
    """
    pygame.joystick.init()
    count = pygame.joystick.get_count()

    if count == 0:
        return None

    logger.info("Found %d joystick(s)", count)

    if joystick_index is not None:
        if 0 <= joystick_index < count:
            js = pygame.joystick.Joystick(joystick_index)
            logger.info("Using joystick #%d: %s", joystick_index, js.get_name())
            return js
        logger.error("Joystick index %d out of range (0-%d)", joystick_index, count - 1)
        return None

    # Auto-detect: look for Joy-Con in device names
    for i in range(count):
        js = pygame.joystick.Joystick(i)
        name = js.get_name().lower()
        logger.info("  [%d] %s (buttons=%d, axes=%d)",
                     i, js.get_name(), js.get_numbuttons(), js.get_numaxes())

        if "joy-con" in name or "joy con" in name or "switch" in name:
            if "r" in name or count == 1:
                logger.info("Auto-selected joystick [%d]: %s", i, js.get_name())
                return js

    # Fallback: if only one joystick, use it
    if count == 1:
        js = pygame.joystick.Joystick(0)
        logger.info("Single joystick found, using: %s", js.get_name())
        return js

    logger.warning("No Joy-Con detected among %d joysticks", count)
    return None


def run_discover_mode(joystick_index: int | None = None) -> None:
    """Run discovery mode: print raw button/axis values for calibration.

    Press Ctrl+C to exit. Use this to determine correct button indices
    for your specific controller/driver combination.
    """
    pygame.init()
    js = find_joycon(joystick_index)

    if js is None:
        print("No joystick found. Make sure your Joy-Con R is connected via Bluetooth.")
        print("Tip: Windows Settings → Bluetooth → Add device → hold the small pairing")
        print("     button on the Joy-Con rail for 3 seconds until lights flash.")
        pygame.quit()
        return

    print(f"\n=== Discovery Mode ===")
    print(f"Controller: {js.get_name()}")
    print(f"GUID: {js.get_guid()}")
    print(f"Buttons: {js.get_numbuttons()}")
    print(f"Axes: {js.get_numaxes()}")
    print(f"\nPress buttons and move sticks to see their indices.")
    print(f"Press Ctrl+C to exit.\n")

    clock = pygame.time.Clock()
    prev_buttons: set[int] = set()

    try:
        while True:
            pygame.event.pump()

            # Button state
            current_buttons: set[int] = set()
            for i in range(js.get_numbuttons()):
                if js.get_button(i):
                    current_buttons.add(i)

            pressed = current_buttons - prev_buttons
            released = prev_buttons - current_buttons

            for i in sorted(pressed):
                name = BUTTON_NAMES.get(i, "???")
                print(f"  BTN {i:2d} ({name:8s}) PRESSED")

            for i in sorted(released):
                name = BUTTON_NAMES.get(i, "???")
                print(f"  BTN {i:2d} ({name:8s}) released")

            prev_buttons = current_buttons

            # Axis state (only print if changed significantly)
            for i in range(js.get_numaxes()):
                val = js.get_axis(i)
                if abs(val) > 0.1:
                    print(f"  AXIS {i}: {val:+.3f}", end="\r")

            clock.tick(60)

    except KeyboardInterrupt:
        print("\nDiscovery mode ended.")
    finally:
        pygame.quit()


def run_polling_loop(
    joystick: pygame.joystick.Joystick,
    key_mapper: KeyMapper,
    config: dict,
    stop_event: threading.Event | None = None,
) -> None:
    """Main polling loop: read controller state and dispatch to key_mapper.

    Args:
        joystick: Initialized pygame Joystick instance.
        key_mapper: KeyMapper instance for action dispatch.
        config: Complete configuration dict.
        stop_event: Threading event to signal loop exit. None = run until Ctrl+C.
    """
    deadzone = config.get("deadzone", 0.15)
    poll_interval = config.get("poll_interval", 0.01)
    stick_mode = config.get("stick_mode", "4dir")
    axis_x = config.get("axis_x", AXIS_RSTICK_X)
    axis_y = config.get("axis_y", AXIS_RSTICK_Y)

    clock = pygame.time.Clock()
    prev_buttons: set[int] = set()
    prev_direction: str | None = None
    center_count: int = 0

    logger.info("Polling started (deadzone=%.2f, interval=%.0fms, mode=%s)",
                deadzone, poll_interval * 1000, stick_mode)

    try:
        while not (stop_event and stop_event.is_set()):
            pygame.event.pump()

            # --- Button polling ---
            current_buttons: set[int] = set()
            for i in range(joystick.get_numbuttons()):
                if joystick.get_button(i):
                    current_buttons.add(i)

            pressed = current_buttons - prev_buttons
            released = prev_buttons - current_buttons

            for btn_idx in sorted(pressed):
                key_mapper.button_down(btn_idx)

            for btn_idx in sorted(released):
                key_mapper.button_up(btn_idx)

            prev_buttons = current_buttons

            # --- Stick polling ---
            raw_x = joystick.get_axis(axis_x)
            raw_y = joystick.get_axis(axis_y)
            filt_x, filt_y = apply_deadzone(raw_x, raw_y, deadzone)
            direction = get_direction(filt_x, filt_y, stick_mode)

            if direction != prev_direction:
                if direction is None:
                    center_count += 1
                    if center_count >= SNAPBACK_FRAMES:
                        key_mapper.stick_centered()
                        prev_direction = None
                else:
                    center_count = 0
                    key_mapper.stick_direction(direction)
                    prev_direction = direction

            # Process auto-action long press detection
            key_mapper.poll()

            clock.tick(1 / poll_interval)

    except KeyboardInterrupt:
        logger.info("Polling interrupted by user")
    finally:
        key_mapper.release_all()
        from . import keyboard_output
        keyboard_output.release_all()


def wait_for_reconnection(joystick_index: int | None = None) -> pygame.joystick.Joystick | None:
    """Scan for Joy-Con reconnection every RECONNECT_INTERVAL seconds.

    Returns a new Joystick instance when found, or None if interrupted.
    """
    logger.info("Controller disconnected. Waiting for reconnection...")

    try:
        while True:
            time.sleep(RECONNECT_INTERVAL)
            # Re-init joystick subsystem to scan for new devices
            pygame.joystick.quit()
            pygame.joystick.init()
            js = find_joycon(joystick_index)
            if js is not None:
                logger.info("Controller reconnected: %s", js.get_name())
                return js
    except KeyboardInterrupt:
        return None
