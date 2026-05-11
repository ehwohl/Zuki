"""
factory.py — Window-Backend-Factory
─────────────────────────────────────
Wählt per sys.platform das passende Window-Control-Backend.
  win32  → WindowsWindowBackend  (ctypes/Win32)
  linux  → LinuxWindowBackend    (xdotool+wmctrl — Stub)
  other  → NotImplementedError

Log-Marker: [WIN-CTRL-FACTORY]
"""

import sys

from core.logger import get_logger
from tools.window_control.backend import WindowBackend

log = get_logger("window_control.factory")


def get_window_backend() -> WindowBackend:
    """Factory: erstellt und gibt das plattformpassende WindowBackend zurück."""
    platform = sys.platform
    if platform == "win32":
        from tools.window_control.windows_backend import WindowsWindowBackend
        log.info("[WIN-CTRL-FACTORY] Platform: win32 → WindowsWindowBackend")
        return WindowsWindowBackend()
    elif platform.startswith("linux"):
        from tools.window_control.linux_backend import LinuxWindowBackend
        log.info("[WIN-CTRL-FACTORY] Platform: linux → LinuxWindowBackend (Stub)")
        return LinuxWindowBackend()
    else:
        raise NotImplementedError(
            f"[WIN-CTRL-FACTORY] Kein Window-Backend für Platform '{platform}'.\n"
            f"  Unterstützt: win32, linux"
        )
