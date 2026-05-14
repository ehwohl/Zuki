# CHANGELOG — Zuki AI Assistant

All changes documented in reverse chronological order. Newest entries first.

---

## Bundle 9 — Coding-Skill + Scratchpad (2026-05-13)

**Status: ✅ Abgeschlossen**

### Implementiert

- **`workspaces/coding/__init__.py`** (neu): Paket-Marker
- **`workspaces/coding/buffer.py`** (neu): `CodeBuffer`-Klasse
  - Persistente JSON-Datei `temp/coding_buffers.json` (Buffer + aktive Sprache)
  - `get(lang)`, `set(lang, code)`, `append_line(lang, line)`, `clear(lang)`
  - `set_active(lang)`, `active()` — aktive Sprache für `code run` / `code show`
  - `has_content() → list[str]` — Sprachen mit nicht-leerem Buffer
  - `get_status() → dict`
  - Sprachen: `python`, `js`, `ts`, `bash`, `go`, `pine`
- **`workspaces/coding/sandbox.py`** (neu): Isolierte Code-Ausführung
  - `run_code(lang, code, timeout=10) → RunResult`
  - `is_available(lang) → tuple[bool, str]` — Interpreter-Check
  - `RunResult` Dataclass: stdout, stderr, returncode, timed_out, error, success, format_output()
  - Temp-Datei pro Run in `temp/sandbox/` — wird nach Ausführung gelöscht
  - Unterstützte Runner: Python (sys.executable), JS (node), TS (ts-node), Bash (bash), Go (go run)
  - Pine Script: kein Runner — explizit nicht ausführbar
- **`workspaces/coding/coding_skill.py`** (neu): `CodingSkill(Skill)`
  - triggers: `{"code", "coding", "skript", "script"}`
  - `tenant_aware = False` (kein Kundenbezug)
  - Befehle: `code <lang>`, `code <lang> show/run/edit/add/set/clear`, `code run`, `code show`, `code status`
  - Interaktiver Multiline-Editor via `code <lang> edit` (analog Interview-Pattern)
    - Modus-Wahl beim Start: Buffer ersetzen oder Zeilen anhängen
    - `END`/`fertig` → speichern  |  `run` → speichern + direkt ausführen  |  `abbrechen` → verwerfen
  - Sprach-Aliase normalisiert: `py`→`python`, `node`→`js`, `sh`→`bash`, `golang`→`go`, `tv`→`pine`
  - Pine Script: zeigt Code + TradingView-Hinweis statt Ausführung
  - TypeScript: Hinweis falls ts-node fehlt, trotzdem Buffer nutzbar
  - Log-Marker: `[CODING-SKILL]`
- **`tools/system_test.py`** (erweitert): 21. Subsystem `"coding"`
  - Smoke-Test: führt `print('zuki-coding-ok')` in Python-Sandbox aus
  - Prüft alle optionalen Interpreter (node, ts-node, bash, go) — warn wenn fehlend
  - Status: ok (alle verfügbar), warn (optionale fehlen), fail (Python-Sandbox defekt)

### Geänderte Files

- `workspaces/coding/__init__.py`       — **neu**
- `workspaces/coding/buffer.py`         — **neu** (CodeBuffer)
- `workspaces/coding/sandbox.py`        — **neu** (Sandbox-Runner)
- `workspaces/coding/coding_skill.py`   — **neu** (CodingSkill)
- `tools/system_test.py`            — `"coding"` (21. Subsystem)
- `ROADMAP.md`                      — Bundle 9 auf ✅

### Neue Status-APIs

- `CodeBuffer.get_status() → dict`          — active, buffers (lang→chars), file
- `RunResult.success → bool`                — rc==0 und kein Timeout/Error
- `RunResult.format_output() → str`         — formatierter Output für Terminal
- `run_code(lang, code, timeout) → RunResult`
- `is_available(lang) → tuple[bool, str]`   — Interpreter vorhanden?

### Notizen

- **Kein main.py-Touch nötig**: CodingSkill wird via Auto-Discovery gefunden.
- **Inline-Editor**: folgt dem Interview-Pattern aus Bundle 12 — kein State-Hack in main.py.
- **Pine Script**: bewusst kein Runner — `code pine run` zeigt Code + Hinweis "In TradingView einfügen".
- **TypeScript**: Buffer funktioniert immer; Ausführung erfordert `npm install -g ts-node`.
- **Sandbox-Sicherheit**: Timeout 10s verhindert Endlos-Loops; Temp-Dateien werden garantiert gelöscht (finally-Block).
- **Impliziter Add-Modus**: `code python print('hello')` ohne Subbefehl fügt Zeile direkt hinzu.

---

## Bundle 12.1 — Cleanup: Tenant-Isolation + Kunden-Dokumente (2026-05-12)

**Status: ✅ Abgeschlossen**

### Implementiert

- **Tenant-isoliertes `cleanup chats`**: Löscht nur Chat-Einträge des aktiven Tenants
  (vorher: gesamte `chat_history.json` geleert)
- **`cleanup kunde`-Befehlsfamilie**: Kunden-PDFs in `temp/business_reports/` verwalten
  - `cleanup kunde`         → alle Dokumente auflisten
  - `cleanup kunde <Name>`  → Dokumente für diesen Kunden anzeigen
  - `cleanup kunde <Name> !`→ Dokumente für diesen Kunden löschen (mit Bestätigung)
  - `cleanup kunde all`     → alle Kunden-Dokumente löschen (mit Bestätigung)
- **`cleanup all`**: nutzt jetzt ebenfalls Tenant-Filter (nicht mehr global)

### Geänderte Files

- `memory/history_manager.py` — `clear_tenant(tenant_id) → int` ergänzt
- `tools/cleanup_manager.py`  — `cleanup_chats()` tenant-aware; `list_client_files()` + `cleanup_client()` neu
- `core/main.py`              — `cleanup chats/all` mit `tenant_id`; vollständiger `cleanup kunde`-Handler
- `core/ui.py`                — Dashboard: `cleanup kunde`-Zeile ergänzt

### Notizen

- `cleanup kunde` greift auf `temp/business_reports/` zu (lokale PDFs, kein Cloud-Upload).
- Löschung nur mit explizitem `!`-Suffix oder `all` — kein versehentliches Löschen.
- Tenant-Isolation in `cleanup chats` gilt rückwirkend: Legacy-Einträge ohne `tenant_id`
  werden als `"self"` behandelt (History-Manager-Konvention).

---

## Bundle 12 — Business-Skill MVP (Gastro-Analyzer) (2026-05-12)

**Status: ✅ Abgeschlossen**

### Implementiert

- **`workspaces/business/__init__.py`** (neu): Paket-Marker
- **`workspaces/business/analyzer.py`** (neu): `GastroAnalyzer` + `AnalysisResult`
  - `AnalysisResult` Dataclass: name, address, rating, review_count, phone, website,
    categories, hours, competitors, instagram_handle/data, weaknesses_found,
    kpi_snapshot, score (0-100), stub_mode, analyzed_at
  - `GastroAnalyzer.run(query) → AnalysisResult` — vollständige Analyse-Pipeline:
    1. `_fetch_place(query)` via `GoogleBusinessAdapter.search_place()`
    2. `_fetch_competitors()` via `GoogleBusinessAdapter.search_radius()`
    3. `_guess_instagram_handle()` + `_fetch_instagram()` via `InstagramPublicAdapter`
    4. `_detect_weaknesses()` — mappt 9 Schwachstellen-IDs aus `knowledge/gastro.yaml`
       gegen erkannte Datenpunkte (rating, review_count, website, instagram_data, etc.)
    5. `_build_kpi_snapshot()` — Ist-Werte aus Daten gegen Ziele aus gastro.yaml
    6. `_calc_score()` — 100 minus Severity-Abzüge (hoch:-20, mittel:-10, niedrig:-5)
  - `GastroAnalyzer.to_report_data(result) → dict` — kwargs für `build_analyse_report()`
    - findings, recommendations (tool-mapped), kpis, next_steps, stub_note
  - `_build_recommendations()` — mappt Schwachstellen auf Tool-Empfehlungen aus gastro.yaml
  - `_build_next_steps()` — konkrete nächste Schritte basierend auf erkannten IDs
  - Log-Marker: `[BUSINESS-ANALYSE]`, `[BUSINESS-SCHWACHSTELLE]`
