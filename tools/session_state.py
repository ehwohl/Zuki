"""
session_state.py — Session-State-Recovery für Zuki
────────────────────────────────────────────────────
Erkennt unsaubere Exits (Crash, Task-Manager-Kill) anhand der
Existenz von temp/session_state.json. Bei sauberem Exit löscht
atexit-Hook die Datei.

Verwendung:
  state = SessionState()
  atexit.register(state.clear)        # sauberer Exit
  state.save({...})                   # bei Zustandsänderung
  state.load() -> dict | None
  state.is_unclean() -> bool

Status-API (für spätere UI-Integration):
  has_unclean_state() -> bool
  last_clean_shutdown() -> datetime | None
"""

import os
import json
import threading
from datetime import datetime

from core.logger import get_logger

log = get_logger("session_state")

_STATE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp", "session_state.json")
)

# Debounce-Intervall — max. Verzögerung zwischen State-Änderung und Schreiben
_DEBOUNCE_SECS = 2.0


class SessionState:
    """
    Crash-Detection + Recovery via temp/session_state.json.
    Datei existiert = Session war aktiv = bei Abwesenheit von clear() = unsauberer Exit.
    """

    def __init__(self, path: str = _STATE_PATH):
        self._path         = os.path.abspath(path)
        self._lock         = threading.Lock()
        self._timer: threading.Timer | None = None
        self._last_clean:  datetime | None  = None

    # ── Status-API ────────────────────────────────────────────────────────────

    def has_unclean_state(self) -> bool:
        return os.path.exists(self._path)

    def is_unclean(self) -> bool:
        """Alias für has_unclean_state() — lesbarere Schreibweise."""
        return self.has_unclean_state()

    def last_clean_shutdown(self) -> datetime | None:
        """Zeitpunkt des letzten sauberen Exits (in-memory, None nach Neustart)."""
        return self._last_clean

    # ── Öffentliche API ───────────────────────────────────────────────────────

    def save(self, state: dict) -> None:
        """
        Speichert State debounced (max 2s Verzögerung).
        Verhindert exzessiven I/O bei schnellen Zustandsänderungen.
        """
        state_copy = {**state}  # Snapshot — Timer schreibt den Stand des letzten Calls
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(
                _DEBOUNCE_SECS, self._write, args=(state_copy,)
            )
            self._timer.daemon = True
            self._timer.start()

    def flush(self, state: dict) -> None:
        """
        Sofortiger Schreibzwang — Timer abbrechen, direkt schreiben.
        Für kritische Zustandsänderungen die nicht verloren gehen dürfen.
        """
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
        self._write({**state})

    def load(self) -> dict | None:
        """Liest den letzten gespeicherten State. None bei Fehler oder fehlendem File."""
        try:
            with open(self._path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def clear(self) -> None:
        """
        Löscht den State-File — signalisiert sauberen Exit.
        Bricht laufenden Debounce-Timer ab.
        Wird von atexit aufgerufen.
        """
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
        try:
            if os.path.exists(self._path):
                os.remove(self._path)
                self._last_clean = datetime.now()
                log.info("[SESSION-CLEAR] State-File gelöscht — sauberer Exit")
        except Exception as e:
            log.error(f"[SESSION-CLEAR] Löschen fehlgeschlagen: {e}")

    # ── Interner Schreiber ────────────────────────────────────────────────────

    def _write(self, state: dict) -> None:
        state["timestamp"] = datetime.now().isoformat()
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            log.info(
                f"[SESSION-SAVE] State gespeichert | "
                f"broker={state.get('broker_mode')} | "
                f"auto_save={state.get('cloud_auto_save')} | "
                f"saves={state.get('cloud_save_count')}"
            )
        except Exception as e:
            log.error(f"[SESSION-SAVE] Schreiben fehlgeschlagen: {e}")
