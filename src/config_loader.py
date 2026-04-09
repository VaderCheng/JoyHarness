"""Configuration loading, validation, and default merging.

Loads JSON config files, validates key names and action types,
and merges user config with built-in defaults.
"""

import json
import logging
from pathlib import Path

import keyboard

from .constants import (
    DEFAULT_CONFIG,
    VALID_ACTIONS,
    BUTTON_NAMES,
    STICK_DIRECTIONS,
)

logger = logging.getLogger(__name__)


def load_config(path: str | None = None) -> dict:
    """Load configuration from a JSON file, or return built-in defaults.

    Args:
        path: Path to JSON config file. None uses built-in defaults.

    Returns:
        Complete configuration dict with all fields populated.

    Raises:
        FileNotFoundError: Config file path specified but doesn't exist.
        json.JSONDecodeError: Config file contains invalid JSON.
        ValueError: Config file contains invalid mappings.
    """
    if path is None:
        logger.info("Using built-in default configuration")
        return DEFAULT_CONFIG.copy()

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        user_config = json.load(f)

    logger.info("Loaded config from: %s", config_path)
    merged = merge_with_defaults(user_config)
    errors = validate_config(merged)

    if errors:
        error_msg = "Invalid configuration:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)

    return merged


def merge_with_defaults(user_config: dict) -> dict:
    """Merge user config into defaults. User values override defaults.

    Deep-merges the mappings section: user-defined buttons/directions
    override defaults, unspecified ones are kept from defaults.
    """
    result = DEFAULT_CONFIG.copy()

    # Override top-level settings
    for key in ("version", "description", "deadzone", "poll_interval", "stick_mode"):
        if key in user_config:
            result[key] = user_config[key]

    # Deep merge mappings
    if "mappings" in user_config:
        result["mappings"] = {
            "buttons": {**DEFAULT_CONFIG["mappings"]["buttons"]},
            "stick_directions": {**DEFAULT_CONFIG["mappings"]["stick_directions"]},
        }
        if "buttons" in user_config["mappings"]:
            result["mappings"]["buttons"].update(user_config["mappings"]["buttons"])
        if "stick_directions" in user_config["mappings"]:
            result["mappings"]["stick_directions"].update(
                user_config["mappings"]["stick_directions"]
            )

    return result


def validate_config(config: dict) -> list[str]:
    """Validate configuration and return list of error strings.

    Empty list means valid configuration.

    Checks:
    - Deadzone is within [0.0, 0.99]
    - Stick mode is "4dir" or "8dir"
    - Every action type is valid
    - Every key name is recognized by the keyboard library
    - Button names are known Joy-Con R buttons
    - Stick direction names are valid
    """
    errors: list[str] = []

    # Top-level validation
    deadzone = config.get("deadzone", 0.15)
    if not isinstance(deadzone, (int, float)) or not (0.0 <= deadzone < 1.0):
        errors.append(f"deadzone must be between 0.0 and 0.99, got {deadzone}")

    stick_mode = config.get("stick_mode", "4dir")
    if stick_mode not in ("4dir", "8dir"):
        errors.append(f"stick_mode must be '4dir' or '8dir', got '{stick_mode}'")

    mappings = config.get("mappings", {})

    # Validate button mappings
    for btn_name, mapping in mappings.get("buttons", {}).items():
        if btn_name not in BUTTON_NAMES.values():
            errors.append(f"Unknown button name: '{btn_name}'")
            continue
        errors.extend(_validate_mapping_entry(btn_name, mapping))

    # Validate stick direction mappings
    for dir_name, mapping in mappings.get("stick_directions", {}).items():
        if dir_name not in STICK_DIRECTIONS:
            errors.append(f"Unknown stick direction: '{dir_name}'")
            continue
        errors.extend(_validate_mapping_entry(dir_name, mapping))

    return errors


def _validate_mapping_entry(name: str, mapping: dict) -> list[str]:
    """Validate a single mapping entry (button or stick direction)."""
    errors: list[str] = []

    if not isinstance(mapping, dict):
        errors.append(f"'{name}' mapping must be a dict, got {type(mapping).__name__}")
        return errors

    action = mapping.get("action")
    if action not in VALID_ACTIONS:
        errors.append(f"'{name}' has invalid action '{action}', must be one of {VALID_ACTIONS}")
        return errors

    if action in ("tap", "hold"):
        key = mapping.get("key")
        if not isinstance(key, str):
            errors.append(f"'{name}' action '{action}' requires a 'key' string")
        elif not _is_valid_key(key):
            errors.append(f"'{name}' has invalid key name: '{key}'")

    elif action in ("combination", "sequence"):
        keys = mapping.get("keys")
        if not isinstance(keys, list) or len(keys) == 0:
            errors.append(f"'{name}' {action} action requires a non-empty 'keys' list")
        else:
            for key in keys:
                if not isinstance(key, str):
                    errors.append(f"'{name}' {action} keys must be strings")
                elif not _is_valid_key(key):
                    errors.append(f"'{name}' has invalid key name in combination: '{key}'")

    return errors


def _is_valid_key(key_name: str) -> bool:
    """Check if a key name is recognized by the keyboard library."""
    try:
        codes = keyboard.key_to_scan_codes(key_name)
        return len(codes) > 0
    except (ValueError, KeyError):
        return False
