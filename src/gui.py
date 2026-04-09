"""Main GUI for NS Joy-Con R Keyboard Mapper.

Provides a tkinter window with controls for:
- Enabling/disabling stick mapping
- Selecting target applications for window switching (R key)
"""

import logging
import tkinter as tk
from tkinter import ttk

from .window_switcher import KNOWN_APPS

logger = logging.getLogger(__name__)


class MainWindow:
    """Main application window for the Joy-Con mapper."""

    def __init__(
        self,
        key_mapper,
        window_cycler,
        stop_event,
        on_minimize=None,
    ) -> None:
        self._key_mapper = key_mapper
        self._window_cycler = window_cycler
        self._stop_event = stop_event
        self._on_minimize = on_minimize

        self._root = tk.Tk()
        self._root.title("NS Joy-Con R 键盘映射器")
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        # App selection variables: display_name → BooleanVar
        self._app_vars: dict[str, tk.BooleanVar] = {}

        self._build_ui()
        self._center_window()

    def _build_ui(self) -> None:
        """Build the UI layout."""
        root = self._root
        root.configure(padx=20, pady=15)

        # Title
        title = ttk.Label(root, text="NS Joy-Con R 键盘映射器", font=("", 14, "bold"))
        title.pack(anchor="w", pady=(0, 15))

        # Stick enable toggle
        self._stick_var = tk.BooleanVar(value=True)
        stick_frame = ttk.Frame(root)
        stick_frame.pack(fill="x", pady=(0, 15))
        stick_cb = ttk.Checkbutton(
            stick_frame,
            text="启用摇杆映射",
            variable=self._stick_var,
            command=self._on_stick_toggle,
        )
        stick_cb.pack(anchor="w")

        # Window switch app selection
        app_label = ttk.Label(root, text="R 键窗口切换目标：", font=("", 10))
        app_label.pack(anchor="w", pady=(0, 5))

        app_frame = ttk.Frame(root)
        app_frame.pack(fill="x", padx=(15, 0), pady=(0, 15))

        for display_name, process_name in KNOWN_APPS.items():
            var = tk.BooleanVar(value=(process_name == "code.exe"))
            self._app_vars[display_name] = var
            cb = ttk.Checkbutton(
                app_frame,
                text=display_name,
                variable=var,
                command=self._on_app_toggle,
            )
            cb.pack(anchor="w", pady=2)

        # Separator
        ttk.Separator(root).pack(fill="x", pady=(0, 15))

        # Bottom button
        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill="x")
        minimize_btn = ttk.Button(
            btn_frame,
            text="最小化到托盘",
            command=self._on_minimize_click,
        )
        minimize_btn.pack(side="right")

    def _center_window(self) -> None:
        """Center the window on screen."""
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() - w) // 2
        y = (self._root.winfo_screenheight() - h) // 2
        self._root.geometry(f"+{x}+{y}")

    def _on_stick_toggle(self) -> None:
        """Handle stick mapping toggle."""
        enabled = self._stick_var.get()
        self._key_mapper._stick_enabled = enabled
        if not enabled:
            self._key_mapper.release_all()
        logger.info("Stick mapping %s", "enabled" if enabled else "disabled")

    def _on_app_toggle(self) -> None:
        """Handle app selection change."""
        selected = []
        for display_name, var in self._app_vars.items():
            if var.get():
                selected.append(KNOWN_APPS[display_name])
        self._window_cycler.app_names = selected
        logger.info("Window switch targets: %s", selected)

    def _on_minimize_click(self) -> None:
        """Minimize to system tray."""
        self._root.withdraw()
        if self._on_minimize:
            self._on_minimize()

    def _on_close(self) -> None:
        """Handle window close — exit the program."""
        logger.info("Main window closed, stopping...")
        self._stop_event.set()
        self._root.destroy()

    @property
    def root(self) -> tk.Tk:
        """Get the tkinter root window."""
        return self._root

    def show(self) -> None:
        """Show the window (restore from minimized)."""
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    def run(self) -> None:
        """Start the tkinter main loop (blocks)."""
        logger.info("GUI started")
        self._root.mainloop()
        logger.info("GUI stopped")
