"""
pc_control.py — Plattform-agnostische PC-Steuerung
────────────────────────────────────────────────────
Delegiert alle Aufrufe an das plattform-spezifische WindowBackend.
Das Backend wird lazy via get_window_backend() erstellt.

Plattform-Backends:
  win32  → tools/window_control/windows_backend.py  (WindowsWindowBackend)
  linux  → tools/window_control/linux_backend.py    (LinuxWindowBackend — Stub)

Status-API:
  PCControl.available()   → bool (True wenn Backend bereit ist)
  PCControl.get_status()  → dict

Clipboard-Operationen (pyperclip, plattform-neutral) sind weiterhin hier.

Log-Marker: [PC-CONTROL]
"""

from core.logger import get_logger
from tools.window_control import get_window_backend
from tools.window_control.backend import WindowBackend

log = get_logger("pc_control")

_backend: WindowBackend | None = None


def _get_backend() -> WindowBackend:
    global _backend
    if _backend is None:
        _backend = get_window_backend()
    return _backend


class PCControl:
    """
    Plattform-agnostische PC-Steuerung.
    Delegiert Fenster-/App-/System-Aktionen an das passende WindowBackend.
    """

    # ── Status-API ────────────────────────────────────────────────────────────

    @staticmethod
    def available() -> bool:
        try:
            return _get_backend().available()
        except Exception:
            return False

    @staticmethod
    def get_status() -> dict:
        try:
            return _get_backend().get_status()
        except Exception as e:
            return {"backend": "unbekannt", "available": False, "error": str(e)}

    # ── Fenster-Verwaltung ────────────────────────────────────────────────────

    def list_windows(self) -> list[str]:
        """Liste aller sichtbaren Fenster-Titel."""
        return _get_backend().list_windows()

    def focus_window(self, title_fragment: str) -> bool:
        """Bringt das Fenster mit passendem Titel in den Vordergrund."""
        return _get_backend().focus_window(title_fragment)

    def minimize_window(self, title_fragment: str) -> bool:
        return _get_backend().minimize_window(title_fragment)

    def maximize_window(self, title_fragment: str) -> bool:
        return _get_backend().maximize_window(title_fragment)

    def close_window(self, title_fragment: str) -> bool:
        return _get_backend().close_window(title_fragment)

    # ── Anwendungen ───────────────────────────────────────────────────────────

    def open_app(self, name: str) -> None:
        """Öffnet eine Anwendung per Name oder Pfad."""
        _get_backend().open_app(name)

    def close_app(self, name: str) -> None:
        """Beendet einen laufenden Prozess per Name."""
        _get_backend().close_app(name)

    # ── System ────────────────────────────────────────────────────────────────

    def shutdown_pc(self, delay_seconds: int = 0) -> None:
        _get_backend().shutdown_pc(delay_seconds)

    def restart_pc(self, delay_seconds: int = 0) -> None:
        _get_backend().restart_pc(delay_seconds)

    def lock_screen(self) -> None:
        _get_backend().lock_screen()

    # ── Clipboard (plattform-neutral via pyperclip) ───────────────────────────

    def get_clipboard(self) -> str:
        """Gibt den aktuellen Clipboard-Inhalt zurück."""
        try:
            import pyperclip  # noqa: PLC0415
            return pyperclip.paste()
        except ImportError:
            log.info("[PC-CONTROL-STUB] get_clipboard — pyperclip nicht installiert")
            raise NotImplementedError(
                "[PC-CONTROL] get_clipboard() benötigt pyperclip: pip install pyperclip"
            )

    def set_clipboard(self, text: str) -> None:
        """Schreibt Text in die Zwischenablage."""
        try:
            import pyperclip  # noqa: PLC0415
            pyperclip.copy(text)
            log.info(f"[PC-CONTROL] Clipboard gesetzt: '{text[:30]}…'")
        except ImportError:
            log.info("[PC-CONTROL-STUB] set_clipboard — pyperclip nicht installiert")
            raise NotImplementedError(
                "[PC-CONTROL] set_clipboard() benötigt pyperclip: pip install pyperclip"
            )

    def open_file(self, path: str) -> None:
        """Öffnet eine Datei mit dem Standard-Programm."""
        import sys
        import subprocess
        if sys.platform == "win32":
            import os
            os.startfile(path)
        elif sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", path])
        else:
            raise NotImplementedError(f"[PC-CONTROL] open_file() — Platform '{sys.platform}' unbekannt")
        log.info(f"[PC-CONTROL] open_file: '{path}'")

    # ── Lautstärke (Windows: pycaw — Stub bei Linux) ──────────────────────────

    def set_volume(self, level: int) -> None:
        """Setzt die System-Lautstärke (0–100). Windows: pycaw, Linux: amixer."""
        import sys
        if sys.platform == "win32":
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                log.info(f"[PC-CONTROL] Lautstärke gesetzt: {level}%")
            except ImportError:
                raise NotImplementedError(
                    "[PC-CONTROL] set_volume() benötigt pycaw: pip install pycaw"
                )
        elif sys.platform.startswith("linux"):
            import subprocess
            subprocess.run(["amixer", "sset", "Master", f"{level}%"], capture_output=True)
            log.info(f"[PC-CONTROL] Lautstärke gesetzt (amixer): {level}%")
        else:
            raise NotImplementedError(f"[PC-CONTROL] set_volume() — Platform '{sys.platform}' unbekannt")

    def mute(self) -> None:
        """Schaltet den Ton stumm."""
        self.set_volume(0)
