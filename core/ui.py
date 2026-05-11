"""
ui.py — TerminalRenderer für Zuki
────────────────────────────────────
ANSI-Farben: PowerShell (Win 10+) und alle modernen Terminals.

Modul-Level-Funktionen (Abwärtskompatibilität mit main.py-Legacy-Code)
werden über die Default-Instanz `_default` weitergeleitet — sie rufen
einfach die entsprechende TerminalRenderer-Methode auf.

Wird über core/ui_factory.py als „terminal"-Renderer bereitgestellt.
"""

import os
import re as _re
import sys

from core.ui_renderer import UIRenderer

# Activate VT100 / ANSI on Windows
if sys.platform == "win32":
    os.system("")

# ── ANSI ───────────────────────────────────────────────────────────────────────
R      = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
RED    = "\033[91m"
GRAY   = "\033[90m"
WHITE  = "\033[97m"

W = 50  # separator width
SEP = f"{GRAY}{'─' * W}{R}"

# ── Dashboard-Konstanten ───────────────────────────────────────────────────────
_DW   = 46          # sichtbare Zeichen pro Box-Zeile (ohne Rahmen)
_ANSI = _re.compile(r"\033\[[^m]*m")   # ANSI-Escape zum Messen der echten Länge


def _vlen(s: str) -> int:
    """Sichtbare Länge eines Strings (ohne ANSI-Codes)."""
    return len(_ANSI.sub("", s))


def _bline(content: str = "", color: str = "") -> None:
    """Eine Box-Zeile: ║  content (auf _DW gepaddet)  ║"""
    pad = max(0, _DW - _vlen(content))
    print(f"  {CYAN}║{R}  {color}{content}{R}{' ' * pad}  {CYAN}║{R}")


def _bsep(char: str = "═") -> None:
    """Horizontale Trennlinie: ╠══…══╣"""
    inner = char * (_DW + 4)
    if char == "═":
        print(f"  {CYAN}╠{inner}╣{R}")
    else:
        print(f"  {CYAN}║{GRAY}{'─' * (_DW + 4)}{CYAN}║{R}")


def _btop() -> None:
    print(f"  {CYAN}╔{'═' * (_DW + 4)}╗{R}")


def _bbot() -> None:
    print(f"  {CYAN}╚{'═' * (_DW + 4)}╝{R}")


def _row(icon: str, color: str, text: str) -> None:
    print(f"  {color}{icon}{R}  {text}")


def _cmd(trigger: str, description: str) -> None:
    """Einzelne Befehlszeile im Dashboard."""
    t = f"{CYAN}{trigger:<18}{R}"
    _bline(f"{t}  {DIM}{description}{R}")


# ── ASCII-Art ──────────────────────────────────────────────────────────────────
ZUKI_ART = f"""{CYAN}{BOLD}
  ______   _    _   _  __   ___
 |___  /  | |  | | | |/ /  |_ _|
    / /   | |  | | | ' /    | |
   / /    | |  | | |  <     | |
  / /__   | |__| | | . \\    | |
 /_____|   \\____/  |_|\\_\\  |___| {R}"""


# ── TerminalRenderer ──────────────────────────────────────────────────────────

