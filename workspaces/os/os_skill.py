"""
os_skill.py — OsSkill for Zuki
────────────────────────────────
Triggers : os

Commands:
  os   → emit TTS/STT/platform status to the React UI

Architecture:
  Reads tts + stt from the skill context (populated by main.py).
  Emits os_status via ui_bridge so the OS workspace panels update.

Log marker: [OS-SKILL]
"""

import sys

import ui_bridge
from core.logger import get_logger
from workspaces.base import Skill

log = get_logger("os.skill")


class OsSkill(Skill):
    name         = "os"
    triggers     = {"os"}
    description  = (
        "Reports live system status: TTS engine, STT mode, and platform. "
        "Emits os_status to the React UI."
    )
    tenant_aware = False

    def handle(self, context: dict) -> str | None:
        tts = context.get("tts")
        stt = context.get("stt")

        tts_status: dict = tts.get_status() if tts else {"voice": "—", "ready": False}
        stt_status: dict = {
            "mode":  getattr(stt, "mode_label", "—"),
            "ready": stt is not None,
        }

        ui_bridge.emit_os_status(
            tts=tts_status,
            stt=stt_status,
            platform=sys.platform,
        )
        log.info("[OS-SKILL] Status emitted (platform=%s)", sys.platform)

        return "\n".join([
            "System-Status",
            f"  Platform : {sys.platform}",
            f"  TTS      : {tts_status.get('voice', '—')}  "
            f"({'bereit' if tts_status.get('ready') else 'nicht bereit'})",
            f"  STT      : {stt_status['mode']}  "
            f"({'bereit' if stt_status['ready'] else 'nicht bereit'})",
        ])
