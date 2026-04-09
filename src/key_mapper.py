"""Button/axis event to keyboard action translation engine.

Translates Joy-Con R button presses and stick directions into keyboard
actions based on the loaded configuration. Handles these action types:
- tap: press and release immediately (short press)
- hold: press on button_down, release on button_up (for modifier keys)
- auto: short press = tap, long press = hold (adaptive)
- combination: press multiple keys simultaneously
- sequence: hold modifier + tap keys, release on button up (e.g. Alt+Tab)
- window_switch: cycle through VS Code windows
"""

import time
import logging

from . import keyboard_output
from .constants import BUTTON_INDICES
from .switcher_overlay import SwitcherOverlay
from .window_switcher import WindowCycler, get_foreground_process_name, find_windows

logger = logging.getLogger(__name__)

# Duration threshold to distinguish short press from long press (seconds)
LONG_PRESS_THRESHOLD = 0.25


class KeyMapper:
    """Maps controller events to keyboard actions using a configuration dict."""

    def __init__(self, config: dict) -> None:
        """Initialize with a validated config dict."""
        mappings = config.get("mappings", {})
        long_threshold = config.get("long_press_threshold", LONG_PRESS_THRESHOLD)

        # Build button index → mapping dict
        self._button_mappings: dict[int, dict] = {}
        for btn_name, mapping in mappings.get("buttons", {}).items():
            if btn_name in BUTTON_INDICES:
                self._button_mappings[BUTTON_INDICES[btn_name]] = mapping

        # Build direction → mapping dict
        self._direction_mappings: dict[str, dict] = {}
        for direction, mapping in mappings.get("stick_directions", {}).items():
            self._direction_mappings[direction] = mapping

        # Track currently active modifier/hold keys: btn_idx → key_name
        self._active_holds: dict[int, str] = {}

        # Track active sequence holds: btn_idx → list of keys
        self._active_sequences: dict[int, list[str]] = {}

        # Track sequence repeat: btn_idx → {keys, interval, last_time}
        self._sequence_repeat: dict[int, dict] = {}

        # Track stick direction repeat: ("stick", direction) → {key, interval, last_time}
        self._stick_repeat: dict[tuple, dict] = {}

        # Track auto-action pending state: btn_idx → (key, press_time)
        self._auto_pending: dict[int, tuple[str, float]] = {}

        self._long_threshold = long_threshold

        # Stick mapping enabled (controllable from GUI)
        self._stick_enabled: bool = True

        # Window cycler for VS Code window switching
        self._window_cycler = WindowCycler()

        # Window switch overlay and state (tkinter root set later via set_tk_root)
        self._switcher_overlay: SwitcherOverlay | None = None
        self._ws_held: bool = False
        self._ws_press_time: float = 0.0
        self._ws_overlay_active: bool = False
        self._ws_last_move: float = 0.0
        self._ws_move_interval: float = config.get("switch_scroll_interval", 400) / 1000.0

        logger.info(
            "KeyMapper initialized: %d button mappings, %d direction mappings, "
            "long_press_threshold=%.2fs",
            len(self._button_mappings),
            len(self._direction_mappings),
            self._long_threshold,
        )

    def _on_overlay_select(self, window_info) -> None:
        """Callback when overlay selection is confirmed."""
        from .window_switcher import switch_to_window
        switch_to_window(window_info.hwnd)

    def set_tk_root(self, root) -> None:
        """Set the tkinter root for overlay creation. Call from main thread."""
        import tkinter as tk
        if isinstance(root, tk.Tk) and self._switcher_overlay is None:
            self._switcher_overlay = SwitcherOverlay(root, on_select=self._on_overlay_select)

    def _find_current_window_index(self, windows: list) -> int:
        """Find the index of the current foreground window in the list."""
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        for i, w in enumerate(windows):
            if w.hwnd == hwnd:
                return i
        return 0

    def button_down(self, button_index: int) -> None:
        """Handle a button press event."""
        mapping = self._button_mappings.get(button_index)
        if mapping is None:
            return

        action = mapping["action"]
        btn_name = _button_label(button_index)

        if action == "hold":
            key = mapping["key"]
            keyboard_output.press(key)
            self._active_holds[button_index] = key
            logger.debug("hold DOWN [%s] → %s", btn_name, key)

        elif action == "tap":
            key = mapping["key"]
            keyboard_output.tap(key)
            logger.debug("tap [%s] → %s", btn_name, key)

        elif action == "auto":
            # Don't act yet — wait to see if it's short or long press
            key = mapping["key"]
            self._auto_pending[button_index] = (key, time.monotonic())
            logger.debug("auto DOWN [%s] → %s (waiting)", btn_name, key)

        elif action == "combination":
            keys = mapping["keys"]
            keyboard_output.send_combination(keys)
            logger.debug("combination [%s] → %s", btn_name, "+".join(keys))

        elif action == "sequence":
            # Press first key (modifier) and hold, then tap remaining keys
            keys = mapping["keys"]
            repeat_ms = mapping.get("repeat", 0)
            # Press modifier (first key) and hold
            keyboard_output.press(keys[0])
            time.sleep(0.02)
            # Tap subsequent keys once
            for key in keys[1:]:
                keyboard_output.tap(key)
            self._active_holds[button_index] = "__sequence__"
            self._active_sequences[button_index] = keys
            # If repeat enabled, set up repeat for keys[1:]
            if repeat_ms > 0 and len(keys) > 1:
                self._sequence_repeat[button_index] = {
                    "keys": keys[1:],
                    "interval": repeat_ms / 1000.0,
                    "last_time": time.monotonic(),
                }
            logger.debug("sequence DOWN [%s] → %s (held, repeat=%sms)",
                         btn_name, "+".join(keys), repeat_ms)

        elif action == "window_switch":
            # Record press time, decide short vs long in poll/button_up
            self._ws_held = True
            self._ws_press_time = time.monotonic()
            self._ws_overlay_active = False
            logger.debug("window_switch DOWN [%s] (waiting)", btn_name)

        elif action == "macro":
            self._execute_macro(mapping, btn_name)

    def button_up(self, button_index: int) -> None:
        """Handle a button release event."""
        btn_name = _button_label(button_index)

        # Handle sequence release (reverse order)
        if button_index in self._active_sequences:
            self._sequence_repeat.pop(button_index, None)
            keys = self._active_sequences.pop(button_index)
            for key in reversed(keys):
                keyboard_output.release(key)
            logger.debug("sequence UP [%s] → %s released", btn_name, "+".join(keys))
            return

        # Handle hold release
        if button_index in self._active_holds:
            key = self._active_holds.pop(button_index)
            keyboard_output.release(key)
            logger.debug("hold UP [%s] → %s released", btn_name, key)
            return

        # Handle auto release
        if button_index in self._auto_pending:
            key, press_time = self._auto_pending.pop(button_index)
            elapsed = time.monotonic() - press_time

            if elapsed < self._long_threshold:
                # Short press → tap
                keyboard_output.tap(key)
                logger.debug("auto UP [%s] → tap %s (%.0fms)", btn_name, key, elapsed * 1000)
            else:
                # Long press was already activated in poll — just release
                keyboard_output.release(key)
                if button_index in self._active_holds:
                    self._active_holds.pop(button_index, None)
                logger.debug("auto UP [%s] → release %s (%.0fms)", btn_name, key, elapsed * 1000)

        # Handle window_switch release
        if self._ws_held:
            self._ws_held = False
            btn_name = _button_label(button_index)

            if self._ws_overlay_active and self._switcher_overlay:
                # Long press: select the highlighted window and hide overlay
                selected = self._switcher_overlay.selected
                self._switcher_overlay.hide()
                self._ws_overlay_active = False
                if selected:
                    self._on_overlay_select(selected)
                    logger.info("window_switch UP [%s] → selected: %s", btn_name, selected.title)
            else:
                # Short press: immediate switch to next
                target = self._window_cycler.next()
                if target:
                    logger.info("window_switch UP [%s] → quick: %s", btn_name, target.title)
                else:
                    logger.warning("window_switch UP [%s] → no windows found", btn_name)

    def poll(self) -> None:
        """Call every polling cycle to handle auto-action long press activation.

        Checks if any pending auto-action (button or stick) has exceeded
        the long press threshold, and if so, activates the hold.
        """
        now = time.monotonic()

        # Button auto-actions
        for btn_idx in list(self._auto_pending.keys()):
            key, press_time = self._auto_pending[btn_idx]
            if now - press_time >= self._long_threshold:
                keyboard_output.press(key)
                self._active_holds[btn_idx] = key
                btn_name = _button_label(btn_idx)
                logger.debug("auto HOLD [%s] → %s (after %.0fms)",
                             btn_name, key, (now - press_time) * 1000)
                del self._auto_pending[btn_idx]

        # Stick auto-actions: already activated immediately in stick_direction(), no pending check needed

        # Sequence repeat (e.g., Alt held + Tab every N ms)
        for btn_idx in list(self._sequence_repeat.keys()):
            info = self._sequence_repeat[btn_idx]
            if now - info["last_time"] >= info["interval"]:
                for key in info["keys"]:
                    keyboard_output.tap(key)
                info["last_time"] = now
                btn_name = _button_label(btn_idx)
                logger.debug("sequence repeat [%s] → %s", btn_name, "+".join(info["keys"]))

        # Stick direction repeat (e.g., arrow key every 100ms while held)
        for k in list(self._stick_repeat.keys()):
            info = self._stick_repeat[k]
            if now - info["last_time"] >= info["interval"]:
                keyboard_output.tap(info["key"])
                info["last_time"] = now
                logger.debug("stick repeat [%s] → %s", k[1], info["key"])

        # Window switch: long press → show overlay and cycle
        if self._ws_held and not self._ws_overlay_active and self._switcher_overlay:
            if now - self._ws_press_time >= self._long_threshold:
                windows = find_windows(self._window_cycler.app_names)
                if windows:
                    initial = self._find_current_window_index(windows)
                    self._switcher_overlay.show(windows, initial_index=initial)
                    self._ws_overlay_active = True
                    self._ws_last_move = now
                    logger.info("window_switch overlay: %d windows", len(windows))

        if self._ws_held and self._ws_overlay_active and self._switcher_overlay:
            if now - self._ws_last_move >= self._ws_move_interval:
                self._switcher_overlay.move_next()
                self._ws_last_move = now

    def _release_stick_auto(self) -> None:
        """Release current stick hold key and cancel repeat."""
        stick_keys = [k for k in self._active_holds if isinstance(k, tuple) and k[0] == "stick"]
        for k in stick_keys:
            key = self._active_holds.pop(k)
            keyboard_output.release(key)
            self._stick_repeat.pop(k, None)
            logger.debug("stick release [%s] → %s", k[1], key)

    def stick_direction(self, direction: str) -> None:
        """Handle a stick direction change event."""
        if not self._stick_enabled:
            return

        # Release any previously active stick direction hold
        self._release_stick_auto()

        mapping = self._direction_mappings.get(direction)
        if mapping is None:
            return

        action = mapping["action"]
        if action == "tap":
            keyboard_output.tap(mapping["key"])
            logger.debug("stick [%s] → %s", direction, mapping["key"])
        elif action == "auto":
            key = mapping["key"]
            repeat_ms = mapping.get("repeat", 100)
            # Tap once immediately, then repeat at interval via poll()
            keyboard_output.tap(key)
            self._active_holds[("stick", direction)] = key
            self._stick_repeat[("stick", direction)] = {
                "key": key,
                "interval": repeat_ms / 1000.0,
                "last_time": time.monotonic(),
            }
            logger.debug("stick auto [%s] → %s (repeat=%dms)", direction, key, repeat_ms)
        elif action == "combination":
            keyboard_output.send_combination(mapping["keys"])
            logger.debug("stick [%s] → %s", direction, "+".join(mapping["keys"]))

    def stick_centered(self) -> None:
        """Handle stick returning to center."""
        if not self._stick_enabled:
            return
        self._release_stick_auto()
        logger.debug("stick centered")

    def release_all(self) -> None:
        """Release all currently held keys and cancel pending auto actions."""
        # Hide overlay if active
        self._ws_held = False
        self._ws_overlay_active = False
        if self._switcher_overlay:
            self._switcher_overlay.hide()
        # Release sequences in reverse
        for keys in self._active_sequences.values():
            for key in reversed(keys):
                keyboard_output.release(key)
        self._active_sequences.clear()
        self._sequence_repeat.clear()
        self._stick_repeat.clear()
        # Release holds
        for key in self._active_holds.values():
            keyboard_output.release(key)
        self._active_holds.clear()
        self._auto_pending.clear()


    def _execute_macro(self, mapping: dict, btn_name: str) -> None:
        """Execute a macro: a sequence of steps, optionally filtered by foreground window.

        Config format:
            {
                "action": "macro",
                "if_window": "code.exe",   # optional: only run if this process is foreground
                "steps": [
                    {"type": "combination", "keys": ["ctrl", "shift", "p"]},
                    {"type": "delay", "ms": 300},
                    {"type": "type", "text": "some text"},
                    {"type": "tap", "key": "enter"},
                ]
            }
        """
        # Check window filter
        if_window = mapping.get("if_window")
        if if_window:
            fg = get_foreground_process_name()
            if fg != if_window:
                logger.debug("macro [%s] skipped: foreground is '%s', need '%s'",
                             btn_name, fg, if_window)
                return

        steps = mapping.get("steps", [])
        logger.info("macro [%s] executing %d steps", btn_name, len(steps))

        for i, step in enumerate(steps):
            step_type = step.get("type")

            if step_type == "combination":
                keyboard_output.send_combination(step["keys"])

            elif step_type == "tap":
                keyboard_output.tap(step["key"])

            elif step_type == "hold":
                keyboard_output.press(step["key"])

            elif step_type == "release":
                keyboard_output.release(step["key"])

            elif step_type == "type":
                keyboard_output.type_text(step["text"])

            elif step_type == "delay":
                time.sleep(step.get("ms", 100) / 1000.0)

            else:
                logger.warning("macro [%s] unknown step type '%s' at step %d",
                               btn_name, step_type, i)


def _button_label(button_index: int) -> str:
    """Get human-readable name for a button index."""
    from .constants import BUTTON_NAMES
    return BUTTON_NAMES.get(button_index, f"BTN_{button_index}")
