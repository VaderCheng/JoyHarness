"""Headless test: Joy-Con input → keyboard simulation (no GUI required).

Usage:
    python3 test_headless.py

Press Joy-Con buttons to see simulated key events.
Press Ctrl+C to exit.
"""

import os
import sys
import time

# Prevent SDL2 from merging Joy-Con L+R
os.environ.setdefault("SDL_JOYSTICK_HIDAPI_COMBINE_JOY_CONS", "0")

import pygame
from pynput.keyboard import Controller, Key

# Button → key mapping (subset of DEFAULT_MAPPINGS for quick test)
BUTTON_MAP = {
    1: ("A", "enter"),
    3: ("B", "tab"),
    0: ("X", "f2"),
    2: ("Y", None),       # sequence, skip for now
    6: ("Plus", None),    # combination, skip for now
    7: ("RStick", "tab"),
}

keyboard = Controller()


def tap_key(key_name: str) -> None:
    """Simulate a key tap via pynput."""
    try:
        # Try as special Key enum first
        k = getattr(Key, key_name, None)
        if k is not None:
            keyboard.press(k)
            keyboard.release(k)
        else:
            keyboard.press(key_name)
            keyboard.release(key_name)
        print(f"  → sent key: {key_name}")
    except Exception as e:
        print(f"  ✗ failed to send key '{key_name}': {e}")


def main() -> None:
    pygame.init()
    pygame.joystick.init()

    count = pygame.joystick.get_count()
    if count == 0:
        print("No joystick found. Make sure Joy-Con is connected via Bluetooth.")
        sys.exit(1)

    js = None
    for i in range(count):
        j = pygame.joystick.Joystick(i)
        name = j.get_name().lower()
        if "joy-con" in name or "switch" in name:
            js = j
            break
    if js is None:
        js = pygame.joystick.Joystick(0)

    print(f"Controller: {js.get_name()}")
    print(f"Buttons: {js.get_numbuttons()}, Axes: {js.get_numaxes()}")
    print()
    print("Switch focus to another app (e.g. Obsidian), then press Joy-Con buttons.")
    print("You have 3 seconds...")
    time.sleep(3)
    print("GO! Press buttons. Ctrl+C to quit.\n")

    clock = pygame.time.Clock()
    prev: set[int] = set()

    try:
        while True:
            pygame.event.pump()

            cur: set[int] = set()
            for i in range(js.get_numbuttons()):
                if js.get_button(i):
                    cur.add(i)

            for btn in sorted(cur - prev):
                label, key = BUTTON_MAP.get(btn, (f"BTN{btn}", None))
                if key:
                    print(f"[{label}] pressed → tapping {key}")
                    tap_key(key)
                else:
                    print(f"[{label}] pressed (no key mapped in this test)")

            prev = cur
            clock.tick(60)

    except KeyboardInterrupt:
        print("\nDone.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
