import json
import os
import random
from datetime import date

from core.logger import get_logger

log = get_logger("news")

_BROKER   = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "skills", "broker"
))
INBOX              = os.path.join(_BROKER, "news_inbox")
WATCHLIST          = os.path.join(_BROKER, "watchlist.txt")
SENTIMENT_KEYWORDS = os.path.join(_BROKER, "sentiment_keywords.json")

REPORT_TRIGGERS = {"report", "auswertung"}

# Sentiment labels with ANSI colours (used by ui layer too)
LABEL = {
    "POS": "\033[92m[POS]\033[0m",
    "NEG": "\033[91m[NEG]\033[0m",
    "NEU": "\033[90m[NEU]\033[0m",
}


class NewsManager:
    """
    Broker skill — scans news_inbox/ for today's articles,
    matches watchlist, scores sentiment, prioritises in report.

    Sentiment strategy:
      SIM  → keyword scoring (this file)
      LIVE → swap _analyze_sentiment() for an API call (see placeholder below)
    """

    def __init__(self):
        self._articles:  list[dict] = []
        self._watchlist: list[str]  = []
        self._keywords:  dict       = {"positive": [], "negative": []}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def scan(self) -> int:
        """Load watchlist, keywords, today's articles. Returns count."""
        self._watchlist = self._load_watchlist()
        self._keywords  = self._load_keywords()
        today = date.today().isoformat()
        self._articles  = []
        os.makedirs(INBOX, exist_ok=True)

        for fname in sorted(os.listdir(INBOX)):
            if not fname.endswith(".txt"):
                continue
            fpath = os.path.join(INBOX, fname)
            mtime_date = date.fromtimestamp(os.path.getmtime(fpath)).isoformat()
            if not (fname.startswith(today) or mtime_date == today):
                continue
            try:
                with open(fpath, encoding="utf-8") as f:
                    content = f.read().strip()
                if not content:
                    continue
                hits      = self._watchlist_hits(content)
                score     = self._analyze_sentiment(content)
                sentiment = self._score_to_label(score)
                self._articles.append({
                    "filename":  fname,
                    "content":   content,
                    "hits":      hits,
                    "priority":  bool(hits),
                    "score":     score,
                    "sentiment": sentiment,   # "POS" | "NEG" | "NEU"
                })
            except OSError as e:
                log.warning(f"News-Datei nicht lesbar: {fpath} — {e}")

        log.info(
            f"Scan: {len(self._articles)} Artikel | "
            f"{self.watchlist_hits} Watchlist-Treffer | "
            f"Tendenz: {self.overall_sentiment}"
        )
        return len(self._articles)

    @property
    def count(self) -> int:
        return len(self._articles)

    @property
    def has_news(self) -> bool:
        return bool(self._articles)

    @property
    def watchlist_hits(self) -> int:
        return sum(1 for a in self._articles if a["priority"])

    @property
    def overall_sentiment(self) -> str:
        """Aggregated sentiment across all articles."""
        if not self._articles:
            return "NEU"
        total = sum(a["score"] for a in self._articles)
        return self._score_to_label(total)

    def is_report_trigger(self, text: str) -> bool:
        return text.strip().lower() in REPORT_TRIGGERS

    def build_prompt(self) -> str:
        """Prioritised API prompt: watchlist hits first, sentiment annotated."""
        if not self._articles:
            return ""
        priority = [a for a in self._articles if a["priority"]]
        general  = [a for a in self._articles if not a["priority"]]
        sections = []
        if priority:
            sections.append("=== WATCHLIST-TREFFER (priorität) ===")
            for a in priority:
                sections.append(
                    f"[{a['filename']} | Treffer: {', '.join(a['hits'])} | "
                    f"Sentiment: {a['sentiment']}]\n{a['content']}"
                )
        if general:
            sections.append("=== ALLGEMEINE NEWS ===")
            for a in general:
                sections.append(
                    f"[{a['filename']} | Sentiment: {a['sentiment']}]\n{a['content']}"
                )
        header = (
            f"Fasse die folgenden {len(self._articles)} News-Artikel "
            f"vom {date.today().isoformat()} zusammen. "
            f"Gesamttendenz: {self.overall_sentiment}. "
            f"Watchlist-Treffer zuerst:\n\n"
        )
        return header + "\n---\n".join(sections)

    def build_sim_report(self) -> str:
        """Simulation report with coloured sentiment labels."""
        if not self._articles:
            return "[SIM] Keine Artikel für heute gefunden."

        priority = [a for a in self._articles if a["priority"]]
        general  = [a for a in self._articles if not a["priority"]]
        lines    = [f"[SIM] Auswertung — {self.count} Artikel | Tendenz: {LABEL[self.overall_sentiment]}\n"]

        if priority:
            lines.append("── WATCHLIST-TREFFER ──")
            for a in priority:
                label = LABEL[a["sentiment"]]
                terms = ", ".join(a["hits"])
                lines.append(f"{label} [{terms}]  {a['filename']}")
                lines.append(a["content"])
                lines.append("")

        if general:
            lines.append("── ALLGEMEINE NEWS ──")
            for a in general:
                label = LABEL[a["sentiment"]]
                lines.append(f"{label}  {a['filename']}")
                lines.append(a["content"])
                lines.append("")

        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # Sentiment — swap this method for AI call when LIVE
    # ------------------------------------------------------------------

    def _analyze_sentiment(self, text: str) -> int:
        """
        Keyword-based sentiment score.
        ─────────────────────────────────────────────────────────────
        LIVE UPGRADE: replace this method body with an API call, e.g.:
            response = llm.chat([{"role": "user",
                "content": f"Rate sentiment -1/0/1: {text[:300]}"}])
            return int(response.strip())
        ─────────────────────────────────────────────────────────────
        """
        lower = text.lower()
        pos = sum(1 for w in self._keywords["positive"] if w in lower)
        neg = sum(1 for w in self._keywords["negative"] if w in lower)
        return pos - neg

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_label(score: int) -> str:
        if score > 0:
            return "POS"
        if score < 0:
            return "NEG"
        return "NEU"

    def _watchlist_hits(self, text: str) -> list[str]:
        lower = text.lower()
        return [t for t in self._watchlist if t.lower() in lower]

    def _load_watchlist(self) -> list[str]:
        if not os.path.exists(WATCHLIST):
            log.debug("watchlist.txt nicht gefunden")
            return []
        try:
            with open(WATCHLIST, encoding="utf-8") as f:
                return [l.strip() for l in f if l.strip()]
        except OSError as e:
            log.warning(f"Watchlist Lesefehler: {e}")
            return []

    def _load_keywords(self) -> dict:
        if not os.path.exists(SENTIMENT_KEYWORDS):
            log.debug("sentiment_keywords.json nicht gefunden — Scoring deaktiviert")
            return {"positive": [], "negative": []}
        try:
            with open(SENTIMENT_KEYWORDS, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            log.warning(f"Sentiment-Keywords Lesefehler: {e} — Scoring deaktiviert")
            return {"positive": [], "negative": []}
