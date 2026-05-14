"""
interview.py — Workflow-Audit-Interview für Gastro-Betriebe
─────────────────────────────────────────────────────────────
Zuki führt einen strukturierten Fragebogen durch.
Antworten werden gesammelt und als Interview-Report aufbereitet.

Verwendung:
  interview = WorkflowInterview()
  # in main.py loop:
  question = interview.next_question()
  if question is None:
      summary = interview.get_summary()
  else:
      interview.answer(user_input)

Status:
  interview.is_done()     → bool
  interview.get_summary() → dict
  interview.to_report_notes() → str

Log-Marker: [BUSINESS-INTERVIEW]
"""

from core.logger import get_logger

log = get_logger("business.interview")


# ── Fragebogen-Definition ─────────────────────────────────────────────────────

_QUESTIONS: list[dict] = [
    {
        "id":      "sitzplaetze",
        "text":    "Wie viele Sitzplätze hat das Restaurant (innen + außen)?",
        "hint":    "Zahl eingeben, z. B. '60' oder '40 innen, 20 außen'",
        "type":    "text",
    },
    {
        "id":      "reservierung",
        "text":    "Wie nehmen Sie aktuell Reservierungen an?",
        "hint":    "z. B. 'nur Telefon', 'Telefon + TheFork', 'keine Reservierungen'",
        "type":    "text",
    },
    {
        "id":      "kassensystem",
        "text":    "Nutzen Sie ein digitales Kassensystem?",
        "hint":    "z. B. 'ja, orderbird', 'nein, klassische Kasse', 'Zettle'",
        "type":    "text",
    },
    {
        "id":      "social_media_zustaendig",
        "text":    "Wer betreut Ihre Social-Media-Kanäle aktuell?",
        "hint":    "z. B. 'ich selbst', 'Mitarbeiter X', 'niemand', 'Agentur'",
        "type":    "text",
    },
    {
        "id":      "post_frequenz",
        "text":    "Wie oft posten Sie ungefähr pro Woche auf Instagram oder Facebook?",
        "hint":    "z. B. '0', '1-2', '3-5', 'täglich'",
        "type":    "text",
    },
    {
        "id":      "bewertungsantworten",
        "text":    "Wie gehen Sie mit Google-Bewertungen um?",
        "hint":    "z. B. 'antworte auf alle', 'manchmal', 'gar nicht', 'weiß nicht wie'",
        "type":    "text",
    },
    {
        "id":      "lieferdienst",
        "text":    "Sind Sie auf Lieferando, Uber Eats oder ähnlichen Plattformen vertreten?",
        "hint":    "z. B. 'ja, Lieferando', 'nein', 'war mal, jetzt nicht mehr'",
        "type":    "text",
    },
    {
        "id":      "newsletter_loyalty",
        "text":    "Haben Sie einen Newsletter oder ein Kundenbindungsprogramm?",
        "hint":    "z. B. 'Mailchimp-Newsletter', 'Stempelkarte', 'nein'",
        "type":    "text",
    },
    {
        "id":      "groesste_herausforderung",
        "text":    "Was ist Ihre größte Herausforderung im Betrieb aktuell?",
        "hint":    "z. B. 'Personalmangel', 'zu wenig Gäste dienstags', 'hohe Kosten'",
        "type":    "text",
    },
    {
        "id":      "ziel_3_monate",
        "text":    "Was wäre für Sie in den nächsten 3 Monaten der wichtigste Fortschritt?",
        "hint":    "z. B. 'mehr Bewertungen', 'bessere Auslastung', 'Lieferdienst starten'",
        "type":    "text",
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# WorkflowInterview
# ══════════════════════════════════════════════════════════════════════════════

class WorkflowInterview:
    """
    Zustandsbehafteter Fragebogen — eine Frage nach der anderen.
    Wird von BusinessSkill.handle() gesteuert (State in main.py gespeichert).
    """

    def __init__(self, restaurant_name: str = "") -> None:
        self._name      = restaurant_name
        self._answers:  dict[str, str] = {}
        self._index:    int            = 0
        self._done:     bool           = False

        log.info(f"[BUSINESS-INTERVIEW] Gestartet für '{restaurant_name}' ({len(_QUESTIONS)} Fragen)")

    # ── Navigation ────────────────────────────────────────────────────────────

    def current_question(self) -> "dict | None":
        if self._done or self._index >= len(_QUESTIONS):
            return None
        return _QUESTIONS[self._index]

    def answer(self, user_input: str) -> None:
        if self._done:
            return
        q = _QUESTIONS[self._index]
        self._answers[q["id"]] = user_input.strip()
        log.info(f"[BUSINESS-INTERVIEW] Frage {self._index + 1}/{len(_QUESTIONS)}: '{q['id']}' → '{user_input[:60]}'")
        self._index += 1
        if self._index >= len(_QUESTIONS):
            self._done = True
            log.info("[BUSINESS-INTERVIEW] Abgeschlossen")

    def go_back(self) -> bool:
        """Geht eine Frage zurück. Gibt False zurück wenn bereits bei Frage 1."""
        if self._index <= 0:
            return False
        self._index -= 1
        self._done = False
        old_id = _QUESTIONS[self._index]["id"]
        self._answers.pop(old_id, None)
        log.info(f"[BUSINESS-INTERVIEW] Zurück zu Frage {self._index + 1}: '{old_id}'")
        return True

    def is_done(self) -> bool:
        return self._done

    def progress(self) -> str:
        return f"{self._index}/{len(_QUESTIONS)}"

    # ── Ergebnis ──────────────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        """Gibt alle Antworten + Erkenntnisse als dict zurück."""
        return {
            "restaurant":   self._name,
            "answers":      self._answers,
            "insights":     self._derive_insights(),
            "total_q":      len(_QUESTIONS),
        }

    def to_report_notes(self) -> str:
        """Kompakter Text für das Notizen-Feld im PDF-Report."""
        lines = [f"Workflow-Audit — {self._name}", ""]
        for q in _QUESTIONS:
            qid = q["id"]
            ans = self._answers.get(qid, "—")
            lines.append(f"• {q['text']}")
            lines.append(f"  Antwort: {ans}")
            lines.append("")
        insights = self._derive_insights()
        if insights:
            lines.append("Erkannte Ansatzpunkte:")
            for i in insights:
                lines.append(f"• {i}")
        return "\n".join(lines)

    def format_question(self) -> str:
        """Formatiert aktuelle Frage für Terminal-Ausgabe."""
        q = self.current_question()
        if q is None:
            return ""
        n    = self._index + 1
        total = len(_QUESTIONS)
        return (
            f"\n  Frage {n}/{total}: {q['text']}\n"
            f"  ({q['hint']})\n"
        )

    # ── Interne Erkenntnisse ──────────────────────────────────────────────────

    def _derive_insights(self) -> list[str]:
        insights = []
        a = self._answers

        freq = a.get("post_frequenz", "0").replace("täglich", "7")
        try:
            freq_n = int(freq.split("-")[0].strip())
        except (ValueError, AttributeError):
            freq_n = 0

        if freq_n == 0:
            insights.append("Keine Social-Media-Aktivität — dringend Posting-Routine aufbauen")
        elif freq_n < 3:
            insights.append("Social-Media-Frequenz ausbaubar — Ziel: min. 3 Posts/Woche")

        bewertung = a.get("bewertungsantworten", "").lower()
        if "gar nicht" in bewertung or "nicht" in bewertung:
            insights.append("Bewertungsantworten fehlen komplett — Google-Ranking leidet")
        elif "manchmal" in bewertung:
            insights.append("Bewertungsantworten unregelmäßig — auf 100% Antwortrate optimieren")

        reserv = a.get("reservierung", "").lower()
        if "nur telefon" in reserv or "nur tel" in reserv:
            insights.append("Nur Telefon-Reservierung — Online-Buchung sperrt Zielgruppe unter 35 aus")

        lieferdienst = a.get("lieferdienst", "").lower()
        if "nein" in lieferdienst:
            insights.append("Kein Lieferdienst — Potenzial für Zusatz-Umsatz (Lieferando-Test empfohlen)")

        newsletter = a.get("newsletter_loyalty", "").lower()
        if "nein" in newsletter or not newsletter:
            insights.append("Kein Kundenbindungskanal — Stammgäste ohne Direktkommunikation")

        zustaendig = a.get("social_media_zustaendig", "").lower()
        if "niemand" in zustaendig or not zustaendig:
            insights.append("Kein Verantwortlicher für Social Media definiert")

        return insights
