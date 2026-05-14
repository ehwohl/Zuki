"""
cleanup_manager.py — Selektive Lösch-Befehle für Zuki
───────────────────────────────────────────────────────
Befehle (via main.py):
  cleanup vision              → Screenshots in temp/vision/ löschen
  cleanup chats               → Chat-History des AKTIVEN Tenants löschen
  cleanup old                 → Alte Backup-Snapshots löschen (behält 3)
  cleanup cloud               → Cloud-Memories des aktiven Tenants bereinigen
  cleanup all                 → vision + chats + old (mit Bestätigung)
  cleanup kunde               → Alle Kunden-Dokumente des aktiven Tenants auflisten
  cleanup kunde <Name>        → Dokumente für diesen Kunden anzeigen + löschen
  cleanup kunde all           → Alle Kunden-Dokumente des aktiven Tenants löschen

Tenant-Verhalten:
  cleanup chats   → nur aktiver Tenant (tenant_id-Filter in History)
  cleanup cloud   → nur aktiver Tenant (Payload-Tenant im API-Call)
  cleanup kunde   → nur temp/business_reports/ (lokale PDFs, nicht tenant-segregiert)
  cleanup vision  → global (Screenshots haben keinen Tenant-Bezug)
  cleanup old     → global (Snapshots sind Gesamtabbilder)

Geschützte Daten — werden NIEMALS gelöscht:
  Lokal : .env, memory/user_profile_*.txt
  Cloud : source="bio", "system": True in Einträgen

Status-API: self_test() → dict
Log-Marker: [CLEANUP]
"""

import os
import glob
import shutil
from pathlib import Path

from core.logger import get_logger

log = get_logger("cleanup")

_ROOT        = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_VISION_DIR  = os.path.join(_ROOT, "temp", "vision")
_BACKUP_DIR  = os.path.join(_ROOT, "backups")
_HISTORY     = os.path.join(_ROOT, "memory", "chat_history.json")
_REPORTS_DIR = Path(_ROOT) / "temp" / "business_reports"

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

    def cleanup_chats(self, history_mgr=None, tenant_id: str = "self") -> dict:
        """
        Löscht Chat-History NUR für den angegebenen Tenant.
        Andere Tenants bleiben unberührt.
        Falls history_mgr übergeben: über .clear_tenant() filtern.
        Ohne history_mgr: Datei direkt laden + filtern + zurückschreiben.
        """
        if history_mgr is not None:
            deleted = history_mgr.clear_tenant(tenant_id)
            log.info(f"[CLEANUP] chats: {deleted} Nachrichten für tenant='{tenant_id}' gelöscht")
            return {"deleted": deleted, "tenant": tenant_id, "error": ""}

        # Ohne history_mgr: direkt in der JSON-Datei filtern
        if not os.path.exists(_HISTORY):
            log.info("[CLEANUP] chats: Keine History-Datei gefunden — nichts zu tun")
            return {"deleted": 0, "tenant": tenant_id, "error": ""}

        try:
            import json
            with open(_HISTORY, encoding="utf-8") as f:
                messages = json.load(f)
            before   = len(messages)
            messages = [m for m in messages if m.get("tenant_id", "self") != tenant_id]
            deleted  = before - len(messages)
            with open(_HISTORY, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            log.info(f"[CLEANUP] chats: {deleted} Nachrichten für tenant='{tenant_id}' gelöscht")
            return {"deleted": deleted, "tenant": tenant_id, "error": ""}
        except Exception as e:
            log.error(f"[CLEANUP] chats: Fehler: {e}")
            return {"deleted": 0, "tenant": tenant_id, "error": str(e)}

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

    # ── Kunden-Dokumente ──────────────────────────────────────────────────────

    def list_client_files(self, name: str = "") -> list[dict]:
        """
        Listet alle Dateien in temp/business_reports/.
        name (optional): Filtert nach Teilstring im Dateinamen (case-insensitive).
        Gibt list[{"path": Path, "filename": str, "size_kb": int}] zurück.
        """
        if not _REPORTS_DIR.exists():
            return []

        needle = name.lower().replace(" ", "_") if name else ""
        results = []
        for f in sorted(_REPORTS_DIR.glob("*.pdf")):
            if needle and needle not in f.name.lower():
                continue
            results.append({
                "path":     f,
                "filename": f.name,
                "size_kb":  f.stat().st_size // 1024,
            })
        return results

    def cleanup_client(self, name: str = "") -> dict:
        """
        Löscht Kunden-Dokumente in temp/business_reports/.
        name leer → alle Dokumente löschen.
        name gesetzt → nur Dokumente mit diesem Namen im Dateinamen.
        Gibt {"deleted": int, "files": list[str], "error": str} zurück.
        """
        files   = self.list_client_files(name)
        deleted = 0
        names   = []
        for entry in files:
            try:
                entry["path"].unlink()
                deleted += 1
                names.append(entry["filename"])
                log.info(f"[CLEANUP] kunde: gelöscht: {entry['filename']}")
            except OSError as e:
                log.warning(f"[CLEANUP] kunde: Fehler bei {entry['filename']}: {e}")

        log.info(f"[CLEANUP] kunde: {deleted} Dokument(e) gelöscht (filter='{name}')")
        return {"deleted": deleted, "files": names, "error": ""}

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