- **`workspaces/business/interview.py`** (neu): `WorkflowInterview`
  - 10 strukturierte Fragen: Sitzplätze, Reservierung, Kassensystem, Social-Media-
    Verantwortung, Post-Frequenz, Bewertungsantworten, Lieferdienst, Newsletter,
    Herausforderung, Ziel 3 Monate
  - `format_question()` → formatierte Frage für Terminal
  - `answer(user_input)` → speichert Antwort, rückt Index vor
  - `is_done()`, `progress()` → Navigation
  - `get_summary() → dict` — alle Antworten + abgeleitete Insights
  - `to_report_notes() → str` — Textblock für PDF-Notizen-Feld
  - `_derive_insights()` — erkennt Muster: inaktives Social-Media, keine Bewertungsantworten,
    Telefon-only Reservierung, kein Lieferdienst, kein Newsletter, kein Verantwortlicher
  - Log-Marker: `[BUSINESS-INTERVIEW]`
- **`workspaces/business/business_skill.py`** (neu): `BusinessSkill(Skill)`
  - triggers: `{"business", "analyse", "analysiere"}`
  - `description` gesetzt (Router-sichtbar)
  - Befehle: `business analyse <query>`, `business report`, `business interview [name]`,
    `business interview [name] report`, `business status`, `business` (Hilfe)
  - Interview läuft **inline** via `ui.user_prompt()` innerhalb einer `handle()`-Invokation
    (analog zum Vision-Handler in `main.py`) — kein main.py-State-Hack nötig
  - Reports in `temp/business_reports/` (datei-sichere Namen via `_safe_filename()`)
  - Log-Marker: `[BUSINESS-SKILL]`

### Geänderte Files

- `workspaces/business/__init__.py`       — **neu**
- `workspaces/business/analyzer.py`       — **neu** (GastroAnalyzer)
- `workspaces/business/interview.py`      — **neu** (WorkflowInterview)
- `workspaces/business/business_skill.py` — **neu** (BusinessSkill)

### Neue Status-APIs

- `GastroAnalyzer.run(query) → AnalysisResult`
- `GastroAnalyzer.last_result() → AnalysisResult | None`
- `GastroAnalyzer.to_report_data(result) → dict`
- `WorkflowInterview.current_question() → dict | None`
- `WorkflowInterview.answer(user_input) → None`
- `WorkflowInterview.is_done() → bool`
- `WorkflowInterview.get_summary() → dict`
- `WorkflowInterview.to_report_notes() → str`

### Notizen

- **Stub-Modus:** `GoogleBusinessAdapter` liefert Beispiel-Daten wenn `SERPAPI_API_KEY`
  fehlt. `AnalysisResult.stub_mode=True` — Output warnt den User. Alle Logik läuft
  trotzdem durch → vollständig testbar ohne echten API-Key.
- **Inline-Interview-Pattern:** Interview blockiert den Main-Loop für Dauer des
  Fragebogens (erwartetes Verhalten bei interaktivem Workflow). Kein Refactor von
  `main.py` nötig — analog zum Vision-Handler.
- **Reports:** `temp/business_reports/` liegt in `.gitignore` (Kundendaten) —
  nur lokale Artefakte, kein Cloud-Upload.
- **ARCHITECTURE.md:** Entscheidung 17 ergänzt (Inline-Interview-Pattern + Stub-Modus).
- **Praxistest:** Vor Weiterentwicklung (Bundle 17 Business-Vermittler) soll der
  Skill mit 5-10 echten Restaurants getestet werden (laut ROADMAP).

---

## Bundle 8.7 — Knowledge-Base-Pattern (2026-05-12)

**Status: ✅ Abgeschlossen**

### Implementiert

- **`knowledge/__init__.py`** (neu): Paket-Marker
- **`knowledge/loader.py`** (neu): `KnowledgeBase`-Klasse
  - Lazy-Loader: scannt `knowledge/` beim ersten Zugriff, cached alle YAML-Dateien
  - `list_branches() → list[str]` — verfügbare Branchen
  - `get_branch(branch) → dict | None` — vollständige Branchen-Daten
  - `get_weaknesses(branch) → list[dict]` — Schwachstellen (id, title, description, severity)
  - `get_kpis(branch) → list[dict]` — KPIs (id, label, description, target, einheit)
  - `get_tools(branch) → list[dict]` — Tool-Empfehlungen (name, category, url, cost)
  - `get_sources(branch) → list[str]` — Datenquellen für Analyse
  - `get_glossary(branch) → dict[str, str]` — Branchen-Glossar
  - `get_label(branch) → str` — Anzeigename der Branche
  - `get_status() → dict` — available, branches, count, directory
  - `self_test() → dict` — für system_test: Subsystem "knowledge"
  - Modul-Level Singleton: `get_knowledge_base()`, `get_status()`, `self_test()`
  - Log-Marker: `[KNOWLEDGE-LOAD]`, `[KNOWLEDGE-MISS]`
- **`knowledge/gastro.yaml`** (neu): Gastro-Branchenwissen
  - 7 Datenquellen (Google Business, TripAdvisor, Instagram, Lieferando, etc.)
  - 10 typische Schwachstellen mit severity (hoch/mittel/niedrig)
  - 8 KPIs mit Zielwerten (Bewertungsschnitt, Antwortrate, Post-Frequenz, etc.)
  - 9 Tool-Empfehlungen mit Kategorie und Kosten
  - 13 Glossar-Einträge (RevPASH, Prime Cost, HACCP, No-Show Rate, etc.)
- **`tools/system_test.py`** (erweitert): 20. Subsystem `"knowledge"`
  - Prüft ob YAML-Dateien geladen werden können
  - Validiert: mindestens eine Branche vorhanden, weaknesses + kpis befüllt
  - Status: ok / warn (keine YAMLs) / fail (Load-Fehler)
  - Neuer Parameter `knowledge_base=` im Konstruktor (optional, Singleton-Fallback)

### Geänderte Files

- `knowledge/__init__.py`  — **neu**
- `knowledge/loader.py`    — **neu** (KnowledgeBase + Singleton)
- `knowledge/gastro.yaml`  — **neu** (Gastro-Branchenwissen)
- `tools/system_test.py`   — `"knowledge"` (20. Subsystem), `knowledge_base` Parameter

### Neue Status-APIs

- `KnowledgeBase.get_status() → dict`      — available, branches, count, directory
- `KnowledgeBase.self_test()  → dict`      — für system_test
- `knowledge.loader.get_status()`          — Modul-Level (Singleton)
- `knowledge.loader.self_test()`           — Modul-Level (Singleton)

### Notizen

- **Erweiterungs-Konvention:** Neue Branche = neue YAML-Datei ablegen, kein Code ändern.
  Loader erkennt sie automatisch via `os.listdir()` beim nächsten Start.
- **Verwendung in Bundle 12 (Business-Skill):** `get_weaknesses("gastro")` befüllt
  Schwachstellen-Sektion im Analyse-Report; `get_kpis()` befüllt KPI-Tabelle im PDF.
- **yaml.safe_load()** — kein `yaml.load()` mit vollem Loader (sicher gegen Code-Injection).
- **ARCHITECTURE.md:** Entscheidung 16 ergänzt (YAML-Pattern + Erweiterungs-Konvention).

---

## Bundle 8.6 — PDF-Report-Generator (2026-05-11)

**Status: ✅ Abgeschlossen**

### Implementiert

