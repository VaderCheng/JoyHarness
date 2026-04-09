"""Joy-Con R hardware constants for pygame button/axis mapping.

NOTE: Button and axis indices are based on SDL2's Switch controller mapping.
These MUST be verified using `python src/main.py --discover` mode,
as indices may vary across SDL2 versions and Windows driver updates.
"""

# === Button Indices (calibrated 2026-04-09) ===
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

# === Axis Indices (calibrated) ===
AXIS_RSTICK_Y = 0   # 垂直 (上=负, 下=正)
AXIS_RSTICK_X = 1   # 水平 (左=负, 右=正)

# === Default Values ===
DEFAULT_DEADZONE = 0.2
DIRECTION_THRESHOLD = 0.5
POLL_INTERVAL = 0.01       # 100Hz polling
SNAPBACK_FRAMES = 2        # Frames required at center before registering release

# === Button Name Lookup ===
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

# === Stick Direction Names ===
STICK_DIRECTIONS = ("up", "down", "left", "right", "up-left", "up-right", "down-left", "down-right")

# === Default Key Mapping (used when no config file is loaded) ===
DEFAULT_MAPPINGS: dict = {
    "buttons": {
        "A":      {"action": "tap", "key": "enter"},
        "B":      {"action": "tap", "key": "escape"},
        "X":      {"action": "auto", "key": "f2"},
        "Y":      {"action": "sequence", "keys": ["alt", "tab"], "repeat": 500},
        "R":      {"action": "window_switch"},
        "ZR":     {"action": "hold", "key": "shift"},
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

DEFAULT_CONFIG: dict = {
    "version": "1.0",
    "description": "Default Joy-Con R to keyboard mapping",
    "deadzone": DEFAULT_DEADZONE,
    "poll_interval": POLL_INTERVAL,
    "stick_mode": "4dir",
    "mappings": DEFAULT_MAPPINGS,
}

VALID_ACTIONS = ("tap", "hold", "auto", "combination", "sequence", "window_switch")
