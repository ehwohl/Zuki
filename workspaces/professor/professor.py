"""
professor.py — The Professor skill for Zuki
────────────────────────────────────────────
Trigger : explain [topic]  (case-insensitive)

Flow:
  SIM  → structured placeholder response, level-dependent
  LIVE → LLM-powered explanation with Wikipedia/source prompt

Level adaptation (from user_profile):
  ""          → neutral, medium level
  "Anfänger"  → simple language, analogies, no jargon
  "Fortgeschrittener" → solid explanation + first technical terms
  "Profi" / "Experte" → full terminology, no spoon-feeding

LIVE UPGRADE:
  build_live_prompt() already generates a structured prompt.
  Optionally query Wikipedia before the LLM call for a factual basis:
    import wikipedia; wikipedia.set_lang("de")
    summary = wikipedia.summary(topic, sentences=5)
    → embed as "Kontext: {summary}" in the prompt
"""

import re
from core.logger import get_logger
from workspaces.base import Skill

log = get_logger("professor")

# ── Trigger ────────────────────────────────────────────────────────────────────

_EXPLAIN_RE = re.compile(r"^explain\s+(.+)", re.IGNORECASE)


def is_explain_trigger(text: str) -> bool:
    return bool(_EXPLAIN_RE.match(text.strip()))


def get_topic(text: str) -> str:
    """Extracts the topic from 'explain [topic]'. Returns '' if no match."""
    m = _EXPLAIN_RE.match(text.strip())
    return m.group(1).strip() if m else ""


# ── Level mapping ──────────────────────────────────────────────────────────────

_LEVEL_BEGINNER    = {"anfänger", "neuling", "beginner", "einsteiger", "keine ahnung"}
_LEVEL_ADVANCED    = {"fortgeschrittener", "fortgeschritten", "intermediate"}
_LEVEL_EXPERT      = {"profi", "experte", "expert", "fachmann", "erfahren", "spezialist"}


def normalize_level(raw: str) -> str:
    """
    Normalises the stored level string to a tier:
      "beginner" | "advanced" | "expert" | "unknown"
    """
    r = raw.strip().lower()
    if r in _LEVEL_BEGINNER:
        return "beginner"
    if r in _LEVEL_ADVANCED:
        return "advanced"
    if r in _LEVEL_EXPERT:
        return "expert"
    return "unknown"


# ── SIM response ───────────────────────────────────────────────────────────────

_SIM_LEVEL_NOTE = {
    "beginner": (
        "Da Sie Anfänger sind, erkläre ich es mit einfachen Worten und Alltagsanalogien "
        "— ganz ohne Fachbegriffe."
    ),
    "advanced": (
        "Da Sie bereits Vorkenntnisse haben, nutze ich solide Fachbegriffe "
        "und setze Grundlagen voraus."
    ),
    "expert": (
        "Da Sie Experte sind, gehe ich direkt in die Tiefe: "
        "volle Fachterminologie, keine vereinfachenden Analogien."
    ),
    "unknown": (
        "Ich passe das Niveau an, sobald ich mehr über Ihren Hintergrund weiß. "
        "Tipp: Sagen Sie 'Ich bin Anfänger' oder 'Ich bin Profi'."
    ),
}

_SIM_STRUCTURE = {
    "beginner": [
        "📖 Einfache Definition",
        "🔍 Alltagsanalogie",
        "🧩 Schritt-für-Schritt-Erklärung (ohne Fachbegriffe)",
        "✅ Zusammenfassung in einem Satz",
    ],
    "advanced": [
        "📖 Definition (mit Kernbegriffen)",
        "🔬 Mechanismus / Funktionsweise",
        "📊 Wichtige Konzepte & Zusammenhänge",
        "🔗 Weiterführende Themen",
    ],
    "expert": [
        "📖 Formale Definition & Herleitung",
        "⚙️  Technische Details & Edge Cases",
        "📐 Mathematische / formale Grundlagen (falls relevant)",
        "🔗 Aktuelle Forschung & Literaturhinweise",
    ],
    "unknown": [
        "📖 Definition",
        "🔍 Erklärung",
        "🧩 Beispiel",
        "✅ Zusammenfassung",
    ],
}


