"""Joy-Con hardware constants for pygame button/axis mapping.

NOTE: Button and axis indices are based on SDL2's Switch controller mapping.
These MUST be verified using `python src/main.py --discover` mode,
as indices may vary across SDL2 versions and Windows driver updates.

Three connection modes are supported:
- single_right: Only right Joy-Con connected
- single_left:  Only left Joy-Con connected
- dual:         Both Joy-Cons connected (as a combined SDL2 device)
"""

# === Right Joy-Con Button Indices (calibrated 2026-04-09) ===
# Face buttons
BTN_X = 0       # X (上位)
BTN_A = 1       # A (右位)
BTN_Y = 2       # Y (左位)
BTN_B = 3       # B (下位)

# System / Home
BTN_HOME = 5    # Home (圆形)
BTN_PLUS = 6    # + 按钮
BTN_RSTICK = 7  # 摇杆按下

# Shoulder / trigger
BTN_SL = 9      # SL (侧边左)
BTN_R = 16      # R 肩键
BTN_SR = 10     # SR (侧边右)
BTN_ZR = 18     # ZR 扳机

# === Left Joy-Con Button Indices (PLACEHOLDER — run --discover to calibrate) ===
BTN_L_Y = 0       # Y
BTN_L_B = 1       # B
BTN_L_X = 2       # X
BTN_L_A = 3       # A
BTN_L_MINUS = 4   # - 按钮
BTN_L_CAPTURE = 5 # Capture 按钮
BTN_L_LSTICK = 6  # 左摇杆按下
BTN_L_SL = 9      # SL
BTN_L_SR = 10     # SR
BTN_L_L = 16      # L 肩键
BTN_L_ZL = 18     # ZL 扳机

# === Dual Mode Button Indices (PLACEHOLDER — run --discover to calibrate) ===
# In dual mode (L+R as combined SDL2 device), all buttons from both sides are available
# with potentially different indices. These are placeholder values.
BTN_DUAL_X = 0
BTN_DUAL_A = 1
BTN_DUAL_Y = 2
BTN_DUAL_B = 3
BTN_DUAL_MINUS = 4
BTN_DUAL_CAPTURE = 5
BTN_DUAL_HOME = 6
BTN_DUAL_PLUS = 7
BTN_DUAL_LSTICK = 8
BTN_DUAL_RSTICK = 9
BTN_DUAL_SL_L = 10
BTN_DUAL_SR_L = 11
BTN_DUAL_SL_R = 12
BTN_DUAL_SR_R = 13
BTN_DUAL_L = 16
BTN_DUAL_ZL = 17
BTN_DUAL_R = 18
BTN_DUAL_ZR = 19

# === Axis Indices (calibrated) ===
AXIS_RSTICK_Y = 0   # 垂直 (上=负, 下=正)
AXIS_RSTICK_X = 1   # 水平 (左=负, 右=正)

# === Default Values ===
DEFAULT_DEADZONE = 0.2
DIRECTION_THRESHOLD = 0.5
POLL_INTERVAL = 0.01       # 100Hz polling
SNAPBACK_FRAMES = 2        # Frames required at center before registering release

# === Right Joy-Con Button Name Lookup ===
BUTTON_NAMES: dict[int, str] = {
    BTN_A: "A",
    BTN_B: "B",
    BTN_X: "X",
    BTN_Y: "Y",
    BTN_R: "R",
    BTN_ZR: "ZR",
    BTN_PLUS: "Plus",
    BTN_RSTICK: "RStick",
    BTN_HOME: "Home",
    BTN_SL: "SL",
    BTN_SR: "SR",
}

# Reverse lookup: name → index
BUTTON_INDICES: dict[str, int] = {v: k for k, v in BUTTON_NAMES.items()}

# === Left Joy-Con Button Name Lookup ===
BUTTON_NAMES_LEFT: dict[int, str] = {
    BTN_L_A: "A",
    BTN_L_B: "B",
    BTN_L_X: "X",
    BTN_L_Y: "Y",
    BTN_L_L: "L",
    BTN_L_ZL: "ZL",
    BTN_L_MINUS: "Minus",
    BTN_L_CAPTURE: "Capture",
    BTN_L_LSTICK: "LStick",
    BTN_L_SL: "SL",
    BTN_L_SR: "SR",
}
BUTTON_INDICES_LEFT: dict[str, int] = {v: k for k, v in BUTTON_NAMES_LEFT.items()}

