"""
user_profile.py — Bio-Memory für Zuki
───────────────────────────────────────
Speichert dauerhaft, was der User über sich preisgibt.
Datei: memory/user_profile.txt  (plain text, human-readable)

Extraktion:
  Regex-basiert — kein API-Call nötig.
  LIVE UPGRADE: _extract_llm() via LLM für komplexere Sätze ersetzen.

Format user_profile.txt:
  Name: Klaus
  Aktien: NVDA, Apple, BTC
  Interessen: KI, Krypto
  Zuletzt aktualisiert: 2026-05-06
"""

import os
import re
import json
import threading
from datetime import date, datetime

from core.logger import get_logger

log = get_logger("profile")

PROFILE_FILE = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_profile.txt")
)

# ── Regex-Muster ───────────────────────────────────────────────────────────────

_NAME_PATTERNS = [
    r"ich (?:bin|hei[sß]e)\s+([A-ZÄÖÜ][a-zäöüß]{1,30})",
    r"mein name ist\s+([A-ZÄÖÜ][a-zäöüß]{1,30})",
    r"nenn(?:en sie|e) mich\s+([A-ZÄÖÜ][a-zäöüß]{1,30})",
]

_STOCK_PATTERNS = [
    r"ich (?:mag|handle|kaufe|halte|besitze|trade)\s+([A-ZÄÖÜ][A-Za-z0-9]{1,10})",
    r"ich investiere(?:re)? in\s+([A-ZÄÖÜ][A-Za-z0-9]{1,10})",
    r"meine (?:aktie|position|watchlist) (?:ist|sind|enthält)\s+([A-ZÄÖÜ][A-Za-z0-9]{1,10})",
]

_INTEREST_PATTERNS = [
    r"ich interessiere mich f[uü]r\s+(.+?)(?:\.|,|$)",
    r"mein hobby ist\s+(.+?)(?:\.|,|$)",
    r"ich besch[äa]ftige mich mit\s+(.+?)(?:\.|,|$)",
]

_LEVEL_PATTERNS = [
    # Anfänger
    (r"ich bin (?:ein\s+)?(?:absoluter\s+)?anf[äa]nger", "Anfänger"),
    (r"ich bin neuling",                                  "Anfänger"),
    (r"ich wei[sß] (?:noch\s+)?(?:gar\s+)?nichts? dar[uü]ber", "Anfänger"),
    (r"erkl[äa]r(?:e|) es mir wie (?:einem\s+)?kind",   "Anfänger"),
    # Fortgeschrittener
    (r"ich bin fortgeschritten",                          "Fortgeschrittener"),
    (r"ich habe grundkenntnisse",                         "Fortgeschrittener"),
    (r"ich kenne (?:mich\s+)?(?:ein bisschen\s+)?(?:damit\s+)?aus", "Fortgeschrittener"),
    # Profi / Experte
    (r"ich bin (?:ein\s+)?(?:echter\s+)?profi",           "Profi"),
    (r"ich bin (?:ein\s+)?experte",                       "Experte"),
    (r"ich bin fachmann",                                 "Experte"),
    (r"ich kenne mich (?:sehr\s+)?(?:gut\s+)?(?:damit\s+)?aus", "Profi"),
    (r"ich arbeite (?:beruflich\s+)?(?:seit\s+\S+\s+)?(?:mit|als|in)",  "Profi"),
]


