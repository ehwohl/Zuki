"""
knowledge/loader.py — Branchen-Wissens-Datenbank
──────────────────────────────────────────────────
Lädt YAML-Dateien aus knowledge/ und stellt typisierte Abfragen bereit.

Jede YAML-Datei repräsentiert eine Branche (z. B. gastro.yaml, friseur.yaml).
Erwartetes YAML-Schema:
  branch: str              — Branchen-ID (z. B. "gastro")
  label: str               — Anzeigename (z. B. "Gastronomie")
  sources: list[str]       — Datenquellen für Analyse
  weaknesses: list[dict]   — Typische Schwachstellen
    - id, title, description, severity (hoch/mittel/niedrig)
  kpis: list[dict]         — Wichtige Kennzahlen
    - id, label, description, target
  tools: list[dict]        — Tool-Empfehlungen
    - name, category, description, url (optional), cost
  glossary: dict[str, str] — Branchen-Begriffe → Erklärung

Verwendung:
  from knowledge.loader import get_knowledge_base
  kb = get_knowledge_base()
  branch = kb.get_branch("gastro")
  weaknesses = kb.get_weaknesses("gastro")

Status-API:
  get_status()  → dict
  self_test()   → dict  (für system_test: Subsystem "knowledge")

Log-Marker: [KNOWLEDGE-LOAD], [KNOWLEDGE-MISS]
"""

import os
import yaml

from core.logger import get_logger

log = get_logger("knowledge")

_KNOWLEDGE_DIR = os.path.dirname(os.path.abspath(__file__))


class KnowledgeBase:
    """
    Lädt alle YAML-Dateien aus knowledge/ beim ersten Zugriff (lazy).
    Branches werden gecacht — kein wiederholtes Disk-IO.
    """

    def __init__(self, knowledge_dir: str = _KNOWLEDGE_DIR):
        self._dir    = knowledge_dir
        self._cache: dict[str, dict] = {}
        self._loaded = False

    # ── Lade-Logik ─────────────────────────────────────────────────────────────

    def _load_all(self) -> None:
        if self._loaded:
            return
        for fname in os.listdir(self._dir):
            if not fname.endswith(".yaml") and not fname.endswith(".yml"):
                continue
            path = os.path.join(self._dir, fname)
            try:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                branch_id = data.get("branch")
                if branch_id:
                    self._cache[branch_id] = data
                    log.info(f"[KNOWLEDGE-LOAD] {branch_id} ({fname})")
            except Exception as e:
                log.warning(f"[KNOWLEDGE-LOAD] Fehler beim Laden von {fname}: {e}")
        self._loaded = True

    # ── Öffentliche Abfragen ───────────────────────────────────────────────────

    def list_branches(self) -> list[str]:
        self._load_all()
        return list(self._cache.keys())

    def get_branch(self, branch: str) -> dict | None:
        self._load_all()
        data = self._cache.get(branch)
        if data is None:
            log.warning(f"[KNOWLEDGE-MISS] Unbekannte Branche: {branch}")
        return data

    def get_weaknesses(self, branch: str) -> list[dict]:
        data = self.get_branch(branch)
        return data.get("weaknesses", []) if data else []

    def get_kpis(self, branch: str) -> list[dict]:
        data = self.get_branch(branch)
        return data.get("kpis", []) if data else []

    def get_tools(self, branch: str) -> list[dict]:
        data = self.get_branch(branch)
        return data.get("tools", []) if data else []

    def get_sources(self, branch: str) -> list[str]:
        data = self.get_branch(branch)
        return data.get("sources", []) if data else []

    def get_glossary(self, branch: str) -> dict[str, str]:
        data = self.get_branch(branch)
        return data.get("glossary", {}) if data else {}

    def get_label(self, branch: str) -> str:
        data = self.get_branch(branch)
        return data.get("label", branch) if data else branch

    # ── Status-API ─────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        self._load_all()
        return {
            "available":  True,
            "branches":   self.list_branches(),
            "count":      len(self._cache),
            "directory":  self._dir,
        }

    def self_test(self) -> dict:
        try:
            self._load_all()
            count = len(self._cache)
            if count == 0:
                return {
                    "status":   "warn",
                    "summary":  "Keine Branchen-Dateien gefunden",
                    "fix_hint": f"YAML-Datei in {self._dir} ablegen (Schema: branch, label, weaknesses, kpis, tools, glossary)",
                }
            branches = ", ".join(self.list_branches())
            # Minimum validation: first branch must have weaknesses + kpis
            first = self.list_branches()[0]
            w_count = len(self.get_weaknesses(first))
            k_count = len(self.get_kpis(first))
            return {
                "status":  "ok",
                "summary": f"{count} Branche(n): {branches}  ·  {first}: {w_count} Schwachstellen, {k_count} KPIs",
            }
        except Exception as e:
            return {
                "status":   "fail",
                "summary":  f"Fehler: {e}",
                "fix_hint": "Logs prüfen",
            }


# ── Modul-Level Singleton ──────────────────────────────────────────────────────

_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


def get_status() -> dict:
    return get_knowledge_base().get_status()


def self_test() -> dict:
    return get_knowledge_base().self_test()
