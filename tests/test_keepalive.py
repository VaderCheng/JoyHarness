"""Keep-alive HID write test.

Sends one zero-intensity rumble to the Joy-Con and verifies that SDL2
input polling is not disrupted before and after.

Usage:
    python3 test_keepalive.py
"""

import os
import sys
import threading
import time

os.environ.setdefault("SDL_JOYSTICK_HIDAPI_COMBINE_JOY_CONS", "0")

import pygame

from src.keep_alive import KeepAliveManager


def sample_axes(js, label: str, duration: float = 2.0) -> None:
    """Pump pygame events for `duration` seconds and print axis activity."""
    print(f"[{label}] Sampling axes for {duration}s — move the stick around now.")
    clock = pygame.time.Clock()
    t_end = time.monotonic() + duration
    max_abs = 0.0
    while time.monotonic() < t_end:
        pygame.event.pump()
        for i in range(js.get_numaxes()):
            v = abs(js.get_axis(i))
            if v > max_abs:
                max_abs = v
        clock.tick(60)
    status = "OK (input alive)" if max_abs > 0.05 else "⚠ No axis motion detected"
    print(f"[{label}] Max |axis| = {max_abs:.3f}  → {status}\n")


def main() -> None:
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No Joy-Con detected via pygame.")
        sys.exit(1)

    js = pygame.joystick.Joystick(0)
    print(f"Controller: {js.get_name()}")
    print(f"Buttons: {js.get_numbuttons()}, Axes: {js.get_numaxes()}\n")

    # --- BEFORE keep-alive: verify input stream works
    sample_axes(js, "BEFORE")

    # --- Send one keep-alive pulse
    print(">>> Sending ONE keep-alive HID write (zero-intensity rumble)...")
    stop_event = threading.Event()
    mgr = KeepAliveManager(stop_event)
    # Call the internal method directly so we don't have to wait 5 minutes
    mgr._send_keep_alive()
    print(">>> Done. Check logs above for 'Keep-alive sent to ...'\n")

    # Small pause, then re-test input
    time.sleep(0.5)

    # --- AFTER keep-alive: verify input still works
    sample_axes(js, "AFTER")

    stop_event.set()
    pygame.quit()
    print("Test complete.")


if __name__ == "__main__":
    # Enable INFO logs so we see "Keep-alive sent to XXXX"
    import logging
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
    main()
