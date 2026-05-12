"""
test_skill.py — Minimaler Dummy-Skill zum Testen der Auto-Discovery.
Trigger: "ping"  →  Antwort: "pong"

Dieses File kann nach dem Test gelöscht werden — es schadet nicht wenn
es liegen bleibt (wird als echter Skill registriert).
"""

from skills.base import Skill


class PingSkill(Skill):
    name         = "ping"
    triggers     = {"ping"}
    tenant_aware = False   # Test-Skill, kein Kundenbezug

    def handle(self, context: dict) -> str | None:
        return "pong  ·  Skill-System funktioniert."
