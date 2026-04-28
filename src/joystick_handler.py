"""Joystick axis processing: deadzone filtering and direction detection.

Uses a circular deadzone algorithm that preserves the full analog range
outside the deadzone while eliminating stick drift near center.
"""

from __future__ import annotations

import math
import logging

logger = logging.getLogger(__name__)


def apply_deadzone(x: float, y: float, deadzone: float) -> tuple[float, float]:
    """Apply circular deadzone to raw axis values.

    Returns (0, 0) inside the deadzone radius.
    Outside, rescales linearly to preserve full [0, 1] range.

    Args:
        x: Raw X axis value (-1.0 to 1.0).
        y: Raw Y axis value (-1.0 to 1.0, negative = up).
        deadzone: Deadzone radius (0.0 to <1.0).

    Returns:
        Filtered (x, y) tuple.
    """
    magnitude = math.sqrt(x * x + y * y)

    if magnitude < deadzone:
        return (0.0, 0.0)

    # Rescale: map [deadzone, 1.0] → [0.0, 1.0] linearly
    scale = (magnitude - deadzone) / (1.0 - deadzone)
    scale = min(scale, 1.0)

    return (x / magnitude * scale, y / magnitude * scale)


def get_direction(x: float, y: float, mode: str = "4dir") -> str | None:
    """Determine stick direction from filtered axis values.

    Args:
        x: Filtered X axis value.
        y: Filtered Y axis value (negative = up).
        mode: "4dir" for cardinal only, "8dir" for diagonals included.

    Returns:
        Direction string ("up", "down", "left", "right", etc.) or None if centered.
    """
    magnitude = math.sqrt(x * x + y * y)
    if magnitude < 0.1:
        return None

    # atan2(y, x): up is -90deg, right is 0deg, down is 90deg, left is 180deg
    angle = math.degrees(math.atan2(y, x))

    if mode == "4dir":
        return _direction_4dir(angle)
    else:
        return _direction_8dir(angle)


def _direction_4dir(angle: float) -> str:
    """Map angle to 4 cardinal directions.

    Zone boundaries centered on cardinal directions:
    - up:    -135 to -45
    - right: -45 to 45
    - down:  45 to 135
    - left:  135 to 180 or -180 to -135
    """
    # Normalize to [-180, 180)
    angle = ((angle + 180) % 360) - 180

    if -135 <= angle < -45:
        return "up"
    elif -45 <= angle < 45:
        return "right"
    elif 45 <= angle < 135:
        return "down"
    else:
        return "left"


def _direction_8dir(angle: float) -> str:
    """Map angle to 8 directions (cardinal + diagonal).

    Each zone spans 45 degrees, centered on the cardinal/diagonal direction:
      right:      -22.5 to  22.5
      down-right:  22.5 to  67.5
      down:        67.5 to 112.5
      down-left: 112.5 to 157.5
      left:      157.5 to 180 / -180 to -157.5
      up-left:  -157.5 to -112.5
      up:       -112.5 to  -67.5
      up-right:  -67.5 to  -22.5
    """
    angle = ((angle + 180) % 360) - 180

    if angle < -157.5:
        return "left"
    elif angle < -112.5:
        return "up-left"
    elif angle < -67.5:
        return "up"
    elif angle < -22.5:
        return "up-right"
    elif angle < 22.5:
        return "right"
    elif angle < 67.5:
        return "down-right"
    elif angle < 112.5:
        return "down"
    elif angle < 157.5:
        return "down-left"
    else:
        return "left"