class TerminalRenderer(UIRenderer):
    """ANSI-Terminal-Renderer — die klassische Zuki-Oberfläche."""

    def kind(self) -> str:
        return "terminal"

    # ── Startup ───────────────────────────────────────────────────────────────

    def print_banner(
        self,
        simulation:      bool,
        memory_count:    int,
        whisper_mode:    str  = "",
        tts_voice:       str  = "",
        news_count:      int  = 0,
        watchlist_hits:  int  = 0,
        sentiment:       str  = "NEU",
        calendar_events: list | None = None,
    ) -> None:
        mode_color = YELLOW if simulation else GREEN
        mode_label = "SIMULATION" if simulation else "LIVE"

        print(ZUKI_ART)
        print(f"  {CYAN}{'═' * W}{R}")
        print(f"  {BOLD}Chef-Analyst  ·  Persönlicher Assistent{R}")
        print(f"  {CYAN}{'═' * W}{R}")
        print()
        _row("[OK]", GREEN,  f"Modus        :  {mode_color}{mode_label}{R}")
        _row("[OK]", GREEN,  f"Gedächtnis   :  {memory_count} Nachrichten geladen")
        _row("[OK]", GREEN,  f"System-Prompt:  identity.md aktiv  {DIM}(komprimiert){R}")
        if whisper_mode:
            _row("[OK]", GREEN, f"Sprache (STT):  {whisper_mode}")
        if tts_voice:
            _row("[OK]", GREEN, f"Stimme (TTS) :  {tts_voice}")
        if news_count:
            hits_str = f"  ·  {watchlist_hits} Watchlist-Treffer" if watchlist_hits else ""
            sentiment_color = {
                "POS": GREEN, "NEG": RED, "NEU": GRAY
            }.get(sentiment, GRAY)
            sentiment_str = f"  ·  Tendenz: {sentiment_color}{sentiment}{R}"
            _row("[🗞]", CYAN, f"News-Inbox   :  {news_count} Artikel{hits_str}{sentiment_str}  →  'Report'")
        for event in (calendar_events or []):
            _row("[!] ", YELLOW, f"HEUTE: {event}")
        if simulation:
            _row("[!] ", YELLOW, "Kein API-Key — volle KI nach Key-Aktivierung")
        print()
        print(f"  {GRAY}{'─' * W}{R}")
        _row("[🎤]", GRAY, "'Hör zu'  →  Mikrofon (5 Sek.)")
        _row("[✕] ", GRAY, "'exit'    →  Beenden")
        print(f"  {CYAN}{'═' * W}{R}\n")

    def print_dashboard(
        self,
        simulation:   bool,
        api_provider: str,
        name:         str,
        level:        str,
        memory_count: int,
        whisper_mode: str,
        tts_voice:    str,
        vision_ok:    bool,
        tenant_name:  str = "self",
    ) -> None:
        chat_color  = YELLOW if simulation else GREEN
        chat_label  = "SIMULATION" if simulation else "LIVE"
        vision_str  = f"{GREEN}bereit{R}" if vision_ok else f"{YELLOW}mss fehlt{R}"
        vision_icon = f"{GREEN}[OK]{R}" if vision_ok else f"{YELLOW}[!]{R} "
        name_str    = name  if name  else f"{GRAY}(unbekannt){R}"
        level_str   = level if level else f"{GRAY}—{R}"
        prof_sim    = api_provider == "SIMULATION"
        prof_color  = YELLOW if prof_sim else GREEN
        prof_icon   = f"{YELLOW}[!]{R} " if prof_sim else f"{GREEN}[OK]{R}"

        print()
        _btop()

        _bline(f"{BOLD}🤖  Z U K I{R}  ·  Assistent & Analyst", CYAN)
        _bsep()

        _bline(
            f"👤 {BOLD}{name_str}{R}"
            f"  ·  Niveau: {level_str}"
            f"  ·  🧠 {memory_count} Erinnerungen"
        )
        _bline(f"🏢 Tenant: {CYAN}{tenant_name}{R}")
        _bsep()

        _bline(f"{BOLD}SYSTEM{R}", GRAY)
        _bline(
            f"{GREEN}[OK]{R}  Chat       {chat_color}{chat_label}{R}"
            f"{'  ·  API aktiv' if not simulation else ''}"
        )
        _bline(
            f"{prof_icon}  Professor  "
            f"{prof_color}{api_provider}{R}"
        )
        _bline(f"{GREEN}[OK]{R}  Sprache    {whisper_mode}  ·  {tts_voice}")
        _bline(f"{vision_icon}  Vision     {vision_str}")
        _bsep()

        _bline(f"{BOLD}BEFEHLE{R}", GRAY)
        _cmd("broker",          "Marktanalyse & News aktivieren")
        _cmd("report",          "News-Auswertung (im Broker-Modus)")
        _cmd("explain [Thema]", "Der Professor — Erklärung")
        _cmd("vision",          "Screenshot analysieren")
        _cmd("tenant [list|switch|create|delete]", "Workspace wechseln")
        _cmd("system backup",   "Projekt-Snapshot erstellen")
        _cmd("hör zu",          "Spracheingabe (5 Sek.)")
        _cmd("exit",            "Beenden")

        _bbot()
        print()

    # ── Dialog ────────────────────────────────────────────────────────────────

    def user_prompt(self) -> str:
        print(f"\n  {YELLOW}👤 SIE  ›{R}  ", end="", flush=True)
        return input("").strip()

    def speak_zuki(self, text: str) -> None:
        print(f"\n  {BLUE}{BOLD}🤖 ZUKI ›{R}")
        for line in text.splitlines():
            print(f"  {line}")
        print(f"  {SEP}")

    # ── Status-Icons ──────────────────────────────────────────────────────────

    def listening(self) -> None:
        print(f"\n  {CYAN}[🎤]{R}  Zuki hört jetzt zu...   ", end="", flush=True)

    def thinking(self) -> None:
        print(f"\n  {CYAN}[🧠]{R}  Verarbeitung läuft...")

    def speaking(self) -> None:
        print(f"  {CYAN}[🔊]{R}  Zuki spricht...")

    def system_msg(self, text: str) -> None:
        print(f"  {GRAY}[SYS]{R}  {DIM}{text}{R}")

    def error_msg(self, text: str) -> None:
        print(f"  {RED}[ ! ]{R}  {text}")

    def voice_echo(self, text: str) -> None:
        print(f"  {GRAY}[🎤 Erkannt]{R}  \"{text}\"")

    # ── Broker-Modus ──────────────────────────────────────────────────────────

    def print_broker_status(
        self,
        news_count:      int,
        watchlist_hits:  int,
        sentiment:       str,
        calendar_events: list,
    ) -> None:
        sentiment_color = {
            "POS": GREEN, "NEG": RED, "NEU": GRAY
        }.get(sentiment, GRAY)

        print(f"\n  {CYAN}{'═' * W}{R}")
        print(f"  {CYAN}{BOLD}📊  BROKER-MODUS AKTIV{R}")
        print(f"  {CYAN}{'─' * W}{R}")
        _row("[🗞]", CYAN,
             f"News-Inbox   :  {news_count} Artikel  "
             f"·  {watchlist_hits} Watchlist-Treffer  "
             f"·  Tendenz: {sentiment_color}{sentiment}{R}")
        for event in calendar_events:
            _row("[!] ", YELLOW, f"HEUTE: {event}")
        print(f"  {CYAN}{'─' * W}{R}")
        _row("[OK]", GREEN, "Broker-Modul aktiv. Sir, ich bin bereit für die Analyse.")
        _row("[📋]", GRAY, "'report'      →  Auswertung starten")
        _row("[🔙]", GRAY, "'main'        →  Standard-Modus")
        print(f"  {CYAN}{'═' * W}{R}\n")

    def print_broker_deactivated(self) -> None:
        print(f"\n  {GRAY}{'─' * W}{R}")
        _row("[OK]", GREEN, "Broker-Modus deaktiviert. Standard-Modus aktiv.")
        print(f"  {GRAY}{'─' * W}{R}\n")

    # ── System-Test ───────────────────────────────────────────────────────────

    def print_system_test(self, results: list) -> None:
        """Gibt System-Diagnose-Ergebnisse als farbige Tabelle aus."""
        SEP_LINE = f"  {GRAY}{'─' * W}{R}"

        print(f"\n  {BOLD}System-Diagnose{R}")
        print(SEP_LINE)

        for r in results:
            if r.status == "ok":
                badge = f"{GREEN}[OK]  {R}"
            elif r.status == "warn":
                badge = f"{YELLOW}[WARN]{R}"
            else:
                badge = f"{RED}[FAIL]{R}"

            name_col = f"{r.name:<12}"
            print(f"   {badge}  {CYAN}{name_col}{R}  {r.summary}")
            if r.fix_hint and r.status != "ok":
                print(f"   {' ' * 6}  {' ' * 12}  {DIM}{r.fix_hint}{R}")

        print(SEP_LINE)

        ok   = sum(1 for r in results if r.status == "ok")
        warn = sum(1 for r in results if r.status == "warn")
        fail = sum(1 for r in results if r.status == "fail")

        ok_s   = f"{GREEN}{ok} OK{R}"
        warn_s = f"{YELLOW}{warn} WARN{R}"
        fail_s = f"{RED}{fail} FAIL{R}"
        print(f"   Ergebnis: {ok_s}  {warn_s}  {fail_s}\n")


# ── Modul-Level-Forwarding (Abwärtskompatibilität) ────────────────────────────
# Damit alter Code der Form `from core import ui; ui.speak_zuki(...)` weiter
# funktioniert, bis er auf ui_factory umgestellt ist.

_default = TerminalRenderer()

def print_banner(*a, **kw):         _default.print_banner(*a, **kw)
def print_dashboard(*a, **kw):      _default.print_dashboard(*a, **kw)
def user_prompt() -> str:           return _default.user_prompt()
def speak_zuki(text: str):          _default.speak_zuki(text)
def listening():                    _default.listening()
def thinking():                     _default.thinking()
def speaking():                     _default.speaking()
def system_msg(text: str):          _default.system_msg(text)
def error_msg(text: str):           _default.error_msg(text)
def voice_echo(text: str):          _default.voice_echo(text)
def print_broker_status(*a, **kw):  _default.print_broker_status(*a, **kw)
def print_broker_deactivated():     _default.print_broker_deactivated()
def print_system_test(results):     _default.print_system_test(results)
