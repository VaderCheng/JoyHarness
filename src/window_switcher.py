"""Window enumeration and switching — cross-platform.

On Windows: Uses ctypes to call Win32 APIs.
On macOS:   Uses AppleScript via subprocess for window enumeration and switching.
"""

from __future__ import annotations

import sys
import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)

KNOWN_APPS: dict[str, str] = {
    "VS Code": "code.exe" if sys.platform == "win32" else "Code",
    "飞书": "feishu.exe" if sys.platform == "win32" else "Lark",
}


def set_known_apps(apps: dict[str, str]) -> None:
    """Replace the known apps dict atomically."""
    KNOWN_APPS.clear()
    KNOWN_APPS.update(apps)


class WindowInfo(NamedTuple):
    hwnd: int         # Window handle (Win32) or index (macOS)
    title: str
    app_name: str = ""  # Process/app name (used on macOS)


# ---------------------------------------------------------------------------
# Platform: Windows
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    WNDENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
    )
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    def get_foreground_process_name() -> str:
        """Return the exe name of the current foreground window's process (lowercase)."""
        hwnd = user32.GetForegroundWindow()
        return _get_process_name(hwnd)

    def get_foreground_hwnd() -> int:
        """Return the HWND of the current foreground window."""
        return user32.GetForegroundWindow()

    def _get_process_name(hwnd: int) -> str:
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
        """Enumerate all visible windows matching the given process names."""
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
                results.append(WindowInfo(hwnd, title, exe_name))

            return True

        user32.EnumWindows(WNDENUMPROC(callback), 0)
        results.sort(key=lambda w: w.title)
        return results

    def switch_to_window(hwnd_or_info) -> None:
        """Bring a window to the foreground."""
        hwnd = hwnd_or_info.hwnd if isinstance(hwnd_or_info, WindowInfo) else hwnd_or_info
        SW_RESTORE = 9

        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)

        foreground_hwnd = user32.GetForegroundWindow()
        foreground_tid = user32.GetWindowThreadProcessId(foreground_hwnd, None)
        current_tid = kernel32.GetCurrentThreadId()

        user32.AttachThreadInput(current_tid, foreground_tid, True)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(current_tid, foreground_tid, False)

# ---------------------------------------------------------------------------
# Platform: macOS
# ---------------------------------------------------------------------------

