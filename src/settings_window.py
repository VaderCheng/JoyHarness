"""Settings window for button mapping customization.

Uses a tabbed layout (Notebook) to separate button mappings
from the window switch app list.
"""

import logging
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from .resizable import ResizableMixin
from .window_switcher import KNOWN_APPS

logger = logging.getLogger(__name__)

EDITABLE_ACTIONS = ("tap", "hold", "auto", "combination", "sequence", "window_switch")
MAPPABLE_BUTTONS = ["A", "B", "X", "Y", "R", "ZR", "Plus", "Home", "RStick", "SL", "SR"]


class SettingsWindow(ResizableMixin):
    """Settings window for customizing button mappings and app list."""

    def __init__(self, parent, key_mapper, config: dict, window_cycler, main_window=None) -> None:
        self._key_mapper = key_mapper
        self._config = config
        self._window_cycler = window_cycler
        self._main_window = main_window
        self._rows: dict[str, dict] = {}
        self._app_rows: list[dict] = []

        self._win = ttk.Toplevel(parent)
        self._win.title("键位设置")
        self._win.resizable(True, True)
        self._win.overrideredirect(True)
        self._win.minsize(420, 400)

        self._build_ui()
        self._setup_resize()
        self._center_on_parent(parent)

    def _build_ui(self) -> None:
        win = self._win

        # === Custom title bar ===
        titlebar = ttk.Frame(win, cursor="fleur")
        titlebar.pack(fill=X)

        ttk.Label(
            titlebar, text="  ⚙ 键位设置",
            font=("Microsoft YaHei UI", 12, "bold"), bootstyle=INFO,
        ).pack(side=LEFT, padx=(8, 0), pady=8)

        close_btn = ttk.Label(titlebar, text=" ✕ ", font=("", 11), bootstyle=DANGER, cursor="hand2")
        close_btn.pack(side=RIGHT, padx=(0, 4), pady=6)
        close_btn.bind("<Button-1>", lambda e: self._win.destroy())

        titlebar.bind("<ButtonPress-1>", self._start_drag)
        titlebar.bind("<B1-Motion>", self._do_drag)

        ttk.Separator(win).pack(fill=X)

        # === Tabs ===
        nb = ttk.Notebook(win)
        nb.pack(fill=BOTH, expand=True, padx=10, pady=(8, 0))

        tab_mapping = ttk.Frame(nb, padding=10)
        nb.add(tab_mapping, text=" 按键映射 ")

        tab_apps = ttk.Frame(nb, padding=10)
        nb.add(tab_apps, text=" 切换应用 ")

        self._build_mapping_tab(tab_mapping)
        self._build_apps_tab(tab_apps)

        # === Bottom buttons ===
        ttk.Separator(win).pack(fill=X, padx=16, pady=(8, 0))
        bottom = ttk.Frame(win, padding=(16, 10, 16, 12))
        bottom.pack(fill=X)

        ttk.Button(bottom, text="恢复默认", command=self._reset_defaults, bootstyle=WARNING, width=10).pack(side=LEFT)
        ttk.Button(bottom, text="取消", command=self._win.destroy, bootstyle=SECONDARY, width=8).pack(side=RIGHT, padx=(8, 0))
        ttk.Button(bottom, text="应用", command=self._apply, bootstyle=SUCCESS, width=8).pack(side=RIGHT)

    # ────────────────────────────────────────
    # Tab 1: Button mappings
    # ────────────────────────────────────────

    def _build_mapping_tab(self, parent: ttk.Frame) -> None:
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=X, pady=(0, 4))
        ttk.Label(header, text="按钮", font=("Microsoft YaHei UI", 9, "bold"), width=8).pack(side=LEFT)
        ttk.Label(header, text="动作类型", font=("Microsoft YaHei UI", 9, "bold"), width=14).pack(side=LEFT, padx=(8, 0))
        ttk.Label(header, text="按键", font=("Microsoft YaHei UI", 9, "bold"), width=14).pack(side=LEFT, padx=(8, 0))

        ttk.Separator(parent).pack(fill=X, pady=(0, 4))

        rows_frame = ttk.Frame(parent)
        rows_frame.pack(fill=BOTH, expand=True)

        mappings = self._config.get("mappings", {}).get("buttons", {})
        for btn_name in MAPPABLE_BUTTONS:
            self._add_button_row(rows_frame, btn_name, mappings.get(btn_name, {}))

    def _add_button_row(self, parent: ttk.Frame, btn_name: str, mapping: dict) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=X, pady=2)

        ttk.Label(row, text=btn_name, font=("Microsoft YaHei UI", 10), width=8).pack(side=LEFT)

        current_action = mapping.get("action", "tap")
        action_var = ttk.StringVar(value=current_action)
        action_cb = ttk.Combobox(
            row, textvariable=action_var, values=EDITABLE_ACTIONS,
            state="readonly", width=12, bootstyle=INFO,
        )
        action_cb.pack(side=LEFT, padx=(8, 0))

        current_key = ""
        if current_action in ("tap", "hold", "auto"):
            current_key = mapping.get("key", "")
        elif current_action in ("combination", "sequence"):
            current_key = "+".join(mapping.get("keys", []))

        key_var = ttk.StringVar(value=current_key)
        key_entry = ttk.Entry(row, textvariable=key_var, width=14, bootstyle=SECONDARY)

        def on_action_change(event=None):
            action = action_var.get()
            if action == "window_switch":
                key_entry.configure(state=DISABLED)
                key_var.set("")
            else:
                key_entry.configure(state=NORMAL)
                if action in ("combination", "sequence"):
                    key_entry.configure(bootstyle=INFO)
                else:
                    key_entry.configure(bootstyle=SECONDARY)

        action_cb.bind("<<ComboboxSelected>>", on_action_change)
        action_cb.pack(side=LEFT, padx=(8, 0))

        if current_action == "window_switch":
            key_entry.configure(state=DISABLED)
        elif current_action == "macro":
            action_var.set(current_action)
            action_cb.configure(state=DISABLED)
            key_entry.configure(state=DISABLED)

        key_entry.pack(side=LEFT, padx=(8, 0))

        self._rows[btn_name] = {
            "action_var": action_var,
            "key_var": key_var,
            "action_cb": action_cb,
            "key_entry": key_entry,
        }

    # ────────────────────────────────────────
    # Tab 2: Window switch apps
    # ────────────────────────────────────────

    def _build_apps_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(
            parent,
            text="设置 R 键可在哪些应用间切换窗口：",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor=W, pady=(0, 8))

        # Header
        header = ttk.Frame(parent)
        header.pack(fill=X, pady=(0, 4))
        ttk.Label(header, text="应用名称", font=("Microsoft YaHei UI", 9, "bold"), width=18).pack(side=LEFT)
        ttk.Label(header, text="EXE 名称", font=("Microsoft YaHei UI", 9, "bold"), width=20).pack(side=LEFT, padx=(8, 0))
        # placeholder for delete column
        ttk.Label(header, text="  ", width=4).pack(side=LEFT)

        ttk.Separator(parent).pack(fill=X, pady=(0, 4))

        self._app_list_frame = ttk.Frame(parent)
        self._app_list_frame.pack(fill=BOTH, expand=True)

        for display_name, exe_name in KNOWN_APPS.items():
            self._add_app_row(display_name, exe_name)

        ttk.Button(
            parent, text="＋ 添加应用", command=lambda: self._add_app_row(),
            bootstyle=SUCCESS, width=14,
        ).pack(anchor=W, pady=(8, 0))

    def _add_app_row(self, display_name: str = "", exe_name: str = "") -> None:
        row = ttk.Frame(self._app_list_frame)
        row.pack(fill=X, pady=2)

        name_var = ttk.StringVar(value=display_name)
        exe_var = ttk.StringVar(value=exe_name)

        name_entry = ttk.Entry(row, textvariable=name_var, width=18, bootstyle=SECONDARY)
        name_entry.pack(side=LEFT)

        ttk.Label(row, text="→", font=("", 10)).pack(side=LEFT, padx=4)

        exe_entry = ttk.Entry(row, textvariable=exe_var, width=18, bootstyle=SECONDARY)
        exe_entry.pack(side=LEFT)

        del_btn = ttk.Label(row, text=" ✕ ", font=("", 10), bootstyle=DANGER, cursor="hand2")
        del_btn.pack(side=LEFT, padx=(4, 0))
        del_btn.bind("<Button-1>", lambda e, r=row: r.destroy())

        self._app_rows.append({"frame": row, "name_var": name_var, "exe_var": exe_var})

    def _collect_apps(self) -> tuple[dict[str, str], list[str]]:
        apps = {}
        errors = []
        for widgets in self._app_rows:
            if not widgets["frame"].winfo_exists():
                continue
            name = widgets["name_var"].get().strip()
            exe = widgets["exe_var"].get().strip()
            if not name and not exe:
                continue
            if not name:
                errors.append("应用名称不能为空")
                continue
            if not exe:
                errors.append(f"{name} 的 EXE 名称不能为空")
                continue
            apps[name] = exe.lower()
        return apps, errors

    # ────────────────────────────────────────
    # Apply / Reset
    # ────────────────────────────────────────

    def _apply(self) -> None:
        errors = []
        new_mappings = {}

        for btn_name, widgets in self._rows.items():
            action = widgets["action_var"].get()
            key = widgets["key_var"].get().strip()
            if action in ("tap", "hold", "auto"):
                if not key:
                    errors.append(f"{btn_name}: 按键不能为空")
                    continue
                new_mappings[btn_name] = {"action": action, "key": key}
            elif action in ("combination", "sequence"):
                keys = [k.strip() for k in key.replace("+", ",").replace("，", ",").split(",") if k.strip()]
                if not keys:
                    errors.append(f"{btn_name}: {action} 至少需要一个按键")
                    continue
                entry = {"action": action, "keys": keys}
                if action == "sequence":
                    old = self._config["mappings"]["buttons"].get(btn_name, {})
                    if old.get("action") == "sequence" and "repeat" in old:
                        entry["repeat"] = old["repeat"]
                new_mappings[btn_name] = entry
            elif action == "window_switch":
                new_mappings[btn_name] = {"action": "window_switch"}
            else:
                new_mappings[btn_name] = self._config["mappings"]["buttons"].get(btn_name, {})

        apps, app_errors = self._collect_apps()
        errors.extend(app_errors)

        if errors:
            Messagebox.show_warning("\n".join(errors), title="配置错误", parent=self._win)
            return

        # Apply button mappings
        self._config["mappings"]["buttons"].update(new_mappings)
        from .constants import BUTTON_INDICES
        self._key_mapper._button_mappings.clear()
        for btn_name, mapping in self._config["mappings"]["buttons"].items():
            if btn_name in BUTTON_INDICES:
                self._key_mapper._button_mappings[BUTTON_INDICES[btn_name]] = mapping

        # Apply app list
        KNOWN_APPS.clear()
        KNOWN_APPS.update(apps)
        self._window_cycler.app_names = list(apps.values())

        # Refresh main window app checkboxes
        if self._main_window:
            self._main_window.refresh_apps()

        logger.info("Settings applied. Apps: %s", apps)
        self._win.destroy()

    def _reset_defaults(self) -> None:
        from .constants import DEFAULT_MAPPINGS

        defaults = DEFAULT_MAPPINGS.get("buttons", {})
        for btn_name in MAPPABLE_BUTTONS:
            mapping = defaults.get(btn_name, {})
            widgets = self._rows.get(btn_name)
            if not widgets:
                continue
            action = mapping.get("action", "tap")
            widgets["action_var"].set(action)
            if action in ("tap", "hold", "auto"):
                widgets["key_var"].set(mapping.get("key", ""))
                widgets["key_entry"].configure(state=NORMAL)
                widgets["action_cb"].configure(state="readonly")
            elif action in ("combination", "sequence"):
                widgets["key_var"].set("+".join(mapping.get("keys", [])))
                widgets["key_entry"].configure(state=NORMAL)
                widgets["action_cb"].configure(state="readonly")
            elif action == "window_switch":
                widgets["key_var"].set("")
                widgets["key_entry"].configure(state=DISABLED)
                widgets["action_cb"].configure(state="readonly")
            else:
                widgets["action_var"].set(action)
                widgets["action_cb"].configure(state=DISABLED)
                widgets["key_entry"].configure(state=DISABLED)

        for widgets in self._app_rows:
            if widgets["frame"].winfo_exists():
                widgets["frame"].destroy()
        self._app_rows.clear()
        for name, exe in {"VS Code": "code.exe", "飞书": "feishu.exe"}.items():
            self._add_app_row(name, exe)

    # ────────────────────────────────────────
    # Window utilities
    # ────────────────────────────────────────

    def _center_on_parent(self, parent) -> None:
        self._win.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        w, h = self._win.winfo_width(), self._win.winfo_height()
        self._win.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

    def _start_drag(self, event) -> None:
        self._drag_x, self._drag_y = event.x, event.y

    def _do_drag(self, event) -> None:
        self._win.geometry(f"+{self._win.winfo_x() + event.x - self._drag_x}+{self._win.winfo_y() + event.y - self._drag_y}")
