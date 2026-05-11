"""
router_agent.py — Zuki Router-Agent für Multi-Skill-Orchestrierung
────────────────────────────────────────────────────────────────────
Entscheidet anhand des Nutzer-Inputs welche Skills aufgerufen werden.

Ablauf:
  1. get_all_descriptions() liefert Skills mit Beschreibung
  2. route() baut einen Klassifikations-Prompt und fragt den LLM
  3. Antwort wird als JSON geparst → Liste von Skill-Namen
  4. In SIM-Modus: immer [] (kein LLM-Call, kein Token-Verbrauch)

Decision-Log:
  Jede Routing-Entscheidung wird in temp/router_decisions.jsonl
  gespeichert für späteres Tuning.

Status-API:
  last_decision()   -> dict | None
  decision_count()  -> int
  self_test()       -> dict

Log-Marker: [ROUTER]
"""

import os
import re
import json
import datetime

from core.logger import get_logger

log = get_logger("router_agent")

_ROOT     = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_LOG_PATH = os.path.join(_ROOT, "temp", "router_decisions.jsonl")

# Skill-Liste im Prompt auf maximal diese Anzahl begrenzen (Token-Sparmaßnahme)
_MAX_SKILLS_IN_PROMPT = 10

# JSON-Extraktor — tolerant gegenüber LLM-Text rund um das Objekt
_JSON_RE = re.compile(r'\{[^{}]*"skills"[^{}]*\}', re.DOTALL)


class RouterAgent:
    """
    LLM-basierter Skill-Router.
    Wird einmalig in main.py instanziiert und bei jeder nicht-direkten
    Eingabe aufgerufen.
    """

    def __init__(self, api_mgr):
        self._api_mgr = api_mgr
        self._count   = 0
        self._last:  dict | None = None
        log.info("[ROUTER] RouterAgent initialisiert")

    # ── Öffentliche API ───────────────────────────────────────────────────────

    def route(self, user_input: str, skills_info: list[dict]) -> list[str]:
        """
        Entscheidet welche Skills für user_input aufgerufen werden sollen.

        Returns:
          list[str]  — Skill-Namen (leer = kein Skill, Fallback auf LLM-Chat)

        skills_info: [{"name": str, "description": str, "triggers": list[str]}]
        """
        if self._api_mgr.simulation:
            return []   # SIM: kein Token-Verbrauch durch Router

        if not skills_info:
            return []

        # Nur Skills mit Beschreibung in Prompt — begrenzt auf _MAX_SKILLS_IN_PROMPT
        usable = skills_info[:_MAX_SKILLS_IN_PROMPT]

        prompt = self._build_prompt(user_input, usable)

        try:
            raw = self._api_mgr.chat(prompt, max_tokens=80)
            chosen = self._parse_response(raw, {s["name"] for s in usable})
        except Exception as e:
            log.warning(f"[ROUTER] LLM-Fehler: {e}")
            chosen = []

        self._count += 1
        self._last = {
            "ts":     datetime.datetime.now().isoformat(),
            "input":  user_input[:120],
            "skills": chosen,
        }
        self._write_log(user_input, chosen)

        if chosen:
            log.info(f"[ROUTER] {chosen}  ←  \"{user_input[:60]}\"")
        else:
            log.info(f"[ROUTER] Kein Skill gewählt  ←  \"{user_input[:60]}\"")

        return chosen

    def last_decision(self) -> "dict | None":
        return self._last

    def decision_count(self) -> int:
        return self._count

    def self_test(self) -> dict:
        return {
            "enabled":        not self._api_mgr.simulation,
            "decision_count": self._count,
            "log_path":       _LOG_PATH,
            "log_exists":     os.path.exists(_LOG_PATH),
            "last_decision":  self._last,
        }

    # ── Interne Helfer ────────────────────────────────────────────────────────

    def _build_prompt(self, user_input: str, skills_info: list[dict]) -> str:
        lines = []
        for s in skills_info:
            triggers = ", ".join(s["triggers"])
            lines.append(f'- {s["name"]}: {s["description"]}  (Trigger: {triggers})')
        skills_block = "\n".join(lines)

        return (
            "Du bist der Zuki Router-Agent. Deine einzige Aufgabe: "
            "entscheide welche Skills für die Nutzeranfrage aufgerufen werden sollen.\n\n"
            f"Verfügbare Skills:\n{skills_block}\n\n"
            f'Nutzeranfrage: "{user_input}"\n\n'
            'Antworte NUR mit JSON: {"skills": ["skillname1"]} '
            'oder {"skills": []} wenn kein Skill passt. '
            "Nenne nur wirklich relevante Skills."
        )

    def _parse_response(self, raw: str, valid_names: set) -> list[str]:
        match = _JSON_RE.search(raw)
        if not match:
            return []
        try:
            data   = json.loads(match.group())
            chosen = data.get("skills", [])
            return [n for n in chosen if isinstance(n, str) and n in valid_names]
        except (json.JSONDecodeError, TypeError):
            return []

    def _write_log(self, user_input: str, skills: list[str]) -> None:
        entry = {
            "ts":     datetime.datetime.now().isoformat(),
            "input":  user_input[:120],
            "skills": skills,
        }
        try:
            os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            log.warning(f"[ROUTER] Log-Schreiben fehlgeschlagen: {e}")
