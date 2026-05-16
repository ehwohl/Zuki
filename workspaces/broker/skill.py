"""
skill.py — BrokerSkill for Zuki
─────────────────────────────────
Triggers : broker

Commands:
  broker   → activate broker mode, emit exchange map to React UI

Architecture:
  Emits broker_map_nodes via ui_bridge so WorldMap panel updates.
  Ticker (broker_tick) and news (news_item) arrive from n8n when active.

Log marker: [BROKER-SKILL]
"""

import ui_bridge
from core.logger import get_logger
from workspaces.base import Skill

log = get_logger("broker.skill")

# Static exchange nodes — superseded by n8n live data once active
_EXCHANGE_NODES: list[dict] = [
    {"id": "nyse",  "coords": [-74.0,  40.7], "label": "NYSE",  "active": True},
    {"id": "lse",   "coords": [ -0.1,  51.5], "label": "LSE",   "active": True},
    {"id": "tse",   "coords": [139.7,  35.7], "label": "TSE",   "active": False},
    {"id": "hkex",  "coords": [114.1,  22.3], "label": "HKEX",  "active": True},
    {"id": "fwb",   "coords": [  8.7,  50.1], "label": "FWB",   "active": False},
]


class BrokerSkill(Skill):
    name         = "broker"
    triggers     = {"broker"}
    description  = (
        "Activates broker mode. Emits live exchange map nodes to the React UI "
        "and stands ready to receive ticker and news data from n8n."
    )
    tenant_aware = False

    def handle(self, context: dict) -> str | None:
        ui_bridge.emit_broker_map_nodes(_EXCHANGE_NODES)
        log.info("[BROKER-SKILL] Map nodes emitted (%d exchanges)", len(_EXCHANGE_NODES))
        return "Broker-Modus aktiv."
