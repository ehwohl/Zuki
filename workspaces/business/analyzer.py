"""
analyzer.py — Gastro analysis engine
──────────────────────────────────────
Collects data (Google Business, Instagram, competition),
detects weaknesses from knowledge/gastro.yaml and
prepares everything for the PDF report.

Classes:
  AnalysisResult  — Dataclass with all analysis results
  GastroAnalyzer  — Runs the analysis

Status API:
  GastroAnalyzer.last_result() → AnalysisResult | None
  GastroAnalyzer.to_report_data(result) → dict for build_analyse_report()

Log markers: [BUSINESS-ANALYSE], [BUSINESS-SCHWACHSTELLE]
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.logger import get_logger

log = get_logger("business.analyzer")

_ROOT = Path(__file__).resolve().parent.parent.parent


# ══════════════════════════════════════════════════════════════════════════════
# AnalysisResult — result of one analysis run
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AnalysisResult:
    query:             str
    name:              str               = ""
    address:           str               = ""
    rating:            float             = 0.0
    review_count:      int               = 0
    phone:             str               = ""
    website:           str               = ""
    categories:        list              = field(default_factory=list)
    hours:             dict              = field(default_factory=dict)
    competitors:       list              = field(default_factory=list)   # list[dict]
    instagram_handle:  str               = ""
    instagram_data:    dict              = field(default_factory=dict)
    # ── Extended SerpAPI fields ──────────────────────────────────────────────
    photos_count:      int               = -1   # -1 = unknown
    menu_link:         str               = ""
    booking_link:      str               = ""
    service_options:   dict              = field(default_factory=dict)  # delivery/takeout/dine_in
    price_range:       str               = ""
    description:       str               = ""
    owner_updates:     int               = -1   # -1 = unknown, 0+ = number of posts
    competitors_count: int               = 0
    pagespeed_score:   int               = -1   # -1 = not checked
    # ────────────────────────────────────────────────────────────────────────
    weaknesses_found:  list              = field(default_factory=list)   # list[dict] from gastro.yaml
    kpi_snapshot:      list              = field(default_factory=list)   # list[(label, actual, target)]
    score:             int               = 0   # 0-100, higher = better
    stub_mode:         bool              = True
    analyzed_at:       str               = ""

    def __post_init__(self) -> None:
        if not self.analyzed_at:
            self.analyzed_at = datetime.now().strftime("%d.%m.%Y %H:%M")


# ══════════════════════════════════════════════════════════════════════════════
# GastroAnalyzer
# ══════════════════════════════════════════════════════════════════════════════

class GastroAnalyzer:
    """
    Runs a digital weakness analysis for a gastro business.

    run(query) → AnalysisResult
      1. Load Google Business Profile (via GoogleBusinessAdapter)
      2. Load nearby competition (stub: 3 entries)
      3. Load Instagram data if handle is detectable
      4. Check weaknesses from knowledge/gastro.yaml against data
      5. Calculate score (0-100)
    """

    def __init__(self) -> None:
        self._last: AnalysisResult | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, query: str) -> AnalysisResult:
        log.info(f"[BUSINESS-ANALYSE] Start: '{query}'")
        result = AnalysisResult(query=query)

        # 1. Google Business Profile
        place = self._fetch_place(query)
        self._apply_place(result, place)

        # 2. Nearby competition
        result.competitors       = self._fetch_competitors(query, place)
        result.competitors_count = len(result.competitors)

        # 2b. PageSpeed (only if website present, runs in background)
        if result.website:
            result.pagespeed_score = self._fetch_pagespeed(result.website)

        # 3. Instagram (if handle detectable from website or name)
        handle = self._guess_instagram_handle(result)
        if handle:
            result.instagram_handle = handle
            result.instagram_data   = self._fetch_instagram(handle)

        # 4. Detect weaknesses
        result.weaknesses_found = self._detect_weaknesses(result)

        # 5. KPI snapshot
        result.kpi_snapshot = self._build_kpi_snapshot(result)

        # 6. Score
        result.score = self._calc_score(result)

        self._last = result
        log.info(
            f"[BUSINESS-ANALYSE] Done: {result.name}  "
            f"Score={result.score}  Weaknesses={len(result.weaknesses_found)}  "
            f"stub={result.stub_mode}"
        )
        return result

    def last_result(self) -> "AnalysisResult | None":
        return self._last

    def to_report_data(self, result: AnalysisResult) -> dict:
        """
        Prepares AnalysisResult as kwargs dict for build_analyse_report().
        """
        findings = [
            f"{w['title']} — {w['description'][:120].rstrip()}..."
            for w in result.weaknesses_found
        ]

        recommendations = self._build_recommendations(result)

        kpis = [
            (label, ist, ziel)
            for label, ist, ziel in result.kpi_snapshot
        ]

        next_steps = self._build_next_steps(result)

        stub_note = (
            "⚠️  Diese Analyse basiert auf Beispiel-Daten (SerpAPI-Key nicht konfiguriert). "
            "Für echte Ergebnisse SERPAPI_API_KEY in .env eintragen."
            if result.stub_mode else ""
        )

        return dict(
            client_name    = result.name or result.query,
            client_address = result.address,
            findings       = findings or ["Keine Schwachstellen erkannt — alle Bereiche unauffällig."],
            recommendations= recommendations,
            kpis           = kpis,
            next_steps     = next_steps,
            notes          = stub_note,
        )

    # ── Data fetch ────────────────────────────────────────────────────────────

    def _fetch_place(self, query: str) -> dict:
        try:
            from tools.scraper import get_google_business_adapter
            adapter = get_google_business_adapter()
            place   = adapter.search_place(query) or {}
            return place
        except Exception as e:
            log.warning(f"[BUSINESS-ANALYSE] Google fetch error: {e}")
            return {}

    def _fetch_competitors(self, query: str, place: dict) -> list:
        try:
            from tools.scraper import get_google_business_adapter
            adapter = get_google_business_adapter()
            # Coordinates from place if available (live: lat/lng)
            lat = place.get("gps_coordinates", {}).get("latitude", 52.5200)
            lng = place.get("gps_coordinates", {}).get("longitude", 13.4050)
            return adapter.search_radius("Restaurant", lat, lng)
        except Exception as e:
            log.warning(f"[BUSINESS-ANALYSE] Competition fetch error: {e}")
            return []

    def _fetch_instagram(self, handle: str) -> dict:
        try:
            from tools.scraper import get_instagram_adapter
            adapter = get_instagram_adapter()
            return adapter.get_profile(handle) or {}
        except Exception as e:
            log.warning(f"[BUSINESS-ANALYSE] Instagram fetch error: {e}")
            return {}

    def _fetch_pagespeed(self, url: str) -> int:
        """
        Fetches Google PageSpeed Insights mobile score (0-100).
        Free, no API key required. Returns -1 on error.
        """
        try:
            import urllib.request
            import json as _json
            api = (
                "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
                f"?url={urllib.request.quote(url, safe='')}&strategy=mobile&category=performance"
            )
            with urllib.request.urlopen(api, timeout=12) as resp:
                data = _json.loads(resp.read())
            score = (
                data.get("lighthouseResult", {})
                    .get("categories", {})
                    .get("performance", {})
                    .get("score")
            )
            if score is not None:
                result = int(score * 100)
                log.info(f"[BUSINESS-ANALYSE] PageSpeed mobile: {result}/100")
                return result
        except Exception as e:
            log.debug(f"[BUSINESS-ANALYSE] PageSpeed not available: {e}")
        return -1

    # ── Data mapping ──────────────────────────────────────────────────────────

    def _apply_place(self, result: AnalysisResult, place: dict) -> None:
        # SerpAPI delivers "title", stub data uses "name" — handle both
        result.name         = place.get("title") or place.get("name") or result.query
        result.address      = place.get("address", "")
        result.rating       = float(place.get("rating", 0.0) or 0.0)
        result.review_count = int(place.get("reviews", 0) or 0)
        result.phone        = place.get("phone", "")
        result.website      = place.get("website", "")
        result.categories   = place.get("type", place.get("categories", []))
        result.hours        = place.get("hours", {})
        result.description  = place.get("description", "") or ""
        result.price_range  = place.get("price_range", "") or ""
        result.menu_link    = place.get("menu_link", "") or ""
        result.booking_link = place.get("booking_link", "") or place.get("reservation_link", "") or ""
        result.service_options = place.get("service_options", {}) or {}
        # Photos: SerpAPI delivers either a list or a count
        imgs = place.get("images") or place.get("photos") or []
        result.photos_count = len(imgs) if isinstance(imgs, list) else int(imgs or -1)
        # Owner posts
        updates = place.get("owner_updates") or place.get("posts") or []
        result.owner_updates = len(updates) if isinstance(updates, list) else int(updates or -1)
        # stub_mode only True when _stub explicitly set (stub fallback)
        result.stub_mode    = place.get("_stub") is True

    def _guess_instagram_handle(self, result: AnalysisResult) -> str:
        # Derive from website URL if instagram.com is in it
        site = result.website.lower()
        if "instagram.com/" in site:
            parts = site.split("instagram.com/")
            if len(parts) > 1:
                return parts[1].strip("/").split("/")[0]
        # Simple heuristic: name without special chars as handle candidate
        name_slug = "".join(
            c for c in result.name.lower().replace(" ", "_")
            if c.isalnum() or c == "_"
        )
        return name_slug if len(name_slug) >= 3 else ""

    # ── Weakness detection ────────────────────────────────────────────────────

    def _detect_weaknesses(self, result: AnalysisResult) -> list:
        """
        Checks detected weaknesses from knowledge/gastro.yaml
        against the available data. Returns list of found weaknesses.
        """
        from knowledge.loader import get_knowledge_base
        kb = get_knowledge_base()
        all_weaknesses = kb.get_weaknesses("gastro")
        found = []

        for w in all_weaknesses:
            wid = w.get("id", "")
            if self._check_weakness(wid, result):
                found.append(w)
                log.info(f"[BUSINESS-SCHWACHSTELLE] {wid} detected ({w.get('severity','?')})")

        # Sort: high → medium → low
        severity_order = {"hoch": 0, "mittel": 1, "niedrig": 2}
        found.sort(key=lambda w: severity_order.get(w.get("severity", "niedrig"), 2))
        return found

    def _check_weakness(self, weakness_id: str, r: AnalysisResult) -> bool:
        """Returns True if the weakness is detectable from the data."""

        if weakness_id == "keine_bewertungsantworten":
            response_rate = r.instagram_data.get("response_rate_pct", None)
            if response_rate is not None:
                return response_rate < 80
            # Heuristic: few reviews → response rate unknown → warn
            return r.review_count < 50

        if weakness_id == "niedrige_bewertungsanzahl":
            return 0 < r.review_count < 50

        if weakness_id == "schlechte_bewertung":
            return 0 < r.rating < 4.0

        if weakness_id == "keine_online_reservierung":
            return not r.booking_link

        if weakness_id == "veraltete_speisekarte":
            return not r.menu_link

        if weakness_id == "fehlendes_google_profil":
            # Weakness if 3 or more fields missing
            missing = sum([
                not r.phone,
                not r.website,
                not r.address,
                not r.hours,
                r.review_count == 0,
                r.photos_count == 0,
                not r.description,
                not r.price_range,
            ])
            return missing >= 3

        if weakness_id == "inaktive_social_media":
            ig = r.instagram_data
            if ig:
                posts_per_week = ig.get("posts_per_week", None)
                if posts_per_week is not None:
                    return posts_per_week < 1
            # No Instagram handle detected → no social presence
            return not r.instagram_handle

        if weakness_id == "kein_lieferdienst":
            svc = r.service_options
            if svc:
                return not svc.get("delivery", False)
            return False  # unknown → no false positive

        if weakness_id == "keine_seo_website":
            return not r.website

        if weakness_id == "kein_newsletter":
            # Not automatically detectable — always flag as hint
            return True

        return False

    # ── KPI snapshot ──────────────────────────────────────────────────────────

    def _build_kpi_snapshot(self, result: AnalysisResult) -> list:
        """Returns list[(label, actual_value, target_value)]."""
        from knowledge.loader import get_knowledge_base
        kb   = get_knowledge_base()
        kpis = kb.get_kpis("gastro")
        rows = []

        for kpi in kpis:
            kid    = kpi.get("id", "")
            label  = kpi.get("label", "")
            target = kpi.get("target", "?")
            ist    = self._get_kpi_ist(kid, result)
            if ist is not None:
                rows.append((label, str(ist), target))

        return rows

    def _get_kpi_ist(self, kpi_id: str, r: AnalysisResult) -> "str | None":
        if kpi_id == "bewertungs_schnitt":
            return f"{r.rating:.1f} ⭐" if r.rating else "unbekannt"
        if kpi_id == "bewertungs_anzahl":
            return str(r.review_count) if r.review_count else "0"
        if kpi_id == "antwortrate":
            rate = r.instagram_data.get("response_rate_pct")
            return f"{rate}%" if rate else "nicht erfasst"
        if kpi_id == "post_frequenz":
            ppw = r.instagram_data.get("posts_per_week")
            return f"{ppw:.1f}/Woche" if ppw is not None else "nicht erfasst"
        if kpi_id == "profil_vollstaendigkeit":
            fields = [
                bool(r.phone), bool(r.website), bool(r.address),
                bool(r.hours), bool(r.categories), r.review_count > 0,
                r.photos_count > 0, bool(r.description), bool(r.price_range),
            ]
            pct = int(sum(fields) / len(fields) * 100)
            return f"{pct}%"
        if kpi_id == "website_mobile":
            if r.pagespeed_score >= 0:
                return f"{r.pagespeed_score}/100"
            return "nicht geprüft" if r.website else "keine Website"
        if kpi_id == "fotos_anzahl":
            return str(r.photos_count) if r.photos_count >= 0 else "unbekannt"
        if kpi_id == "menu_vorhanden":
            return "ja" if r.menu_link else "nein"
        if kpi_id == "buchung_vorhanden":
            return "ja" if r.booking_link else "nein"
        if kpi_id == "lieferung_aktiviert":
            svc = r.service_options
            if not svc:
                return "unbekannt"
            parts = []
            if svc.get("delivery"):   parts.append("Lieferung")
            if svc.get("takeout"):    parts.append("Abholung")
            if svc.get("dine_in"):    parts.append("Vor Ort")
            return ", ".join(parts) if parts else "nein"
        if kpi_id == "preis_erfasst":
            return r.price_range if r.price_range else "nicht gesetzt"
        if kpi_id == "google_posts_aktiv":
            if r.owner_updates >= 0:
                return f"{r.owner_updates} Posts" if r.owner_updates else "keine"
            return "unbekannt"
        if kpi_id == "konkurrenz_dichte":
            return f"{r.competitors_count} im Umkreis"
        if kpi_id == "lieferdienst_rating":
            return "nicht erfasst"
        if kpi_id == "tripadvisor_rang":
            return "nicht erfasst"
        return None

    # ── Score ─────────────────────────────────────────────────────────────────

    def _calc_score(self, result: AnalysisResult) -> int:
        """
        Simple score 0-100 based on detected problems.
        Starts at 100, deducts per weakness severity.
        """
        score = 100
        deductions = {"hoch": 20, "mittel": 10, "niedrig": 5}
        for w in result.weaknesses_found:
            score -= deductions.get(w.get("severity", "niedrig"), 5)
        return max(0, min(100, score))

    # ── Recommendations + next steps ──────────────────────────────────────────

    def _build_recommendations(self, result: AnalysisResult) -> list:
        """Returns list[(measure, priority, cost)]."""
        from knowledge.loader import get_knowledge_base
        kb    = get_knowledge_base()
        tools = kb.get_tools("gastro")

        # Map weaknesses to tool recommendations
        tool_map = {
            "keine_bewertungsantworten":  "Google Business Profile",
            "niedrige_bewertungsanzahl":  "Google Business Profile",
            "schlechte_bewertung":        "SurveyMonkey / Typeform",
            "keine_online_reservierung":  "TheFork (ehemals Lafourchette)",
            "inaktive_social_media":      "Later / Buffer",
            "fehlendes_google_profil":    "Google Business Profile",
            "keine_seo_website":          "Google Business Profile",
            "kein_newsletter":            "Mailchimp",
        }

        seen: set = set()
        recs = []
        for w in result.weaknesses_found:
            wid      = w.get("id", "")
            tool_name = tool_map.get(wid)
            if tool_name and tool_name not in seen:
                seen.add(tool_name)
                tool = next((t for t in tools if t["name"] == tool_name), None)
                cost = tool["cost"] if tool else "variabel"
                prio = "Hoch" if w.get("severity") == "hoch" else "Mittel"
                recs.append((f"{w['title']} → {tool_name}", prio, cost))

        return recs[:8]  # max 8 rows in report

    def _build_next_steps(self, result: AnalysisResult) -> list:
        steps = []
        has_ids = {w["id"] for w in result.weaknesses_found}

        if "fehlendes_google_profil" in has_ids:
            steps.append("Google Business Profile vollständig ausfüllen (Öffnungszeiten, Fotos, Speisekarte)")
        if "keine_bewertungsantworten" in has_ids or "niedrige_bewertungsanzahl" in has_ids:
            steps.append("QR-Code mit Google-Bewertungslink am Tisch und auf Kassenbons platzieren")
            steps.append("Alle offenen Bewertungen innerhalb 48h beantworten — Google priorisiert aktive Profile")
        if "keine_online_reservierung" in has_ids:
            steps.append("Online-Reservierungssystem einrichten (TheFork oder direkte Google-Buchung)")
        if "inaktive_social_media" in has_ids:
            steps.append("Social-Media-Kalender erstellen: min. 3 Posts/Woche (Tagesgericht, Behind-the-Scenes, Aktionen)")
        if "kein_newsletter" in has_ids:
            steps.append("Mailchimp-Newsletter aufsetzen für Stammgäste-Bindung (Aktionen, Events)")
        if not steps:
            steps.append("Regelmäßige Pflege aller Online-Profile beibehalten")
            steps.append("Bewertungsschnitt über 4.5 Sterne anstreben durch aktive Gäste-Einladung")

        steps.append("Praxistest: Analyse nach 90 Tagen wiederholen um Fortschritt zu messen")
        return steps