# === Dual Mode Button Name Lookup ===
BUTTON_NAMES_DUAL: dict[int, str] = {
    BTN_DUAL_A: "A",
    BTN_DUAL_B: "B",
    BTN_DUAL_X: "X",
    BTN_DUAL_Y: "Y",
    BTN_DUAL_R: "R",
    BTN_DUAL_ZR: "ZR",
    BTN_DUAL_L: "L",
    BTN_DUAL_ZL: "ZL",
    BTN_DUAL_PLUS: "Plus",
    BTN_DUAL_MINUS: "Minus",
    BTN_DUAL_HOME: "Home",
    BTN_DUAL_CAPTURE: "Capture",
    BTN_DUAL_RSTICK: "RStick",
    BTN_DUAL_LSTICK: "LStick",
    BTN_DUAL_SL_L: "SL_L",
    BTN_DUAL_SR_L: "SR_L",
    BTN_DUAL_SL_R: "SL_R",
    BTN_DUAL_SR_R: "SR_R",
}
BUTTON_INDICES_DUAL: dict[str, int] = {v: k for k, v in BUTTON_NAMES_DUAL.items()}

# === Mode-based lookup tables ===
BUTTON_NAMES_BY_MODE: dict[str, dict[int, str]] = {
    "single_right": BUTTON_NAMES,
    "single_left": BUTTON_NAMES_LEFT,
    "dual": BUTTON_NAMES_DUAL,
}

BUTTON_INDICES_BY_MODE: dict[str, dict[str, int]] = {
    "single_right": BUTTON_INDICES,
    "single_left": BUTTON_INDICES_LEFT,
    "dual": BUTTON_INDICES_DUAL,
}

MAPPABLE_BUTTONS_BY_MODE: dict[str, tuple[str, ...]] = {
    "single_right": ("A", "B", "X", "Y", "R", "ZR", "Plus", "Home", "RStick", "SL", "SR"),
    "single_left": ("A", "B", "X", "Y", "L", "ZL", "Minus", "Capture", "LStick", "SL", "SR"),
    "dual": ("A", "B", "X", "Y", "R", "ZR", "L", "ZL", "Plus", "Minus", "Home",
             "RStick", "LStick", "Capture", "SL_L", "SR_L", "SL_R", "SR_R"),
}

MODE_LABELS: dict[str, str] = {
    "single_right": "右手柄",
    "single_left": "左手柄",
    "dual": "左右手柄",
}


def get_button_names(mode: str = "single_right") -> dict[int, str]:
    """Get button name lookup table for a connection mode."""
    return BUTTON_NAMES_BY_MODE.get(mode, BUTTON_NAMES)


def get_button_indices(mode: str = "single_right") -> dict[str, int]:
    """Get button index lookup table for a connection mode."""
    return BUTTON_INDICES_BY_MODE.get(mode, BUTTON_INDICES)


# === Stick Direction Names ===
STICK_DIRECTIONS = ("up", "down", "left", "right", "up-left", "up-right", "down-left", "down-right")

# === Default Key Mapping (used when no config file is loaded) ===
DEFAULT_MAPPINGS: dict = {
    "buttons": {
        "A":      {"action": "tap", "key": "enter"},
        "B":      {"action": "sequence", "keys": ["shift", "tab"]},
        "X":      {"action": "auto", "key": "f2"},
        "Y":      {"action": "sequence", "keys": ["alt", "tab"], "repeat": 500},
        "R":      {"action": "window_switch"},
        "ZR":     {
            "action": "macro",
            "if_window": "code.exe",
            "steps": [
                {"type": "combination", "keys": ["ctrl", "shift", "p"]},
                {"type": "delay", "ms": 100},
                {"type": "type", "text": "Claude Code: Focus input"},
                {"type": "delay", "ms": 100},
                {"type": "tap", "key": "enter"},
            ],
        },
        "Plus":   {"action": "combination", "keys": ["ctrl", "s"]},
        "Home":   {"action": "tap", "key": "windows"},
        "RStick": {"action": "tap", "key": "tab"},
        "SL":     {"action": "hold", "key": "alt"},
        "SR":     {"action": "window_switch"},
    },
    "stick_directions": {
        "up":    {"action": "auto", "key": "down", "repeat": 100},
        "down":  {"action": "auto", "key": "up", "repeat": 100},
        "left":  {"action": "auto", "key": "left", "repeat": 100},
        "right": {"action": "auto", "key": "right", "repeat": 100},
    },
}

