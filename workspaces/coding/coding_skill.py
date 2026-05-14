"""
coding_skill.py — CodingSkill for Zuki
────────────────────────────────────────
Triggers : code, coding, skript, script

Commands:
  code                          → help + active buffer status
  code status                   → show all buffers with content
  code <lang>                   → set active language + show buffer
  code <lang> show              → show buffer
  code <lang> run               → execute code (sandbox, 10s timeout)
  code <lang> edit              → interactive multiline editor
  code <lang> add <line>        → append line to buffer
  code <lang> set <code>        → replace buffer with single-line code
  code <lang> clear             → clear buffer
  code run                      → run active buffer
  code show                     → show active buffer

Languages: python, js, ts, bash, go, pine
Pine Script: not locally executable → hint "Paste into TradingView"
TypeScript:  requires ts-node       → hint if not installed

Log marker: [CODING-SKILL]
"""

from core.logger import get_logger
from workspaces.base import Skill
from workspaces.coding.buffer import LANGUAGES, NO_RUN_LANGS, LANG_LABEL, CodeBuffer

log = get_logger("coding.skill")

_CANCEL_CMDS = {"abort", "exit", "abbrechen", "stop", ":q"}
_END_CMDS    = {"end", "done", "fertig", "run", ":wq"}

_PINE_HINT = (
    "Pine Script kann nicht lokal ausgeführt werden.\n"
    "→ Code in TradingView-Editor einfügen (pine.tradingview.com)"
)
_TS_HINT = (
    "TypeScript-Ausführung erfordert ts-node.\n"
    "→ Installieren: npm install -g ts-node typescript"
)


