"""
email_interface.py — Mail-Infrastruktur für Zuki Business-Skill
────────────────────────────────────────────────────────────────
AKTUELL: SIM-Modus — Dummy-Mails und Template-Entwürfe

LIVE UPGRADE — Gmail API:
  ┌────────────────────────────────────────────────────────────┐
  │  from google.oauth2.credentials import Credentials         │
  │  from googleapiclient.discovery import build               │
  │                                                            │
  │  creds = Credentials.from_authorized_user_file(           │
  │      'token.json', SCOPES)                                 │
  │  service = build('gmail', 'v1', credentials=creds)         │
  │  results = service.users().messages().list(                │
  │      userId='me', q='is:unread').execute()                 │
  └────────────────────────────────────────────────────────────┘

LIVE UPGRADE — Outlook / Microsoft Graph API:
  ┌────────────────────────────────────────────────────────────┐
  │  import msal, requests                                     │
  │  token = app.acquire_token_silent(SCOPES, account=None)    │
  │  headers = {'Authorization': f'Bearer {token["access_token"]}'} │
  │  r = requests.get(                                         │
  │      'https://graph.microsoft.com/v1.0/me/messages'        │
  │      '?$filter=isRead eq false', headers=headers)          │
  └────────────────────────────────────────────────────────────┘

  Gemeinsame Schnittstelle: get_pending_mails() gibt immer
  list[dict] zurück → main.py muss nicht geändert werden.
"""

from datetime import date
from core.logger import get_logger

log = get_logger("email")

# ── SIM-Dummy-Mails ────────────────────────────────────────────────────────────

_DUMMY_MAILS = [
    {
        "id":      "sim-001",
        "from":    "Max Mustermann <max@example.com>",
        "subject": "Anfrage Paket A — Preis?",
        "date":    "2026-05-05",
        "body":    "Hallo, ich würde gerne wissen, was Paket A kostet. Können wir telefonieren?",
        "read":    False,
        "customer": "Max Mustermann",
    },
    {
        "id":      "sim-002",
        "from":    "Thomas Schmidt <thomas@example.com>",
        "subject": "Re: Erstgespräch — Wann geht es weiter?",
        "date":    "2026-05-06",
        "body":    "Guten Tag, ich warte noch auf das versprochene Angebot. Haben Sie es vergessen?",
        "read":    False,
        "customer": "Thomas Schmidt",
    },
]


class EmailInterface:
    """
    Einheitliche Mail-Schnittstelle.
    SIM → Dummy-Daten.
    LIVE → Gmail/Outlook API (siehe LIVE UPGRADE oben).
    """

    def get_pending_mails(self, simulation: bool = True) -> list[dict]:
        """
        Gibt ungelesene / ausstehende Mails zurück.

        simulation=True  → Dummy-Mails aus _DUMMY_MAILS
        simulation=False → LIVE UPGRADE: API-Call hier ersetzen
        """
        if simulation:
            log.debug("EmailInterface: SIM-Modus — Dummy-Mails geladen")
            return [m for m in _DUMMY_MAILS if not m["read"]]

        # ── LIVE UPGRADE ───────────────────────────────────────────────────────
        # Hier Gmail oder Outlook API einbinden.
        # Always returns list[dict] with keys:
        #   id, from, subject, date, body, read, customer (optional)
        # ──────────────────────────────────────────────────────────────────────
        log.warning("EmailInterface: LIVE-Modus noch nicht implementiert — fallback SIM")
        return [m for m in _DUMMY_MAILS if not m["read"]]

    def count_pending(self, simulation: bool = True) -> int:
        return len(self.get_pending_mails(simulation))

    def get_mail_for_customer(self, customer_name: str,
                               simulation: bool = True) -> list[dict]:
        """Filtert Mails nach Kundenname (Fuzzy-Match auf 'customer'-Feld)."""
        mails = self.get_pending_mails(simulation)
        name_lower = customer_name.strip().lower()
        return [
            m for m in mails
            if name_lower in m.get("customer", "").lower()
            or name_lower in m.get("from", "").lower()
        ]

    def build_draft(self, customer: dict, mail: dict | None,
                    simulation: bool = True) -> str:
        """
        Erstellt einen Antwort-Entwurf.

        SIM  → Template mit Kundendaten
        LIVE → LLM-Aufruf mit Kontext (mail body + customer notes)

        LIVE UPGRADE:
          prompt = f"Schreibe eine professionelle Antwort auf:
          {mail['body']}\nKunde: {customer['name']}\nNotizen: {customer['notes']}"
          return llm.chat([{"role": "user", "content": prompt}])
        """
        name   = customer.get("name", "Unbekannt")
        status = customer.get("status", "—")
        notes  = customer.get("notes", "—")
        today  = date.today().strftime("%d.%m.%Y")

        if mail:
            subject_ref = f"Re: {mail['subject']}"
            body_ref    = f'\n\nBezug auf Ihre Nachricht: "{mail["body"][:120]}..."'
        else:
            subject_ref = f"Ihre Anfrage — {today}"
            body_ref    = ""

        draft = (
            f"[ENTWURF] An: {name}\n"
            f"Betreff: {subject_ref}\n"
            f"{'─' * 40}\n"
            f"Guten Tag {name.split()[0]},{body_ref}\n\n"
            f"vielen Dank für Ihre Nachricht. "
            f"[Hier individuelle Antwort einfügen — Status: {status}]\n\n"
            f"Notizen intern: {notes}\n\n"
            f"Mit freundlichen Grüßen\n"
            f"[Ihr Name]\n"
            f"{'─' * 40}\n"
            f"(SIM: Im Live-Modus würde Zuki diesen Entwurf via LLM personalisieren.)"
        )
        log.debug(f"Mail-Entwurf erstellt für: {name}")
        return draft