DEFAULT_MAPPINGS_LEFT: dict = {
    "buttons": {
        "A":       {"action": "tap", "key": "enter"},
        "B":       {"action": "tap", "key": "escape"},
        "X":       {"action": "tap", "key": "backspace"},
        "Y":       {"action": "sequence", "keys": ["alt", "tab"], "repeat": 500},
        "L":       {"action": "window_switch"},
        "ZL":      {"action": "hold", "key": "ctrl"},
        "Minus":   {"action": "combination", "keys": ["ctrl", "s"]},
        "Capture": {"action": "tap", "key": "print_screen"},
        "LStick":  {"action": "tap", "key": "tab"},
        "SL":      {"action": "hold", "key": "shift"},
        "SR":      {"action": "window_switch"},
    },
    "stick_directions": {
        "up":    {"action": "tap", "key": "up"},
        "down":  {"action": "tap", "key": "down"},
        "left":  {"action": "tap", "key": "left"},
        "right": {"action": "tap", "key": "right"},
    },
}

DEFAULT_MAPPINGS_DUAL: dict = {
    "buttons": {
        "A":       {"action": "tap", "key": "enter"},
        "B":       {"action": "sequence", "keys": ["shift", "tab"]},
        "X":       {"action": "auto", "key": "f2"},
        "Y":       {"action": "sequence", "keys": ["alt", "tab"], "repeat": 500},
        "R":       {"action": "window_switch"},
        "ZR":     {
            "action": "macro",
            "if_window": "code.exe",
            "steps": [
                {"type": "combination", "keys": ["ctrl", "shift", "p"]},
                {"type": "delay", "ms": 100},
                {"type": "type", "text": "Claude Code: Focus input"},
                {"type": "delay", "ms": 100},
                {"type": "tap", "key": "enter"},
            ],
        },
        "L":       {"action": "hold", "key": "ctrl"},
        "ZL":      {"action": "hold", "key": "shift"},
        "Plus":    {"action": "combination", "keys": ["ctrl", "s"]},
        "Minus":   {"action": "tap", "key": "escape"},
        "Home":    {"action": "tap", "key": "windows"},
        "Capture": {"action": "tap", "key": "print_screen"},
        "RStick":  {"action": "tap", "key": "tab"},
        "LStick":  {"action": "tap", "key": "enter"},
        "SL_L":    {"action": "hold", "key": "alt"},
        "SR_L":    {"action": "window_switch"},
        "SL_R":    {"action": "hold", "key": "alt"},
        "SR_R":    {"action": "window_switch"},
    },
    "stick_directions": {
        "up":    {"action": "tap", "key": "up"},
        "down":  {"action": "tap", "key": "down"},
        "left":  {"action": "tap", "key": "left"},
        "right": {"action": "tap", "key": "right"},
    },
}

DEFAULT_CONFIG: dict = {
    "version": "1.0",
    "description": "Default Joy-Con R to keyboard mapping",
    "deadzone": DEFAULT_DEADZONE,
    "poll_interval": POLL_INTERVAL,
    "stick_mode": "4dir",
    "stick_enabled": True,
    "keep_alive_enabled": True,
    "mappings": DEFAULT_MAPPINGS,
}

DEFAULT_CONFIG_LEFT: dict = {
    "version": "1.0",
    "description": "Default Joy-Con L to keyboard mapping",
    "deadzone": DEFAULT_DEADZONE,
    "poll_interval": POLL_INTERVAL,
    "stick_mode": "4dir",
    "stick_enabled": True,
    "keep_alive_enabled": True,
    "mappings": DEFAULT_MAPPINGS_LEFT,
}

DEFAULT_CONFIG_DUAL: dict = {
    "version": "1.0",
    "description": "Default Joy-Con L+R to keyboard mapping",
    "deadzone": DEFAULT_DEADZONE,
    "poll_interval": POLL_INTERVAL,
    "stick_mode": "4dir",
    "stick_enabled": True,
    "keep_alive_enabled": True,
    "mappings": DEFAULT_MAPPINGS_DUAL,
}

DEFAULT_CONFIGS: dict[str, dict] = {
    "single_right": DEFAULT_CONFIG,
    "single_left": DEFAULT_CONFIG_LEFT,
    "dual": DEFAULT_CONFIG_DUAL,
}

VALID_ACTIONS = ("tap", "hold", "auto", "combination", "sequence", "window_switch", "macro", "exec")

__version__ = "1.1.0"
