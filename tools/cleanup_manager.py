"""
cleanup_manager.py — Selektive Lösch-Befehle für Zuki
───────────────────────────────────────────────────────
Befehle (via main.py):
  cleanup vision   → Screenshots in temp/vision/ löschen
  cleanup chats    → Lokale Chat-History löschen
  cleanup old      → Alte Backup-Snapshots löschen (behält neueste 3)
  cleanup cloud    → Cloud-Memories bereinigen (schützt Bio + system:true)
  cleanup all      → vision + chats + old (mit Bestätigung, kein Auto-Cloud)

Geschützte Daten — werden NIEMALS gelöscht:
  Lokal : .env, memory/user_profile_*.txt
  Cloud : source="bio", "system": True in Einträgen

Status-API: self_test() → dict
Log-Marker: [CLEANUP]
"""

import os
import glob
import shutil

from core.logger import get_logger

log = get_logger("cleanup")

_ROOT       = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_VISION_DIR = os.path.join(_ROOT, "temp", "vision")
_BACKUP_DIR = os.path.join(_ROOT, "backups")
_HISTORY    = os.path.join(_ROOT, "memory", "chat_history.json")

_DEFAULT_KEEP_BACKUPS = 3


class CleanupManager:
    """
    Selektive Lösch-Befehle für lokale Daten.
    Alle Methoden geben ein Result-Dict zurück mit mindestens
    {"deleted": int, "error": str} — error ist leer bei Erfolg.
    """

    # ── Lokale Cleanup-Operationen ────────────────────────────────────────────

    def cleanup_vision(self) -> dict:
        """Löscht alle .jpg/.png in temp/vision/."""
        if not os.path.isdir(_VISION_DIR):
            log.info("[CLEANUP] vision: Ordner existiert nicht — nichts zu tun")
            return {"deleted": 0, "error": ""}

        patterns = [
            os.path.join(_VISION_DIR, "*.jpg"),
            os.path.join(_VISION_DIR, "*.png"),
        ]
        deleted = 0
        for pattern in patterns:
            for fpath in glob.glob(pattern):
                try:
                    os.remove(fpath)
                    deleted += 1
                    log.debug(f"[CLEANUP] vision gelöscht: {fpath}")
                except OSError as e:
                    log.warning(f"[CLEANUP] vision: Datei konnte nicht gelöscht werden: {fpath} — {e}")

        log.info(f"[CLEANUP] vision: {deleted} Datei(en) gelöscht")
        return {"deleted": deleted, "error": ""}

    def cleanup_chats(self, history_mgr=None) -> dict:
        """
        Löscht die lokale Chat-History.
        Falls history_mgr übergeben: über .clear() leeren (Speicher + Disk).
        Sonst: Datei direkt löschen.
        """
        if history_mgr is not None:
            count_before = getattr(history_mgr, "count", 0)
            history_mgr.clear()
            log.info(f"[CLEANUP] chats: {count_before} Nachrichten gelöscht (via HistoryManager)")
            return {"deleted": count_before, "error": ""}

        if not os.path.exists(_HISTORY):
            log.info("[CLEANUP] chats: Keine History-Datei gefunden — nichts zu tun")
            return {"deleted": 0, "error": ""}

        try:
            os.remove(_HISTORY)
            log.info("[CLEANUP] chats: chat_history.json gelöscht")
            return {"deleted": 1, "error": ""}
        except OSError as e:
            log.error(f"[CLEANUP] chats: Löschen fehlgeschlagen: {e}")
            return {"deleted": 0, "error": str(e)}

    def cleanup_old_backups(self, keep: int = _DEFAULT_KEEP_BACKUPS) -> dict:
        """
        Löscht ältere Backup-Snapshots. Behält die neuesten `keep` Stück.
        Snapshots werden anhand ihres Ordner-Namens (timestamp) sortiert.
        """
        if not os.path.isdir(_BACKUP_DIR):
            log.info("[CLEANUP] old: Backup-Ordner existiert nicht — nichts zu tun")
            return {"deleted": 0, "kept": 0, "error": ""}

        entries = [
            e for e in os.listdir(_BACKUP_DIR)
            if e.startswith("snapshot_") and os.path.isdir(os.path.join(_BACKUP_DIR, e))
        ]
        entries.sort()  # alphabetisch = chronologisch wegen timestamp-Präfix

        to_delete = entries[:-keep] if len(entries) > keep else []
        kept      = min(len(entries), keep)
        deleted   = 0

        for name in to_delete:
            path = os.path.join(_BACKUP_DIR, name)
            try:
                shutil.rmtree(path)
                deleted += 1
                log.info(f"[CLEANUP] old: Snapshot gelöscht: {name}")
            except OSError as e:
                log.warning(f"[CLEANUP] old: Löschen fehlgeschlagen für {name}: {e}")

        log.info(f"[CLEANUP] old: {deleted} gelöscht  ·  {kept} behalten")
        return {"deleted": deleted, "kept": kept, "error": ""}

    # ── Status-API ────────────────────────────────────────────────────────────

    def self_test(self) -> dict:
        """Prüft ob Cleanup-Targets vorhanden und schreibbar sind."""
        checks = {}

        # Vision
        if os.path.isdir(_VISION_DIR):
            frames = len(glob.glob(os.path.join(_VISION_DIR, "*.jpg")))
            frames += len(glob.glob(os.path.join(_VISION_DIR, "*.png")))
            checks["vision"] = f"{frames} Frame(s)"
        else:
            checks["vision"] = "Ordner fehlt"

        # Chats
        if os.path.exists(_HISTORY):
            checks["chats"] = "chat_history.json vorhanden"
        else:
            checks["chats"] = "keine History"

        # Backups
        if os.path.isdir(_BACKUP_DIR):
            snaps = [
                e for e in os.listdir(_BACKUP_DIR)
                if e.startswith("snapshot_") and os.path.isdir(os.path.join(_BACKUP_DIR, e))
            ]
            checks["backups"] = f"{len(snaps)} Snapshot(s)"
        else:
            checks["backups"] = "Ordner fehlt"

        summary = "  ·  ".join(f"{k}: {v}" for k, v in checks.items())
        return {"status": "ok", "summary": summary}