- **`tools/report.py`** (neu): PDF-Report-Generator via reportlab PLATYPUS
  - `ReportMeta` — Branding-Dataclass (Titel, Untertitel, Kunden-Name/-Adresse, Datum, Vertraulich-Flag)
  - `TextSection`, `BulletSection`, `TableSection` — typisierte Inhalts-Bausteine
  - `ReportBuilder` — Kern-Engine
    - Branded Header: Logo (assets/logo.png falls vorhanden) oder Text-Fallback „ZUKI"
    - Farb-Palette: Navy (#1A2744) + Akzentblau (#4F8EF7) + Hellblau (#EEF3FB)
    - Footer-Hook (Canvas): Kunden-Name links, Datum zentriert, Seitenzahl rechts
    - Alternierend gefärbte Tabellenzeilen (weiß / hellblau), Navy-Header
    - `_render_text()`, `_render_bullets()` (bullet / numbered / check), `_render_table()`
    - `build(sections, output_path, meta)` → absoluter Pfad zur erzeugten PDF
    - `get_status()` → dict mit available, library, logo
    - `self_test()` → erzeugt Minimal-PDF, prüft Größe, löscht sie wieder
  - Template-Factories:
    - `build_analyse_report()` — Gastro-Analyzer Erstgespräch-Report (Schwachstellen, KPIs, Empfehlungen, nächste Schritte)
    - `build_steuer_report()` — Steuer-Übersicht (Dokumente-Tabelle, Kategorien-Zusammenfassung)
    - `build_workflow_report()` — Workflow-Audit (Prozesse, Engpässe, Tool-Empfehlungen, Implementierungs-Roadmap)
  - Modul-Level Status-API: `get_status()`, `self_test()`
- **`tools/system_test.py`** (erweitert): 19. Subsystem `"report"`
  - Erzeugt Minimal-PDF, prüft Dateigröße, löscht sie — ok/fail in < 1s

### Geänderte Files

- `tools/report.py`      — **neu** (PDF-Generator)
- `tools/system_test.py` — `"report"` (19. Subsystem)

### Neue Status-APIs

- `ReportBuilder.get_status() → dict`   — available, library, logo
- `ReportBuilder.self_test()  → dict`   — für system_test
- `tools.report.get_status()`           — Modul-Level
- `tools.report.self_test()`            — Modul-Level

### Dependency

- `reportlab==4.5.0` — neu installiert (pip install reportlab)

### Notizen

- Logo: `assets/logo.png` → wird automatisch eingebunden wenn vorhanden, sonst „ZUKI"-Text-Fallback
- Test-PDFs in `temp/test_reports/` erzeugt (3-4 KB je Template) — manuell prüfbar
- Alle Template-Factories akzeptieren optionale Parameter → robuste Defaults ohne Pflichtfelder außer Titel

---

## Bundle 8.5 — Web-Scraping-Layer (2026-05-11)

**Status: ✅ Abgeschlossen**

### Implementiert

- **`tools/scraper.py`** (neu): Zentraler Web-Scraping-Layer
  - `ScraperCache` — JSON-Disk-Cache in `temp/scraper_cache/` mit konfigurierbarem TTL (Standard: 6h)
    - `get(key)` → Inhalt wenn frisch, sonst None
    - `set(key, content)` — speichert mit Unix-Timestamp
    - `invalidate(key)` — löscht Einzeleintrag
    - `clear_expired()` → Anzahl gelöschter abgelaufener Einträge
    - `clear_all()` → Anzahl gelöschter Einträge
    - `stats()` → dict mit total, fresh, expired, ttl_seconds
  - `Scraper` — Kern-Engine
    - User-Agent-Pool: 8 moderne Browser-UAs (Chrome, Firefox, Safari — Win/Mac/Linux)
    - UA-Rotation: round-robin via `_ua_index`
    - Rate-Limiting: pro Domain — Mindestabstand via `SCRAPER_RATE_DELAY` (Standard: 2.0s)
    - `fetch(url, bypass_cache, ttl)` → HTML-Inhalt oder None
    - `fetch_json(url, params, bypass_cache)` → dict/list oder None
    - `get_status()` → dict mit available, total_fetched, total_cached, errors, rate_delay, cache
    - `self_test()` → dict für system_test-Integration
  - `GoogleBusinessAdapter` — SerpAPI-Integration
    - `search_place(query)` → place_results dict (SerpAPI live oder Stub)
    - `search_radius(query, lat, lng)` → local_results list
    - Stub-Modus wenn `SERPAPI_API_KEY` nicht konfiguriert
    - LIVE UPGRADE Kommentare mit vollständigen SerpAPI-Params-Beispielen
  - `InstagramPublicAdapter` — Öffentliche Profil-Daten
    - `get_profile(username)` → Profil-dict
    - `get_recent_posts(username, limit)` → Post-Liste
    - Stub-Modus wenn `INSTAGRAM_ACCESS_TOKEN` nicht konfiguriert
    - LIVE UPGRADE mit Option A (Basic Display API) und Option B (Public Scraper)
  - Modul-Level Singleton: `get_scraper()`, `get_google_business_adapter()`, `get_instagram_adapter()`
  - Modul-Level Status-API: `get_status()`, `self_test()`
  - `_write_error_log` + `_friendly_error` — analog api_manager.py-Pattern
- **`tools/system_test.py`** (erweitert): 18. Subsystem `"scraper"`
  - Prüft: requests-Bibliothek verfügbar, Cache-Verzeichnis erstellbar, SERPAPI_API_KEY konfiguriert
  - Status: ok wenn SerpAPI konfiguriert, warn wenn Stub-Modus

### Geänderte Files

- `tools/scraper.py`      — **neu** (Scraping-Layer)
- `tools/system_test.py`  — `"scraper"` (18. Subsystem)

### Neue Status-APIs

- `Scraper.get_status() → dict`     — available, fetched, cached, errors, rate_delay, cache
- `Scraper.self_test()  → dict`     — für system_test
- `tools.scraper.get_status()`      — Modul-Level (Singleton)
- `tools.scraper.self_test()`       — Modul-Level (Singleton)

### ENV-Variablen (neu, optional)

- `SCRAPER_CACHE_TTL`   — Cache-Lebenszeit in Sekunden (Standard: 21600 = 6h)
- `SCRAPER_RATE_DELAY`  — Mindestabstand pro Domain in Sekunden (Standard: 2.0)
- `SERPAPI_API_KEY`     — bereits in .env als Platzhalter vorhanden → LIVE UPGRADE
- `INSTAGRAM_ACCESS_TOKEN` — neu (optional, für Instagram Live)

### Notizen

- `requests` war bereits installiert — kein neues Dependency-Problem
- Broker-Skill `workspaces/broker/scraper.py` bleibt unverändert (Mock-News-Fetcher für Broker-Skill)
- `tools/scraper.py` ist die wiederverwendbare Infrastruktur für Business-, Office-, Broker-Skills
- Cache speichert in `temp/scraper_cache/` — wird von cleanup_manager's `temp/`-Bereinigung erfasst

---

## Bundle 8 — Plattform-Agnostik (2026-05-11)

**Status: ✅ Abgeschlossen**

### Implementiert

- **`core/text_to_speech/tts_backend.py`** (neu): `TTSBackend` ABC
  - `speak(text)`, `shutdown()`, `list_voices()`, `get_status()` als abstractmethods
- **`core/text_to_speech/windows_tts.py`** (neu): `WindowsTTS(TTSBackend)`
  - pyttsx3 / SAPI5 Implementierung aus `tts_engine.py` extrahiert
  - Spacebar-Mute via msvcrt-Watcher-Thread
  - `get_status() → dict` mit backend, platform, voice, ready, speaking
- **`core/text_to_speech/linux_tts.py`** (neu): `LinuxTTS(TTSBackend)`
  - Piper-Stub mit vollständigem LIVE UPGRADE Kommentar
  - `get_status()` → ready=False (Stub klar markiert)
- **`core/text_to_speech/tts_engine.py`** (überarbeitet): wird zur Factory
  - `_build_backend()` wählt per `sys.platform`: win32→WindowsTTS, linux→LinuxTTS
  - Öffentliche API (`speak`, `shutdown`, `list_voices`, `get_status`) delegiert ans Backend
- **`tools/window_control/`** (neues Paket):
  - `backend.py`: `WindowBackend` ABC — `available()`, `get_status()`, `list_windows()`, `focus_window()`, `minimize_window()`, `maximize_window()`, `close_window()`, `open_app()`, `close_app()`, `lock_screen()`, `shutdown_pc()`, `restart_pc()`
  - `windows_backend.py`: `WindowsWindowBackend` — echte Win32-Implementierung via ctypes
    - `_enum_windows()` via `EnumWindows` + `IsWindowVisible`
    - `_find_window()` case-insensitive Titel-Suche
    - `list_windows()` gibt alle sichtbaren Fenster-Titel zurück
    - `focus_window()`, `minimize_window()`, `maximize_window()` via `ShowWindow`
    - `close_window()` via `WM_CLOSE` PostMessage
    - `open_app()` via `start` shell, `close_app()` via `taskkill /f /im`
    - `lock_screen()` via `LockWorkStation()`, Shutdown/Restart via subprocess
  - `linux_backend.py`: `LinuxWindowBackend` — xdotool+wmctrl Stub
    - Alle Methoden mit vollständigen LIVE UPGRADE Kommentaren für xdotool/wmctrl
  - `factory.py`: `get_window_backend()` — wählt per `sys.platform`
  - `__init__.py`: Paket-Export
- **`tools/pc_control.py`** (überarbeitet): delegiert ans WindowBackend
  - Lazy-Init via `_get_backend()` Singleton
  - `available()` + `get_status()` als Status-API
  - `list_windows()`, `focus_window()`, `minimize_window()`, `maximize_window()`, `close_window()` — neu
  - `open_file()` plattformbewusst: `os.startfile` (Win) / `xdg-open` (Linux)
  - `set_volume()` plattformbewusst: pycaw (Win) / amixer (Linux)
  - Clipboard-Methoden via pyperclip (plattform-neutral, optional)
- **`core/speech_to_text/whisper_engine.py`** (erweitert): Audio-In Linux-Validierung
  - `sounddevice` Import mit try/except: `_SD_AVAILABLE` + `_SD_ERROR` Flags
  - `transcribe_microphone()` prüft `_SD_AVAILABLE` vor Aufnahme
  - Plattformbewusster Fix-Hint: Windows vs. Linux Installationsanleitung
  - `shutdown()` prüft `_SD_AVAILABLE` vor `sd.stop()`
- **`tools/system_test.py`**: 17. Subsystem `"platform"`
  - Prüft TTS-Backend (bereit?), Window-Control-Backend (verfügbar?), sounddevice
  - Status: ok wenn alle drei bereit, warn wenn Stubs oder fehlende Dependencies

### Geänderte Files

- `core/text_to_speech/tts_backend.py`    — **neu** (ABC)
- `core/text_to_speech/windows_tts.py`   — **neu** (WindowsTTS)
- `core/text_to_speech/linux_tts.py`     — **neu** (LinuxTTS Stub)
- `core/text_to_speech/tts_engine.py`    — Factory (war: monolithisch)
- `tools/window_control/__init__.py`      — **neu** (Paket)
- `tools/window_control/backend.py`       — **neu** (WindowBackend ABC)
- `tools/window_control/windows_backend.py` — **neu** (Win32 Implementierung)
- `tools/window_control/linux_backend.py` — **neu** (Stub)
- `tools/window_control/factory.py`       — **neu** (Factory)
- `tools/pc_control.py`                   — delegiert ans Backend, erweitert
- `core/speech_to_text/whisper_engine.py` — Audio-In Validierung
- `tools/system_test.py`                  — `"platform"` (17. Subsystem)

### Neue Status-APIs

- `TTSEngine.get_status() → dict`         — backend, platform, voice, ready, speaking
- `WindowsWindowBackend.get_status() → dict` — backend, platform, available
- `LinuxWindowBackend.get_status() → dict`   — backend, platform, available=False
- `PCControl.get_status() → dict`         — delegiert ans Backend
- `PCControl.available() → bool`          — delegiert ans Backend
- `PCControl.list_windows() → list[str]`  — neu (war nicht im Stub)

### Notizen

- **Keine Breaking Changes**: `TTSEngine` öffentliche API unverändert (`speak`, `shutdown`, `list_voices`).
  `get_status()` ist neu hinzugekommen.
- **PCControl Erweiterung**: Das alte Stub hatte nur 10 Methoden mit `NotImplementedError`.
  Jetzt sind auf Windows `list_windows`, `focus_window`, `minimize_window`, `maximize_window`,
  `close_window` echt implementiert.
- **Stimme Katja**: Nicht auf diesem Windows installiert → Fallback auf "Hedda". Erwartetes Verhalten.
- **Linux-Migration**: Wenn Zuki auf Linux umzieht, müssen nur `LinuxTTS` (Piper) und
  `LinuxWindowBackend` (xdotool+wmctrl) befüllt werden — kein Core-Touch.

---

## Bundle 7 — Cleanup-Befehle (2026-05-11)

**Status: ✅ Abgeschlossen**

### Implementiert

- **`tools/cleanup_manager.py`** (neu): `CleanupManager`-Klasse
  - `cleanup_vision() → dict` — Löscht .jpg/.png aus `temp/vision/`
  - `cleanup_chats(history_mgr) → dict` — Löscht lokale Chat-History via HistoryManager oder Datei-direkt
  - `cleanup_old_backups(keep=3) → dict` — Löscht ältere Backup-Snapshots, behält neueste `keep` Stück
  - `self_test() → dict` — Prüft Status aller Cleanup-Targets (für system test 16)
  - Log-Marker: `[CLEANUP]`
- **`zuki_cloud/api/index.py`** neuer Endpunkt:
  - `POST /api/memory/cleanup` — Löscht Cloud-Memories für Tenant
  - Geschützt: `source="bio"`, `"system": True` in Einträgen — werden **niemals** gelöscht
  - `scope`: `"all"` oder `"source:<name>"` für selektive Bereinigung
  - Audit-Log-Eintrag bei jedem Cleanup
  - Response: `{deleted, protected, total, tenant, scope}`
- **`tools/cloud_memory.py`** neue Methoden:
  - `cleanup_cloud(scope="all") → dict` — Ruft `/api/memory/cleanup` auf
  - `_cleanup_url()` — URL-Helper (analog zu `_skill_conversations_url`)
- **`core/main.py`** Cleanup-Befehls-Handler:
  - `cleanup` → Hilfe-Übersicht
  - `cleanup vision` → sofort, kein Prompt
  - `cleanup chats` → mit Bestätigungs-Prompt
  - `cleanup old` → sofort (3 Snapshots behalten)
  - `cleanup cloud` → mit Bestätigungs-Prompt, Cloud-Enabled-Check
  - `cleanup all` → vision + chats + old mit Bestätigungs-Prompt (kein Auto-Cloud)
- **`core/ui_renderer.py`**: `print_cleanup_result(results)` als `@abstractmethod`
- **`core/ui.py`**: `print_cleanup_result()` in `TerminalRenderer` + Forwarding-Funktion
  - Farbige Ergebnis-Tabelle: grün OK / grau nichts zu tun / rot Fehler
  - Dashboard-Befehlsreferenz um `cleanup` erweitert
- **16. Subsystem "cleanup"** in `tools/system_test.py`:
  - Zeigt Status aller Cleanup-Targets (Frames, History, Snapshots)

### Geänderte Files

- `tools/cleanup_manager.py`   — **neu**
- `zuki_cloud/api/index.py`    — `POST /api/memory/cleanup`, Audit-Log-Eintrag
- `tools/cloud_memory.py`      — `cleanup_cloud()`, `_cleanup_url()`
- `core/ui_renderer.py`        — `print_cleanup_result()` als abstractmethod
- `core/ui.py`                 — `print_cleanup_result()` in TerminalRenderer + Forwarding,
                                 Dashboard-Befehlsreferenz ergänzt
- `core/main.py`               — CleanupManager-Import, Cleanup-Befehls-Handler
- `tools/system_test.py`       — `"cleanup": self._test_cleanup` (16. Subsystem)

### Neue Status-APIs

- `CleanupManager.cleanup_vision() → dict`
- `CleanupManager.cleanup_chats(history_mgr) → dict`
- `CleanupManager.cleanup_old_backups(keep=3) → dict`
- `CleanupManager.self_test() → dict`
- `CloudMemory.cleanup_cloud(scope="all") → dict`

### Notizen

- **Schutz-Logik in Cloud**: `source="bio"` und `"system": True` werden vor Cleanup
  herausgefiltert und zurückgeschrieben — kein Datenverlust möglich.
- **`cleanup all` schließt Cloud bewusst aus**: User muss Cloud-Cleanup explizit mit
  `cleanup cloud` bestätigen — verhindert versehentlichen Massenverlust.
- **`cleanup old` behält 3 Snapshots** (statt 7 wie AutoBackup) — für Cleanup bewusst
  konservativ. Konstante `_DEFAULT_KEEP_BACKUPS = 3` in cleanup_manager.py anpassbar.
- **16. system-test-Subsystem**: `system test cleanup` zeigt Frames / History / Snapshots-Count.

---

## Bundle 6 — Router-Agent (2026-05-11)

**Status: ✅ Abgeschlossen**

### Implementiert

- **`core/router_agent.py`** (neu): `RouterAgent`-Klasse
  - `route(user_input, skills_info) → list[str]` — LLM entscheidet welche Skills relevant sind
  - Klassifikations-Prompt mit Skill-Namen, Beschreibungen, Triggern
  - JSON-Parsing der LLM-Antwort (tolerant gegenüber Freitext rund um JSON)
  - SIM-Modus: immer `[]` — kein Token-Verbrauch durch Router
  - Decision-Log in `temp/router_decisions.jsonl` (JSONL, append-only)
  - `last_decision() → dict | None`, `decision_count() → int`, `self_test() → dict`
  - Log-Marker: `[ROUTER]`, `[ROUTER-INVOKE]`
- **Skill-Dispatch in `core/main.py`** zweistufig:
  1. Schnellpfad: exakter Trigger-Match via `get_skill_for(cmd)` (0 Token)
  2. Router-Pfad: LLM-Klassifikation wenn kein Trigger-Match (1 kleiner LLM-Call)
  - Skill-Antworten werden per `cloud.save_skill_conversation()` in der Cloud gespeichert
  - Output zeigt `[Router] -> skill1, skill2` wenn Router-Pfad aktiv
  - Fallback auf General-LLM-Chat wenn Router `[]` zurückgibt
- **`workspaces/base.py`**: `description: str = ""` — neues Feld für Router-Klassifikation
- **`workspaces/professor/professor.py`**: `description` gesetzt
- **`workspaces/registry.py`**: `get_all_descriptions() → list[dict]` — Skills mit Beschreibung
  für Router (filtert Skills ohne description heraus)
- **Cloud-API `zuki_cloud/api/index.py`** zwei neue Endpunkte:
  - `POST /api/skill/conversations` — speichert in `zuki:skill:{name}:conversations:{tenant}`
  - `GET  /api/skill/conversations?skill=<name>&tenant=<tenant>&limit=<n>` — abrufen
  - Redis-Key-Helfer: `_skill_key(skill_name, tenant)`
- **`tools/cloud_memory.py`** neue Methoden:
  - `save_skill_conversation(skill_name, text) → str` — fire-and-forget im Hintergrund
  - `get_skill_conversations(skill_name, limit) → list[dict]` — synchroner Abruf
  - `_post_skill(payload)` — HTTP-Backend für Skill-Endpunkt
  - `_skill_conversations_url()` — leitet URL aus CLOUD_MEMORY_URL ab
- **`core/ui_renderer.py`**: `print_router_decision(skills, user_input)` als `@abstractmethod`
- **`core/ui.py`**: `print_router_decision()` in `TerminalRenderer` + Forwarding-Funktion
- **15. Subsystem "router"** in `tools/system_test.py`:
  - OK: Router aktiv + Entscheidungs-Statistik
  - WARN: SIM-Modus (kein API-Key) → Router deaktiviert

### Geänderte Files

- `core/router_agent.py`   — **neu**
- `core/main.py`           — RouterAgent-Import + Initialisierung, zweistufiger Dispatch,
                             `cloud.save_skill_conversation()` im Skill-Pfad,
                             `router_agent=router` im SystemTest
- `core/ui_renderer.py`    — `print_router_decision()` als abstractmethod
- `core/ui.py`             — `print_router_decision()` in TerminalRenderer + Forwarding
- `workspaces/base.py`         — `description: str = ""` Feld
- `workspaces/registry.py`     — `get_all_descriptions() → list[dict]`
- `workspaces/professor/professor.py` — `description` gesetzt
- `tools/cloud_memory.py`  — `save_skill_conversation()`, `get_skill_conversations()`,
                             `_post_skill()`, `_skill_conversations_url()`
- `tools/system_test.py`   — `router_agent` Parameter + `_test_router()`
- `zuki_cloud/api/index.py` — `POST/GET /api/skill/conversations`, `_skill_key()`,
                              `MAX_SKILL_CONV_ENTRIES`

### Neue Status-APIs

- `RouterAgent.route(user_input, skills_info) → list[str]`
- `RouterAgent.last_decision() → dict | None`
- `RouterAgent.decision_count() → int`
- `RouterAgent.self_test() → dict`
- `CloudMemory.save_skill_conversation(skill_name, text) → str`
- `CloudMemory.get_skill_conversations(skill_name, limit) → list[dict]`
- `skill_registry.get_all_descriptions() → list[dict]`

### Notizen

- **Zweistufiges Routing**: Exakter Trigger (0 Token) hat immer Vorrang vor Router-Pfad.
  Router läuft nur wenn kein Trigger passt — Token-Effizienz gewahrt.
- **SIM-Modus-sicher**: Router gibt im SIM-Modus sofort `[]` zurück — kein API-Call,
  kein Token-Verbrauch, sauberer Fallback auf General-LLM-Chat.
- **Decision-Log**: `temp/router_decisions.jsonl` für späteres Tuning der Skill-Prompts
  und Trigger-Coverage. Noch kein UI — kommt in späterem Bundle.
- **Skill-Description**: Neue Skills MÜSSEN `description` setzen um für den Router sichtbar
  zu sein. Skills ohne description (z. B. PingSkill) werden ignoriert.
- **Multi-Skill-Responses**: Router kann mehrere Skills zurückgeben; Antworten werden
  mit `\n\n` verbunden. In der Praxis wird meist 0 oder 1 Skill zurückgegeben.
- **ARCHITECTURE.md**: Entscheidung 14 ergänzt (Zweistufiges Routing).

---

## Bundle 5 — Tenant-Pattern (2026-05-11)

**Status: ✅ Abgeschlossen**

### Implementiert

- **`core/tenant.py`** (neu): `TenantManager`-Singleton + `TenantConfig`.
  - `current()`, `switch(name)`, `create(name, config)`, `delete(name)`,
    `list_known()`, `config(name)`, `get_config(name)`
  - Persistenz: `temp/tenants.json` (current + tenants-Dict + Migration-Marker)
  - `migration_done()` / `mark_migration_done()` — idempotente Migration
  - `self_test() → dict` — Status-API für system test
- **Einmalige Bundle-5-Migration** (beim ersten Start automatisch):
  1. `user_profile.txt` → `user_profile_self.txt` (lokal, vor UserProfile-Init)
  2. `POST /api/memory/migrate` — kopiert `zuki:memories` → `zuki:memories:self`
  3. Marker `__migration_v1_done__` gesetzt — idempotent, Re-Run-sicher
  4. Log-Marker `[TENANT-MIGRATION]`
- **Tenant-Befehle** in `main.py`:
  - `tenant` — zeigt aktiven Workspace + alle bekannten
  - `tenant list` — alle Tenants
  - `tenant switch <name>` — wechselt + lädt Profil neu
  - `tenant create <name>` — legt neuen Tenant an (Business-Default: require_dsgvo=True)
  - `tenant delete <name>` — fragt nach Bestätigung, löscht Profil-Datei
- **Dashboard** zeigt neu: `🏢 Tenant: self`
- **Cloud-API `zuki_cloud/api/index.py`** tenant-aware:
  - Redis-Keys: `zuki:memories:{tenant}`, `zuki:audit:{tenant}`
  - Legacy-Fallback: GET liest `zuki:memories` falls neuer Key leer (bis 2026-05-25)
  - `POST /api/memory/migrate` — Migrations-Endpunkt (idempotent)
  - Audit-Log: jeder Save erzeugt Eintrag in `zuki:audit:{tenant}` (max. 500)
  - View-Seite: `?tenant=client-xyz` Parameter, Badge im Header
- **`tools/cloud_memory.py`**: `tenant`-Feld in allen Payloads; `migrate_to_tenant()`
- **`memory/history_manager.py`**: `tenant_id`-Feld pro Nachricht; `get_context()` filtert
- **`memory/user_profile.py`**: `user_profile_{tenant}.txt` Datei-Pattern; `reload()`
- **`core/api_manager.py`**: DSGVO-Constraint via `TenantConfig.require_dsgvo`;
  klare Fehlermeldung statt stiller Simulation wenn Gemini blockiert
- **14. Subsystem "tenant"** in `tools/system_test.py`: prüft tenants.json,
  aktiven Tenant, Config-Validität, Migration abgeschlossen
- **`docs/MIGRATION.md`** (neu): Hinweise für künftige Bundles ("muss tenant-aware sein")

### Geänderte Files

- `core/tenant.py` — **neu**
- `core/main.py` — TenantManager-Import, Migrations-Block, tenant-Befehle,
  Dashboard-Tenant-Anzeige, SystemTest mit tenant_mgr
- `core/api_manager.py` — `_dsgvo_blocked`, DSGVO-Prüfung in `_detect_provider()`
- `core/ui_renderer.py` — `print_dashboard` + `tenant_name` Parameter
- `core/ui.py` — Tenant-Zeile + Tenant-Befehl im Dashboard
- `memory/history_manager.py` — `tenant_id` in `append()`, Filter in `get_context()`
- `memory/user_profile.py` — `_profile_path(tenant)`, `_current_path()`, `reload()`
- `tools/cloud_memory.py` — tenant in Payloads + `migrate_to_tenant()`
- `tools/system_test.py` — `tenant_mgr` Parameter + `_test_tenant()`
- `zuki_cloud/api/index.py` — vollständig überarbeitet (Tenant-Keys, Audit, Migrate)
- `docs/MIGRATION.md` — **neu**

### Neue Status-APIs

- `TenantManager.current() → str`
- `TenantManager.switch(name) → bool`
- `TenantManager.create(name, config) → bool`
- `TenantManager.delete(name) → bool`
- `TenantManager.list_known() → list[str]`
- `TenantManager.config(name) → dict`
- `TenantManager.get_config(name) → TenantConfig`
- `TenantManager.migration_done() → bool`
- `TenantManager.self_test() → dict`
- `UserProfile.reload() → None`
- `CloudMemory.migrate_to_tenant(tenant) → str`

### Notizen

- **Standard-Tenant "self"** hat `require_dsgvo=False` — verhält sich wie bisher.
- **Business-Tenants** haben `require_dsgvo=True` per Default — schützt vor
  versehentlichem Gemini-Free-Einsatz mit Kundendaten.
- **History-Datei** bleibt eine Datei — Tenant-Isolation durch `tenant_id`-Filter,
  nicht durch separate Dateien. Spart Disk-IO, funktioniert bei Live-Switch.
- **Audit-Log** ist Foundation-only — kein UI im MVP. Kommt in späterem Bundle.
- **Migration ist idempotent**: zweiter Start ohne Marker → Migration versucht erneut;
  lokale Datei-Kopie übersprungen falls Ziel bereits existiert.
- **ARCHITECTURE.md**: Entscheidung 13 ergänzt (Tenant-Pattern).

---

## Bundle 4.5 — GitHub-Backup (2026-05-11)

**Status: ✅ Abgeschlossen**

### Implementiert

- **GitHubBackup-Klasse** (`tools/github_backup.py`): Off-Site Code-Backup via
  privatem GitHub-Repo. Auto-Commit alle 6h falls Änderungen vorliegen, Push zu
  Remote. Bei Offline: Commit lokal, Push beim nächsten Cycle (Git puffert nativ).
- **Background-Thread** analog zu AutoBackup: daemon + atexit-Event-Cleanup.
- **Status-API**: `last_commit_time()`, `last_push_time()`, `commits_today()`,
  `has_uncommitted_changes()`, `is_configured()`, `self_test() → dict`
- **Befehle in main.py**:
  - `system github init` → einmaliges Repo-Setup (git init, remote, initial commit, push)
  - `system github commit` → manueller Commit + Push
  - `system github status` → Branch, letzter Commit, Änderungen, Push-Zeit
- **`.gitignore`** (neu im Repo-Root): schützt `.env`, `temp/`, `logs/`, `backups/`,
  `memory/clients/`, `claude_project_upload/`, Python-Artifacts, IDEs, OS-Dateien
- **`docs/RECOVERY.md`** (neu): vollständige Wiederherstellungs-Doku mit 5-Schritt-
  Plan, Checkliste, Hinweisen zu Cloud-Memory-Recovery + GitHub-PAT-Erneuerung
- **13. Subsystem "github"** in `tools/system_test.py`: prüft Konfiguration,
  Remote-Erreichbarkeit und ob `.env` in Git-History vorhanden (kritisch!)
- **ENV-Vars in `.env`** ergänzt: `GITHUB_REPO_URL`, `GITHUB_TOKEN`,
  `GITHUB_AUTOBACKUP`, `GITHUB_INTERVAL_HOURS`

### Geänderte Files

- `tools/github_backup.py` — **neu:** `GitHubBackup`-Klasse mit Auto-Commit-Thread
- `.gitignore` — **neu:** schützt Secrets und Laufzeit-Daten vor Commit
- `docs/RECOVERY.md` — **neu:** Disaster-Recovery-Dokumentation
- `tools/system_test.py` — `github_backup`-Parameter + `_test_github()`-Methode
- `core/main.py` — Import `GitHubBackup`, Thread-Start, `system github *`-Befehle,
  `github_backup=_github_backup` in SystemTest-Aufruf
- `.env` — GitHub-Backup-Variablen-Block ergänzt

### Neue Status-APIs

- `GitHubBackup.last_commit_time() → datetime | None`
- `GitHubBackup.last_push_time() → datetime | None`
- `GitHubBackup.commits_today() → int`
- `GitHubBackup.has_uncommitted_changes() → bool`
- `GitHubBackup.is_configured() → bool`
- `GitHubBackup.self_test() → dict`

### Notizen

- **Code-Backup ≠ Daten-Backup**: Cloud-Memory bleibt auf Vercel, lokale Daten
  in `temp/`/`logs/`/`backups/` — nur Code geht ins GitHub-Repo.
- **Token-Sicherheit**: GITHUB_TOKEN wird nie geloggt (in `_auth_url()` und
  `_safe_output()` maskiert). Gespeicherte Remote-URL enthält keinen Token.
- **Offline-Robustheit**: Commit lokal erstellen geht immer; Push schlägt bei
  Offline fehl mit `[GITHUB-FAIL]`-Warnung; nächster Cycle versucht erneut.
- **`system test github`**: schlägt mit FAIL an falls `.env` in Git-History —
  eingebaut als Sicherheitsnetz falls Commit-Fehler passiert.
- **ARCHITECTURE.md**: neue Entscheidung 12 ergänzt (Code-Backup via Git
  getrennt von Daten-Backup via Cloud + lokale Snapshots).

---

## Bundle 4 — System-Test-Funktion (2026-05-11)

**Status: ✅ Abgeschlossen**

### Implementiert

- **SystemTest-Klasse** (`tools/system_test.py`): 12 Subsystem-Tests mit
  `run_all() → list[TestResult]`, `run_one(name) → TestResult | None`,
  `available_names() → list[str]`
- **TestResult-Dataclass**: `name`, `status` ("ok"|"warn"|"fail"), `summary`, `fix_hint`
- **12 Subsystem-Tests**: cloud, llm, stt, tts, vision, mic, filesystem,
  memory, skills, session, backup, env
- **`print_system_test(results)`** in `UIRenderer` ABC (neu: abstract method) +
  `TerminalRenderer` (farbige Tabelle: grün/gelb/rot + Reparatur-Hinweise)
- **Befehls-Routing** in `main.py`:
  - `system test` → alle 12 Tests
  - `system test <name>` → Einzeltest (cloud, tts, mic, …)
  - `system test xyz` → Fehlermeldung mit Liste verfügbarer Tests

### Geänderte Files

- `tools/system_test.py` — **neu:** `TestResult` + `SystemTest` mit 12 Test-Methoden
- `core/ui_renderer.py` — `print_system_test(results)` als `@abstractmethod` ergänzt
- `core/ui.py` — `print_system_test()` in `TerminalRenderer` + Forwarding-Funktion
- `core/main.py` — Import `SystemTest`, `system test*` Befehlsblock

### Neue Status-APIs

- `SystemTest.run_all() → list[TestResult]` — vollständige Diagnose
- `SystemTest.run_one(name) → TestResult | None` — Einzeltest
- `SystemTest.available_names() → list[str]` — verfügbare Test-Namen

### Notizen

- **LLM-Test** macht einen echten API-Call mit `max_tokens=5` — Kosten < $0.001 pro Aufruf
- **Session-Test** zeigt "unclean-Flag aktiv" während laufender Session (normaler Zustand)
- **Backup-Test**: "noch kein Auto-Backup in dieser Sitzung" bis erster 6h-Zyklus läuft
- **ARCHITECTURE.md**: kein Update nötig — keine neuen Architektur-Entscheidungen.
  UIRenderer-ABC-Erweiterung um `print_system_test()` ist reguläre Feature-Ergänzung
  gemäß bestehender Konvention (wie `print_broker_status`)

---

## Bundle 3 — Plugin-Architektur (2026-05-11)

**Status: ✅ Abgeschlossen**

### Implementiert

- **Feature 1 — Skill-Plugin-System:** `Skill` ABC + `registry.py` mit Auto-Discovery via `pkgutil.walk_packages`; `ProfessorSkill` refactored; `PingSkill` als Test-Skill; generischer Skill-Dispatch in `main.py`
- **Feature 2 — UI-Adapter-Layer:** `UIRenderer` ABC mit 13 Methoden; `TerminalRenderer` als einzige Implementierung; `ui_factory.py` Singleton (`ZUKI_UI` ENV); Modul-Level-Forwarding für Abwärtskompatibilität
- **Feature 3 — Provider-Stubs:** `"local"` als vierter LLM-Provider-Kandidat in `api_manager.py` (`LOCAL_LLM_URL`/`LOCAL_LLM_MODEL`); `PCControl`-Stub mit 10 Methoden und plattformspezifischen LIVE-UPGRADE-Kommentaren

### Neue / geänderte Files

- `workspaces/base.py` — neu: `Skill` ABC
- `workspaces/registry.py` — neu: Auto-Discovery + `get_skill_for()` + Status-API
- `workspaces/professor/professor.py` — `ProfessorSkill` angehängt
- `workspaces/test_skill.py` — neu: `PingSkill` (ping → pong)
- `workspaces/__init__.py`, `workspaces/professor/__init__.py`, `workspaces/broker/__init__.py`, `workspaces/business/__init__.py` — neu: leere Package-Marker
- `core/ui_renderer.py` — neu: `UIRenderer` ABC
- `core/ui.py` — refactored: alle Funktionen → `TerminalRenderer`-Methoden; Forwarding-Layer erhalten
- `core/ui_factory.py` — neu: `get_renderer()` Singleton, `reset_renderer()`
- `core/api_manager.py` — `"local"` Provider + `_call_local()` Stub + `NotImplementedError`-Propagation
- `tools/pc_control.py` — neu: `PCControl` Stub mit 10 Methoden
- `core/main.py` — Skill-Dispatch; `ui_factory`-Import; `ui: UIRenderer` global
- `.env` — `LOCAL_LLM_URL=`, `LOCAL_LLM_MODEL=`, `ZUKI_UI=terminal`

### Neue Status-APIs

- `skill_registry.skill_count() → int` — Anzahl registrierter Skills
- `skill_registry.list_names() → list[str]` — Namen aller Skills
- `renderer.kind() → str` — Renderer-Bezeichner (`"terminal"` | …)
- `PCControl.available() → bool` — immer `False` solange Stub

### Notizen für nächste Bundles

- **Bundle 13 (UI-Foundation):** `UIRenderer`-ABC ist vorbereitet — neuer Web-Renderer muss nur erben + `ZUKI_UI=web` setzen; `ui_factory.py` als Einstiegspunkt statt direktem `ui.py`-Import
- **Bundle 8 (Plattform-Agnostik):** `PCControl.open_app()` / `lock_screen()` etc. sind bereits als Stubs registriert — nur `_call_local()` und PCControl-Methoden befüllen
- **`NotImplementedError` propagiert** durch `chat()` — wer Local-LLM aktiviert ohne Implementierung, sieht sofort klares Feedback statt stillem SIM-Fallback

---



## Bundle 1 — Resilienz-Layer

### Feature 1 — Schema-Versionierung
**Dateien:** `tools/cloud_memory.py`, `zuki_cloud/api/index.py`

- `cloud_memory.py → save()`: Jeder Cloud-Eintrag erhält jetzt `"v": 1` im Payload-Dict.
- `zuki_cloud/api/index.py → POST-Handler`: `"v": body.get("v", 1)` wird aus dem Request-Body gelesen und im Redis-Entry gespeichert.
- Zweck: Vorwärtskompatibilität — zukünftige Schema-Änderungen können via `v`-Feld migriert werden.

### Feature 2 — Offline-Outbox
**Dateien:** `tools/cloud_memory.py`

Neue Klasse `_Outbox` und Integration in `CloudMemory`:

- **`_Outbox`** (`tools/cloud_memory.py`):
  - Crash-sichere JSONL-Datei `temp/cloud_outbox.jsonl` (append + fsync).
  - `queue(payload)` — Eintrag anhängen; No-Op während eines laufenden Flush (`_in_flush`-Flag, verhindert Endlos-Duplikate).
  - `flush_async()` — startet FIFO-Flush in Daemon-Thread (idempotent).
  - `_flush()` — verarbeitet Einträge, entfernt erste Zeile nach erfolgreichem POST, bricht bei Netzwerkfehler ab.
  - `_remove_first_line()` — atomares Entfernen der ersten Zeile via Temp-File + Rename.
  - Status-API: `size()`, `is_flushing()`, `last_flush_time()`.

- **`CloudMemory._post()`**: Bei `URLError`/`TimeoutError` → Payload wird in Outbox gequeuet (sofern nicht `_in_flush`).
- **`CloudMemory.ping()`**: Erfolgreicher Ping → `outbox.flush_async()` triggern.
- **`CloudMemory.__init__()`**: Outbox-Instanz wird erzeugt, path = `temp/cloud_outbox.jsonl`.

**Fixes implementiert:**
- `_in_flush`-Flag verhindert Re-Queue während Flush (Endlos-Duplikat-Bug).
- `_last_flush` in `finally`-Block → wird auch bei Fehler gesetzt.
- Test mit non-routeable IP `10.255.255.1` statt Fake-URL (echte `URLError` statt `HTTPError`).

### Feature 3 — Auto-Backup-Thread
**Dateien:** `tools/backup_manager.py`, `core/main.py`

- **`_prune_old_snapshots(keep=7)`** (`tools/backup_manager.py`):
  - Liest `list_snapshots()` (neueste zuerst).
  - Löscht alle Snapshots ab Index `keep` via `shutil.rmtree`.

- **`AutoBackup`** (`tools/backup_manager.py`):
  - `DEFAULT_INTERVAL = 6 * 3600` (6 Stunden), `MAX_SNAPSHOTS = 7`.
  - `start()` — startet Daemon-Thread `_loop()`, registriert `stop_event.set` via `atexit`.
  - `_loop(stop_event)` — `while not stop_event.wait(timeout=interval)`.
  - `_run_snapshot()` — `create_snapshot()` + `_prune_old_snapshots(7)`.
  - Status-API: `last_snapshot_time()`, `snapshot_count()`, `next_scheduled()`.
  - Log-Marker: `[AUTOBACKUP]`.

- **`core/main.py`**: `AutoBackup().start()` in `run()` aufgerufen.

---

## Bundle 2 — State-Recovery

### Feature 4 — Session-Recovery
**Dateien:** `tools/session_state.py` (neu), `core/main.py`

- **`SessionState`** (`tools/session_state.py`):
  - Pfad: `temp/session_state.json`.
  - `save(state)` — Debounced 2s via `threading.Timer` (Pending-Timer wird bei erneutem Aufruf abgebrochen).
  - `flush(state)` — Sofortiger Schreibvorgang (umgeht Debounce), z. B. bei Exit.
  - `load()` — Lädt JSON; gibt `None` zurück wenn Datei fehlt oder ungültig.
  - `clear()` — Löscht Datei, setzt `_last_clean` Timestamp.
  - `is_unclean()` / `has_unclean_state()` — `True` wenn Datei vorhanden (= unclean Exit).
  - `last_clean_shutdown()` — In-Memory Timestamp des letzten sauberen Shutdowns.

- **State-Dict** (in `session_state.json`):
  `broker_mode`, `cloud_auto_save`, `cloud_session_id`, `cloud_save_count`, `last_response` (max 500 Zeichen), `timestamp`.

- **`core/main.py`** Integration:
  - `SessionState` wird nach Instance-Guard initialisiert.
  - Unclean-Check → User-Angebot zur Session-Wiederherstellung (Broker-Modus, last Response).
  - `_save_state()` — Closure, die aktuellen `broker_mode`/`last_response` aus enclosing scope liest.
  - `atexit`-Reihenfolge (LIFO): `state.clear` zuerst registriert → wird als letztes ausgeführt.
  - Log-Marker: `[SESSION-RECOVER]`, `[SESSION-STATE]`.

### Feature 5 — Bio-Recovery aus Cloud
**Dateien:** `tools/cloud_memory.py`, `memory/user_profile.py`, `zuki_cloud/api/index.py`, `core/main.py`

- **`CloudMemory.get_latest_bio()`** (`tools/cloud_memory.py`):
  - `GET {url}?source=bio&limit=1`.
  - Parst das `text`-Feld als JSON.
  - Gibt `{"data": bio_data, "saved_at": saved_at}` zurück oder `None`.

- **`zuki_cloud/api/index.py` (GET-Handler)**:
  - `source_filter = request.args.get("source", "")` — Python-seitiges Filter-Loop.
  - Lädt bis zu `MAX_ENTRIES` Einträge aus Redis, bricht beim Erreichen des `limit` ab.

- **`UserProfile`** (`memory/user_profile.py`):
  - `set_cloud(cloud)` — setzt `self._cloud`.
  - `last_cloud_sync()` — gibt `self._last_sync` zurück.
  - `_sync_to_cloud()` — serialisiert `_data` als JSON-String, ruft `cloud.save(payload, source="bio")` auf.
  - `extract_and_update()` — ruft `_sync_to_cloud()` nach erlernten Fakten.
  - Log-Marker: `[BIO-SAVE]`.

- **`core/main.py`** Integration:
  - `profile.set_cloud(cloud)` nach Cloud-Initialisierung.
  - Bio-Recovery-Block: wenn `profile` leer + Cloud verfügbar → `get_latest_bio()` → `profile.load_dict()`.
  - Log-Marker: `[BIO-RECOVER]`.

---

## Bundle 3 — Plugin-Architektur

### Feature 1 — Skill-Plugin-System
**Dateien:** `workspaces/base.py` (neu), `workspaces/registry.py` (neu), `workspaces/professor/professor.py`, `workspaces/test_skill.py` (neu), `workspaces/__init__.py`, mehrere `__init__.py`-Marker, `core/main.py`

- **`Skill` ABC** (`workspaces/base.py`):
  - `name: str` — eindeutiger Skill-Name (Pflicht).
  - `triggers: set[str]` — Befehlswörter die den Skill auslösen.
  - `handle(context: dict) -> str | None` — abstrakt; `None` = Skill hat nichts zu sagen.
  - Context-Dict enthält: `user_input`, `cmd`, `api_mgr`, `llm`, `profile`.

- **`registry.py`** (`workspaces/registry.py`):
  - `discover_skills()` — `pkgutil.walk_packages` scannt `workspaces/`-Paket, importiert alle Module, instantiiert alle `Skill`-Subklassen, registriert nach Trigger (lowercase).
  - `get_skill_for(cmd)` — erstes Wort von `cmd` als Lookup-Key.
  - Status-API: `skill_count()`, `list_names()`.
  - Log-Marker: `[SKILL-DISCOVER]`.

- **`ProfessorSkill`** (ans Ende von `workspaces/professor/professor.py` angehängt):
  - `triggers = {"explain", "erklaer", "erklaere", "erkläre"}`.
  - `handle()` — ruft bestehende `build_sim_response()` / `build_live_prompt()` + `api_mgr.chat()` auf.

- **`PingSkill`** (`workspaces/test_skill.py`):
  - Trigger: `"ping"` → Antwort: `"pong  ·  Skill-System funktioniert."`.

- **Package-Marker** `__init__.py`:
  - `workspaces/__init__.py`, `workspaces/professor/__init__.py`, `workspaces/broker/__init__.py`, `workspaces/business/__init__.py` — leer, für `pkgutil.walk_packages`.

- **`core/main.py`** Integration:
  - `from skills import registry as skill_registry`.
  - `skill_registry.discover_skills()` einmalig beim Start.
  - Generischer Skill-Dispatch ersetzt den früheren hardcodierten Professor-Block:
    ```python
    skill = skill_registry.get_skill_for(cmd)
    if skill:
        response = skill.handle({...})
    ```
  - Log-Marker: `[SKILL-INVOKE]`.

---

### Feature 2 — UI-Adapter-Layer
**Dateien:** `core/ui_renderer.py` (neu), `core/ui.py` (refactored), `core/ui_factory.py` (neu), `core/main.py`

- **`UIRenderer` ABC** (`core/ui_renderer.py`):
  - Abstrakte Basis für alle Renderer mit vollständiger Methoden-Signatur:
    `print_banner`, `print_dashboard`, `user_prompt`, `speak_zuki`,
    `listening`, `thinking`, `speaking`, `system_msg`, `error_msg`,
    `voice_echo`, `print_broker_status`, `print_broker_deactivated`.
  - `kind() -> str` — Renderer-Bezeichner für Status-API.

- **`TerminalRenderer(UIRenderer)`** (`core/ui.py`):
  - Alle bisherigen Modul-Funktionen wandern als Methoden in die Klasse.
  - ANSI-Konstanten und Box-Helfer bleiben modul-level (privat).
  - Modul-Level-Forwarding-Funktionen für Abwärtskompatibilität:
    `from core import ui; ui.speak_zuki(...)` funktioniert weiter.
  - `kind()` gibt `"terminal"` zurück.

- **`ui_factory.py`** (`core/ui_factory.py`):
  - `get_renderer() -> UIRenderer` — Singleton, lazy-initialisiert.
  - Liest `ZUKI_UI` ENV (Standard: `"terminal"`).
  - Unbekannter Key → Warning + Fallback auf `"terminal"`.
  - `reset_renderer()` — setzt Singleton zurück (für Tests).
  - Log-Marker: `[UI-INIT]`.

- **`core/main.py`**:
  - `from core import ui` → `from core.ui_factory import get_renderer as _get_renderer`.
  - Modul-Level-Fallback `ui: UIRenderer = _get_renderer()`.
  - In `run()`: `global ui; ui = _get_renderer()` nach `load_env()` (ZUKI_UI aus .env wirkt).

- **`.env`**: `ZUKI_UI=terminal` hinzugefügt.

### Feature 3 — Provider-Stubs
**Dateien:** `core/api_manager.py`, `tools/pc_control.py` (neu), `.env`

- **Local-LLM-Stub** (`core/api_manager.py`):
  - `_is_valid_local(url)` — prüft `LOCAL_LLM_URL` auf Non-Placeholder.
  - `_detect_provider()` — prüft `"local"` als vierter Kandidat (vor `"sim"`).
  - `provider_label` — gibt `"Local LLM (<modell>)"` zurück.
  - `_call_local(prompt, system, max_tokens)` — Stub mit ausführlichem LIVE-UPGRADE-Kommentar für Ollama und OpenAI-kompatible Endpunkte; wirft `NotImplementedError`.
  - `chat()` / `chat_messages()` — `except NotImplementedError: raise` damit Stub-Fehler nicht geschluckt werden.
  - Log-Marker: `[LOCAL-LLM-STUB]`.

- **`PCControl`** (`tools/pc_control.py`):
  - Stub-Klasse mit Methoden: `open_app`, `close_app`, `shutdown_pc`, `restart_pc`, `lock_screen`, `set_volume`, `mute`, `get_clipboard`, `set_clipboard`, `open_file`.
  - Alle Methoden: Log-Eintrag + `NotImplementedError` mit LIVE-UPGRADE-Kommentaren (Windows / macOS / Linux).
  - `available() -> False` — Status-API, wird `True` sobald implementiert.
  - Log-Marker: `[PC-CONTROL-STUB]`.

- **`.env`**:
  - `LOCAL_LLM_URL=` (leer = Stub inaktiv).
  - `LOCAL_LLM_MODEL=`.
  - Kommentare mit Beispiel-URLs (Ollama, LM Studio).
