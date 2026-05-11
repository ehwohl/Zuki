"""
registry.py — Skill-Discovery und -Registry für Zuki
──────────────────────────────────────────────────────
Einmalig discover_skills() aufrufen → alle Skill-Subklassen
in skills/ werden importiert und nach triggers registriert.

Status-API:
  skill_count() -> int
  list_names()  -> list[str]

Log-Marker: [SKILL-DISCOVER]
"""

import importlib
import pkgutil

import skills
from skills.base import Skill
from core.logger import get_logger

log = get_logger("skill_registry")

_registry:   dict[str, Skill] = {}   # trigger (lower) -> Skill-Instanz
_discovered: bool              = False


def _all_subclasses(cls) -> list:
    """Rekursiv alle Subklassen ermitteln."""
    result = []
    for sub in cls.__subclasses__():
        result.append(sub)
        result.extend(_all_subclasses(sub))
    return result


def discover_skills() -> int:
    """
    Scannt das skills/-Paket, importiert alle Module und registriert
    Skill-Subklassen anhand ihrer triggers.
    Idempotent — mehrfacher Aufruf ist sicher.
    """
    global _discovered
    if _discovered:
        return skill_count()

    _discovered = True

    for _finder, name, _ispkg in pkgutil.walk_packages(
        path      = skills.__path__,
        prefix    = "skills.",
        onerror   = lambda n: log.warning(f"[SKILL-DISCOVER] Walk-Fehler: {n}"),
    ):
        # Infrastruktur-Module überspringen
        if name in ("skills.base", "skills.registry"):
            continue
        try:
            importlib.import_module(name)
            log.debug(f"[SKILL-DISCOVER] Importiert: {name}")
        except Exception as e:
            log.warning(f"[SKILL-DISCOVER] Import fehlgeschlagen ({name}): {e}")

    # Alle Skill-Subklassen einsammeln und registrieren
    for cls in _all_subclasses(Skill):
        if not cls.name or not cls.triggers:
            continue
        try:
            instance = cls()
            for trigger in cls.triggers:
                _registry[trigger.lower()] = instance
        except Exception as e:
            log.warning(f"[SKILL-DISCOVER] Instanziierung fehlgeschlagen ({cls.__name__}): {e}")

    unique = skill_count()
    log.info(f"[SKILL-DISCOVER] {unique} Skills registriert: {list_names()}")
    return unique


def get_skill_for(cmd: str) -> "Skill | None":
    """
    Gibt den Skill zurück dessen trigger dem ersten Wort von cmd entspricht.
    None wenn kein passender Skill gefunden.
    """
    first_word = cmd.strip().split()[0].lower() if cmd.strip() else ""
    return _registry.get(first_word)


# ── Status-API ────────────────────────────────────────────────────────────────

def skill_count() -> int:
    """Anzahl registrierter (einzigartiger) Skills."""
    return len(set(_registry.values()))


def list_names() -> list[str]:
    """Namen aller registrierten Skills."""
    return sorted({s.name for s in _registry.values()})


def get_all_descriptions() -> list[dict]:
    """Skills mit Beschreibung — für den Router-Agent.
    Gibt nur Skills zurück die eine description haben (keine Test-Stubs)."""
    seen = set()
    result = []
    for skill in _registry.values():
        if skill.name not in seen and skill.description:
            seen.add(skill.name)
            result.append({
                "name":        skill.name,
                "description": skill.description,
                "triggers":    sorted(skill.triggers),
            })
    return result
