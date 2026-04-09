"""Semi-transparent window switcher overlay.

Shows a floating list of target application windows with the
currently selected one highlighted. Used during long-press R key.

All UI operations are thread-safe via _schedule() which uses root.after()
to marshal calls to the main thread.
"""

import tkinter as tk
import logging
from typing import Callable

from .window_switcher import WindowInfo

logger = logging.getLogger(__name__)


class SwitcherOverlay:
    """A semi-transparent overlay showing window list for selection."""

    def __init__(self, root: tk.Tk, on_select: Callable[[WindowInfo], None]) -> None:
        self._on_select = on_select
        self._root_tk = root  # main tkinter root for after() scheduling
        self._windows: list[WindowInfo] = []
        self._selected_index: int = 0
        self._visible: bool = False

        self._overlay = tk.Toplevel(root)
        self._overlay.overrideredirect(True)
        self._overlay.attributes("-topmost", True)
        self._overlay.attributes("-alpha", 0.85)
        self._overlay.withdraw()

        self._frame = tk.Frame(
            self._overlay,
            bg="#1e1e2e",
            highlightthickness=1,
            highlightbackground="#45475a",
        )
        self._frame.pack(fill="both", expand=True)

        self._title_label = tk.Label(
            self._frame,
            text="切换窗口",
            font=("Microsoft YaHei UI", 10),
            fg="#cdd6f4",
            bg="#1e1e2e",
            anchor="w",
            padx=12,
            pady=8,
        )
        self._title_label.pack(fill="x", pady=(8, 4))

        sep = tk.Frame(self._frame, bg="#45475a", height=1)
        sep.pack(fill="x", padx=8)

        self._list_frame = tk.Frame(self._frame, bg="#1e1e2e")
        self._list_frame.pack(fill="both", expand=True, padx=4, pady=(4, 8))

        self._labels: list[tk.Label] = []

    def _schedule(self, func: Callable) -> None:
        """Schedule a function to run on the main thread."""
        try:
            self._root_tk.after(0, func)
        except RuntimeError:
            pass  # tkinter already destroyed

    def show(self, windows: list[WindowInfo], initial_index: int = 0) -> None:
        """Show the overlay (thread-safe)."""
        self._schedule(lambda: self._do_show(windows, initial_index))

    def _do_show(self, windows: list[WindowInfo], initial_index: int) -> None:
        """Actually show the overlay on the main thread."""
        self._windows = windows
        self._selected_index = initial_index % max(len(windows), 1)
        self._visible = True

        for lbl in self._labels:
            lbl.destroy()
        self._labels.clear()

        for w in self._windows:
            lbl = tk.Label(
                self._list_frame,
                text=f"  {w.title}",
                font=("Microsoft YaHei UI", 11),
                fg="#cdd6f4",
                bg="#1e1e2e",
                anchor="w",
                padx=12,
                pady=4,
            )
            lbl.pack(fill="x", padx=4, pady=1)
            self._labels.append(lbl)

        self._highlight()

        self._overlay.update_idletasks()
        w = self._overlay.winfo_width()
        h = self._overlay.winfo_height()
        x = (self._overlay.winfo_screenwidth() - w) // 2
        y = self._overlay.winfo_screenheight() // 4
        self._overlay.geometry(f"+{x}+{y}")
        self._overlay.deiconify()

    def hide(self) -> None:
        """Hide the overlay (thread-safe)."""
        self._schedule(self._do_hide)

    def _do_hide(self) -> None:
        """Actually hide on main thread."""
        self._visible = False
        try:
            self._overlay.withdraw()
        except tk.TclError:
            pass

    def move_next(self) -> WindowInfo | None:
        """Move selection to next item (thread-safe)."""
        if not self._windows:
            return None
        self._selected_index = (self._selected_index + 1) % len(self._windows)
        self._schedule(self._highlight)
        return self._windows[self._selected_index]

    @property
    def selected(self) -> WindowInfo | None:
        if not self._windows:
            return None
        return self._windows[self._selected_index]

    @property
    def visible(self) -> bool:
        return self._visible

    def _highlight(self) -> None:
        for i, lbl in enumerate(self._labels):
            if i == self._selected_index:
                lbl.configure(bg="#313244", fg="#f5e0dc", font=("Microsoft YaHei UI", 11, "bold"))
            else:
                lbl.configure(bg="#1e1e2e", fg="#cdd6f4", font=("Microsoft YaHei UI", 11))
