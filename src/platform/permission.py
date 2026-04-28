"""Platform-specific permission checks.

Windows: Administrator privileges (required by keyboard library).
macOS:   Accessibility permission (required by pynput).
"""

from __future__ import annotations

import sys
import logging

logger = logging.getLogger(__name__)


def has_required_permissions() -> bool:
    """Check if the process has the permissions needed for keyboard simulation."""
    if sys.platform == "win32":
        return _check_windows_admin()
    elif sys.platform == "darwin":
        return _check_macos_accessibility()
    return True


def get_permission_warning() -> str:
    """Return a user-facing warning message for missing permissions."""
    if sys.platform == "win32":
        return (
            "WARNING: Not running as administrator. Keyboard simulation may not work.\n"
            "         Try: run.bat  or  run as admin in PowerShell\n"
        )
    elif sys.platform == "darwin":
        return (
            "WARNING: Accessibility permission not granted.\n"
            "         Go to: System Settings → Privacy & Security → Accessibility\n"
            "         Add your terminal app (e.g. Terminal, iTerm2) to the allowed list.\n"
            "         Then restart JoyHarness.\n"
        )
    return ""


def _check_windows_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _check_macos_accessibility() -> bool:
    """Check macOS Accessibility permission by attempting a pynput operation."""
    try:
        import subprocess
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to key code 0'],
            capture_output=True,
            timeout=3,
        )
        return result.returncode == 0
    except Exception:
        logger.debug("Accessibility check failed, assuming not granted")
        return False
