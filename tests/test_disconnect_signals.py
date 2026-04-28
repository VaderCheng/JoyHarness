"""Diagnose what signals pygame/SDL2 emit on Joy-Con disconnect on macOS.

Watches ALL possible disconnect indicators simultaneously:
  1. pygame events (JOYDEVICEREMOVED / JOYDEVICEADDED)
  2. pygame.event.pump() raising pygame.error
  3. joystick.get_init() returning False
  4. Axis values freezing
  5. get_numbuttons/get_numaxes returning 0 or raising
  6. pygame.joystick.get_count() change

Usage:
    python3 test_disconnect_signals.py

Steps:
  • Let it run, press buttons a few times
  • Disconnect via macOS Bluetooth
  • Watch what fires
  • Reconnect, watch what fires
  • Ctrl+C to exit
"""

import os
import sys
import time

os.environ.setdefault("SDL_JOYSTICK_HIDAPI_COMBINE_JOY_CONS", "0")

import pygame

# All event types we want to monitor, with readable names
_EVENT_NAMES = {}
for attr in dir(pygame):
    val = getattr(pygame, attr)
    if isinstance(val, int) and attr.startswith(("JOY", "CONTROLLER")):
        _EVENT_NAMES[val] = attr


def main() -> None:
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No Joy-Con found.")
        sys.exit(1)

    js = pygame.joystick.Joystick(0)
    print(f"Controller: {js.get_name()}")
    print(f"Instance ID: {js.get_instance_id()}")
    print()
    print("Watching for disconnect signals. Try disconnecting/reconnecting now.")
    print("Ctrl+C to exit.\n")

    last_axis0 = None
    last_count = pygame.joystick.get_count()
    last_init = js.get_init()
    freeze_start = None

    tick = 0
    try:
        while True:
            tick += 1

            # --- Method 1: pygame.event.pump() raising
            pump_error = None
            try:
                pygame.event.pump()
            except pygame.error as e:
                pump_error = str(e)

            if pump_error:
                print(f"[tick {tick}] 🔴 pygame.event.pump() raised: {pump_error}")

            # --- Method 2: event queue (JOYDEVICEREMOVED etc.)
            for ev in pygame.event.get():
                name = _EVENT_NAMES.get(ev.type, f"type={ev.type}")
                info = ""
                if hasattr(ev, "instance_id"):
                    info = f" instance_id={ev.instance_id}"
                elif hasattr(ev, "device_index"):
                    info = f" device_index={ev.device_index}"
                print(f"[tick {tick}] 🔔 EVENT: {name}{info}")

            # --- Method 3: joystick.get_init()
            try:
                cur_init = js.get_init()
            except Exception as e:
                cur_init = None
                print(f"[tick {tick}] 🔴 get_init() raised: {e}")
            if cur_init != last_init:
                print(f"[tick {tick}] ⚠ get_init() changed: {last_init} → {cur_init}")
                last_init = cur_init

            # --- Method 4: pygame.joystick.get_count() change
            cur_count = pygame.joystick.get_count()
            if cur_count != last_count:
                print(f"[tick {tick}] ⚠ get_count() changed: {last_count} → {cur_count}")
                last_count = cur_count

            # --- Method 5: axis values / get_numbuttons probe
            try:
                axis0 = js.get_axis(0)
                nbtn = js.get_numbuttons()
                # Detect freeze: same axis0 for 5+ seconds with no pump activity
                if axis0 == last_axis0:
                    if freeze_start is None:
                        freeze_start = time.monotonic()
                    elif time.monotonic() - freeze_start > 5 and tick % 30 == 0:
                        # Print occasionally so we know it's frozen but not re-init
                        pass
                else:
                    if freeze_start is not None and time.monotonic() - freeze_start > 3:
                        print(f"[tick {tick}] ↻ axis0 unfroze after "
                              f"{time.monotonic() - freeze_start:.1f}s")
                    freeze_start = None
                last_axis0 = axis0
            except Exception as e:
                print(f"[tick {tick}] 🔴 get_axis/get_numbuttons raised: {e}")

            # Every ~3s, print a heartbeat with current state
            if tick % 180 == 0:
                print(f"[tick {tick}] heartbeat: count={cur_count}, init={cur_init}, "
                      f"axis0={last_axis0:.3f}, nbtn={nbtn}")

            time.sleep(1 / 60)

    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
