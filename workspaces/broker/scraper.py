"""
scraper.py — Web scraper skill for Zuki broker module
──────────────────────────────────────────────────────
CURRENT: Mock mode — creates sample news in news_inbox/

LIVE UPGRADE:
  Replace the body of fetch_news() with a real scraper, e.g.:
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

  All scraper results → save_article(filename, content)
"""

import os
from datetime import date, datetime

from core.logger import get_logger

log = get_logger("scraper")

_BROKER = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "workspaces", "broker"
))

# Resolve from scraper.py's own location (workspaces/broker/scraper.py → workspaces/broker/)
INBOX = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "news_inbox"
)

# ── Mock articles ──────────────────────────────────────────────────────────────
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
    Creates sample news files in the news_inbox/ folder.
    Filenames get today's date as prefix → NewsManager recognises them.
    Returns number of files created.
    """
    os.makedirs(INBOX, exist_ok=True)
    today = date.today().isoformat()
    created = 0

    for article in _MOCK_ARTICLES:
        fname = f"{today}_{article['filename']}"
        fpath = os.path.join(INBOX, fname)
        if os.path.exists(fpath):
            log.debug(f"Already exists, skipped: {fname}")
            continue
        try:
            _save_article(fpath, article["content"])
            created += 1
            log.info(f"Mock article created: {fname}")
        except OSError as e:
            log.warning(f"Could not write article: {fname} — {e}")

    log.info(f"fetch_mock_news: {created} new articles created")
    return created


def fetch_news() -> int:
    """
    Entry point for real scraper (LIVE UPGRADE).
    Currently: delegates to fetch_mock_news().

    ── LIVE UPGRADE ──────────────────────────────────────────
    Replace this function body with real API calls.
    Use NEWSAPI_KEY, SERPAPI_API_KEY from .env.
    All results → _save_article(fpath, content)
    ──────────────────────────────────────────────────────────
    """
    return fetch_mock_news()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _save_article(fpath: str, content: str) -> None:
    """Writes an article as .txt into news_inbox/."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(f"[Erstellt: {timestamp}]\n\n{content}\n")
