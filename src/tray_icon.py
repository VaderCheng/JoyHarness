"""System tray icon for NS Joy-Con R Keyboard Mapper.

Provides a system tray icon with right-click context menu.
Uses pystray for cross-platform tray support and Pillow for icon generation.
"""

import threading
import logging
from typing import Callable

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


def create_icon_image() -> Image.Image:
    """Generate a simple Joy-Con R style icon image.

    Creates a 64x64 rounded rectangle with "R" text,
    resembling a controller button.
    """
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background (dark blue)
    margin = 4
    radius = 14
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(30, 60, 180),
        outline=(60, 100, 220),
        width=2,
    )

    # "R" text in the center
    text = "R"
    bbox = draw.textbbox((0, 0), text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) / 2
    y = (size - th) / 2 - 2
    draw.text((x, y), text, fill=(255, 255, 255))

    return img


def create_tray_icon(
    stop_event: threading.Event,
    on_show_mappings: Callable | None = None,
) -> pystray.Icon:
    """Create and return a system tray icon.

    Args:
        stop_event: Threading event to signal program exit.
        on_show_mappings: Optional callback to display current mappings.

    Returns:
        Configured pystray.Icon instance (not yet running).
    """
    image = create_icon_image()

    menu_items = []

    if on_show_mappings:
        menu_items.append(pystray.MenuItem("显示映射", on_show_mappings))
        menu_items.append(pystray.Menu.SEPARATOR)

    menu_items.append(pystray.MenuItem("退出", _make_quit_handler(stop_event)))

    menu = pystray.Menu(*menu_items)

    icon = pystray.Icon(
        name="NS Joy-Con R",
        icon=image,
        title="NS Joy-Con R 键盘映射",
        menu=menu,
    )

    return icon


def _make_quit_handler(stop_event: threading.Event) -> Callable:
    """Create a quit menu handler that sets the stop event and stops the icon."""

    def quit_action(icon: pystray.Icon, item: pystray.MenuItem) -> None:
        logger.info("Quit requested from tray menu")
        icon.stop()
        stop_event.set()

    return quit_action


def run_tray(icon: pystray.Icon) -> None:
    """Run the tray icon event loop (blocks until icon.stop() is called)."""
    logger.info("System tray icon started")
    icon.run()
    logger.info("System tray icon stopped")
