"""
business_skill.py — BusinessSkill for Zuki
───────────────────────────────────────────
Triggers : business, analyse, analysiere

Commands:
  business                        → help overview
  business analyse <Name/Address> → digital weakness analysis + PDF
  business interview [Name]       → workflow audit questionnaire (interactive)
  business interview [Name] report → interview + PDF report
  business status                 → show last analysis
  business report                 → generate PDF from last analysis

Architecture:
  GastroAnalyzer    → fetches data + detects weaknesses
  WorkflowInterview → runs questionnaire inline (analogous to vision handler)
  build_analyse_report() / build_workflow_report() → PDF output

Log marker: [BUSINESS-SKILL]
"""

import os
from pathlib import Path

from core.logger import get_logger
from workspaces.base import Skill

log = get_logger("business.skill")

_ROOT       = Path(__file__).resolve().parent.parent.parent
_REPORT_DIR = _ROOT / "temp" / "business_reports"


class BusinessSkill(Skill):
    name        = "business"
    triggers    = {"business", "analyse", "analysiere"}
    description = (
        "Digital weakness analysis for gastro businesses: "
        "Google Business Profile, social media, reviews, competition. "
        "Creates PDF report and runs workflow interview."
    )

    def __init__(self) -> None:
        self._last_analysis = None   # AnalysisResult | None
        self._last_report_path: str = ""

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def handle(self, context: dict) -> "str | None":
        cmd        = context.get("cmd", "").strip()
        user_input = context.get("user_input", "").strip()

        # Normalise: "analysiere X" → "business analyse X"
        if cmd.startswith("analysiere ") or cmd.startswith("analyse "):
            rest = cmd.split(" ", 1)[1].strip()
            cmd  = f"business analyse {rest}"

        parts = cmd.split()   # ["business", "analyse", ...]

        # ── Help ──────────────────────────────────────────────────────────────
        if len(parts) == 1 and parts[0] == "business":
            return self._help()

        # ── Analysis ──────────────────────────────────────────────────────────
        if len(parts) >= 3 and parts[1] == "analyse":
            query = " ".join(parts[2:])
            return self._run_analyse(query, context)

        # ── Status ────────────────────────────────────────────────────────────
        if len(parts) == 2 and parts[1] == "status":
            return self._show_status()

        # ── Report from last analysis ─────────────────────────────────────────
        if len(parts) == 2 and parts[1] == "report":
            return self._generate_report()

        # ── Interview ─────────────────────────────────────────────────────────
        if len(parts) >= 2 and parts[1] == "interview":
            name = " ".join(parts[2:]).strip()
            return self._run_interview(name, context)

        return self._help()

    # ── Analysis ──────────────────────────────────────────────────────────────

    def _run_analyse(self, query: str, context: dict) -> str:
        from workspaces.business.analyzer import GastroAnalyzer

        ui = self._get_ui()
        ui.system_msg(f"[Business] Analysiere: {query} ...")

        analyzer = GastroAnalyzer()
        try:
            result = analyzer.run(query)
        except Exception as e:
            log.error(f"[BUSINESS-SKILL] Analysis error: {e}")
            return f"Analyse fehlgeschlagen: {e}\nDetails in logs/error.log"

        self._last_analysis = result

        stub_hint = "  ⚠️  Stub-Daten (kein SerpAPI-Key)" if result.stub_mode else ""
        lines = [
            f"Analyse: {result.name}  |  Score: {result.score}/100{stub_hint}",
            f"Bewertung: {result.rating:.1f} ⭐  ({result.review_count} Reviews)",
        ]

        if result.weaknesses_found:
            lines.append(f"\nErkannte Schwachstellen ({len(result.weaknesses_found)}):")
            for w in result.weaknesses_found:
                sev_icon = {"hoch": "🔴", "mittel": "🟡", "niedrig": "🟢"}.get(w.get("severity", ""), "•")
                lines.append(f"  {sev_icon} {w['title']}")
        else:
            lines.append("\nKeine kritischen Schwachstellen erkannt.")

        if result.competitors:
            lines.append(f"\nKonkurrenz im Umkreis: {len(result.competitors)} Betriebe gefunden")

        lines.append(
            "\n'business report'   → PDF-Report generieren"
            "\n'business interview <Name>'  → Workflow-Audit starten"
        )

        log.info(f"[BUSINESS-SKILL] Analysis complete: {result.name}  score={result.score}")
        return "\n".join(lines)

    # ── PDF report from last analysis ─────────────────────────────────────────

    def _generate_report(self) -> str:
        if self._last_analysis is None:
            return (
                "Noch keine Analyse durchgeführt.\n"
                "Zuerst: business analyse <Name oder Adresse>"
            )

        from tools.report import build_analyse_report
        from workspaces.business.analyzer import GastroAnalyzer

        _REPORT_DIR.mkdir(parents=True, exist_ok=True)
        filename = _safe_filename(self._last_analysis.name or "report") + ".pdf"
        output   = _REPORT_DIR / filename

        try:
            analyzer    = GastroAnalyzer()
            report_data = analyzer.to_report_data(self._last_analysis)
            path        = build_analyse_report(output_path=output, **report_data)
            self._last_report_path = path
            log.info(f"[BUSINESS-SKILL] Report saved: {path}")
            return f"PDF-Report erstellt:\n  {path}"
        except Exception as e:
            log.error(f"[BUSINESS-SKILL] Report error: {e}")
            return f"Report-Erstellung fehlgeschlagen: {e}"

    # ── Interview (runs inline) ───────────────────────────────────────────────

    def _run_interview(self, name: str, context: dict) -> str:
        from workspaces.business.interview import WorkflowInterview
        from tools.report import build_workflow_report

        ui = self._get_ui()

        display_name = name or "Unbekannter Betrieb"
        interview    = WorkflowInterview(restaurant_name=display_name)

        _BACK_CMDS   = {"zurück", "zurueck", "back", "z", "<"}
        _CANCEL_CMDS = {"abbrechen", "abort", "exit", "stop"}

        ui.speak_zuki(
            f"Workflow-Audit-Interview für: {display_name}\n"
            f"10 Fragen zum Betriebsablauf  ·  'zurück' = vorherige Frage  ·  'abbrechen' = beenden"
        )

        # Interactive questionnaire loop
        while not interview.is_done():
            ui.speak_zuki(interview.format_question())
            answer = ui.user_prompt().strip()

            if answer.lower() in _CANCEL_CMDS:
                log.info("[BUSINESS-SKILL] Interview cancelled")
                return "Interview abgebrochen."

            if answer.lower() in _BACK_CMDS:
                if interview.go_back():
                    ui.speak_zuki("  ← Zurück zur vorherigen Frage.")
                else:
                    ui.speak_zuki("  Bereits bei der ersten Frage.")
                continue

            interview.answer(answer)

        # Interview complete — always generate PDF
        summary  = interview.get_summary()
        insights = summary.get("insights", [])

        lines = [f"Interview abgeschlossen — {display_name}"]
        if insights:
            lines.append("\nErkannte Ansatzpunkte:")
            for ins in insights:
                lines.append(f"  • {ins}")
        else:
            lines.append("\nKeine kritischen Workflow-Probleme erkannt.")

        _REPORT_DIR.mkdir(parents=True, exist_ok=True)
        filename = _safe_filename(display_name) + "_workflow.pdf"
        output   = _REPORT_DIR / filename
        try:
            path = build_workflow_report(
                output_path = output,
                client_name = display_name,
                notes       = interview.to_report_notes(),
            )
            self._last_report_path = path
            lines.append(f"\nWorkflow-Report gespeichert:\n  {path}")
            log.info(f"[BUSINESS-SKILL] Workflow report: {path}")
        except Exception as e:
            log.warning(f"[BUSINESS-SKILL] Workflow report error: {e}")
            lines.append(f"\nReport-Erstellung fehlgeschlagen: {e}")

        log.info(f"[BUSINESS-SKILL] Interview done: {display_name}")
        return "\n".join(lines)

    # ── Status ────────────────────────────────────────────────────────────────

    def _show_status(self) -> str:
        if self._last_analysis is None:
            return (
                "Noch keine Analyse in dieser Session.\n"
                "Start: business analyse <Name oder Adresse>"
            )
        r = self._last_analysis
        lines = [
            f"Letzte Analyse: {r.name}  ({r.analyzed_at})",
            f"Score: {r.score}/100  |  Bewertung: {r.rating:.1f} ⭐  |  Reviews: {r.review_count}",
            f"Schwachstellen: {len(r.weaknesses_found)}",
            f"Stub-Modus: {'ja (Beispiel-Daten)' if r.stub_mode else 'nein (echte Daten)'}",
        ]
        if self._last_report_path:
            lines.append(f"Letzter Report: {self._last_report_path}")
        return "\n".join(lines)

    # ── Help ──────────────────────────────────────────────────────────────────

    def _help(self) -> str:
        return (
            "Business-Skill — Digitale Schwachstellen-Analyse\n\n"
            "  business analyse <Name oder Adresse>\n"
            "      → Google Business Profile, Bewertungen, Konkurrenz analysieren\n"
            "      → Schwachstellen aus Gastro-Wissens-Datenbank erkennen\n\n"
            "  business report\n"
            "      → PDF-Report aus letzter Analyse generieren\n\n"
            "  business interview <Name>\n"
            "      → Workflow-Audit-Fragebogen (10 Fragen) + PDF-Report\n"
            "      → 'zurück' während Interview = vorherige Frage wiederholen\n\n"
            "  business status\n"
            "      → Letzte Analyse-Ergebnisse anzeigen\n\n"
            "  analyse <Name> / analysiere <Name>\n"
            "      → Kurzform für 'business analyse'"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _get_ui():
        from core.ui_factory import get_renderer
        return get_renderer()


def _safe_filename(name: str) -> str:
    """Converts a name into a filesystem-safe string."""
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
    return safe.strip().replace(" ", "_")[:60] or "report"
