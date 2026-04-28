"""Platform abstraction layer.

Auto-detects the current OS and exports the correct backend implementations
for keyboard simulation, window management, and permission checks.

Supported platforms: Windows, macOS.
"""

import sys

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
