"""Window enumeration and switching using Windows API.

Uses ctypes to call Win32 APIs for finding and switching between
application windows without going through Alt+Tab.
"""

import ctypes
import ctypes.wintypes
import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Known applications for window switching: display name → process name
KNOWN_APPS: dict[str, str] = {
    "VS Code": "code.exe",
    "飞书": "feishu.exe",
}


def get_foreground_process_name() -> str:
    """Return the exe name of the current foreground window's process (lowercase)."""
    hwnd = user32.GetForegroundWindow()
    return _get_process_name(hwnd)


class WindowInfo(NamedTuple):
    hwnd: int
    title: str


def _get_process_name(hwnd: int) -> str:
    """Get the executable name for the process owning a window."""
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""

    try:
        buf_size = ctypes.wintypes.DWORD(260)
        buf = ctypes.create_unicode_buffer(260)
        kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(buf_size))
        return buf.value.split("\\")[-1].lower()
    finally:
        kernel32.CloseHandle(handle)


def find_windows(app_names: list[str] | None = None) -> list[WindowInfo]:
    """Enumerate all visible windows matching the given process names.

    Args:
        app_names: List of process names to match (lowercase). None = match all.

    Returns:
        List of WindowInfo(hwnd, title) sorted by window title.
    """
    results: list[WindowInfo] = []

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True

        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value

        exe_name = _get_process_name(hwnd)
        if app_names is None or exe_name in app_names:
            results.append(WindowInfo(hwnd, title))

        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    results.sort(key=lambda w: w.title)
    return results


def switch_to_window(hwnd: int) -> None:
    """Bring a window to the foreground.

    Only restores if actually minimized (preserves maximize/fullscreen).
    Uses AttachThreadInput to bypass foreground window restrictions.
    """
    SW_RESTORE = 9

    # Only restore if actually minimized
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)

    # Bypass SetForegroundWindow restrictions via AttachThreadInput
    foreground_hwnd = user32.GetForegroundWindow()
    foreground_tid = user32.GetWindowThreadProcessId(foreground_hwnd, None)
    current_tid = kernel32.GetCurrentThreadId()

    user32.AttachThreadInput(current_tid, foreground_tid, True)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(current_tid, foreground_tid, False)


class WindowCycler:
    """Cycle through application windows in order on each call."""

    def __init__(self, app_names: list[str] | None = None) -> None:
        self._app_names: list[str] = app_names or ["code.exe"]
        self._windows: list[WindowInfo] = []
        self._current_index: int = -1

    @property
    def app_names(self) -> list[str]:
        """Get the current target app process names."""
        return self._app_names

    @app_names.setter
    def app_names(self, names: list[str]) -> None:
        """Set target app process names and clear cached window list."""
        self._app_names = names
        self._windows.clear()
        self._current_index = -1

    def refresh(self) -> int:
        """Re-scan windows. Returns count found."""
        self._windows = find_windows(self._app_names)

        if self._current_index >= len(self._windows):
            self._current_index = 0

        logger.info("Found %d windows for %s", len(self._windows), self._app_names)
        for i, w in enumerate(self._windows):
            logger.debug("  [%d] %s (hwnd=%d)", i, w.title, w.hwnd)

        return len(self._windows)

    def next(self) -> WindowInfo | None:
        """Switch to the next window in the list.

        Auto-refreshes if no windows cached.
        Returns the WindowInfo switched to, or None if no windows found.
        """
        if not self._windows:
            self.refresh()

        if not self._windows:
            logger.warning("No windows found for %s", self._app_names)
            return None

        self._current_index = (self._current_index + 1) % len(self._windows)
        target = self._windows[self._current_index]
        logger.info("Switching to [%d/%d]: %s",
                    self._current_index + 1, len(self._windows), target.title)
        switch_to_window(target.hwnd)
        return target
