"""
report.py — PDF-Report-Generator für Zuki
──────────────────────────────────────────
Erzeugt branded PDFs via reportlab (PLATYPUS).

Templates:
  analyse_report()  — Business-Analyse für Erstgespräch (Gastro-Analyzer)
  steuer_report()   — Steuer-Übersicht für Office-Skill
  workflow_report() — Workflow-Audit für Business-Skill

Verwendung:
  from tools.report import build_analyse_report
  path = build_analyse_report(
      output_path = "output/analyse_pizza_bella.pdf",
      client_name = "Pizza Bella",
      client_address = "Musterstraße 1, 12345 Musterstadt",
      findings    = ["Keine Google-Antworten auf Bewertungen", ...],
      recommendations = [("SEO-Optimierung", "Hoch", "~150€/Monat"), ...],
      kpis        = [("Bewertungen", "87", "Ziel: 100+"), ...],
  )

Status-API:
  get_status()  → dict
  self_test()   → dict  (für system_test: Subsystem "report")

Branding:
  Logo: assets/logo.png falls vorhanden, sonst Text-Fallback
  Farben: Navy (#1A2744) + Akzentblau (#4F8EF7)
  Footer: Seitenzahl + Erstellungsdatum + optionaler Kunden-Name
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.logger import get_logger

log = get_logger("report")

_ROOT      = Path(__file__).resolve().parent.parent
_ASSETS    = _ROOT / "assets"
_ERROR_LOG = _ROOT / "logs" / "error.log"
_LOGO_PATH = _ASSETS / "logo.png"

# ── reportlab Import (optional) ───────────────────────────────────────────────

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    _RL_AVAILABLE = True
except ImportError:
    _RL_AVAILABLE = False
    log.warning("reportlab fehlt — pip install reportlab")


# ── Fehler-Logging ────────────────────────────────────────────────────────────

def _write_error_log(context: str, exc: Exception) -> None:
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(_ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}]  report — {context}\n  {type(exc).__name__}: {exc}\n\n")
    except Exception:
        pass


# ── Farb-Palette ──────────────────────────────────────────────────────────────

if _RL_AVAILABLE:
    _C_NAVY    = colors.HexColor("#1A2744")
    _C_BLUE    = colors.HexColor("#4F8EF7")
    _C_LIGHT   = colors.HexColor("#EEF3FB")
    _C_BORDER  = colors.HexColor("#CBD5E1")
    _C_TEXT    = colors.HexColor("#1E2432")
    _C_GRAY    = colors.HexColor("#64748B")
    _C_WHITE   = colors.white
    _C_SUCCESS = colors.HexColor("#16A34A")
    _C_WARN    = colors.HexColor("#D97706")


# ══════════════════════════════════════════════════════════════════════════════
# Datenstrukturen
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ReportMeta:
    """Branding und Kunden-Metadaten für alle Templates."""
    title: str
    subtitle: str         = ""
    author: str           = "Zuki KI-Assistent"
    client_name: str      = ""
    client_address: str   = ""
    report_date: str      = ""   # leer → heute
    confidential: bool    = True

    def __post_init__(self) -> None:
        if not self.report_date:
            self.report_date = datetime.now().strftime("%d.%m.%Y")


@dataclass
class TableSection:
    """Tabelle mit optionalem Titel und Header-Zeile."""
    title: str
    headers: list
    rows: list           # list[list[str]]
    col_widths: "list | None" = None
    note: str = ""


@dataclass
class BulletSection:
    """Aufzählung mit Titel und optionalem Einleitungstext."""
    title: str
    items: list          # list[str]
    intro: str = ""
    style: str = "bullet"   # "bullet" | "numbered" | "check"


@dataclass
class TextSection:
    """Freier Fließtext mit Titel."""
    title: str
    body: str


# ══════════════════════════════════════════════════════════════════════════════
# Style-Sheet
# ══════════════════════════════════════════════════════════════════════════════

def _build_styles() -> dict:
    """Gibt ein dict mit benannten ParagraphStyles zurück."""
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "ZukiTitle",
            parent=base["Normal"],
            fontSize=22,
            textColor=_C_NAVY,
            fontName="Helvetica-Bold",
            spaceAfter=4,
            leading=26,
        ),
        "subtitle": ParagraphStyle(
            "ZukiSubtitle",
            parent=base["Normal"],
            fontSize=12,
            textColor=_C_GRAY,
            fontName="Helvetica",
            spaceAfter=2,
        ),
        "client": ParagraphStyle(
            "ZukiClient",
            parent=base["Normal"],
            fontSize=11,
            textColor=_C_TEXT,
            fontName="Helvetica",
            spaceAfter=2,
        ),
        "section_heading": ParagraphStyle(
            "ZukiSectionHeading",
            parent=base["Normal"],
            fontSize=13,
            textColor=_C_NAVY,
            fontName="Helvetica-Bold",
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ZukiBody",
            parent=base["Normal"],
            fontSize=10,
            textColor=_C_TEXT,
            fontName="Helvetica",
            leading=14,
            spaceAfter=4,
        ),
        "bullet_item": ParagraphStyle(
            "ZukiBullet",
            parent=base["Normal"],
            fontSize=10,
            textColor=_C_TEXT,
            fontName="Helvetica",
            leftIndent=16,
            leading=14,
            spaceAfter=3,
        ),
        "table_header": ParagraphStyle(
            "ZukiTableHeader",
            parent=base["Normal"],
            fontSize=9,
            textColor=_C_WHITE,
            fontName="Helvetica-Bold",
            alignment=TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            "ZukiTableCell",
            parent=base["Normal"],
            fontSize=9,
            textColor=_C_TEXT,
            fontName="Helvetica",
            leading=12,
        ),
        "footer": ParagraphStyle(
            "ZukiFooter",
            parent=base["Normal"],
            fontSize=8,
            textColor=_C_GRAY,
            fontName="Helvetica",
            alignment=TA_CENTER,
        ),
        "confidential": ParagraphStyle(
            "ZukiConfidential",
            parent=base["Normal"],
            fontSize=8,
            textColor=_C_WARN,
            fontName="Helvetica-Bold",
            alignment=TA_RIGHT,
        ),
    }
    return styles


# ══════════════════════════════════════════════════════════════════════════════
# ReportBuilder — Kern-Engine
# ══════════════════════════════════════════════════════════════════════════════

class ReportBuilder:
    """
    Baut PDFs aus strukturierten Sections.

    build(sections, output_path, meta) → absoluter Pfad zur PDF-Datei
    """

    PAGE_W, PAGE_H = A4
    MARGIN = 2.0 * cm

    def build(
        self,
        sections: list,
        output_path: "str | Path",
        meta: "ReportMeta | None" = None,
    ) -> str:
        """
        Rendert sections in eine PDF-Datei.
        Gibt den absoluten Pfad zur erzeugten Datei zurück.
        Raises RuntimeError wenn reportlab nicht verfügbar.
        """
        if not _RL_AVAILABLE:
            raise RuntimeError("reportlab nicht installiert — pip install reportlab")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if meta is None:
            meta = ReportMeta(title="Zuki Report")

        styles = _build_styles()

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=self.MARGIN,
            rightMargin=self.MARGIN,
            topMargin=self.MARGIN + 0.5 * cm,
            bottomMargin=self.MARGIN + 0.5 * cm,
            title=meta.title,
            author=meta.author,
        )

        story = []
        story += self._build_header(meta, styles)
        story.append(HRFlowable(width="100%", thickness=1.5, color=_C_BLUE, spaceAfter=12))

        for section in sections:
            if isinstance(section, TextSection):
                story += self._render_text(section, styles)
            elif isinstance(section, BulletSection):
                story += self._render_bullets(section, styles)
            elif isinstance(section, TableSection):
                story += self._render_table(section, styles)
            elif section == "pagebreak":
                story.append(PageBreak())

        footer_fn = self._make_footer_fn(meta, styles)
        doc.build(story, onFirstPage=footer_fn, onLaterPages=footer_fn)

        log.info(f"PDF erstellt: {output_path}  ({output_path.stat().st_size // 1024} KB)")
        return str(output_path.resolve())

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self, meta: ReportMeta, styles: dict) -> list:
        story = []
        usable_w = self.PAGE_W - 2 * self.MARGIN

        logo_elem = self._load_logo(height=1.2 * cm)

        if logo_elem:
            header_data = [[logo_elem, Paragraph(meta.title, styles["title"])]]
            col_ws = [2.5 * cm, usable_w - 2.5 * cm]
        else:
            brand = Paragraph(
                f'<font color="#4F8EF7"><b>ZUKI</b></font>',
                ParagraphStyle("Brand", fontSize=14, fontName="Helvetica-Bold",
                               textColor=_C_NAVY),
            )
            header_data = [[brand, Paragraph(meta.title, styles["title"])]]
            col_ws = [2.5 * cm, usable_w - 2.5 * cm]

        header_table = Table(header_data, colWidths=col_ws)
        header_table.setStyle(TableStyle([
            ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",   (0, 0), (0, 0),   "LEFT"),
            ("ALIGN",   (1, 0), (1, 0),   "LEFT"),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)

        if meta.subtitle:
            story.append(Spacer(1, 4))
            story.append(Paragraph(meta.subtitle, styles["subtitle"]))

        if meta.client_name:
            story.append(Spacer(1, 6))
            client_line = meta.client_name
            if meta.client_address:
                client_line += f"  ·  {meta.client_address}"
            story.append(Paragraph(client_line, styles["client"]))

        meta_line = f"Erstellt am: {meta.report_date}  ·  {meta.author}"
        if meta.confidential:
            meta_line += "  ·  <font color='#D97706'><b>VERTRAULICH</b></font>"
        story.append(Paragraph(meta_line, styles["body"]))
        story.append(Spacer(1, 6))
        return story

    # ── Sections ──────────────────────────────────────────────────────────────

    def _render_text(self, s: TextSection, styles: dict) -> list:
        story = [Paragraph(s.title, styles["section_heading"])]
        for para in s.body.split("\n\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para, styles["body"]))
        story.append(Spacer(1, 4))
        return story

    def _render_bullets(self, s: BulletSection, styles: dict) -> list:
        story = [Paragraph(s.title, styles["section_heading"])]
        if s.intro:
            story.append(Paragraph(s.intro, styles["body"]))

        for i, item in enumerate(s.items, 1):
            if s.style == "numbered":
                prefix = f"{i}.&nbsp;&nbsp;"
            elif s.style == "check":
                prefix = "✓&nbsp;&nbsp;"
            else:
                prefix = "•&nbsp;&nbsp;"
            story.append(Paragraph(f"{prefix}{item}", styles["bullet_item"]))

        story.append(Spacer(1, 4))
        return story

    def _render_table(self, s: TableSection, styles: dict) -> list:
        story = [Paragraph(s.title, styles["section_heading"])]

        header_cells = [Paragraph(str(h), styles["table_header"]) for h in s.headers]
        data = [header_cells]
        for row in s.rows:
            data.append([Paragraph(str(c), styles["table_cell"]) for c in row])

        usable_w = self.PAGE_W - 2 * self.MARGIN
        col_ws = s.col_widths
        if col_ws is None:
            n = len(s.headers)
            col_ws = [usable_w / n] * n

        tbl = Table(data, colWidths=col_ws, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  _C_NAVY),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  _C_WHITE),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_C_WHITE, _C_LIGHT]),
            ("GRID",          (0, 0), (-1, -1), 0.4, _C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(tbl)

        if s.note:
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<i>{s.note}</i>", styles["body"]))

        story.append(Spacer(1, 4))
        return story

    # ── Footer (Canvas-Hook) ──────────────────────────────────────────────────

    @staticmethod
    def _make_footer_fn(meta: ReportMeta, styles: dict):
        def draw_footer(canvas, doc):
            canvas.saveState()
            w, h = A4
            margin = ReportBuilder.MARGIN

            canvas.setStrokeColor(_C_BORDER)
            canvas.setLineWidth(0.5)
            canvas.line(margin, 1.5 * cm, w - margin, 1.5 * cm)

            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(_C_GRAY)

            left = meta.client_name if meta.client_name else meta.author
            canvas.drawString(margin, 1.1 * cm, left)

            canvas.drawCentredString(w / 2, 1.1 * cm, meta.report_date)

            page_str = f"Seite {doc.page}"
            canvas.drawRightString(w - margin, 1.1 * cm, page_str)

            canvas.restoreState()

        return draw_footer

    # ── Logo ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_logo(height: float = 1.2 * cm) -> "Image | None":
        if _LOGO_PATH.exists():
            try:
                img = Image(str(_LOGO_PATH))
                ratio = img.imageWidth / img.imageHeight
                img._restrictSize(ratio * height, height)
                return img
            except Exception:
                pass
        return None

    # ── Status-API ────────────────────────────────────────────────────────────

    @staticmethod
    def get_status() -> dict:
        return {
            "available": _RL_AVAILABLE,
            "library":   "reportlab" if _RL_AVAILABLE else None,
            "logo":      str(_LOGO_PATH) if _LOGO_PATH.exists() else None,
        }

    @staticmethod
    def self_test() -> dict:
        """Schnell-Test: minimale PDF erzeugen und wieder löschen."""
        if not _RL_AVAILABLE:
            return {
                "status":   "fail",
                "summary":  "report: reportlab fehlt",
                "fix_hint": "pip install reportlab",
            }

        tmp = _ROOT / "temp" / "_report_selftest.pdf"
        try:
            builder = ReportBuilder()
            builder.build(
                sections=[TextSection(title="Test", body="Self-Test OK")],
                output_path=tmp,
                meta=ReportMeta(title="Zuki Self-Test"),
            )
            size_kb = tmp.stat().st_size // 1024
            tmp.unlink()
            logo = "mit Logo" if _LOGO_PATH.exists() else "ohne Logo (kein assets/logo.png)"
            return {
                "status":  "ok",
                "summary": f"report: reportlab ok  |  PDF erzeugt ({size_kb} KB)  |  {logo}",
                "fix_hint": "",
            }
        except Exception as e:
            _write_error_log("self_test()", e)
            if tmp.exists():
                tmp.unlink()
            return {
                "status":   "fail",
                "summary":  f"report: PDF-Erzeugung fehlgeschlagen — {e}",
                "fix_hint": "Details in logs/error.log",
            }


# ══════════════════════════════════════════════════════════════════════════════
# Template-Factories
# ══════════════════════════════════════════════════════════════════════════════

def build_analyse_report(
    output_path: "str | Path",
    client_name: str,
    client_address: str = "",
    findings: "list[str] | None" = None,
    recommendations: "list[tuple] | None" = None,
    kpis: "list[tuple] | None" = None,
    next_steps: "list[str] | None" = None,
    notes: str = "",
) -> str:
    """
    Erstellt einen Analyse-Report für das Erstgespräch (Gastro-Analyzer).

    recommendations: list of (Maßnahme, Priorität, Geschätzte Kosten)
    kpis:            list of (Kennzahl, Ist-Wert, Ziel-Wert)
    Gibt Pfad zur erzeugten PDF zurück.
    """
    meta = ReportMeta(
        title      = "Analyse-Report",
        subtitle   = "Digitale Schwachstellen-Analyse",
        client_name    = client_name,
        client_address = client_address,
        confidential   = True,
    )

    sections: list = []

    sections.append(TextSection(
        title = "Über diese Analyse",
        body  = (
            f"Dieser Report fasst die Ergebnisse der digitalen Schwachstellen-Analyse "
            f"für {client_name} zusammen. "
            f"Die Analyse umfasst Online-Präsenz, Kundenbewertungen, Social Media sowie "
            f"sichtbare Optimierungspotenziale."
        ),
    ))

    if findings:
        sections.append(BulletSection(
            title = "Identifizierte Schwachstellen",
            intro = "Folgende Bereiche zeigen konkreten Handlungsbedarf:",
            items = findings,
            style = "bullet",
        ))

    if kpis:
        sections.append(TableSection(
            title    = "Kennzahlen im Überblick",
            headers  = ["Kennzahl", "Ist-Wert", "Ziel-Wert"],
            rows     = [list(k) for k in kpis],
            col_widths = [7 * cm, 5 * cm, 5 * cm],
        ))

    if recommendations:
        sections.append(TableSection(
            title    = "Empfohlene Maßnahmen",
            headers  = ["Maßnahme", "Priorität", "Geschätzte Kosten"],
            rows     = [list(r) for r in recommendations],
            col_widths = [9 * cm, 3.5 * cm, 4.5 * cm],
        ))

    if next_steps:
        sections.append(BulletSection(
            title = "Empfohlene nächste Schritte",
            items = next_steps,
            style = "numbered",
        ))

    if notes:
        sections.append(TextSection(title="Anmerkungen", body=notes))

    return ReportBuilder().build(sections, output_path, meta)


def build_steuer_report(
    output_path: "str | Path",
    tax_year: "int | str",
    documents: "list[tuple] | None" = None,
    summary: "list[tuple] | None" = None,
    tenant_name: str = "",
    notes: str = "",
) -> str:
    """
    Erstellt eine Steuer-Übersicht.

    documents: list of (Dateiname, Typ, Datum, Betrag)
    summary:   list of (Kategorie, Summe, Steuerrelevant)
    Gibt Pfad zur erzeugten PDF zurück.
    """
    meta = ReportMeta(
        title        = f"Steuer-Übersicht {tax_year}",
        subtitle     = "Zusammenfassung steuerrelevanter Dokumente",
        client_name  = tenant_name,
        confidential = True,
    )

    sections: list = []

    sections.append(TextSection(
        title = "Übersicht",
        body  = (
            f"Dieser Report enthält alle steuerrelevanten Dokumente für das Jahr {tax_year}. "
            f"Die Klassifikation erfolgte automatisch durch Zuki. "
            f"Bitte prüfen Sie alle Einträge vor der Weitergabe an Ihren Steuerberater."
        ),
    ))

    if documents:
        sections.append(TableSection(
            title      = "Dokumente",
            headers    = ["Dateiname", "Typ", "Datum", "Betrag"],
            rows       = [list(d) for d in documents],
            col_widths = [7 * cm, 4 * cm, 3 * cm, 3 * cm],
            note       = "Automatisch klassifiziert — manuelle Prüfung empfohlen.",
        ))

    if summary:
        sections.append(TableSection(
            title      = "Zusammenfassung nach Kategorie",
            headers    = ["Kategorie", "Summe (€)", "Steuerrelevant"],
            rows       = [list(s) for s in summary],
            col_widths = [8 * cm, 4 * cm, 5 * cm],
        ))

    if notes:
        sections.append(TextSection(title="Hinweise", body=notes))

    return ReportBuilder().build(sections, output_path, meta)


def build_workflow_report(
    output_path: "str | Path",
    client_name: str,
    client_address: str = "",
    processes: "list[tuple] | None" = None,
    bottlenecks: "list[str] | None" = None,
    tool_recommendations: "list[tuple] | None" = None,
    roadmap: "list[tuple] | None" = None,
    notes: str = "",
) -> str:
    """
    Erstellt einen Workflow-Audit-Report.

    processes:            list of (Prozess, Status, Bewertung)
    bottlenecks:          list[str]
    tool_recommendations: list of (Tool, Nutzen, Kosten/Monat)
    roadmap:              list of (Phase, Maßnahme, Zeitrahmen)
    Gibt Pfad zur erzeugten PDF zurück.
    """
    meta = ReportMeta(
        title          = "Workflow-Audit",
        subtitle       = "Prozessanalyse & Optimierungsempfehlungen",
        client_name    = client_name,
        client_address = client_address,
        confidential   = True,
    )

    sections: list = []

    sections.append(TextSection(
        title = "Zielsetzung",
        body  = (
            f"Dieser Workflow-Audit für {client_name} analysiert bestehende Prozesse, "
            f"identifiziert Engpässe und liefert konkrete Tool-Empfehlungen mit ROI-Abschätzung. "
            f"Die Empfehlungen sind nach Implementierungsaufwand und Wirkung priorisiert."
        ),
    ))

    if processes:
        sections.append(TableSection(
            title      = "Prozess-Übersicht",
            headers    = ["Prozess", "Status", "Bewertung"],
            rows       = [list(p) for p in processes],
            col_widths = [8 * cm, 4 * cm, 5 * cm],
        ))

    if bottlenecks:
        sections.append(BulletSection(
            title = "Identifizierte Engpässe",
            intro = "Folgende Prozesse bremsen den Betrieb am stärksten:",
            items = bottlenecks,
            style = "bullet",
        ))

    if tool_recommendations:
        sections.append(TableSection(
            title      = "Tool-Empfehlungen",
            headers    = ["Tool / Lösung", "Hauptnutzen", "Kosten/Monat"],
            rows       = [list(t) for t in tool_recommendations],
            col_widths = [6 * cm, 7 * cm, 4 * cm],
        ))

    if roadmap:
        sections.append(TableSection(
            title      = "Implementierungs-Roadmap",
            headers    = ["Phase", "Maßnahme", "Zeitrahmen"],
            rows       = [list(r) for r in roadmap],
            col_widths = [3 * cm, 10 * cm, 4 * cm],
        ))

    if notes:
        sections.append(TextSection(title="Anmerkungen", body=notes))

    return ReportBuilder().build(sections, output_path, meta)


# ══════════════════════════════════════════════════════════════════════════════
# Modul-Level Status-API
# ══════════════════════════════════════════════════════════════════════════════

def get_status() -> dict:
    return ReportBuilder.get_status()


def self_test() -> dict:
    return ReportBuilder.self_test()
