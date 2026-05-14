"""
linux_backend.py — Window-Control für Linux (xdotool + wmctrl — Stub)
───────────────────────────────────────────────────────────────────────
Stub-Implementierung für Linux-Fensterverwaltung.

LIVE UPGRADE — Voraussetzungen (Ubuntu/Pop!_OS):
  sudo apt install xdotool wmctrl

LIVE UPGRADE — Implementierungshinweise:

  list_windows():
    import subprocess
    result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
    # Format: "0x... desktop PID title"
    return [line.split(None, 3)[3] for line in result.stdout.strip().splitlines()]

  focus_window(title_fragment):
    subprocess.run(["wmctrl", "-a", title_fragment])

  minimize_window(title_fragment):
    hwnd = _get_window_id(title_fragment)  # via xdotool search
    subprocess.run(["xdotool", "windowminimize", hwnd])

  maximize_window(title_fragment):
    hwnd = _get_window_id(title_fragment)
    subprocess.run(["wmctrl", "-ir", hwnd, "-b", "add,maximized_vert,maximized_horz"])

  close_window(title_fragment):
    subprocess.run(["wmctrl", "-c", title_fragment])

  open_app(name):
    subprocess.Popen([name])

  close_app(name):
    subprocess.run(["pkill", "-f", name])

  lock_screen():
    subprocess.run(["xdg-screensaver", "lock"])
    # Alt: loginctl lock-session  (for systemd sessions)

  shutdown_pc(delay_seconds):
    import shutil
    if shutil.which("systemctl"):
        subprocess.run(["systemctl", "poweroff"])
    else:
        subprocess.run(["shutdown", "-h", f"+{delay_seconds // 60}"])

  restart_pc(delay_seconds):
    subprocess.run(["systemctl", "reboot"])

Log-Marker: [WIN-CTRL-LINUX]

Status:
  available() = False  (Stub — xdotool/wmctrl nicht geprüft)
"""

from core.logger import get_logger
from tools.window_control.backend import WindowBackend

log = get_logger("window_control.linux")


class LinuxWindowBackend(WindowBackend):
    """
    xdotool+wmctrl-basiertes Window-Control-Backend für Linux.
    Aktuell Stub — alle Methoden werfen NotImplementedError.
    """

    def __init__(self) -> None:
        log.info("[WIN-CTRL-LINUX] LinuxWindowBackend-Stub initialisiert")

    # ── Status-API ────────────────────────────────────────────────────────────

    def available(self) -> bool:
        return False

    def get_status(self) -> dict:
        return {
            "backend":   "LinuxWindowBackend",
            "platform":  "linux",
            "available": False,
        }

    # ── Fenster-Verwaltung ────────────────────────────────────────────────────

    def list_windows(self) -> list[str]:
        log.info("[WIN-CTRL-LINUX-STUB] list_windows() — nicht implementiert")
        raise NotImplementedError(
            "[WIN-CTRL-LINUX-STUB] list_windows() — siehe LIVE UPGRADE in linux_backend.py"
        )

    def focus_window(self, title_fragment: str) -> bool:
        log.info(f"[WIN-CTRL-LINUX-STUB] focus_window('{title_fragment}') — nicht implementiert")
        raise NotImplementedError("[WIN-CTRL-LINUX-STUB] focus_window()")

    def minimize_window(self, title_fragment: str) -> bool:
        log.info(f"[WIN-CTRL-LINUX-STUB] minimize_window('{title_fragment}') — nicht implementiert")
        raise NotImplementedError("[WIN-CTRL-LINUX-STUB] minimize_window()")

    def maximize_window(self, title_fragment: str) -> bool:
        log.info(f"[WIN-CTRL-LINUX-STUB] maximize_window('{title_fragment}') — nicht implementiert")
        raise NotImplementedError("[WIN-CTRL-LINUX-STUB] maximize_window()")

    def close_window(self, title_fragment: str) -> bool:
        log.info(f"[WIN-CTRL-LINUX-STUB] close_window('{title_fragment}') — nicht implementiert")
        raise NotImplementedError("[WIN-CTRL-LINUX-STUB] close_window()")

    # ── Anwendungen ───────────────────────────────────────────────────────────

    def open_app(self, name: str) -> None:
        log.info(f"[WIN-CTRL-LINUX-STUB] open_app('{name}') — nicht implementiert")
        raise NotImplementedError("[WIN-CTRL-LINUX-STUB] open_app()")

    def close_app(self, name: str) -> None:
        log.info(f"[WIN-CTRL-LINUX-STUB] close_app('{name}') — nicht implementiert")
        raise NotImplementedError("[WIN-CTRL-LINUX-STUB] close_app()")

    # ── System ────────────────────────────────────────────────────────────────

    def lock_screen(self) -> None:
        log.info("[WIN-CTRL-LINUX-STUB] lock_screen() — nicht implementiert")
        raise NotImplementedError("[WIN-CTRL-LINUX-STUB] lock_screen()")

    def shutdown_pc(self, delay_seconds: int = 0) -> None:
        log.info(f"[WIN-CTRL-LINUX-STUB] shutdown_pc(delay={delay_seconds}) — nicht implementiert")
        raise NotImplementedError("[WIN-CTRL-LINUX-STUB] shutdown_pc()")

    def restart_pc(self, delay_seconds: int = 0) -> None:
        log.info(f"[WIN-CTRL-LINUX-STUB] restart_pc(delay={delay_seconds}) — nicht implementiert")
        raise NotImplementedError("[WIN-CTRL-LINUX-STUB] restart_pc()")
