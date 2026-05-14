"""
registry.py — Workspace discovery and registry for Zuki

Call discover_skills() once → all Skill subclasses in workspaces/
are imported and registered by their triggers.

Status API:
  skill_count() -> int
  list_names()  -> list[str]

Log marker: [SKILL-DISCOVER]
"""

import importlib
import pkgutil

import workspaces
from workspaces.base import Skill
from core.logger import get_logger

log = get_logger("skill_registry")

_registry:   dict[str, Skill] = {}   # trigger (lower) -> Skill instance
_discovered: bool              = False


def _all_subclasses(cls) -> list:
    """Recursively collect all subclasses."""
    result = []
    for sub in cls.__subclasses__():
        result.append(sub)
        result.extend(_all_subclasses(sub))
    return result


def discover_skills() -> int:
    """
    Scans the workspaces/ package, imports all modules and registers
    Skill subclasses by their triggers.
    Idempotent — safe to call multiple times.
    """
    global _discovered
    if _discovered:
        return skill_count()

    _discovered = True

    for _finder, name, _ispkg in pkgutil.walk_packages(
        path      = workspaces.__path__,
        prefix    = "workspaces.",
        onerror   = lambda n: log.warning(f"[SKILL-DISCOVER] Walk error: {n}"),
    ):
        # Skip infrastructure modules
        if name in ("workspaces.base", "workspaces.registry"):
            continue
        try:
            importlib.import_module(name)
            log.debug(f"[SKILL-DISCOVER] Imported: {name}")
        except Exception as e:
            log.warning(f"[SKILL-DISCOVER] Import failed ({name}): {e}")

    # Collect and register all Skill subclasses
    for cls in _all_subclasses(Skill):
        if not cls.name or not cls.triggers:
            continue
        try:
            instance = cls()
            for trigger in cls.triggers:
                _registry[trigger.lower()] = instance
        except Exception as e:
            log.warning(f"[SKILL-DISCOVER] Instantiation failed ({cls.__name__}): {e}")

    unique = skill_count()
    log.info(f"[SKILL-DISCOVER] {unique} skills registered: {list_names()}")
    return unique


def get_skill_for(cmd: str) -> "Skill | None":
    """
    Returns the skill whose trigger matches the first word of cmd.
    None if no matching skill is found.
    """
    first_word = cmd.strip().split()[0].lower() if cmd.strip() else ""
    return _registry.get(first_word)


# ── Status API ────────────────────────────────────────────────────────────────

def skill_count() -> int:
    """Number of registered (unique) skills."""
    return len(set(_registry.values()))


def list_names() -> list[str]:
    """Names of all registered skills."""
    return sorted({s.name for s in _registry.values()})


def get_all_descriptions() -> list[dict]:
    """Skills with descriptions — for the router agent.
    Returns only skills that have a description (no test stubs)."""
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
