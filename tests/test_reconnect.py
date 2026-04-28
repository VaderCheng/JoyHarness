"""Hot-plug reconnection test.

Runs the polling loop. You will be asked to:
  1. Move the stick / press buttons (verify live input)
  2. Turn OFF the Joy-Con (hold the power-adjacent buttons for ~3s,
     OR disconnect via macOS Bluetooth settings)
  3. Watch the log for "Joystick disconnected, attempting reconnection..."
  4. Re-pair / wake the Joy-Con — watch for "Controller reconnected"
  5. Move the stick again to verify input resumed
  6. Ctrl+C to exit

Usage:
    python3 test_reconnect.py
"""

import os
import sys
import threading
import time

os.environ.setdefault("SDL_JOYSTICK_HIDAPI_COMBINE_JOY_CONS", "0")

import pygame

from src.joycon_reader import find_joycon, wait_for_reconnection


def main() -> None:
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    pygame.init()
    pygame.joystick.init()

    js = find_joycon(None)
    if js is None:
        print("No Joy-Con detected.")
        sys.exit(1)

    print(f"Controller: {js.get_name()}\n")
    print("Instructions:")
    print("  • Move stick / press buttons — see live output")
    print("  • Turn off Joy-Con OR disconnect via Bluetooth menu")
    print("  • Re-pair / wake the Joy-Con")
    print("  • Move stick again — should still work after reconnect")
    print("  • Ctrl+C to exit\n")

    clock = pygame.time.Clock()
    prev_buttons = set()

    try:
        while True:
            try:
                pygame.event.pump()
                for ev in pygame.event.get(pygame.JOYDEVICEREMOVED):
                    print(f"\n>>> JOYDEVICEREMOVED received (instance_id="
                          f"{getattr(ev, 'instance_id', '?')})")
                    raise pygame.error("Joystick device removed")
                if pygame.joystick.get_count() == 0:
                    raise pygame.error("No joysticks connected")
            except pygame.error:
                print("\n>>> Joystick disconnected — waiting for reconnection...")
                js = wait_for_reconnection(None)
                if js is None:
                    break
                print(f">>> Reconnected: {js.get_name()}")
                prev_buttons = set()
                continue

            # Button state
            cur = set()
            for i in range(js.get_numbuttons()):
                if js.get_button(i):
                    cur.add(i)
            for btn in sorted(cur - prev_buttons):
                print(f"  BTN {btn} pressed")
            for btn in sorted(prev_buttons - cur):
                print(f"  BTN {btn} released")
            prev_buttons = cur

            # Stick state (only when moving)
            for i in range(js.get_numaxes()):
                v = js.get_axis(i)
                if abs(v) > 0.5:
                    print(f"  AXIS {i}: {v:+.2f}", end="\r")

            clock.tick(60)

    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
