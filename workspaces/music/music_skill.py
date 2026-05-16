"""
music_skill.py — MusicSkill for Zuki
──────────────────────────────────────
Triggers : musik, music, music start, musik start

Handles:
  pitch_event  WebSocket messages — accumulates session stats
  navigate     to music workspace on terminal command

Emits:
  music_session_stats — note count, avg cents deviation, time active

Log marker: [MUSIC-SKILL]
"""

import threading
from datetime import datetime

import ui_bridge
from core.logger import get_logger
from workspaces.base import Skill

log = get_logger("music.skill")


class MusicSkill(Skill):
    name        = "music"
    triggers    = {"musik", "music", "music start", "musik start"}
    description = (
        "Music practice workspace: real-time pitch detection with piano roll. "
        "Handles voice and instrument practice sessions."
    )
    tenant_aware = True

    def __init__(self) -> None:
        self._session_start: datetime | None = None
        self._note_count: int = 0
        self._cents_sum: float = 0.0
        self._last_note: str = ""
        self._lock = threading.Lock()

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def handle(self, context: dict) -> str | None:
        cmd = context.get("cmd", "").strip()
        # Route internal pitch_event messages (dispatched from ui_bridge)
        if cmd == "_pitch_event":
            self._handle_pitch_event(context)
            return None
        # Navigate to music workspace via terminal command
        ui_bridge.emit_workspace_change("music")
        log.info("[MUSIC-SKILL] Navigating to music workspace")
        return "Musikpraxis-Bereich geöffnet."

    # ── Pitch event handler ───────────────────────────────────────────────────

    def _handle_pitch_event(self, context: dict) -> None:
        """Receives a pitch_event dict from the WebSocket bridge and updates session stats."""
        data = context.get("data", {})
        with self._lock:
            if self._session_start is None:
                self._session_start = datetime.utcnow()
                log.info("[MUSIC-SKILL] Session started")
            self._note_count += 1
            self._cents_sum += abs(data.get("cents", 0))
            self._last_note = data.get("note", "")
        self._emit_stats()

    # ── Stats emitter ─────────────────────────────────────────────────────────

    def _emit_stats(self) -> None:
        """Broadcasts accumulated session statistics to all frontend clients."""
        with self._lock:
            elapsed = (
                int((datetime.utcnow() - self._session_start).total_seconds())
                if self._session_start else 0
            )
            avg = self._cents_sum / self._note_count if self._note_count > 0 else 0.0
            note_count   = self._note_count
            last_note    = self._last_note
            started_iso  = self._session_start.isoformat() if self._session_start else ""

        ui_bridge.emit_music_session(
            note_count=note_count,
            avg_cents_deviation=round(avg, 1),
            time_active_seconds=elapsed,
            last_note=last_note,
            session_started=started_iso,
        )
        log.debug(
            "[MUSIC-SKILL] Stats emitted: notes=%d  avg_cents=%.1f  elapsed=%ds",
            note_count, avg, elapsed,
        )
