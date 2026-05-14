"""
test_skill.py — Minimal dummy skill for testing auto-discovery.
Trigger: "ping"  →  Response: "pong"

This file can be deleted after testing — it causes no harm if left in place
(it will be registered as a real skill).
"""

from workspaces.base import Skill


class PingSkill(Skill):
    name         = "ping"
    triggers     = {"ping"}
    tenant_aware = False   # test skill, no customer context

    def handle(self, context: dict) -> str | None:
        return "pong  ·  Skill-System funktioniert."