elif sys.platform == "darwin":
    import subprocess

    # Fast path: PyObjC (Quartz + AppKit + ApplicationServices). No subprocess overhead.
    # Fallback: AppleScript via osascript (slower, ~150ms/call subprocess startup).
    try:
        from AppKit import NSWorkspace, NSRunningApplication  # type: ignore
        from Quartz import (  # type: ignore
            CGWindowListCopyWindowInfo,
            kCGWindowListOptionOnScreenOnly,
            kCGWindowListExcludeDesktopElements,
            kCGNullWindowID,
        )
        from ApplicationServices import (  # type: ignore
            AXUIElementCreateApplication,
            AXUIElementCopyAttributeValue,
            AXUIElementSetAttributeValue,
            AXUIElementPerformAction,
        )
        _PYOBJC_OK = True
    except ImportError:
        _PYOBJC_OK = False
        logger.warning(
            "PyObjC not installed — falling back to AppleScript path. "
            "Install pyobjc-framework-Cocoa + pyobjc-framework-Quartz for faster window switching."
        )

    # NSApplicationActivationOptions
    _NSAPP_ACTIVATE_IGNORING_OTHER_APPS = 1 << 1  # = 2

    # AX attribute / action names (CFString constants — string literals work fine)
    _AX_WINDOWS = "AXWindows"
    _AX_TITLE = "AXTitle"
    _AX_MAIN = "AXMain"
    _AX_RAISE = "AXRaise"

    def get_foreground_process_name() -> str:
        """Return the name of the frontmost application on macOS (lowercase)."""
        if _PYOBJC_OK:
            try:
                front = NSWorkspace.sharedWorkspace().frontmostApplication()
                if front is not None:
                    name = front.localizedName() or ""
                    return str(name).lower()
                return ""
            except Exception:
                logger.debug("NSWorkspace frontmost lookup failed", exc_info=True)
                # fall through to AppleScript
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of first process whose frontmost is true'],
                capture_output=True, text=True, timeout=3,
            )
            return result.stdout.strip().lower() if result.returncode == 0 else ""
        except Exception:
            return ""

    def get_foreground_hwnd() -> int:
        """Not applicable on macOS — returns 0."""
        return 0

    def _find_windows_quartz(app_names: list[str] | None) -> list[WindowInfo]:
        """Enumerate on-screen windows via Quartz. WindowInfo.hwnd is the owner PID."""
        results: list[WindowInfo] = []
        opts = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
        windows = CGWindowListCopyWindowInfo(opts, kCGNullWindowID) or []
        for w in windows:
            # Layer 0 = normal app windows; non-zero = menubar, dock, panels, etc.
            if w.get("kCGWindowLayer", 1) != 0:
                continue
            owner = w.get("kCGWindowOwnerName", "") or ""
            title = w.get("kCGWindowName", "") or ""
            pid = int(w.get("kCGWindowOwnerPID", 0) or 0)
            if not owner or not pid:
                continue
            if not title:
                # Some apps (e.g. Chrome incognito, certain Electron apps) hide titles
                # from CGWindowList for privacy. Fall back to the app name.
                title = owner
            if app_names is not None and owner not in app_names:
                continue
            results.append(WindowInfo(pid, str(title), str(owner)))
        return results

    def _find_windows_applescript(app_names: list[str] | None) -> list[WindowInfo]:
        """Fallback AppleScript window enumeration (slow)."""
        results: list[WindowInfo] = []
        if app_names is None:
            script = '''
            tell application "System Events"
                set appList to every process whose visible is true
                set output to ""
                repeat with proc in appList
                    set procName to name of proc
                    try
                        set winNames to name of every window of proc
                        repeat with w in winNames
                            set output to output & procName & "||" & w & linefeed
                        end repeat
                    end try
                end repeat
                return output
            end tell
            '''
        else:
            names_str = ", ".join(f'"{n}"' for n in app_names)
            script = f'''
            tell application "System Events"
                set targetNames to {{{names_str}}}
                set output to ""
                repeat with appName in targetNames
                    try
                        set proc to first process whose name is appName
                        set winNames to name of every window of proc
                        repeat with w in winNames
                            set output to output & appName & "||" & w & linefeed
                        end repeat
                    end try
                end repeat
                return output
            end tell
            '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                for idx, line in enumerate(result.stdout.strip().split("\n")):
                    parts = line.split("||", 1)
                    if len(parts) == 2:
                        app_name, title = parts[0].strip(), parts[1].strip()
                        results.append(WindowInfo(idx, title, app_name))
        except Exception:
            logger.debug("AppleScript window enumeration failed", exc_info=True)
        return results

    def find_windows(app_names: list[str] | None = None) -> list[WindowInfo]:
        """List windows for specified applications.

        Uses Quartz (CGWindowListCopyWindowInfo) when PyObjC is available — typically
        a few milliseconds. Falls back to AppleScript otherwise (~200–500ms).
        """
        if _PYOBJC_OK:
            try:
                results = _find_windows_quartz(app_names)
            except Exception:
                logger.debug("Quartz enumeration failed, using AppleScript", exc_info=True)
                results = _find_windows_applescript(app_names)
        else:
            results = _find_windows_applescript(app_names)
        results.sort(key=lambda w: (w.app_name, w.title))
        return results

    def _activate_via_pyobjc(pid: int, window_title: str) -> bool:
        """Activate app and raise a specific window using AppKit + AX. Returns True on success."""
        try:
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
            if app is None:
                return False
            # Bring app to front. activateWithOptions_ is deprecated in macOS 14+ but
            # still functional and is the only way to reliably steal focus across all
            # supported macOS versions.
            app.activateWithOptions_(_NSAPP_ACTIVATE_IGNORING_OTHER_APPS)
        except Exception:
            logger.debug("NSRunningApplication.activate failed for pid=%d", pid, exc_info=True)
            return False

        # Try to raise the specific window via Accessibility API.
        # If AX permission isn't granted, this silently no-ops — the app is still
        # activated, which is the most important step.
        try:
            ax_app = AXUIElementCreateApplication(pid)
            err, windows = AXUIElementCopyAttributeValue(ax_app, _AX_WINDOWS, None)
            if err == 0 and windows:
                for win in windows:
                    err2, title = AXUIElementCopyAttributeValue(win, _AX_TITLE, None)
                    if err2 == 0 and title == window_title:
                        AXUIElementSetAttributeValue(win, _AX_MAIN, True)
                        AXUIElementPerformAction(win, _AX_RAISE)
                        break
        except Exception:
            logger.debug("AX raise failed for pid=%d title=%s", pid, window_title, exc_info=True)
        return True

    def _activate_via_applescript(app_name: str, window_title: str) -> None:
        """Fallback activation using two osascript calls (slow)."""
        try:
            script = f'''
            tell application "{app_name}" to activate
            tell application "System Events"
                tell process "{app_name}"
                    try
                        set frontmost to true
                        perform action "AXRaise" of window "{window_title}"
                    end try
                end tell
            end tell
            '''
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
        except Exception:
            try:
                subprocess.run(
                    ["osascript", "-e", f'tell application "{app_name}" to activate'],
                    capture_output=True, timeout=3,
                )
            except Exception:
                logger.debug("Failed to switch to %s", app_name, exc_info=True)

    def switch_to_window(hwnd_or_info) -> None:
        """Activate an application and raise a specific window on macOS."""
        if not isinstance(hwnd_or_info, WindowInfo):
            logger.warning("switch_to_window: macOS requires WindowInfo, got %s", type(hwnd_or_info))
            return

        pid = hwnd_or_info.hwnd  # On macOS (Quartz path), hwnd field stores the owner PID.
        title = hwnd_or_info.title
        app_name = hwnd_or_info.app_name

        if _PYOBJC_OK and pid > 0:
            if _activate_via_pyobjc(pid, title):
                return
        # Fallback (PyObjC missing, or pid==0 from AppleScript-enumerated WindowInfo)
        _activate_via_applescript(app_name, title)


# ---------------------------------------------------------------------------
# Cross-platform: WindowCycler
# ---------------------------------------------------------------------------

class WindowCycler:
    """Cycle through application windows in order on each call."""

    def __init__(self, app_names: list[str] | None = None) -> None:
        default = ["code.exe"] if sys.platform == "win32" else ["Code"]
        self._app_names: list[str] = app_names or default
        self._windows: list[WindowInfo] = []
        self._current_index: int = -1

    @property
    def app_names(self) -> list[str]:
        return self._app_names

    @app_names.setter
    def app_names(self, names: list[str]) -> None:
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
        """Switch to the next window in the list."""
        self.refresh()

        if not self._windows:
            logger.warning("No windows found for %s", self._app_names)
            return None

        self._current_index = (self._current_index + 1) % len(self._windows)
        target = self._windows[self._current_index]
        logger.info("Switching to [%d/%d]: %s",
                    self._current_index + 1, len(self._windows), target.title)
        switch_to_window(target)
        return target
