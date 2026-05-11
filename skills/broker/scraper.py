"""
scraper.py — Web-Scraper Skill für Zuki Broker-Modul
─────────────────────────────────────────────────────
AKTUELL: Mock-Modus — erstellt Beispiel-News in news_inbox/

LIVE UPGRADE:
  Ersetze den Body von fetch_news() mit einem echten Scraper, z.B.:
  ┌─────────────────────────────────────────────────────────┐
  │  # Option A — Newspaper3k                               │
  │  from newspaper import Article                          │
  │  art = Article(url); art.download(); art.parse()        │
  │  content = art.text                                     │
  │                                                         │
  │  # Option B — BeautifulSoup + requests                 │
  │  import requests; from bs4 import BeautifulSoup         │
  │  soup = BeautifulSoup(requests.get(url).text, "html")   │
  │  content = soup.get_text()                              │
  │                                                         │
  │  # Option C — NewsAPI                                   │
  │  import os, requests                                    │
  │  key = os.getenv("NEWSAPI_KEY")                        │
  │  r = requests.get(f"https://newsapi.org/v2/top-..."    │
  │                   f"?apiKey={key}")                     │
  │  articles = r.json()["articles"]                        │
  └─────────────────────────────────────────────────────────┘

  Alle Scraper-Ergebnisse → save_article(filename, content)
"""

import os
from datetime import date, datetime

from core.logger import get_logger

log = get_logger("scraper")

_BROKER = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "skills", "broker"
))

# Resolve from scraper.py's own location (skills/broker/scraper.py → skills/broker/)
INBOX = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "news_inbox"
)

# ── Mock-Artikel ───────────────────────────────────────────────────────────────
_MOCK_ARTICLES = [
    {
        "filename": "mock_tech.txt",
        "content": (
            "NVIDIA meldet Rekordgewinn im Q2 — Umsatz übersteigt Erwartungen.\n"
            "CEO Jensen Huang: 'KI-Nachfrage bleibt auf Allzeithoch.'\n"
            "Analysten erhöhen Kursziel auf $1.200. Kaufempfehlung bestätigt."
        ),
    },
    {
        "filename": "mock_crypto.txt",
        "content": (
            "Bitcoin stabil über $65.000 — institutionelle Käufer dominieren.\n"
            "BTC ETF-Zuflüsse auf Rekordhoch. Rally erwartet.\n"
            "Gold ebenfalls stark: +1,2% — sichere Häfen gefragt."
        ),
    },
    {
        "filename": "mock_macro.txt",
        "content": (
            "Fed-Protokoll: Zinssenkung im September wahrscheinlich.\n"
            "SP500 klettert auf neuem Rekordhoch. Aufschwung setzt sich fort.\n"
            "Wachstumsprognose für 2025 von IWF angehoben."
        ),
    },
    {
        "filename": "mock_risk.txt",
        "content": (
            "Gewinnwarnung von mehreren DAX-Unternehmen — Schwäche im Industriesektor.\n"
            "Rückgang der Auftragseingänge signalisiert mögliche Krise.\n"
            "Analysten: Bearish-Signal für europäische Märkte."
        ),
    },
]


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_mock_news() -> int:
    """
    Erstellt Beispiel-News-Dateien im news_inbox/ Ordner.
    Dateinamen erhalten das heutige Datum als Präfix → NewsManager erkennt sie.
    Gibt Anzahl erstellter Dateien zurück.
    """
    os.makedirs(INBOX, exist_ok=True)
    today = date.today().isoformat()
    created = 0

    for article in _MOCK_ARTICLES:
        fname = f"{today}_{article['filename']}"
        fpath = os.path.join(INBOX, fname)
        if os.path.exists(fpath):
            log.debug(f"Bereits vorhanden, übersprungen: {fname}")
            continue
        try:
            _save_article(fpath, article["content"])
            created += 1
            log.info(f"Mock-Artikel erstellt: {fname}")
        except OSError as e:
            log.warning(f"Konnte Artikel nicht schreiben: {fname} — {e}")

    log.info(f"fetch_mock_news: {created} neue Artikel erstellt")
    return created


def fetch_news() -> int:
    """
    Einstiegspunkt für echten Scraper (LIVE UPGRADE).
    Aktuell: Delegiert an fetch_mock_news().

    ── LIVE UPGRADE ──────────────────────────────────────────
    Ersetze diesen Funktions-Body mit echten API-Calls.
    Nutze NEWSAPI_KEY, SERPAPI_API_KEY aus .env.
    Alle Ergebnisse → _save_article(fpath, content)
    ──────────────────────────────────────────────────────────
    """
    return fetch_mock_news()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _save_article(fpath: str, content: str) -> None:
    """Schreibt einen Artikel als .txt in news_inbox/."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(f"[Erstellt: {timestamp}]\n\n{content}\n")
