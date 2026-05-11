"""
ui_renderer.py — Abstrakte Basis für alle Zuki-UI-Renderer
────────────────────────────────────────────────────────────
Jeder Renderer (Terminal, Web, GUI, …) erbt von UIRenderer
und implementiert die unten definierten Methoden.

Aktuell registrierte Renderer:
  "terminal"  →  TerminalRenderer  (core/ui.py)

Neuen Renderer hinzufügen:
  1. Klasse schreiben, von UIRenderer erben
  2. In core/ui_factory.py in _RENDERERS eintragen
  3. ENV ZUKI_UI=<key> setzen

Status-API:
  renderer.kind()  →  str   ("terminal" | "web" | …)

Log-Marker: [UI-INIT]
"""

from abc import ABC, abstractmethod


class UIRenderer(ABC):
    """Abstrakte Basis für alle UI-Renderer."""

    # ── Meta ──────────────────────────────────────────────────────────────────

    @abstractmethod
    def kind(self) -> str:
        """Eindeutiger Renderer-Bezeichner, z. B. 'terminal' oder 'web'."""
        ...

    # ── Startup ───────────────────────────────────────────────────────────────

    @abstractmethod
    def print_banner(
        self,
        simulation:      bool,
        memory_count:    int,
        whisper_mode:    str  = "",
        tts_voice:       str  = "",
        news_count:      int  = 0,
        watchlist_hits:  int  = 0,
        sentiment:       str  = "NEU",
        calendar_events: list | None = None,
    ) -> None:
        """Start-Banner mit Modus, Gedächtnis und optionalen News."""
        ...

    @abstractmethod
    def print_dashboard(
        self,
        simulation:   bool,
        api_provider: str,
        name:         str,
        level:        str,
        memory_count: int,
        whisper_mode: str,
        tts_voice:    str,
        vision_ok:    bool,
        tenant_name:  str = "self",
    ) -> None:
        """Kompaktes Startup-Dashboard — ein schneller Blick auf alles."""
        ...

    # ── Dialog ────────────────────────────────────────────────────────────────

    @abstractmethod
    def user_prompt(self) -> str:
        """Zeigt den User-Prompt und gibt die Eingabe zurück."""
        ...

    @abstractmethod
    def speak_zuki(self, text: str) -> None:
        """Gibt Zukis Antwort vollständig aus."""
        ...

    # ── Status-Icons ──────────────────────────────────────────────────────────

    @abstractmethod
    def listening(self) -> None:
        """Zeigt an, dass Zuki auf Spracheingabe wartet."""
        ...

    @abstractmethod
    def thinking(self) -> None:
        """Zeigt an, dass Zuki verarbeitet."""
        ...

    @abstractmethod
    def speaking(self) -> None:
        """Zeigt an, dass Zuki spricht (TTS läuft)."""
        ...

    @abstractmethod
    def system_msg(self, text: str) -> None:
        """System-Nachricht (dim, nicht kritisch)."""
        ...

    @abstractmethod
    def error_msg(self, text: str) -> None:
        """Fehlermeldung (rot, sichtbar)."""
        ...

    @abstractmethod
    def voice_echo(self, text: str) -> None:
        """Zeigt den vom Mikrofon erkannten Text."""
        ...

    # ── Broker-Modus ──────────────────────────────────────────────────────────

    @abstractmethod
    def print_broker_status(
        self,
        news_count:      int,
        watchlist_hits:  int,
        sentiment:       str,
        calendar_events: list,
    ) -> None:
        """Kompakter Broker-Status-Block."""
        ...

    @abstractmethod
    def print_broker_deactivated(self) -> None:
        """Meldet Deaktivierung des Broker-Modus."""
        ...

    # ── System-Test ───────────────────────────────────────────────────────────

    @abstractmethod
    def print_system_test(self, results: list) -> None:
        """Gibt System-Diagnose-Ergebnisse als farbige Tabelle aus."""
        ...
