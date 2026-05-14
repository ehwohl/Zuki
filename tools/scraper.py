"""
scraper.py — Zentraler Web-Scraping-Layer für Zuki
────────────────────────────────────────────────────
Bietet HTTP-Fetching mit:
  - User-Agent-Rotation (Browser-Pool)
  - Rate-Limiting pro Domain (konfigurierbares Delay)
  - Disk-Cache mit TTL (verhindert doppelte Requests)
  - Quell-spezifische Adapter (Google Business, Instagram)

Status-API:
  get_status()  → dict    (Singleton-Status)
  self_test()   → dict    (für system_test: Subsystem "scraper")

Verwendbar von: Broker-Skill, Business-Skill, Office-Skill

ENV-Variablen:
  SCRAPER_CACHE_TTL    — Cache-Lebenszeit in Sekunden (Standard: 21600 = 6h)
  SCRAPER_RATE_DELAY   — Mindestabstand pro Domain in Sekunden (Standard: 2.0)
  SERPAPI_API_KEY      — Für GoogleBusinessAdapter (SerpAPI)
"""

import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from core.logger import get_logger

log = get_logger("scraper")

_ROOT      = Path(__file__).resolve().parent.parent
_CACHE_DIR = _ROOT / "temp" / "scraper_cache"
_ERROR_LOG = _ROOT / "logs" / "error.log"

_DEFAULT_TTL   = int(os.getenv("SCRAPER_CACHE_TTL",  str(6 * 3600)))
_DEFAULT_DELAY = float(os.getenv("SCRAPER_RATE_DELAY", "2.0"))

# ── Import: requests (optional, graceful degradation) ─────────────────────────

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _requests = None
    _REQUESTS_AVAILABLE = False

# ── User-Agent-Pool ────────────────────────────────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


# ── Fehler-Logging (analog api_manager.py) ────────────────────────────────────

def _write_error_log(context: str, exc: Exception) -> None:
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(_ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}]  scraper — {context}\n  {type(exc).__name__}: {exc}\n\n")
    except Exception:
        pass


def _friendly_error(context: str, exc: Exception) -> str:
    _write_error_log(context, exc)
    if "timeout" in str(exc).lower():
        return f"Zeitüberschreitung beim Laden — bitte später erneut versuchen"
    if "connection" in str(exc).lower():
        return f"Keine Verbindung — Netzwerk prüfen"
    return f"Fehler beim Abrufen — Details in logs/error.log"


# ══════════════════════════════════════════════════════════════════════════════
# ScraperCache — Disk-Cache mit TTL
# ══════════════════════════════════════════════════════════════════════════════

