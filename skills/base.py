"""
base.py — Abstrakte Basis für alle Zuki-Skills
───────────────────────────────────────────────
Ein Skill ist eine Drop-in-Klasse: Datei in skills/ ablegen,
Klasse erbt von Skill, name + triggers setzen — fertig.
Die Registry findet sie automatisch via discover_skills().

Context-Dict (wird von main.py befüllt):
  user_input : str           — rohe Nutzereingabe
  cmd        : str           — user_input.strip().lower()
  api_mgr    : APIManager    — Multi-Provider-LLM
  llm        : LLMManager    — Chat-Loop-LLM
  profile    : UserProfile
"""

from abc import ABC, abstractmethod


class Skill(ABC):
    """Abstrakte Basis für alle Skills."""

    name: str          = ""        # Eindeutiger Skill-Name (Pflicht)
    triggers: set[str] = set()     # Befehlswörter die diesen Skill auslösen
    description: str   = ""        # Kurzbeschreibung für den Router-Agent

    # ── Tenant-Guard ──────────────────────────────────────────────────────────
    # True  (Standard): Zuki warnt bevor Skill im 'self'-Tenant läuft.
    # False: Kein Guard — für interne/Test-Skills ohne Kundenbezug (z. B. PingSkill).
    #
    # KONVENTION FÜR NEUE SKILLS:
    #   - Jeder neue Skill der potenziell Kunden-Daten verarbeitet → tenant_aware = True (Default)
    #   - Reine Utility-Skills ohne Kundenbezug → tenant_aware = False explizit setzen
    #   - Im Zweifel: True lassen — der Guard kostet nichts wenn man im richtigen Tenant ist
    tenant_aware: bool = True

    @abstractmethod
    def handle(self, context: dict) -> str | None:
        """
        Verarbeitet den Befehl und gibt eine Antwort zurück.
        None → Skill hat nichts zu sagen (Main-Loop geht weiter).
        """
        ...
