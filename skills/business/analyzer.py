"""
analyzer.py — Gastro-Analyse-Engine
─────────────────────────────────────
Sammelt Daten (Google Business, Instagram, Konkurrenz),
erkennt Schwachstellen aus knowledge/gastro.yaml und
bereitet alles für den PDF-Report vor.

Klassen:
  AnalysisResult  — Dataclass mit allen Analyse-Ergebnissen
  GastroAnalyzer  — Führt die Analyse durch

Status-API:
  GastroAnalyzer.last_result() → AnalysisResult | None
  GastroAnalyzer.to_report_data(result) → dict für build_analyse_report()

Log-Marker: [BUSINESS-ANALYSE], [BUSINESS-SCHWACHSTELLE]
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.logger import get_logger

log = get_logger("business.analyzer")

_ROOT = Path(__file__).resolve().parent.parent.parent


# ══════════════════════════════════════════════════════════════════════════════
# AnalysisResult — Ergebnis einer Analyse
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
    weaknesses_found:  list              = field(default_factory=list)   # list[dict] aus gastro.yaml
    kpi_snapshot:      list              = field(default_factory=list)   # list[(label, ist, ziel)]
    score:             int               = 0   # 0-100, höher = besser
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
    Führt eine digitale Schwachstellen-Analyse für ein Gastro-Betrieb durch.

    run(query) → AnalysisResult
      1. Google Business Profile laden (via GoogleBusinessAdapter)
      2. Konkurrenz im Umkreis laden (Stub: 3 Einträge)
      3. Instagram-Daten laden falls Handle erkennbar
      4. Schwachstellen aus knowledge/gastro.yaml gegen Daten prüfen
      5. Score berechnen (0-100)
    """

    def __init__(self) -> None:
        self._last: AnalysisResult | None = None

    # ── Öffentliche API ───────────────────────────────────────────────────────

    def run(self, query: str) -> AnalysisResult:
        log.info(f"[BUSINESS-ANALYSE] Start: '{query}'")
        result = AnalysisResult(query=query)

        # 1. Google Business Profile
        place = self._fetch_place(query)
        self._apply_place(result, place)

        # 2. Konkurrenz im Umkreis
        result.competitors = self._fetch_competitors(query, place)

        # 3. Instagram (falls Handle in Website oder Name erkennbar)
        handle = self._guess_instagram_handle(result)
        if handle:
            result.instagram_handle = handle
            result.instagram_data   = self._fetch_instagram(handle)

        # 4. Schwachstellen erkennen
        result.weaknesses_found = self._detect_weaknesses(result)

        # 5. KPI-Snapshot
        result.kpi_snapshot = self._build_kpi_snapshot(result)

        # 6. Score
        result.score = self._calc_score(result)

        self._last = result
        log.info(
            f"[BUSINESS-ANALYSE] Fertig: {result.name}  "
            f"Score={result.score}  Schwachstellen={len(result.weaknesses_found)}  "
            f"stub={result.stub_mode}"
        )
        return result

    def last_result(self) -> "AnalysisResult | None":
        return self._last

    def to_report_data(self, result: AnalysisResult) -> dict:
        """
        Bereitet AnalysisResult als kwargs-dict für build_analyse_report() auf.
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

    # ── Daten-Fetch ───────────────────────────────────────────────────────────

    def _fetch_place(self, query: str) -> dict:
        try:
            from tools.scraper import get_google_business_adapter
            adapter = get_google_business_adapter()
            place   = adapter.search_place(query) or {}
            return place
        except Exception as e:
            log.warning(f"[BUSINESS-ANALYSE] Google-Fetch Fehler: {e}")
            return {}

    def _fetch_competitors(self, query: str, place: dict) -> list:
        try:
            from tools.scraper import get_google_business_adapter
            adapter = get_google_business_adapter()
            # Koordinaten aus place falls vorhanden (Live: lat/lng)
            lat = place.get("gps_coordinates", {}).get("latitude", 52.5200)
            lng = place.get("gps_coordinates", {}).get("longitude", 13.4050)
            return adapter.search_radius("Restaurant", lat, lng)
        except Exception as e:
            log.warning(f"[BUSINESS-ANALYSE] Konkurrenz-Fetch Fehler: {e}")
            return []

    def _fetch_instagram(self, handle: str) -> dict:
        try:
            from tools.scraper import get_instagram_adapter
            adapter = get_instagram_adapter()
            return adapter.get_profile(handle) or {}
        except Exception as e:
            log.warning(f"[BUSINESS-ANALYSE] Instagram-Fetch Fehler: {e}")
            return {}

    # ── Daten-Mapping ─────────────────────────────────────────────────────────

    def _apply_place(self, result: AnalysisResult, place: dict) -> None:
        result.name         = place.get("name", result.query)
        result.address      = place.get("address", "")
        result.rating       = float(place.get("rating", 0.0) or 0.0)
        result.review_count = int(place.get("reviews", 0) or 0)
        result.phone        = place.get("phone", "")
        result.website      = place.get("website", "")
        result.categories   = place.get("categories", [])
        result.hours        = place.get("hours", {})
        result.stub_mode    = bool(place.get("_stub", True))

    def _guess_instagram_handle(self, result: AnalysisResult) -> str:
        # Aus Website-URL ableiten falls instagram.com drin
        site = result.website.lower()
        if "instagram.com/" in site:
            parts = site.split("instagram.com/")
            if len(parts) > 1:
                return parts[1].strip("/").split("/")[0]
        # Einfache Heuristik: Name ohne Sonderzeichen als Handle-Kandidat
        name_slug = "".join(
            c for c in result.name.lower().replace(" ", "_")
            if c.isalnum() or c == "_"
        )
        return name_slug if len(name_slug) >= 3 else ""

    # ── Schwachstellen-Erkennung ──────────────────────────────────────────────

    def _detect_weaknesses(self, result: AnalysisResult) -> list:
        """
        Prüft erkannte Schwachstellen aus knowledge/gastro.yaml
        gegen die vorliegenden Daten. Gibt liste der gefundenen zurück.
        """
        from knowledge.loader import get_knowledge_base
        kb = get_knowledge_base()
        all_weaknesses = kb.get_weaknesses("gastro")
        found = []

        for w in all_weaknesses:
            wid = w.get("id", "")
            if self._check_weakness(wid, result):
                found.append(w)
                log.info(f"[BUSINESS-SCHWACHSTELLE] {wid} erkannt ({w.get('severity','?')})")

        # Sortierung: hoch → mittel → niedrig
        severity_order = {"hoch": 0, "mittel": 1, "niedrig": 2}
        found.sort(key=lambda w: severity_order.get(w.get("severity", "niedrig"), 2))
        return found

    def _check_weakness(self, weakness_id: str, r: AnalysisResult) -> bool:
        """Gibt True zurück wenn die Schwachstelle aus den Daten erkennbar ist."""

        if weakness_id == "keine_bewertungsantworten":
            # Keine Response-Rate in Stub — prüfen ob Website fehlt als Proxy
            # In Live-Daten: response_rate aus SerpAPI
            response_rate = r.instagram_data.get("response_rate_pct", None)
            if response_rate is not None:
                return response_rate < 80
            # Heuristik: wenn wenig Reviews → Antwortrate unbekannt → Warnung
            return r.review_count < 50

        if weakness_id == "niedrige_bewertungsanzahl":
            return 0 < r.review_count < 50

        if weakness_id == "schlechte_bewertung":
            return 0 < r.rating < 4.0

        if weakness_id == "keine_online_reservierung":
            # Proxy: kein Website-Link im Profil
            return not r.website

        if weakness_id == "veraltete_speisekarte":
            # Proxy: keine Website
            return not r.website

        if weakness_id == "fehlendes_google_profil":
            # Schwachstelle wenn Profil unvollständig (fehlende Pflichtfelder)
            missing = sum([
                not r.phone,
                not r.website,
                not r.address,
                not r.hours,
                r.review_count == 0,
            ])
            return missing >= 2

        if weakness_id == "inaktive_social_media":
            ig = r.instagram_data
            if ig:
                posts_per_week = ig.get("posts_per_week", None)
                if posts_per_week is not None:
                    return posts_per_week < 1
            # Kein Instagram-Handle erkannt → keine Social-Präsenz
            return not r.instagram_handle

        if weakness_id == "kein_lieferdienst":
            # Kann ohne Lieferando-API nicht zuverlässig erkannt werden
            # → nur in Stub-Modus bewusst auslassen um False-Positives zu vermeiden
            return False

        if weakness_id == "keine_seo_website":
            return not r.website

        if weakness_id == "kein_newsletter":
            # Nicht automatisch erkennbar — immer als Hinweis
            return True

        return False

    # ── KPI-Snapshot ──────────────────────────────────────────────────────────

    def _build_kpi_snapshot(self, result: AnalysisResult) -> list:
        """Gibt list[(label, ist_wert, ziel_wert)] zurück."""
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
            filled = sum([
                bool(r.phone), bool(r.website), bool(r.address),
                bool(r.hours), bool(r.categories), r.review_count > 0,
            ])
            pct = int(filled / 6 * 100)
            return f"{pct}%"
        if kpi_id == "website_mobile":
            return "nicht geprüft" if r.website else "keine Website"
        if kpi_id == "lieferdienst_rating":
            return "nicht erfasst"
        if kpi_id == "tripadvisor_rang":
            return "nicht erfasst"
        return None

    # ── Score ─────────────────────────────────────────────────────────────────

    def _calc_score(self, result: AnalysisResult) -> int:
        """
        Einfacher Score 0-100 basierend auf erkannten Problemen.
        Start bei 100, Abzüge pro Schwachstelle nach Severity.
        """
        score = 100
        deductions = {"hoch": 20, "mittel": 10, "niedrig": 5}
        for w in result.weaknesses_found:
            score -= deductions.get(w.get("severity", "niedrig"), 5)
        return max(0, min(100, score))

    # ── Empfehlungen + Next Steps ─────────────────────────────────────────────

    def _build_recommendations(self, result: AnalysisResult) -> list:
        """Gibt list[(Maßnahme, Priorität, Kosten)] zurück."""
        from knowledge.loader import get_knowledge_base
        kb    = get_knowledge_base()
        tools = kb.get_tools("gastro")

        # Mappe Schwachstellen auf Tool-Empfehlungen
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

        return recs[:8]  # max 8 Zeilen im Report

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
            steps.append("Bewerungsschnitt über 4.5 Sterne anstreben durch aktive Gäste-Einladung")

        steps.append("Praxistest: Analyse nach 90 Tagen wiederholen um Fortschritt zu messen")
        return steps
