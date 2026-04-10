"""Main GUI for NS Joy-Con R Keyboard Mapper.

Uses ttkbootstrap for a modern dark theme appearance.
Provides controls for:
- Enabling/disabling stick mapping
- Selecting target applications for window switching (R key)
"""

import logging

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from .resizable import ResizableMixin
from .window_switcher import KNOWN_APPS

logger = logging.getLogger(__name__)


class MainWindow(ResizableMixin):
    """Main application window for the Joy-Con mapper."""

    def __init__(
        self,
        key_mapper,
        window_cycler,
        config,
        stop_event,
        on_minimize=None,
    ) -> None:
        self._key_mapper = key_mapper
        self._window_cycler = window_cycler
        self._config = config
        self._stop_event = stop_event
        self._on_minimize = on_minimize

        self._root = ttk.Window(
            title="NS Joy-Con R 键盘映射器",
            themename="darkly",
            size=(453, 400),
            resizable=(True, True),
        )
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.minsize(400, 347)

        # Remove native title bar for a clean dark look
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", False)

        # App selection variables: display_name → BooleanVar
        self._app_vars: dict = {}

        self._build_ui()
        self._setup_resize()
        self._center_window()

    def _build_ui(self) -> None:
        """Build the UI layout."""
        root = self._root

        # Custom title bar (draggable, with close & minimize buttons)
        titlebar = ttk.Frame(root, cursor="fleur")
        titlebar.pack(fill=X)

        # Title text in title bar
        title_text = ttk.Label(
            titlebar,
            text="  🎮 NS Joy-Con R",
            font=("Microsoft YaHei UI", 12, "bold"),
            bootstyle=INFO,
        )
        title_text.pack(side=LEFT, padx=(8, 0), pady=8)

        # Minimize & close buttons
        close_btn = ttk.Label(titlebar, text=" ✕ ", font=("", 11), bootstyle=DANGER, cursor="hand2")
        close_btn.pack(side=RIGHT, padx=(0, 4), pady=6)
        close_btn.bind("<Button-1>", lambda e: self._on_close())

        min_btn = ttk.Label(titlebar, text=" ─ ", font=("", 11), bootstyle=SECONDARY, cursor="hand2")
        min_btn.pack(side=RIGHT, padx=(0, 2), pady=6)
        min_btn.bind("<Button-1>", lambda e: self._on_minimize_click())

        # Drag binding on title bar
        for widget in (titlebar, title_text):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._do_drag)

        # Separator below title bar
        ttk.Separator(root).pack(fill=X)

        # Main content area
        main = ttk.Frame(root, padding=(20, 12, 20, 16))
        main.pack(fill=BOTH, expand=True)

        # Stick enable toggle
        self._stick_var = ttk.BooleanVar(value=True)
        stick_cb = ttk.Checkbutton(
            main,
            text="  启用摇杆映射",
            variable=self._stick_var,
            command=self._on_stick_toggle,
            bootstyle=SUCCESS,
        )
        stick_cb.pack(anchor=W, pady=(0, 12))

        # Window switch app selection
        app_label = ttk.Label(
            main,
            text="R 键窗口切换目标：",
            font=("Microsoft YaHei UI", 10),
        )
        app_label.pack(anchor=W, pady=(0, 6))

        app_frame = ttk.Frame(main)
        app_frame.pack(fill=X, padx=(20, 0), pady=(0, 12))
        self._app_frame = app_frame

        self._build_app_checkboxes()

        # Spacer
        ttk.Frame(main).pack(fill=BOTH, expand=True)

        # Bottom buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=X)

        ttk.Button(
            btn_frame,
            text="⚙ 键位设置",
            command=self._open_settings,
            bootstyle=INFO,
            width=12,
        ).pack(side=LEFT)

        ttk.Button(
            btn_frame,
            text="最小化到托盘",
            command=self._on_minimize_click,
            bootstyle=SECONDARY,
            width=12,
        ).pack(side=RIGHT)

    def _center_window(self) -> None:
        """Center the window on screen."""
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() - w) // 2
        y = (self._root.winfo_screenheight() - h) // 2
        self._root.geometry(f"+{x}+{y}")

    def _start_drag(self, event) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event) -> None:
        x = self._root.winfo_x() + event.x - self._drag_x
        y = self._root.winfo_y() + event.y - self._drag_y
        self._root.geometry(f"+{x}+{y}")

    def _on_stick_toggle(self) -> None:
        """Handle stick mapping toggle."""
        enabled = self._stick_var.get()
        self._key_mapper._stick_enabled = enabled
        if not enabled:
            self._key_mapper.release_all()
        logger.info("Stick mapping %s", "enabled" if enabled else "disabled")

    def _build_app_checkboxes(self) -> None:
        """Build/refresh app checkboxes from KNOWN_APPS."""
        # Clear existing
        for widget in self._app_frame.winfo_children():
            widget.destroy()
        self._app_vars.clear()

        # Get current cycler targets to know which are checked
        active_apps = set(self._window_cycler.app_names)

        for display_name, process_name in KNOWN_APPS.items():
            var = ttk.BooleanVar(value=(process_name in active_apps))
            self._app_vars[display_name] = var
            cb = ttk.Checkbutton(
                self._app_frame,
                text=f"  {display_name}",
                variable=var,
                command=self._on_app_toggle,
                bootstyle=INFO,
            )
            cb.pack(anchor=W, pady=3)

    def refresh_apps(self) -> None:
        """Refresh app checkboxes (call after settings change)."""
        self._build_app_checkboxes()

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

    def _open_settings(self) -> None:
        """Open the settings window."""
        from .settings_window import SettingsWindow
        SettingsWindow(self._root, self._key_mapper, self._config, self._window_cycler, main_window=self)

    def _on_close(self) -> None:
        """Handle window close — exit the program."""
        logger.info("Main window closed, stopping...")
        self._stop_event.set()
        self._root.destroy()

    @property
    def root(self):
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
