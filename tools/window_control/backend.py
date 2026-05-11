"""
backend.py — Abstrakte Basis für Window-Control-Backends
─────────────────────────────────────────────────────────
Neue Backends erben von WindowBackend und implementieren alle
abstractmethods. Die Factory in factory.py wählt per sys.platform
das richtige Backend.

Aktuell verfügbare Backends:
  WindowsWindowBackend  (Win32 via ctypes)  — windows_backend.py
  LinuxWindowBackend    (xdotool+wmctrl — Stub) — linux_backend.py

Status-API:
  backend.get_status() -> dict
  backend.available()  -> bool
"""

from abc import ABC, abstractmethod


class WindowBackend(ABC):
    """Abstrakte Basis für plattform-spezifische Window-Management-Implementierungen."""

    # ── Status-API ────────────────────────────────────────────────────────────

    @abstractmethod
    def available(self) -> bool:
        """True wenn Backend einsatzbereit ist."""

    @abstractmethod
    def get_status(self) -> dict:
        """
        Return current backend state as serializable dict.
        Mindestfelder: backend, platform, available (bool).
        """

    # ── Fenster-Verwaltung ────────────────────────────────────────────────────

    @abstractmethod
    def list_windows(self) -> list[str]:
        """Liste aller sichtbaren Fenster-Titel."""

    @abstractmethod
    def focus_window(self, title_fragment: str) -> bool:
        """
        Bringt das erste Fenster dessen Titel title_fragment enthält in den Vordergrund.
        Gibt True zurück wenn erfolgreich, False wenn kein Fenster gefunden.
        """

    @abstractmethod
    def minimize_window(self, title_fragment: str) -> bool:
        """Minimiert das passende Fenster. True bei Erfolg."""

    @abstractmethod
    def maximize_window(self, title_fragment: str) -> bool:
        """Maximiert das passende Fenster. True bei Erfolg."""

    @abstractmethod
    def close_window(self, title_fragment: str) -> bool:
        """Schließt das passende Fenster. True bei Erfolg."""

    # ── Anwendungen ───────────────────────────────────────────────────────────

    @abstractmethod
    def open_app(self, name: str) -> None:
        """Startet eine Anwendung per Name oder Pfad."""

    @abstractmethod
    def close_app(self, name: str) -> None:
        """Beendet einen laufenden Prozess per Name."""

    # ── System ────────────────────────────────────────────────────────────────

    @abstractmethod
    def lock_screen(self) -> None:
        """Sperrt den Bildschirm."""

    @abstractmethod
    def shutdown_pc(self, delay_seconds: int = 0) -> None:
        """Fährt den PC herunter."""

    @abstractmethod
    def restart_pc(self, delay_seconds: int = 0) -> None:
        """Startet den PC neu."""
