"""Headless battery test: read Joy-Con battery via hidapi.

Usage:
    python3 test_battery.py
"""

import os
import sys
import threading
import time

os.environ.setdefault("SDL_JOYSTICK_HIDAPI_COMBINE_JOY_CONS", "0")

# Also start pygame to simulate the real environment where pygame is polling
import pygame

from src.battery_reader import BatteryReader, _find_joycons


def main() -> None:
    print("=== Joy-Con HID enumeration ===")
    devices = _find_joycons()
    if not devices:
        print("No Joy-Con HID devices found.")
        print("Check: System Settings → Bluetooth → is Joy-Con listed as connected?")
        sys.exit(1)

    for d in devices:
        print(f"  Side: {d['_side']}")
        print(f"    VID/PID: {d['vendor_id']:#06x} / {d['product_id']:#06x}")
        print(f"    Product: {d.get('product_string', '?')}")
        print(f"    Path:    {d['path']}")
        print()

    # Start pygame to simulate concurrent SDL2 usage
    print("=== Starting pygame (SDL2 will also hold the HID) ===")
    pygame.init()
    pygame.joystick.init()
    js_count = pygame.joystick.get_count()
    print(f"pygame joysticks: {js_count}")
    if js_count > 0:
        js = pygame.joystick.Joystick(0)
        print(f"  [{0}] {js.get_name()}")
    print()

    # Now start BatteryReader
    print("=== BatteryReader running (reads every 5s, 3 cycles) ===")
    stop_event = threading.Event()
    reader = BatteryReader(stop_event)
    reader.start()

    try:
        for i in range(3):
            time.sleep(6)  # Let reader do one cycle
            state = reader.get_state()
            print(f"Cycle {i+1}:")
            for side, (status, pct) in state.items():
                print(f"  {side}: status={status}, pct={pct}%")
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        reader.join(timeout=2.0)
        pygame.quit()
        print("\nDone.")


if __name__ == "__main__":
    main()
