"""
ui_factory.py — UIRenderer-Factory für Zuki
─────────────────────────────────────────────
Gibt eine Singleton-Instanz des konfigurierten Renderers zurück.

Konfiguration via ENV:
  ZUKI_UI=terminal   →  TerminalRenderer  (Standard)
  ZUKI_UI=web        →  (noch nicht implementiert — Stub folgt)

Verwendung in main.py:
  from core.ui_factory import get_renderer
  ui = get_renderer()

Status-API:
  renderer.kind()  →  "terminal" | "web" | …

Log-Marker: [UI-INIT]
"""

import os
from core.logger import get_logger
from core.ui_renderer import UIRenderer

log = get_logger("ui_factory")

# ── Renderer-Registry ─────────────────────────────────────────────────────────

def _build_registry() -> dict:
    """Lazy-gebaut damit Imports nur bei Bedarf gezogen werden."""
    from core.ui import TerminalRenderer
    return {
        "terminal": TerminalRenderer,
    }


# ── Singleton-State ───────────────────────────────────────────────────────────

_instance: UIRenderer | None = None


def get_renderer() -> UIRenderer:
    """
    Gibt den konfigurierten Renderer zurück (Singleton).
    Beim ersten Aufruf wird die Instanz erzeugt und geloggt.
    """
    global _instance
    if _instance is not None:
        return _instance

    key = os.environ.get("ZUKI_UI", "terminal").strip().lower()
    registry = _build_registry()

    cls = registry.get(key)
    if cls is None:
        log.warning(
            f"[UI-INIT] Unbekannter Renderer '{key}' — Fallback auf 'terminal'."
        )
        cls = registry["terminal"]
        key = "terminal"

    _instance = cls()
    log.info(f"[UI-INIT] Renderer aktiv: '{_instance.kind()}'")
    return _instance


def reset_renderer() -> None:
    """Setzt den Singleton zurück (nur für Tests)."""
    global _instance
    _instance = None