class UserProfile:
    """
    Lädt, aktualisiert und persistiert das User-Profil.
    Optional: Cloud-Sync via set_cloud() — async, non-blocking.
    """

    def __init__(self, path: str = PROFILE_FILE):
        self._path       = path
        self._cloud      = None                   # gesetzt via set_cloud()
        self._last_sync: datetime | None = None   # Status-API
        self._data: dict[str, str | list[str]] = {
            "name":       "",
            "level":      "",   # "Anfänger" | "Fortgeschrittener" | "Profi" | "Experte"
            "stocks":     [],
            "interests":  [],
        }
        self._load()

    # ── Cloud-Integration ─────────────────────────────────────────────────────

    def set_cloud(self, cloud) -> None:
        """Setzt CloudMemory-Instanz für asynchronen Bio-Sync."""
        self._cloud = cloud

    def last_cloud_sync(self) -> datetime | None:
        """Zeitpunkt des letzten erfolgreichen Cloud-Syncs (Status-API)."""
        return self._last_sync

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def extract_and_update(self, text: str) -> list[str]:
        """
        Scanne *text* nach Profil-Infos. Persistiert bei Fund.
        Gibt Liste zurück was gelernt wurde (für UI-Feedback), leer wenn nichts Neues.

        LIVE UPGRADE: diesen Body mit einem LLM-Call ersetzen für
        freie Texterkennung ohne starre Regex-Muster.
        """
        learned: list[str] = []

        # Name
        for pattern in _NAME_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                name = m.group(1).capitalize()
                if name != self._data.get("name"):
                    self._data["name"] = name
                    learned.append(f"Name: {name}")
                break

        # Aktien
        for pattern in _STOCK_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                stock = m.group(1).upper()
                stocks = self._data.setdefault("stocks", [])
                if stock not in stocks:
                    stocks.append(stock)
                    learned.append(f"Aktie: {stock}")

        # Interessen
        for pattern in _INTEREST_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                interest = m.group(1).strip().rstrip(".,").capitalize()
                if len(interest) < 3 or len(interest) > 60:
                    continue
                interests = self._data.setdefault("interests", [])
                if interest not in interests:
                    interests.append(interest)
                    learned.append(f"Interesse: {interest}")

        # Wissensniveau (für Professor-Skill)
        for pattern, level_label in _LEVEL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                if self._data.get("level") != level_label:
                    self._data["level"] = level_label
                    learned.append(f"Niveau: {level_label}")
                break

        if learned:
            self._save()
            log.info(f"Profil aktualisiert: {learned}")
            self._sync_to_cloud()

        return learned

    @property
    def level(self) -> str:
        """Rohes Level-Label aus dem Profil ('Anfänger', 'Profi', …) oder ''."""
        return self._data.get("level", "")

    def get_summary(self) -> str:
        """
        Kurze Zusammenfassung für LLM-Kontext-Injection.
        Leer wenn noch kein Profil vorhanden.
        """
        parts: list[str] = []
        if self._data.get("name"):
            parts.append(f"Name: {self._data['name']}")
        if self._data.get("level"):
            parts.append(f"Niveau: {self._data['level']}")
        stocks = self._data.get("stocks", [])
        if stocks:
            parts.append(f"Aktien: {', '.join(stocks)}")
        interests = self._data.get("interests", [])
        if interests:
            parts.append(f"Interessen: {', '.join(interests)}")
        return "  |  ".join(parts)

    def get_profile_text(self) -> str:
        """Vollständiger Profiltext — für SIM-Anzeige und Debug."""
        if not os.path.exists(self._path):
            return "(kein Profil gespeichert)"
        try:
            with open(self._path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            return "(Profildatei nicht lesbar)"

    @property
    def is_empty(self) -> bool:
        return not any([
            self._data.get("name"),
            self._data.get("level"),
            self._data.get("stocks"),
            self._data.get("interests"),
        ])

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _sync_to_cloud(self) -> None:
        """Speichert aktuelles Profil async in Cloud (source='bio'). Non-blocking."""
        if not self._cloud or not self._cloud.enabled:
            return
        payload = json.dumps(self._data, ensure_ascii=False)
        # fire-and-forget via auto-Pfad in cloud.save()
        self._cloud.save(payload, source="bio")
        self._last_sync = datetime.now()
        log.info(f"[BIO-SAVE] Profil-Snapshot zur Cloud gesendet | {self.get_summary()}")

    def _load(self) -> None:
        if not os.path.exists(self._path):
            log.debug("user_profile.txt nicht vorhanden — starte leer")
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or ":" not in line:
                        continue
                    key, _, value = line.partition(":")
                    key   = key.strip().lower()
                    value = value.strip()
                    if key == "name":
                        self._data["name"] = value
                    elif key == "niveau":
                        self._data["level"] = value
                    elif key == "aktien":
                        self._data["stocks"] = [
                            s.strip() for s in value.split(",") if s.strip()
                        ]
                    elif key == "interessen":
                        self._data["interests"] = [
                            s.strip() for s in value.split(",") if s.strip()
                        ]
            log.info(f"Profil geladen: {self.get_summary() or 'leer'}")
        except OSError as e:
            log.warning(f"Profil konnte nicht geladen werden: {e}")

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            stocks    = ", ".join(self._data.get("stocks", []))
            interests = ", ".join(self._data.get("interests", []))
            with open(self._path, "w", encoding="utf-8") as f:
                f.write(
                    f"Name: {self._data.get('name', '')}\n"
                    f"Niveau: {self._data.get('level', '')}\n"
                    f"Aktien: {stocks}\n"
                    f"Interessen: {interests}\n"
                    f"Zuletzt aktualisiert: {date.today().isoformat()}\n"
                )
        except OSError as e:
            log.error(f"Profil konnte nicht gespeichert werden: {e}")
