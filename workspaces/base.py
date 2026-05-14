"""
base.py — Abstract base class for all Zuki skills

A skill is a drop-in class: place a file in workspaces/,
inherit from Skill, set name + triggers — done.
The registry finds it automatically via discover_skills().

Context dict (populated by main.py):
  user_input : str           — raw user input
  cmd        : str           — user_input.strip().lower()
  api_mgr    : APIManager    — multi-provider LLM
  llm        : LLMManager    — chat loop LLM
  profile    : UserProfile
"""

from abc import ABC, abstractmethod


class Skill(ABC):
    """Abstract base for all skills."""

    name: str          = ""        # Unique skill name (required)
    triggers: set[str] = set()     # Command words that activate this skill
    description: str   = ""        # Short description for the router agent

    # ── Tenant guard ──────────────────────────────────────────────────────────
    # True  (default): Zuki warns before the skill runs in the 'self' tenant.
    # False: No guard — for internal/test skills with no customer context (e.g. PingSkill).
    #
    # CONVENTION FOR NEW SKILLS:
    #   - Any new skill that may process customer data → tenant_aware = True (default)
    #   - Pure utility skills with no customer context → tenant_aware = False explicitly
    #   - When in doubt: leave True — the guard costs nothing if you're in the right tenant
    tenant_aware: bool = True

    @abstractmethod
    def handle(self, context: dict) -> str | None:
        """
        Processes the command and returns a response.
        None → skill has nothing to say (main loop continues).
        """
        ...
