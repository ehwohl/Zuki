"""
web_renderer.py — UIRenderer for the React/WebSocket UI

Overrides user_prompt() to block on a thread-safe queue instead of stdin.
The bridge calls feed_input() to unblock it when a WS command arrives.

Usage: set ZUKI_UI=web in .env
"""

import queue
import threading

from core.ui import TerminalRenderer


class WebUIRenderer(TerminalRenderer):
    """UI renderer for the React front-end. Input comes via WebSocket, not stdin."""

    def __init__(self) -> None:
        super().__init__()
        self._q: queue.Queue[str] = queue.Queue()
        self._waiting = threading.Event()

    def kind(self) -> str:
        return "web"

    # ── Interactive input (replaces stdin) ────────────────────────────────────

    def user_prompt(self) -> str:
        """Block until feed_input() delivers an answer (or 10-min timeout)."""
        self._waiting.set()
        try:
            return self._q.get(timeout=600)
        except queue.Empty:
            # Browser closed or no response — raise so the calling loop exits cleanly
            raise RuntimeError("WebUI: Keine Eingabe nach 10 Minuten — Interaktion beendet")
        finally:
            self._waiting.clear()

    def feed_input(self, text: str) -> bool:
        """
        Called by the bridge command handler when a WS command arrives.
        Returns True if the text was consumed by a waiting user_prompt(),
        False if no interactive prompt is currently blocking.
        """
        if self._waiting.is_set():
            self._q.put(text)
            return True
        return False

    def is_waiting_for_input(self) -> bool:
        return self._waiting.is_set()

    # ── Output — emit to React terminal in addition to Python terminal ────────

    def speak_zuki(self, text: str) -> None:
        super().speak_zuki(text)
        self._emit(text)

    def system_msg(self, text: str) -> None:
        super().system_msg(text)
        self._emit(text)

    @staticmethod
    def _emit(text: str) -> None:
        try:
            import ui_bridge
            ui_bridge.emit_response(text)
        except Exception:
            pass