class CodingSkill(Skill):
    name         = "coding"
    triggers     = {"code", "coding", "skript", "script"}
    description  = (
        "Multi-language code scratchpad: Python, JS, TS, Bash, Go, Pine Script. "
        "Write, edit and execute code directly in a sandbox."
    )
    tenant_aware = False   # no customer context, pure utility

    def __init__(self) -> None:
        self._buf = CodeBuffer()

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def handle(self, context: dict) -> str | None:
        cmd = context.get("cmd", "").strip()

        # Normalise trigger aliases to "code ..."
        for alias in ("coding ", "skript ", "script "):
            if cmd.startswith(alias):
                cmd = "code " + cmd[len(alias):]
                break
        if cmd in ("coding", "skript", "script"):
            cmd = "code"

        parts = cmd.split(None, 3)   # ["code", lang?, subcommand?, rest?]

        if len(parts) == 1:
            return self._help()

        second = parts[1]

        # ── code status ───────────────────────────────────────────────────────
        if second == "status":
            return self._status()

        # ── code run / code show (active language) ────────────────────────────
        if second == "run":
            return self._run_lang(self._buf.active(), context)
        if second == "show":
            return self._show(self._buf.active())

        # ── code <lang> ... ───────────────────────────────────────────────────
        lang = _resolve_lang(second)
        if lang is None:
            return f"Unbekannte Sprache: '{second}'\nVerfügbar: {', '.join(sorted(LANGUAGES))}"

        sub  = parts[2] if len(parts) > 2 else ""
        rest = parts[3] if len(parts) > 3 else ""

        if not sub:
            # "code python" → activate language + show buffer
            self._buf.set_active(lang)
            return self._show(lang, header=f"Aktive Sprache: {LANG_LABEL[lang]}")

        if sub == "show":
            return self._show(lang)
        if sub == "run":
            return self._run_lang(lang, context)
        if sub == "clear":
            return self._clear(lang)
        if sub == "edit":
            return self._edit(lang, context)
        if sub == "add":
            if not rest:
                return "Verwendung: code <lang> add <zeile>"
            self._buf.append_line(lang, rest)
            log.info(f"[CODING-SKILL] add → {lang}")
            return f"Zeile hinzugefügt ({LANG_LABEL[lang]}).\n{self._show(lang)}"
        if sub == "set":
            if not rest:
                return "Verwendung: code <lang> set <code>"
            self._buf.set(lang, rest)
            log.info(f"[CODING-SKILL] set → {lang}")
            return f"Buffer gesetzt ({LANG_LABEL[lang]}).\n{self._show(lang)}"

        # Unknown subcommand — interpret rest as implicit "add"
        # e.g.: "code python print('hello')" → appends line
        line = sub + (" " + rest if rest else "")
        self._buf.append_line(lang, line)
        self._buf.set_active(lang)
        log.info(f"[CODING-SKILL] implicit add → {lang}")
        return f"Zeile hinzugefügt ({LANG_LABEL[lang]}).\n{self._show(lang)}"

    # ── Display ───────────────────────────────────────────────────────────────

    def _show(self, lang: str, header: str = "") -> str:
        code = self._buf.get(lang)
        label = LANG_LABEL.get(lang, lang)
        lines = []
        if header:
            lines.append(header)
        lines.append(f"── {label} Buffer {'─' * max(0, 40 - len(label))} ")
        if code.strip():
            lines.append(code)
        else:
            lines.append("(leer)")
        lines.append(f"── Ende {'─' * 43}")
        lines.append("code run   → ausführen  |  code edit   → bearbeiten  |  code clear   → leeren")
        return "\n".join(lines)

    # ── Status ────────────────────────────────────────────────────────────────

    def _status(self) -> str:
        filled = self._buf.has_content()
        active = self._buf.active()
        lines  = [f"Aktive Sprache: {LANG_LABEL.get(active, active)}"]
        if filled:
            lines.append(f"\nBuffer mit Inhalt: {len(filled)}")
            for lang in filled:
                code  = self._buf.get(lang)
                chars = len(code)
                lcount = code.count("\n") + 1
                marker = " ◄ aktiv" if lang == active else ""
                lines.append(f"  {LANG_LABEL.get(lang, lang):<14}  {lcount} Zeilen  ({chars} Zeichen){marker}")
        else:
            lines.append("Alle Buffer leer.")
        lines.append(f"\nVerfügbare Sprachen: {', '.join(sorted(LANGUAGES))}")
        return "\n".join(lines)

    # ── Clear ─────────────────────────────────────────────────────────────────

    def _clear(self, lang: str) -> str:
        self._buf.clear(lang)
        log.info(f"[CODING-SKILL] clear → {lang}")
        return f"{LANG_LABEL.get(lang, lang)}-Buffer geleert."

    # ── Interactive editor ────────────────────────────────────────────────────

    def _edit(self, lang: str, context: dict) -> str:
        ui    = _get_ui()
        label = LANG_LABEL.get(lang, lang)

        existing = self._buf.get(lang)
        if existing.strip():
            ui.speak_zuki(
                f"Bestehender {label}-Buffer wird überschrieben.\n"
                f"'behalten' → Zeilen anhängen statt ersetzen\n"
                f"Enter      → ersetzen"
            )
            choice = ui.user_prompt().strip().lower()
            append_mode = choice in {"behalten", "b", "append"}
        else:
            append_mode = False

        ui.speak_zuki(
            f"{label}-Editor  —  Zeile für Zeile eingeben.\n"
            f"'END' oder 'fertig'   → abschließen + Buffer speichern\n"
            f"'run'                 → abschließen + direkt ausführen\n"
            f"'abbrechen'           → verwerfen"
        )

        lines       = []
        run_after   = False
        line_number = 1

        while True:
            try:
                user_line = ui.user_prompt(f"  {line_number:>3}  ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if user_line.lower() in _CANCEL_CMDS:
                log.info(f"[CODING-SKILL] edit cancelled → {lang}")
                return "Editor abgebrochen — Buffer unverändert."

            if user_line.lower() in _END_CMDS:
                run_after = user_line.lower() == "run"
                break

            lines.append(user_line)
            line_number += 1

        if not lines:
            return "Keine Eingabe — Buffer unverändert."

        new_code = "\n".join(lines)
        if append_mode:
            self._buf.append_line(lang, new_code)
        else:
            self._buf.set(lang, new_code)

        self._buf.set_active(lang)
        log.info(f"[CODING-SKILL] edit saved → {lang}  ({len(lines)} lines)")

        if run_after:
            return self._show(lang) + "\n\n" + self._run_lang(lang, context)
        return self._show(lang)

    # ── Execute ───────────────────────────────────────────────────────────────

    def _run_lang(self, lang: str, context: dict) -> str:
        code = self._buf.get(lang)
        if not code.strip():
            return f"Buffer leer. Zuerst Code eingeben:\n  code {lang} edit"

        label = LANG_LABEL.get(lang, lang)

        # Pine Script → never locally executable
        if lang == "pine":
            lines = [_PINE_HINT, "", f"── {label} Code ─────────────────────────────────", code]
            return "\n".join(lines)

        # TypeScript → check for ts-node
        if lang == "ts":
            from workspaces.coding.sandbox import is_available
            ok, hint = is_available("ts")
            if not ok:
                lines = [_TS_HINT]
                if hint:
                    lines.append(hint)
                lines += ["", f"── {label} Code ─────────────────────────────────", code]
                return "\n".join(lines)

        ui = _get_ui()
        ui.system_msg(f"[Coding] Ausführen: {label} ...")

        from workspaces.coding.sandbox import run_code
        result = run_code(lang, code)

        log.info(
            f"[CODING-SKILL] run → {lang}  "
            f"rc={result.returncode}  timeout={result.timed_out}"
        )

        status = "✓" if result.success else "✗"
        header = f"── {label} [{status}] {'─' * max(0, 38 - len(label))} "
        return f"{header}\n{result.format_output()}"

    # ── Help ──────────────────────────────────────────────────────────────────

    def _help(self) -> str:
        active = self._buf.active()
        filled = self._buf.has_content()
        status_line = (
            f"Aktiv: {LANG_LABEL.get(active, active)}"
            + (f"  |  Buffer mit Inhalt: {', '.join(LANG_LABEL.get(l, l) for l in filled)}"
               if filled else "  |  Alle Buffer leer")
        )
        return (
            f"Coding-Scratchpad  —  {status_line}\n\n"
            "  code <lang>               → Sprache aktivieren + Buffer anzeigen\n"
            "  code <lang> edit          → Interaktiver Multiline-Editor\n"
            "  code <lang> add <zeile>   → Zeile anhängen\n"
            "  code <lang> run           → Code in Sandbox ausführen\n"
            "  code <lang> clear         → Buffer leeren\n"
            "  code run                  → Aktiven Buffer ausführen\n"
            "  code status               → Alle Buffer anzeigen\n\n"
            f"  Sprachen: {', '.join(sorted(LANGUAGES))}\n"
            "  Timeout: 10s  |  Pine Script → TradingView  |  TS → ts-node"
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_lang(token: str) -> str | None:
    """Normalises language aliases to the internal key."""
    aliases = {
        "py":         "python",
        "python":     "python",
        "javascript": "js",
        "js":         "js",
        "node":       "js",
        "ts":         "ts",
        "typescript": "ts",
        "sh":         "bash",
        "shell":      "bash",
        "bash":       "bash",
        "go":         "go",
        "golang":     "go",
        "pine":       "pine",
        "pinescript": "pine",
        "tv":         "pine",
    }
    return aliases.get(token.lower())


def _get_ui():
    from core.ui_factory import get_renderer
    return get_renderer()
