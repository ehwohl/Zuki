"""
windows_backend.py — Window-Control für Windows (Win32 via ctypes)
───────────────────────────────────────────────────────────────────
Echte Implementierung für Windows-Fensterverwaltung.

Abhängigkeiten:
  - ctypes (stdlib, immer verfügbar)
  - subprocess (stdlib)
  - pywin32 optional (bessere EnumWindows-Unterstützung)
    pip install pywin32

Log-Marker: [WIN-CTRL-WIN]
"""

import ctypes
import ctypes.wintypes
import subprocess
import sys
from core.logger import get_logger
from tools.window_control.backend import WindowBackend

log = get_logger("window_control.windows")

user32 = ctypes.windll.user32

# Win32 Konstanten
SW_MINIMIZE  = 6
SW_MAXIMIZE  = 3
SW_RESTORE   = 9
SW_SHOWDEFAULT = 10


def _enum_windows() -> list[tuple[int, str]]:
    """Gibt Liste von (hwnd, title) aller sichtbaren Top-Level-Fenster zurück."""
    windows: list[tuple[int, str]] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def callback(hwnd, lParam):  # noqa: ANN001
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                windows.append((hwnd, buf.value))
        return True

    user32.EnumWindows(callback, 0)
    return windows


def _find_window(title_fragment: str) -> int | None:
    """Sucht erstes Fenster dessen Titel title_fragment enthält (case-insensitive)."""
    frag = title_fragment.lower()
    for hwnd, title in _enum_windows():
        if frag in title.lower():
            return hwnd
    return None


class WindowsWindowBackend(WindowBackend):
    """Win32-basiertes Window-Control-Backend für Windows."""

    # ── Status-API ────────────────────────────────────────────────────────────

    def available(self) -> bool:
        return sys.platform == "win32"

    def get_status(self) -> dict:
        return {
            "backend":   "WindowsWindowBackend",
            "platform":  "win32",
            "available": self.available(),
        }

    # ── Fenster-Verwaltung ────────────────────────────────────────────────────

    def list_windows(self) -> list[str]:
        titles = [title for _, title in _enum_windows() if title.strip()]
        log.debug(f"[WIN-CTRL-WIN] {len(titles)} Fenster gefunden")
        return titles

    def focus_window(self, title_fragment: str) -> bool:
        hwnd = _find_window(title_fragment)
        if hwnd is None:
            log.warning(f"[WIN-CTRL-WIN] Fenster nicht gefunden: '{title_fragment}'")
            return False
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        log.info(f"[WIN-CTRL-WIN] Fenster fokussiert: '{title_fragment}'")
        return True

    def minimize_window(self, title_fragment: str) -> bool:
        hwnd = _find_window(title_fragment)
        if hwnd is None:
            log.warning(f"[WIN-CTRL-WIN] Fenster nicht gefunden: '{title_fragment}'")
            return False
        user32.ShowWindow(hwnd, SW_MINIMIZE)
        log.info(f"[WIN-CTRL-WIN] Fenster minimiert: '{title_fragment}'")
        return True

    def maximize_window(self, title_fragment: str) -> bool:
        hwnd = _find_window(title_fragment)
        if hwnd is None:
            log.warning(f"[WIN-CTRL-WIN] Fenster nicht gefunden: '{title_fragment}'")
            return False
        user32.ShowWindow(hwnd, SW_MAXIMIZE)
        log.info(f"[WIN-CTRL-WIN] Fenster maximiert: '{title_fragment}'")
        return True

    def close_window(self, title_fragment: str) -> bool:
        hwnd = _find_window(title_fragment)
        if hwnd is None:
            log.warning(f"[WIN-CTRL-WIN] Fenster nicht gefunden: '{title_fragment}'")
            return False
        WM_CLOSE = 0x0010
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        log.info(f"[WIN-CTRL-WIN] WM_CLOSE gesendet: '{title_fragment}'")
        return True

    # ── Anwendungen ───────────────────────────────────────────────────────────

    def open_app(self, name: str) -> None:
        log.info(f"[WIN-CTRL-WIN] open_app: '{name}'")
        subprocess.Popen(["start", name], shell=True)

    def close_app(self, name: str) -> None:
        log.info(f"[WIN-CTRL-WIN] close_app: '{name}'")
        exe = name if name.endswith(".exe") else name + ".exe"
        subprocess.run(["taskkill", "/f", "/im", exe], capture_output=True)

    # ── System ────────────────────────────────────────────────────────────────

    def lock_screen(self) -> None:
        log.info("[WIN-CTRL-WIN] lock_screen()")
        ctypes.windll.user32.LockWorkStation()

    def shutdown_pc(self, delay_seconds: int = 0) -> None:
        log.info(f"[WIN-CTRL-WIN] shutdown_pc(delay={delay_seconds})")
        subprocess.run(["shutdown", "/s", "/t", str(delay_seconds)])

    def restart_pc(self, delay_seconds: int = 0) -> None:
        log.info(f"[WIN-CTRL-WIN] restart_pc(delay={delay_seconds})")
        subprocess.run(["shutdown", "/r", "/t", str(delay_seconds)])
