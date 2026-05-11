"""
business_manager.py — Operativer Abteilungsleiter für Zuki
────────────────────────────────────────────────────────────
Verwaltet:
  • Kundendatenbank  (data/customers.json)
  • Aufgabenliste    (data/task_list.json)
  • CRM-Sync         (HTML → customers.json)
  • Mail-Entwürfe    (via EmailInterface)

Befehle (in main.py):
  business status           → Übersicht
  add customer [Name]       → Kunden anlegen
  draft mail [Kunde]        → Antwort-Entwurf

CRM HTML-Sync:
  sync_crm(html_path) parst <table>-Tags aus einer HTML-Datei.
  Spalten-Mapping: Name / E-Mail / Status / Datum (configurable).
  Ohne BeautifulSoup: Regex-Fallback.

  LIVE UPGRADE: BeautifulSoup für robusteres HTML-Parsing:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for row in soup.select("table tr")[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
"""

import json
import os
import re
import uuid
from datetime import date, datetime

from core.logger import get_logger
from skills.business.email_interface import EmailInterface

log = get_logger("business")

_BUSINESS = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.abspath(os.path.join(_BUSINESS, "..", ".."))
DATA_DIR  = os.path.join(_BUSINESS, "data")

CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
TASKS_FILE     = os.path.join(DATA_DIR, "task_list.json")

# Lokale CRM-HTML-Datei (Standard: web/crm/index.html)
_CRM_FILE     = os.path.join(_ROOT, "web", "crm", "index.html")
CRM_HTML_PATH = os.getenv("CRM_HTML_PATH", "") or _CRM_FILE

# Spalten-Namen die im HTML-CRM erwartet werden (case-insensitive)
_CRM_COL_NAME   = {"name", "kunde", "customer", "firma", "company"}
_CRM_COL_EMAIL  = {"email", "e-mail", "mail"}
_CRM_COL_STATUS = {"status", "phase", "typ"}
_CRM_COL_DATE   = {"datum", "date", "last contact", "letzter kontakt"}


