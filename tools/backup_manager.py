"""
backup_manager.py — Projekt-Snapshot für Zuki
───────────────────────────────────────────────
Befehl: system backup

Erstellt backups/snapshot_YYYY-MM-DD_HHMMSS/ und kopiert alle relevanten
Projektdateien dorthin — mit erhaltener Ordnerstruktur.

Eingeschlossene Typen : .py  .txt  .md  .json  .env  .bat
Ausgeschlossene Ordner: __pycache__  .git  backups  temp  venv  .venv

Auto-Backup:
  AutoBackup(interval=21600).start()  →  alle 6h, behält 7 Snapshots
  Status-API: last_snapshot_time(), snapshot_count(), next_scheduled()
"""

import os
import atexit
import shutil
import threading
from datetime import datetime, timedelta

from core.logger import get_logger

log = get_logger("backup")

ROOT       = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BACKUP_DIR = os.path.join(ROOT, "backups")

INCLUDE_EXT   = {".py", ".txt", ".md", ".json", ".bat"}
INCLUDE_NAMES = {".env"}
EXCLUDE_DIRS  = {
    "__pycache__", ".git", "backups", "temp",
    "venv", ".venv", "node_modules", ".mypy_cache",
}


# ── Snapshot-Erstellung ───────────────────────────────────────────────────────

def create_snapshot() -> dict:
    """
    Kopiert alle relevanten Projektdateien in einen Snapshot-Ordner.

    Rückgabe:
      {
        "path"    : str   — absoluter Pfad zum Snapshot-Ordner
        "files"   : int   — Anzahl kopierter Dateien
        "size_kb" : int   — Gesamtgröße in KB
        "error"   : str   — leer bei Erfolg
      }
    """
    timestamp    = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snapshot_dir = os.path.join(BACKUP_DIR, f"snapshot_{timestamp}")

    result = {"path": snapshot_dir, "files": 0, "size_kb": 0, "error": ""}

    try:
        os.makedirs(snapshot_dir, exist_ok=True)
    except OSError as e:
        result["error"] = f"Backup-Ordner konnte nicht erstellt werden: {e}"
        log.error(result["error"])
        return result

    for dirpath, dirnames, filenames in os.walk(ROOT):
        # Ausgeschlossene Ordner in-place entfernen → os.walk überspringt sie
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in INCLUDE_EXT and filename not in INCLUDE_NAMES:
                continue

            src = os.path.join(dirpath, filename)
            rel = os.path.relpath(src, ROOT)
            dst = os.path.join(snapshot_dir, rel)

            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                result["files"]   += 1
                result["size_kb"] += os.path.getsize(src) // 1024
                log.debug(f"Backup: {rel}")
            except OSError as e:
                log.warning(f"Übersprungen ({rel}): {e}")

    log.info(
        f"Snapshot erstellt: {snapshot_dir}  "
        f"({result['files']} Dateien, {result['size_kb']} KB)"
    )
    return result


# ── Snapshot-Verwaltung ───────────────────────────────────────────────────────

def list_snapshots() -> list[str]:
    """Gibt alle vorhandenen Snapshot-Ordner zurück (neueste zuerst)."""
    if not os.path.isdir(BACKUP_DIR):
        return []
    snaps = sorted(
        [d for d in os.listdir(BACKUP_DIR) if d.startswith("snapshot_")],
        reverse=True,
    )
    return snaps


def format_snapshot_list() -> str:
    """Formatierte Übersicht aller Snapshots für die Konsole."""
    snaps = list_snapshots()
    if not snaps:
        return "(keine Snapshots vorhanden)"
    lines = [f"  {i+1:>2}.  {s}" for i, s in enumerate(snaps[:10])]
    return "\n".join(lines)


def _prune_old_snapshots(keep: int = 7) -> None:
    """Löscht Snapshots jenseits der keep-Grenze (älteste zuerst)."""
    snaps     = list_snapshots()   # neueste zuerst
    to_delete = snaps[keep:]       # alles hinter den ersten `keep` Einträgen
    for name in to_delete:
        path = os.path.join(BACKUP_DIR, name)
        try:
            shutil.rmtree(path)
            log.info(f"[AUTO-BACKUP] Alter Snapshot gelöscht: {name}")
        except OSError as e:
            log.warning(f"[AUTO-BACKUP] Löschen fehlgeschlagen ({name}): {e}")


# ── Auto-Backup-Thread ────────────────────────────────────────────────────────

class AutoBackup:
    """
    Hintergrund-Thread: erstellt alle `interval` Sekunden einen Snapshot
    und hält nur die letzten MAX_SNAPSHOTS Einträge.

    Threading-Pattern identisch zum Scraper in core/main.py:
      stop_event = threading.Event()
      thread = threading.Thread(target=_loop, args=(stop_event,), daemon=True)
      atexit.register(stop_event.set)

    Status-API (für spätere UI-Integration):
      last_snapshot_time() -> datetime | None
      snapshot_count()     -> int
      next_scheduled()     -> datetime
    """

    DEFAULT_INTERVAL = 6 * 3600   # 6 Stunden
    MAX_SNAPSHOTS    = 7

    def __init__(self, interval: int = DEFAULT_INTERVAL):
        self._interval    = interval
        self._stop        = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_snap:  datetime | None = None
        self._started_at: datetime | None = None

    # ── Start / Stop ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Startet den Hintergrund-Thread. Idempotent."""
        if self._thread and self._thread.is_alive():
            return
        self._started_at = datetime.now()
        self._thread = threading.Thread(
            target = self._loop,
            args   = (self._stop,),
            daemon = True,
            name   = "auto-backup-bg",
        )
        self._thread.start()
        atexit.register(self._stop.set)
        log.info(
            f"[AUTO-BACKUP] Thread gestartet | "
            f"Intervall: {self._interval}s | Max-Snapshots: {self.MAX_SNAPSHOTS}"
        )

    def stop(self) -> None:
        self._stop.set()

    # ── Status-API ────────────────────────────────────────────────────────────

    def last_snapshot_time(self) -> datetime | None:
        """Zeitpunkt des letzten automatischen Snapshots."""
        return self._last_snap

    def snapshot_count(self) -> int:
        """Anzahl aktuell vorhandener Snapshots."""
        return len(list_snapshots())

    def next_scheduled(self) -> datetime:
        """Geplanter Zeitpunkt des nächsten Snapshots."""
        base = self._last_snap or self._started_at or datetime.now()
        return base + timedelta(seconds=self._interval)

    # ── Thread-Loop ───────────────────────────────────────────────────────────

    def _loop(self, stop_event: threading.Event) -> None:
        log.info(f"[AUTO-BACKUP] Erster Snapshot in {self._interval}s")
        while not stop_event.wait(timeout=self._interval):
            self._run_snapshot()
        log.info("[AUTO-BACKUP] Thread beendet")

    def _run_snapshot(self) -> None:
        log.info("[AUTO-BACKUP] Erstelle automatischen Snapshot...")
        try:
            snap = create_snapshot()
            if snap["error"]:
                log.error(f"[AUTO-BACKUP] Snapshot fehlgeschlagen: {snap['error']}")
                return
            self._last_snap = datetime.now()
            log.info(
                f"[AUTO-BACKUP] Snapshot erstellt | "
                f"{snap['files']} Dateien | {snap['size_kb']} KB"
            )
            _prune_old_snapshots(keep=self.MAX_SNAPSHOTS)
        except Exception as e:
            log.error(f"[AUTO-BACKUP] Unerwarteter Fehler: {e}")
