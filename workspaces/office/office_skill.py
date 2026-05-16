"""
office_skill.py — OfficeSkill for Zuki
────────────────────────────────────────
Triggers : büro

Commands (German — user speaks German to Zuki):
  büro                    → Status: wieviele Dateien indexiert, Kategorien
  büro suche <Begriff>    → Datei-Suche im lokalen Index
  büro brief <Kunde>      → Kundendossier: alle Docs + LLM-Zusammenfassung
  büro hochladen          → Letzten Business-Report → Google Drive
  büro index              → Drive neu einlesen, SQLite-Index aktualisieren

Env vars (all optional):
  GOOGLE_CREDENTIALS_FILE     — Pfad zur OAuth2-Credentials-JSON (default: credentials.json)
  GOOGLE_DRIVE_INDEX_FOLDER   — Drive-Ordner-ID für den Index-Scope (default: gesamte Drive)
  GOOGLE_DRIVE_REPORTS_FOLDER — Drive-Ordner-ID für Report-Uploads (default: Zuki/Berichte)

Architecture:
  drive_client.py → Drive API (OAuth2, upload, folder ops)
  indexer.py      → SQLite (upsert, search, client lookup)
  LLM via APIManager: document classification + Kundendossier-Zusammenfassung

Log marker: [OFFICE-SKILL]
"""

import os
import re
from pathlib import Path

from core.logger import get_logger
from workspaces.base import Skill
from workspaces.office import drive_client, indexer
import ui_bridge

log = get_logger("office.skill")

_ROOT       = Path(__file__).resolve().parent.parent.parent
_REPORT_DIR = _ROOT / "temp" / "business_reports"

_CATEGORIES = ("Rechnung", "Vertrag", "Bericht", "Angebot", "Sonstiges")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _classify(api_mgr, filename: str, folder_path: str) -> tuple[str, str]:
    """
    Use APIManager to classify a Drive file.
    Returns (category, client_name).
    Category is one of: Rechnung, Vertrag, Bericht, Angebot, Sonstiges.
    """
    prompt = (
        f"Dateiname: {filename}\n"
        f"Ordnerpfad: {folder_path}\n\n"
        "Beantworte NUR mit einer JSON-Zeile:\n"
        '{\"kategorie\": \"<Rechnung|Vertrag|Bericht|Angebot|Sonstiges>\", \"kunde\": \"<Kundenname oder leer>\"}\n'
        "Keine Erklärung, kein Markdown."
    )
    try:
        import json as _json
        raw = api_mgr.complete(prompt, max_tokens=60).strip()
        # Strip markdown fences if model wraps anyway
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip()
        data = _json.loads(raw)
        cat  = data.get("kategorie", "Sonstiges")
        if cat not in _CATEGORIES:
            cat = "Sonstiges"
        return cat, data.get("kunde", "")
    except Exception as exc:
        log.warning("[OFFICE-SKILL] Klassifizierung fehlgeschlagen (%s): %s", filename, exc)
        return "Sonstiges", ""