class BusinessManager:
    """Zentrale Klasse für alle Business-Operationen."""

    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._customers: list[dict] = []
        self._tasks:     list[dict] = []
        self._crm_synced: bool       = False
        self._email = EmailInterface()
        self._load()

    # ──────────────────────────────────────────────────────────────────────────
    # Public — Status
    # ──────────────────────────────────────────────────────────────────────────

    def get_status(self, simulation: bool = True) -> dict:
        """
        Gibt ein Status-Dict zurück:
          open_tasks       : Anzahl offener Aufgaben
          high_prio        : Anzahl hoher Priorität
          total_customers  : Gesamtkunden
          leads            : Nur Leads
          pending_mails    : Ausstehende Mails (SIM oder LIVE)
          crm_synced       : Bool
          last_contacts    : Liste der letzten 3 Kundenkontakte
        """
        open_tasks  = [t for t in self._tasks if t.get("status") == "offen"]
        high_prio   = [t for t in open_tasks  if t.get("priority") == "hoch"]
        leads       = [c for c in self._customers if c.get("status") == "Lead"]

        # Letzte Kontakte: sortiert nach last_contact, neueste zuerst
        sorted_customers = sorted(
            self._customers,
            key=lambda c: c.get("last_contact", ""),
            reverse=True,
        )

        return {
            "open_tasks":      len(open_tasks),
            "high_prio":       len(high_prio),
            "total_customers": len(self._customers),
            "leads":           len(leads),
            "pending_mails":   self._email.count_pending(simulation),
            "crm_synced":      self._crm_synced,
            "last_contacts":   [c["name"] for c in sorted_customers[:3]],
            "open_task_list":  [(t["task"], t["priority"]) for t in open_tasks[:5]],
        }

    def build_status_sim(self) -> str:
        """SIM-Ausgabe für 'business status'."""
        s = self.get_status(simulation=True)
        tasks_str  = "\n".join(
            f"    [{p.upper()}] {t}" for t, p in s["open_task_list"]
        ) or "    (keine offenen Tasks)"
        contacts_str = ", ".join(s["last_contacts"]) or "—"

        return (
            f"[BIZ] Synchronisiere mit CRM-HTML... "
            f"Status: {s['leads']} Leads gefunden. "
            f"{s['pending_mails']} Mails ausstehend. "
            f"Soll ich die Entwürfe vorbereiten?\n\n"
            f"── ÜBERSICHT ──────────────────────────────────\n"
            f"  Kunden gesamt :  {s['total_customers']}  "
            f"({s['leads']} Leads)\n"
            f"  Offene Tasks  :  {s['open_tasks']}  "
            f"({s['high_prio']} mit hoher Priorität)\n"
            f"  Mails aussteh.:  {s['pending_mails']}\n"
            f"  CRM-Sync      :  {'✓ aktuell' if s['crm_synced'] else '⚠ noch nicht synchronisiert'}\n"
            f"  Letzte Kontak.:  {contacts_str}\n\n"
            f"── OFFENE TASKS ───────────────────────────────\n"
            f"{tasks_str}\n"
            f"───────────────────────────────────────────────\n"
            f"Befehle: 'add customer [Name]'  ·  'draft mail [Kunde]'"
        )

    def build_status_live_prompt(self) -> str:
        """LLM-Prompt für Live-Statusanalyse."""
        s      = self.get_status(simulation=False)
        tasks  = "\n".join(f"- [{p}] {t}" for t, p in s["open_task_list"])
        return (
            f"Du bist Zukis Business-Assistent. Gib eine kurze, operative Lagebesprechung:\n\n"
            f"Kunden: {s['total_customers']} total, {s['leads']} Leads\n"
            f"Offene Aufgaben: {s['open_tasks']} ({s['high_prio']} dringend)\n"
            f"Ausstehende Mails: {s['pending_mails']}\n"
            f"Letzte Kontakte: {', '.join(s['last_contacts'])}\n"
            f"Aufgaben:\n{tasks}\n\n"
            f"Was sind die 3 wichtigsten nächsten Schritte? Kurz und direkt."
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Public — Kunden
    # ──────────────────────────────────────────────────────────────────────────

    def add_customer(self, name: str) -> dict:
        """Legt neuen Kunden an. Gibt Kunden-Dict zurück."""
        # Duplikat-Check
        existing = self._find_customer(name)
        if existing:
            log.info(f"Kunde bereits vorhanden: {name}")
            return existing

        customer = {
            "id":           str(uuid.uuid4())[:8],
            "name":         name.strip(),
            "status":       "Lead",
            "email":        "",
            "last_contact": date.today().isoformat(),
            "notes":        "",
            "added":        date.today().isoformat(),
        }
        self._customers.append(customer)
        self._save_customers()
        log.info(f"Neuer Kunde angelegt: {name}")
        return customer

    def get_customer(self, name: str) -> dict | None:
        return self._find_customer(name)

    def format_customer_card(self, customer: dict) -> str:
        return (
            f"── Kundenkarte ────────────────────────────────\n"
            f"  Name          :  {customer.get('name', '—')}\n"
            f"  Status        :  {customer.get('status', '—')}\n"
            f"  E-Mail        :  {customer.get('email', '—') or '(keine)'}\n"
            f"  Letzter Kont. :  {customer.get('last_contact', '—')}\n"
            f"  Notizen       :  {customer.get('notes', '—') or '(keine)'}\n"
            f"  Seit          :  {customer.get('added', '—')}\n"
            f"───────────────────────────────────────────────"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Public — Mail-Entwurf
    # ──────────────────────────────────────────────────────────────────────────

    def draft_mail(self, customer_name: str, simulation: bool = True) -> str:
        """Erstellt einen Mail-Entwurf für den Kunden."""
        customer = self._find_customer(customer_name)
        if not customer:
            return (
                f"[BIZ] Kein Eintrag für '{customer_name}' gefunden.\n"
                f"Tipp: 'add customer {customer_name}' um ihn anzulegen."
            )
        mails = self._email.get_mail_for_customer(customer_name, simulation)
        mail  = mails[0] if mails else None
        return self._email.build_draft(customer, mail, simulation)

    # ──────────────────────────────────────────────────────────────────────────
    # Public — CRM öffnen
    # ──────────────────────────────────────────────────────────────────────────

    def open_crm(self) -> tuple[str, str]:
        """
        Öffnet web/crm/index.html im Standard-Browser.

        Rückgabe: (pfad: str, fehler: str)
          Fehler ist leer bei Erfolg.
        """
        import webbrowser

        if not os.path.exists(_CRM_FILE):
            err = (
                f"CRM-Datei nicht gefunden: {_CRM_FILE}\n"
                f"Bitte ablegen unter: web/crm/index.html"
            )
            log.warning(err)
            return "", err

        # file:// URL — Backslashes auf Windows zu Forward-Slashes
        url = "file:///" + _CRM_FILE.replace("\\", "/")
        webbrowser.open(url)
        log.info(f"CRM geöffnet: {url}")
        return _CRM_FILE, ""

    # ──────────────────────────────────────────────────────────────────────────
    # Public — CRM-Sync
    # ──────────────────────────────────────────────────────────────────────────

    def sync_crm(self, html_path: str = "") -> dict:
        """
        Scannt eine HTML-CRM-Datei und spiegelt die Daten in customers.json.

        Rückgabe: {"imported": int, "updated": int, "skipped": int, "error": str}

        Parsing-Strategie:
          1. Versuche BeautifulSoup (robuster, aber optionale Dep.)
          2. Fallback: Regex für einfache <tr>/<td>-Tabellen

        LIVE UPGRADE: BeautifulSoup für komplexe HTML-Strukturen:
          from bs4 import BeautifulSoup
          soup = BeautifulSoup(html, "html.parser")
          header = [th.get_text(strip=True).lower()
                    for th in soup.select("table tr:first-child th, table tr:first-child td")]
          for row in soup.select("table tr")[1:]:
              cells = [td.get_text(strip=True) for td in row.find_all("td")]
              record = dict(zip(header, cells))
              ...
        """
        path = html_path or CRM_HTML_PATH
        result = {"imported": 0, "updated": 0, "skipped": 0, "error": ""}

        if not path:
            result["error"] = "Kein CRM_HTML_PATH in .env gesetzt"
            log.warning(result["error"])
            return result

        if not os.path.exists(path):
            result["error"] = f"CRM-Datei nicht gefunden: {path}"
            log.warning(result["error"])
            return result

        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                html = f.read()
        except OSError as e:
            result["error"] = str(e)
            return result

        rows = self._parse_html_table(html)
        if not rows:
            result["error"] = "Keine Tabellendaten gefunden"
            return result

        for row in rows:
            name = self._pick_col(row, _CRM_COL_NAME)
            if not name or len(name) < 2:
                result["skipped"] += 1
                continue

            existing = self._find_customer(name)
            if existing:
                # Update vorhandener Felder
                existing["email"]        = self._pick_col(row, _CRM_COL_EMAIL)  or existing["email"]
                existing["status"]       = self._pick_col(row, _CRM_COL_STATUS) or existing["status"]
                existing["last_contact"] = self._pick_col(row, _CRM_COL_DATE)   or existing["last_contact"]
                result["updated"] += 1
            else:
                self._customers.append({
                    "id":           str(uuid.uuid4())[:8],
                    "name":         name,
                    "status":       self._pick_col(row, _CRM_COL_STATUS) or "Lead",
                    "email":        self._pick_col(row, _CRM_COL_EMAIL)  or "",
                    "last_contact": self._pick_col(row, _CRM_COL_DATE)   or date.today().isoformat(),
                    "notes":        "",
                    "added":        date.today().isoformat(),
                })
                result["imported"] += 1

        self._save_customers()
        self._crm_synced = True
        log.info(f"CRM-Sync: {result}")
        return result

    # ──────────────────────────────────────────────────────────────────────────
    # Internal — HTML-Parsing
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_html_table(html: str) -> list[dict]:
        """
        Regex-basierter <table>-Parser.
        Gibt list[dict] zurück, Keys = Spaltenköpfe (lowercase).
        """
        # Alle Zeilen extrahieren
        row_re  = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
        cell_re = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.IGNORECASE | re.DOTALL)
        tag_re  = re.compile(r"<[^>]+>")

        def clean(s: str) -> str:
            return tag_re.sub("", s).strip()

        rows = row_re.findall(html)
        if not rows:
            return []

        # Erste Zeile = Header
        headers = [clean(c).lower() for c in cell_re.findall(rows[0])]
        if not headers:
            return []

        result = []
        for row_html in rows[1:]:
            cells = [clean(c) for c in cell_re.findall(row_html)]
            if not any(cells):
                continue
            # Auffüllen/kürzen auf Header-Länge
            while len(cells) < len(headers):
                cells.append("")
            result.append(dict(zip(headers, cells[:len(headers)])))

        return result

    @staticmethod
    def _pick_col(row: dict, col_names: set[str]) -> str:
        """Findet den ersten Wert aus einem Row-Dict der zu einem der Spaltennamen passt."""
        for key, val in row.items():
            if key.strip().lower() in col_names:
                return val.strip()
        return ""

    # ──────────────────────────────────────────────────────────────────────────
    # Internal — Persistenz
    # ──────────────────────────────────────────────────────────────────────────

    def _find_customer(self, name: str) -> dict | None:
        name_lower = name.strip().lower()
        for c in self._customers:
            if c.get("name", "").lower() == name_lower:
                return c
        # Fuzzy: Teilstring-Match
        for c in self._customers:
            if name_lower in c.get("name", "").lower():
                return c
        return None

    def _load(self) -> None:
        self._customers = self._load_json(CUSTOMERS_FILE, default=[])
        self._tasks     = self._load_json(TASKS_FILE,     default=[])
        log.info(
            f"Business geladen: {len(self._customers)} Kunden, "
            f"{len([t for t in self._tasks if t.get('status')=='offen'])} offene Tasks"
        )

    def _save_customers(self) -> None:
        self._save_json(CUSTOMERS_FILE, self._customers)

    def _save_tasks(self) -> None:
        self._save_json(TASKS_FILE, self._tasks)

    @staticmethod
    def _load_json(path: str, default):
        if not os.path.exists(path):
            return default
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"JSON-Ladefehler {path}: {e}")
            return default

    @staticmethod
    def _save_json(path: str, data) -> None:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            log.error(f"JSON-Speicherfehler {path}: {e}")