def build_sim_response(topic: str, level_raw: str) -> str:
    level  = normalize_level(level_raw)
    note   = _SIM_LEVEL_NOTE[level]
    struct = _SIM_STRUCTURE[level]

    sections = "\n".join(f"  {s}" for s in struct)

    return (
        f"[PROF] Ich bereite eine detaillierte Vorlesung zu '{topic}' vor.\n"
        f"{note}\n\n"
        f"Gliederung der Erklärung:\n{sections}\n\n"
        f"(In der Live-Version würde ich jetzt Wikipedia und Fachquellen analysieren\n"
        f" und Ihnen eine vollständige, quellenbelegte Erklärung liefern.)"
    )


# ── LIVE prompt ────────────────────────────────────────────────────────────────

_LIVE_LEVEL_INSTRUCTION = {
    "beginner": (
        "Erkläre es einem absoluten Anfänger: einfache Sprache, Alltagsanalogien, "
        "keine Fachbegriffe ohne Erklärung. Baue auf Vorwissen von null auf."
    ),
    "advanced": (
        "Der User hat Grundkenntnisse. Verwende Fachbegriffe, erkläre sie aber kurz. "
        "Gehe tiefer als eine Wikipedia-Zusammenfassung."
    ),
    "expert": (
        "Der User ist Experte. Verwende volle Fachterminologie. "
        "Kein Spoon-Feeding, keine Kindergarten-Analogien. "
        "Gehe auf technische Details und Grenzfälle ein."
    ),
    "unknown": (
        "Niveau unbekannt — erkläre auf mittlerem Niveau: "
        "klar und präzise, wenige Fachbegriffe mit kurzer Definition."
    ),
}


def build_live_prompt(topic: str, level_raw: str, profile_summary: str = "") -> str:  # noqa: E302
    """
    Builds a structured LLM prompt for a live explanation.

    LIVE UPGRADE:
      Optionally query Wikipedia before this prompt call:
        import wikipedia; wikipedia.set_lang("de")
        context = wikipedia.summary(topic, sentences=5)
      → embed as 'Kontext: {context}' in the prompt
    """
    level       = normalize_level(level_raw)
    instruction = _LIVE_LEVEL_INSTRUCTION[level]
    profile_note = f"\nNutzerprofil: {profile_summary}" if profile_summary else ""

    return (
        f"Du bist Der Professor — Zukis Erklärungs-Skill. "
        f"Erkläre das folgende Thema umfassend und strukturiert.{profile_note}\n\n"
        f"Thema: {topic}\n\n"
        f"Niveau-Anweisung: {instruction}\n\n"
        f"Struktur:\n"
        f"1. Definition / Was ist {topic}?\n"
        f"2. Wie funktioniert es? (Mechanismus / Kernkonzept)\n"
        f"3. Praxisbeispiel oder Anwendungsfall\n"
        f"4. Häufige Missverständnisse oder Stolperfallen\n"
        f"5. Weiterführende Themen (2-3 Stichworte)\n\n"
        f"Antworte auf Deutsch. Sei präzise, nicht geschwätzig."
    )


# ── Skill class ────────────────────────────────────────────────────────────────

class ProfessorSkill(Skill):
    """The Professor — explains topics level-adaptively via 'explain [topic]'."""

    name         = "professor"
    triggers     = {"explain", "erklaer", "erklaere", "erkläre"}
    tenant_aware = False   # explains general knowledge, no customer data
    description = "Explains topics, concepts and terms in a structured, level-adaptive way"

    def handle(self, context: dict) -> str | None:
        user_input = context.get("user_input", "")
        if not is_explain_trigger(user_input):
            return None
        topic = get_topic(user_input)
        if not topic:
            return None

        api_mgr = context.get("api_mgr")
        profile = context.get("profile")
        llm     = context.get("llm")

        level   = profile.level if profile else ""
        summary = profile.get_summary() if profile else ""

        if not api_mgr or api_mgr.simulation:
            log.info(f"[SKILL-INVOKE] professor | SIM | topic={topic}")
            return build_sim_response(topic, level)

        prompt = build_live_prompt(topic, level, summary)
        log.info(f"[SKILL-INVOKE] professor | LIVE | topic={topic}")
        return api_mgr.chat(
            prompt     = prompt,
            system     = llm.system_prompt if llm else "",
            max_tokens = 2048,
        )