def _latest_report() -> Path | None:
    """Return the most recently modified PDF in temp/business_reports/, or None."""
    if not _REPORT_DIR.exists():
        return None
    pdfs = sorted(_REPORT_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pdfs[0] if pdfs else None


def _stem_to_label(stem: str) -> str:
    """Convert a safe filename stem back to a human-readable label.
    mario_s_pizzeria → Mario S Pizzeria
    """
    return stem.replace("_", " ").title()


# ── Skill ─────────────────────────────────────────────────────────────────────

class OfficeSkill(Skill):
    name         = "office"
    triggers     = {"büro"}
    description  = (
        "Google Drive Verwaltung: Dateien indexieren, suchen, Kundendossiers abrufen "
        "und Business-Reports hochladen. Trigger: 'büro'."
    )
    tenant_aware = True

    # ── Bridge helpers ────────────────────────────────────────────────────────

    def _emit_status(self) -> None:
        """Broadcast current index state + Drive auth status to the UI."""
        try:
            indexer.init_db()
            count = indexer.file_count()
            cats  = indexer.category_counts()
            categories = [{"label": k, "count": v} for k, v in cats.items()]

            drive_status = drive_client.get_status()
            auth_ready   = bool(drive_status.get("ready"))
            creds_exist  = bool(drive_status.get("credentials_exist"))

            # Recent reports: last 5 PDFs in temp/business_reports/
            reports = []
            if _REPORT_DIR.exists():
                pdfs = sorted(
                    _REPORT_DIR.glob("*.pdf"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )[:5]
                for p in pdfs:
                    from datetime import datetime
                    ts = datetime.fromtimestamp(p.stat().st_mtime).strftime("%d.%m. %H:%M")
                    reports.append({"name": p.name, "path": str(p), "ts": ts})

            ui_bridge.emit_office_status(
                total=count,
                categories=categories,
                auth_ready=auth_ready,
                credentials_exist=creds_exist,
                recent_reports=reports,
            )
        except Exception as exc:
            log.warning("[OFFICE-SKILL] _emit_status fehlgeschlagen: %s", exc)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def handle(self, context: dict) -> str | None:
        cmd     = context.get("cmd", "").strip()
        api_mgr = context.get("api_mgr")

        parts = cmd.split(maxsplit=1)
        sub   = parts[1].strip() if len(parts) > 1 else ""

        if not sub:
            return self._status()

        if sub == "index":
            return self._rebuild_index(api_mgr)

        if sub == "hochladen":
            return self._upload_report()

        if sub.startswith("suche "):
            query = sub[6:].strip()
            return self._search(query)

        if sub.startswith("brief "):
            client = sub[6:].strip()
            return self._brief(client, api_mgr)

        if sub == "auth reset":
            return self._auth_reset()

        if sub == "auth":
            return self._auth_status()

        return (
            "Büro-Befehle:\n"
            "  büro                  → Status\n"
            "  büro auth             → OAuth-Status anzeigen\n"
            "  büro auth reset       → Token löschen, OAuth neu starten\n"
            "  büro index            → Drive neu einlesen\n"
            "  büro suche <Begriff>  → Datei suchen\n"
            "  büro brief <Kunde>    → Kundendossier\n"
            "  büro hochladen        → Letzten Report hochladen"
        )

    # ── Status ────────────────────────────────────────────────────────────────

    def _status(self) -> str:
        indexer.init_db()
        count  = indexer.file_count()
        cats   = indexer.category_counts()
        self._emit_status()

        if count == 0:
            return (
                "Büro-Index ist leer.\n"
                "Starte mit: büro index"
            )

        lines = [f"Büro-Index: {count} Dateien"]
        for cat, n in cats.items():
            lines.append(f"  {cat:<12} {n}")
        return "\n".join(lines)

    # ── Index rebuild ─────────────────────────────────────────────────────────

    def _rebuild_index(self, api_mgr) -> str:
        indexer.init_db()
        indexer.clear()

        try:
            svc = drive_client.build_service()
        except FileNotFoundError as exc:
            return f"Drive-Verbindung fehlgeschlagen:\n{exc}"
        except Exception as exc:
            log.error("[OFFICE-SKILL] Drive-Verbindung: %s", exc)
            return f"Drive-Verbindung fehlgeschlagen: {exc}"

        scope_folder = os.getenv("GOOGLE_DRIVE_INDEX_FOLDER")
        files        = drive_client.list_all_files(svc, folder_id=scope_folder or None)
        folder_map   = drive_client.get_folder_map(svc)

        indexed = 0
        for f in files:
            parent_id    = (f.get("parents") or [""])[0]
            folder_name  = folder_map.get(parent_id, "")
            category, client = _classify(api_mgr, f["name"], folder_name) if api_mgr else ("Sonstiges", "")

            indexer.upsert({
                "id":          f["id"],
                "name":        f["name"],
                "mime_type":   f.get("mimeType", ""),
                "client":      client,
                "category":    category,
                "summary":     "",
                "web_link":    f.get("webViewLink", ""),
                "modified_at": f.get("modifiedTime", ""),
            })
            indexed += 1

        log.info("[OFFICE-SKILL] Index neu aufgebaut: %d Dateien", indexed)
        self._emit_status()
        return f"Index aktualisiert: {indexed} Dateien eingelesen."

    # ── Search ────────────────────────────────────────────────────────────────

    def _search(self, query: str) -> str:
        if not query:
            return "Suchbegriff fehlt. Beispiel: büro suche Rechnung"

        indexer.init_db()
        results = indexer.search(query)

        if not results:
            return f"Keine Dateien gefunden für: {query}"

        ui_bridge.emit_office_search_results(
            query=query,
            results=[
                {
                    "name":     r["name"],
                    "category": r.get("category", ""),
                    "client":   r.get("client", ""),
                    "web_link": r.get("web_link", ""),
                }
                for r in results
            ],
        )

        lines = [f"{len(results)} Ergebnis(se) für '{query}':"]
        for r in results:
            client = f" [{r['client']}]" if r.get("client") else ""
            lines.append(f"  [{r['category']}]{client}  {r['name']}")
            if r.get("web_link"):
                lines.append(f"    → {r['web_link']}")
        return "\n".join(lines)

    # ── Client dossier ────────────────────────────────────────────────────────

    def _brief(self, client: str, api_mgr) -> str:
        if not client:
            return "Kundenname fehlt. Beispiel: büro brief Rossini"

        indexer.init_db()
        files = indexer.get_by_client(client)

        if not files:
            return f"Keine Dateien für Kunde '{client}' im Index.\nIndex aktuell? → büro index"

        file_list = "\n".join(
            f"- [{r['category']}] {r['name']} ({r.get('modified_at', '')[:10]})"
            for r in files
        )

        if not api_mgr:
            return f"Dateien für '{client}':\n{file_list}"

        prompt = (
            f"Erstelle eine kurze Zusammenfassung der folgenden Dokumente für den Kunden '{client}'.\n"
            f"Schreibe auf Deutsch, maximal 5 Sätze. Betone was vorhanden ist und was fehlen könnte.\n\n"
            f"Dokumente:\n{file_list}"
        )
        try:
            summary = api_mgr.complete(prompt, max_tokens=200).strip()
        except Exception as exc:
            log.warning("[OFFICE-SKILL] Brief-Zusammenfassung fehlgeschlagen: %s", exc)
            summary = "(Zusammenfassung nicht verfügbar)"

        return f"Dossier: {client} ({len(files)} Dokumente)\n\n{summary}\n\nDateien:\n{file_list}"

    # ── Auth status / reset ───────────────────────────────────────────────────

    def _auth_status(self) -> str:
        s = drive_client.get_status()
        lines = ["Google Drive — OAuth Status"]
        lines.append(f"  Credentials-Datei : {s['credentials_file']}")
        lines.append(f"  Datei vorhanden   : {'ja' if s['credentials_exist'] else 'NEIN — fehlt!'}")
        lines.append(f"  Token gecacht     : {'ja' if s['token_cached'] else 'nein'}")

        if s["token_cached"]:
            if s.get("error"):
                lines.append(f"  Token-Fehler      : {s['error']}")
            else:
                lines.append(f"  Token gültig      : {'ja' if s['token_valid'] else 'nein'}")
                lines.append(f"  Token abgelaufen  : {'ja' if s['token_expired'] else 'nein'}")
                lines.append(f"  Refresh-Token     : {'vorhanden' if s['has_refresh_token'] else 'fehlt!'}")
                lines.append(f"  Ablauf            : {s['expiry'] or 'unbekannt'}")
                lines.append(f"  Bereit            : {'ja' if s['ready'] else 'NEIN'}")

        if not s["credentials_exist"]:
            lines.append(
                "\nCredentials fehlen!\n"
                "Download: Google Cloud Console → APIs & Dienste → Zugangsdaten → OAuth 2.0-Client-IDs\n"
                f"Speichern als: {s['credentials_file']}"
            )
        elif not s["token_cached"]:
            lines.append("\nKein Token vorhanden — starte: büro auth reset")
        elif not s["ready"]:
            lines.append("\nToken ungültig — starte: büro auth reset")

        return "\n".join(lines)

    def _auth_reset(self) -> str:
        drive_client.reset_token()
        log.info("[OFFICE-SKILL] Token zurückgesetzt via büro auth reset")
        try:
            drive_client.build_service()
            return "OAuth-Flow abgeschlossen. Drive verbunden."
        except FileNotFoundError as exc:
            return f"Credentials-Datei fehlt:\n{exc}"
        except Exception as exc:
            log.error("[OFFICE-SKILL] OAuth-Reset fehlgeschlagen: %s", exc)
            return f"OAuth-Flow fehlgeschlagen: {exc}"

    # ── Upload last report ────────────────────────────────────────────────────

    def _upload_report(self) -> str:
        report = _latest_report()
        if not report:
            return "Kein Report gefunden in temp/business_reports/."

        try:
            svc = drive_client.build_service()
        except FileNotFoundError as exc:
            return f"Drive-Verbindung fehlgeschlagen:\n{exc}"
        except Exception as exc:
            log.error("[OFFICE-SKILL] Drive-Verbindung: %s", exc)
            return f"Drive-Verbindung fehlgeschlagen: {exc}"

        # Determine target folder
        target_folder_id = os.getenv("GOOGLE_DRIVE_REPORTS_FOLDER")
        if not target_folder_id:
            zuki_id   = drive_client.find_or_create_folder(svc, "Zuki")
            target_folder_id = drive_client.find_or_create_folder(svc, "Berichte", parent_id=zuki_id)

        # Extract client label from stem for log output
        stem   = report.stem.replace("_workflow", "")
        client = _stem_to_label(stem)

        link = drive_client.upload_file(svc, report, folder_id=target_folder_id)
        log.info("[OFFICE-SKILL] Report hochgeladen: %s", report.name)
        self._emit_status()

        result = f"Report hochgeladen: {report.name}"
        if client:
            result += f"\nKunde: {client}"
        if link:
            result += f"\nLink: {link}"
        return result