class ScraperCache:
    """
    JSON-basierter Disk-Cache in temp/scraper_cache/.
    Jeder Eintrag: { "ts": unix_timestamp, "content": str }
    """

    def __init__(self, ttl: int = _DEFAULT_TTL) -> None:
        self._ttl = ttl
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, key: str) -> "str | None":
        """Gibt gecachten Inhalt zurück, falls frisch. Sonst None."""
        path = self._key_to_path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            age = time.time() - entry["ts"]
            if age > self._ttl:
                log.debug(f"Cache abgelaufen ({int(age)}s): {key[:60]}")
                return None
            log.debug(f"Cache-Treffer ({int(age)}s alt): {key[:60]}")
            return entry["content"]
        except Exception as e:
            log.warning(f"Cache-Lesefehler: {e}")
            return None

    def set(self, key: str, content: str) -> None:
        """Speichert Inhalt im Cache."""
        path = self._key_to_path(key)
        try:
            entry = {"ts": time.time(), "content": content}
            path.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
            log.debug(f"Gecacht: {key[:60]}")
        except Exception as e:
            log.warning(f"Cache-Schreibfehler: {e}")

    def invalidate(self, key: str) -> bool:
        """Löscht einen Cache-Eintrag. Gibt True zurück wenn gefunden."""
        path = self._key_to_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear_expired(self) -> int:
        """Löscht alle abgelaufenen Einträge. Gibt Anzahl zurück."""
        removed = 0
        now = time.time()
        for p in _CACHE_DIR.glob("*.json"):
            try:
                entry = json.loads(p.read_text(encoding="utf-8"))
                if now - entry.get("ts", 0) > self._ttl:
                    p.unlink()
                    removed += 1
            except Exception:
                p.unlink()
                removed += 1
        return removed

    def clear_all(self) -> int:
        """Löscht alle Cache-Einträge."""
        removed = 0
        for p in _CACHE_DIR.glob("*.json"):
            p.unlink()
            removed += 1
        return removed

    def stats(self) -> dict:
        """Gibt Cache-Statistiken zurück."""
        now = time.time()
        total = 0
        fresh = 0
        for p in _CACHE_DIR.glob("*.json"):
            total += 1
            try:
                entry = json.loads(p.read_text(encoding="utf-8"))
                if now - entry.get("ts", 0) <= self._ttl:
                    fresh += 1
            except Exception:
                pass
        return {"total": total, "fresh": fresh, "expired": total - fresh, "ttl_seconds": self._ttl}

    # ── Intern ───────────────────────────────────────────────────────────────

    @staticmethod
    def _key_to_path(key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        safe = safe[:180]
        return _CACHE_DIR / f"{safe}.json"


# ══════════════════════════════════════════════════════════════════════════════
# Scraper — Kern-Engine
# ══════════════════════════════════════════════════════════════════════════════

class Scraper:
    """
    Zentraler HTTP-Fetcher mit UA-Rotation, Rate-Limiting und Cache.

    fetch(url)   → gecachten oder frischen HTML-Inhalt (str)
    get_status() → dict für Status-APIs
    self_test()  → dict für system_test
    """

    def __init__(
        self,
        ttl: int = _DEFAULT_TTL,
        rate_delay: float = _DEFAULT_DELAY,
        timeout: int = 15,
    ) -> None:
        self._cache       = ScraperCache(ttl=ttl)
        self._rate_delay  = rate_delay
        self._timeout     = timeout
        self._ua_index    = 0
        self._domain_last: dict[str, float] = {}
        self._total_fetched = 0
        self._total_cached  = 0
        self._errors        = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch(
        self,
        url: str,
        *,
        bypass_cache: bool = False,
        ttl: "int | None" = None,
    ) -> "str | None":
        """
        Lädt URL-Inhalt. Gibt gecachten Inhalt zurück wenn frisch.
        Gibt None zurück bei Fehler.
        """
        if not _REQUESTS_AVAILABLE:
            log.warning("requests nicht installiert — pip install requests")
            return None

        cache_key = url
        if not bypass_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._total_cached += 1
                return cached

        self._rate_limit(url)

        try:
            headers = {"User-Agent": self._next_ua()}
            resp = _requests.get(url, headers=headers, timeout=self._timeout)
            resp.raise_for_status()
            content = resp.text
            effective_ttl = ttl if ttl is not None else self._cache._ttl
            self._cache.set(cache_key, content) if effective_ttl > 0 else None
            self._total_fetched += 1
            log.info(f"Geladen ({resp.status_code}): {url[:80]}")
            return content
        except Exception as e:
            self._errors += 1
            _write_error_log(f"fetch({url[:60]})", e)
            log.warning(f"Fetch fehlgeschlagen: {url[:60]} — {e}")
            return None

    def fetch_json(
        self,
        url: str,
        *,
        params: "dict | None" = None,
        bypass_cache: bool = False,
    ) -> "dict | list | None":
        """
        Lädt URL als JSON. Params werden als Query-String angehängt.
        Cache-Key beinhaltet serialisierte Params.
        """
        if not _REQUESTS_AVAILABLE:
            log.warning("requests nicht installiert — pip install requests")
            return None

        import urllib.parse
        cache_key = url
        if params:
            cache_key += "?" + urllib.parse.urlencode(sorted(params.items()))

        if not bypass_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._total_cached += 1
                try:
                    return json.loads(cached)
                except Exception:
                    pass

        self._rate_limit(url)

        try:
            headers = {"User-Agent": self._next_ua()}
            resp = _requests.get(url, headers=headers, params=params, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
            self._cache.set(cache_key, json.dumps(data, ensure_ascii=False))
            self._total_fetched += 1
            log.info(f"JSON geladen ({resp.status_code}): {url[:80]}")
            return data
        except Exception as e:
            self._errors += 1
            _write_error_log(f"fetch_json({url[:60]})", e)
            log.warning(f"JSON-Fetch fehlgeschlagen: {url[:60]} — {e}")
            return None

    def get_status(self) -> dict:
        cache_stats = self._cache.stats()
        return {
            "available":     _REQUESTS_AVAILABLE,
            "requests_lib":  _REQUESTS_AVAILABLE,
            "total_fetched": self._total_fetched,
            "total_cached":  self._total_cached,
            "errors":        self._errors,
            "rate_delay":    self._rate_delay,
            "cache":         cache_stats,
        }

    def self_test(self) -> dict:
        """Schnell-Test ohne echte HTTP-Requests."""
        issues: list[str] = []

        if not _REQUESTS_AVAILABLE:
            issues.append("requests fehlt — pip install requests")

        if not _CACHE_DIR.exists():
            try:
                _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(f"Cache-Verzeichnis nicht erstellbar: {e}")

        serpapi_key = os.getenv("SERPAPI_API_KEY", "")
        serpapi_ok  = bool(serpapi_key) and not any(
            p in serpapi_key for p in ("your-", "placeholder", "key-here")
        )

        cache_stats = self._cache.stats()

        if issues:
            return {
                "status":   "fail",
                "summary":  f"Scraper: {issues[0]}",
                "fix_hint": " | ".join(issues),
            }

        lines = [f"requests: ok", f"Cache: {cache_stats['fresh']} frisch / {cache_stats['total']} gesamt"]
        if serpapi_ok:
            lines.append("SerpAPI: konfiguriert")
        else:
            lines.append("SerpAPI: kein Key (GoogleBusiness-Adapter im Stub-Modus)")

        return {
            "status":  "ok" if serpapi_ok else "warn",
            "summary": "  |  ".join(lines),
            "fix_hint": "" if serpapi_ok else "SERPAPI_API_KEY in .env eintragen für Google Business Profile Scraping",
        }

    # ── Intern ───────────────────────────────────────────────────────────────

    def _next_ua(self) -> str:
        ua = _USER_AGENTS[self._ua_index % len(_USER_AGENTS)]
        self._ua_index += 1
        return ua

    def _rate_limit(self, url: str) -> None:
        domain = urlparse(url).netloc or url
        last   = self._domain_last.get(domain, 0.0)
        wait   = self._rate_delay - (time.time() - last)
        if wait > 0:
            log.debug(f"Rate-Limit: {domain} — warte {wait:.1f}s")
            time.sleep(wait)
        self._domain_last[domain] = time.time()


# ══════════════════════════════════════════════════════════════════════════════
# GoogleBusinessAdapter — SerpAPI-Integration
# ══════════════════════════════════════════════════════════════════════════════

class GoogleBusinessAdapter:
    """
    Sucht Google Business Profile-Daten via SerpAPI.
    Gibt strukturiertes dict zurück mit: name, address, rating, reviews, hours,
    phone, website, categories, local_results.

    ── LIVE UPGRADE ──────────────────────────────────────────────────────────
    Benötigt: SERPAPI_API_KEY in .env
    SerpAPI-Endpunkt: https://serpapi.com/search.json
    Engine: "google_maps" für Place-Details, "google_local" für Radius-Suche

    Beispiel — Einzelnes Profil laden:
      params = {
          "engine": "google_maps",
          "q": f"{name} {address}",
          "type": "search",
          "api_key": SERPAPI_API_KEY,
      }
      data = scraper.fetch_json("https://serpapi.com/search.json", params=params)
      place = data.get("place_results", {})

    Beispiel — Konkurrenz im Radius:
      params = {
          "engine": "google_maps",
          "q": "Restaurant",
          "ll": "@lat,lng,15z",
          "type": "search",
          "api_key": SERPAPI_API_KEY,
      }
    ──────────────────────────────────────────────────────────────────────────
    """

    _SERPAPI_BASE = "https://serpapi.com/search.json"

    def __init__(self, scraper: "Scraper | None" = None) -> None:
        self._scraper  = scraper or get_scraper()
        # BUSINESS_SERPAPI_KEY hat Vorrang, Fallback auf SERPAPI_API_KEY
        self._api_key  = os.getenv("BUSINESS_SERPAPI_KEY", "") or os.getenv("SERPAPI_API_KEY", "")
        self._key_ok   = bool(self._api_key) and "your-" not in self._api_key

    def available(self) -> bool:
        return self._key_ok and _REQUESTS_AVAILABLE

    def search_place(self, query: str) -> "dict | None":
        """
        Sucht einen Ort per Name/Adresse.
        Gibt place_results-dict zurück oder None (Stub/Fehler).

        ── STUB — kein API-Key konfiguriert ──────────────────────────────────
        """
        if not self._key_ok:
            log.debug("GoogleBusinessAdapter: Stub — SERPAPI_API_KEY nicht konfiguriert")
            return self._stub_place(query)

        # ── LIVE ──────────────────────────────────────────────────────────────
        params = {
            "engine":  "google_maps",
            "q":       query,
            "type":    "search",
            "api_key": self._api_key,
        }
        data = self._scraper.fetch_json(self._SERPAPI_BASE, params=params)
        if data is None:
            return None
        return data.get("place_results") or (data.get("local_results") or [{}])[0]

    def search_radius(self, query: str, lat: float, lng: float, zoom: int = 15) -> "list[dict]":
        """
        Sucht Orte in Radius (via Google Maps local search).
        Gibt Liste von local_results zurück.

        ── STUB — kein API-Key konfiguriert ──────────────────────────────────
        """
        if not self._key_ok:
            log.debug("GoogleBusinessAdapter: Stub — SERPAPI_API_KEY nicht konfiguriert")
            return self._stub_radius(query)

        # ── LIVE ──────────────────────────────────────────────────────────────
        params = {
            "engine":  "google_maps",
            "q":       query,
            "ll":      f"@{lat},{lng},{zoom}z",
            "type":    "search",
            "api_key": self._api_key,
        }
        data = self._scraper.fetch_json(self._SERPAPI_BASE, params=params)
        if data is None:
            return []
        return data.get("local_results", [])

    # ── Stub-Daten ────────────────────────────────────────────────────────────

    @staticmethod
    def _stub_place(query: str) -> dict:
        return {
            "_stub": True,
            "name": f"[Stub] {query}",
            "address": "Musterstraße 1, 12345 Musterstadt",
            "rating": 4.2,
            "reviews": 87,
            "phone": "+49 30 12345678",
            "website": "https://example.com",
            "hours": {"Mo-Fr": "09:00-22:00", "Sa-So": "10:00-23:00"},
            "categories": ["Restaurant", "Gastronomie"],
            "description": "Gemütliches Restaurant in bester Lage.",
            "price_range": "€€",
            "menu_link": "",
            "booking_link": "",
            "service_options": {"dine_in": True, "takeout": False, "delivery": False},
            "images": [],           # 0 Fotos → Schwachstelle erkennbar
            "owner_updates": [],    # keine Posts → Schwachstelle erkennbar
        }

    @staticmethod
    def _stub_radius(query: str) -> list:
        return [
            {"_stub": True, "name": f"[Stub] {query} — Konkurrent A", "rating": 4.5, "reviews": 210},
            {"_stub": True, "name": f"[Stub] {query} — Konkurrent B", "rating": 3.8, "reviews": 54},
            {"_stub": True, "name": f"[Stub] {query} — Konkurrent C", "rating": 4.1, "reviews": 132},
        ]


# ══════════════════════════════════════════════════════════════════════════════
# InstagramPublicAdapter — Öffentliche Profil-Daten
# ══════════════════════════════════════════════════════════════════════════════

class InstagramPublicAdapter:
    """
    Liest öffentliche Instagram-Profil-Metadaten.

    ── LIVE UPGRADE ──────────────────────────────────────────────────────────
    Option A — Instagram Basic Display API (OAuth):
      POST https://api.instagram.com/oauth/access_token
      GET  https://graph.instagram.com/me?fields=id,username,media_count
           &access_token={token}
      Benötigt: INSTAGRAM_ACCESS_TOKEN in .env

    Option B — Öffentlicher Scraper (kein Token, instabil):
      url  = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
      html = scraper.fetch(url)
      data = json.loads(html)  # funktioniert nur ohne Login-Gate

    Empfehlung: Option A für Production, Option B nur für Tests.
    ──────────────────────────────────────────────────────────────────────────
    """

    def __init__(self, scraper: "Scraper | None" = None) -> None:
        self._scraper = scraper or get_scraper()
        self._token   = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        self._token_ok = bool(self._token) and "your-" not in self._token

    def available(self) -> bool:
        return self._token_ok and _REQUESTS_AVAILABLE

    def get_profile(self, username: str) -> "dict | None":
        """
        Gibt öffentliche Profil-Daten zurück.
        Aktuell: Stub-Modus (kein Token konfiguriert).

        ── STUB ──────────────────────────────────────────────────────────────
        """
        if not self._token_ok:
            log.debug(f"InstagramAdapter: Stub — kein INSTAGRAM_ACCESS_TOKEN")
            return self._stub_profile(username)

        # ── LIVE (Option A — Basic Display API) ───────────────────────────────
        data = self._scraper.fetch_json(
            "https://graph.instagram.com/me",
            params={"fields": "id,username,media_count,account_type", "access_token": self._token},
        )
        return data

    def get_recent_posts(self, username: str, limit: int = 12) -> list:
        """
        Gibt letzte Posts zurück (Zeitstempel, Caption, Like-Count).
        Aktuell: Stub-Modus.

        ── STUB ──────────────────────────────────────────────────────────────
        """
        if not self._token_ok:
            return self._stub_posts(username, limit)

        # ── LIVE ──────────────────────────────────────────────────────────────
        data = self._scraper.fetch_json(
            "https://graph.instagram.com/me/media",
            params={
                "fields": "id,timestamp,caption,media_type,like_count",
                "limit":  str(limit),
                "access_token": self._token,
            },
        )
        if data is None:
            return []
        return data.get("data", [])

    # ── Stub-Daten ────────────────────────────────────────────────────────────

    @staticmethod
    def _stub_profile(username: str) -> dict:
        return {
            "_stub": True,
            "username":     username,
            "followers":    342,
            "following":    89,
            "posts":        47,
            "bio":          "[Stub] Kein INSTAGRAM_ACCESS_TOKEN konfiguriert",
            "last_post":    "2026-04-28",
        }

    @staticmethod
    def _stub_posts(username: str, limit: int) -> list:
        return [
            {
                "_stub":     True,
                "timestamp": "2026-04-28T12:00:00",
                "caption":   f"[Stub] Post von @{username}",
                "likes":     23,
            }
        ] * min(limit, 3)


# ══════════════════════════════════════════════════════════════════════════════
# Modul-Level-Singleton + Adapter-Factory
# ══════════════════════════════════════════════════════════════════════════════

_instance: "Scraper | None" = None


def get_scraper() -> Scraper:
    """Gibt den Singleton-Scraper zurück (lazy init)."""
    global _instance
    if _instance is None:
        _instance = Scraper()
        log.debug("Scraper-Singleton initialisiert")
    return _instance


def get_google_business_adapter() -> GoogleBusinessAdapter:
    """Gibt einen GoogleBusinessAdapter mit Singleton-Scraper zurück."""
    return GoogleBusinessAdapter(scraper=get_scraper())


def get_instagram_adapter() -> InstagramPublicAdapter:
    """Gibt einen InstagramPublicAdapter mit Singleton-Scraper zurück."""
    return InstagramPublicAdapter(scraper=get_scraper())


# ── Modul-Level Status-API (für system_test ohne Instanz-Übergabe) ─────────────

def get_status() -> dict:
    return get_scraper().get_status()


def self_test() -> dict:
    return get_scraper().self_test()
