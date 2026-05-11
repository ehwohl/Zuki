# Zuki Roadmap

> Stand: 2026-05-11
> Lebendiger Plan. Wird nach jedem Bundle vom verantwortlichen
> Chat aktualisiert (Status, Notizen, eventuelle Neuordnung).

## Status-Legende

- ✅ Done
- 🟡 In Progress
- ⬜ Pending
- 🔒 Cross-cutting (muss in EINEM Chat bleiben)
- 💤 Deferred (bewusst zurückgestellt)

---

## Workflow-Regeln

1. **Pro Bundle ein eigener Chat** — Naming: `Zuki Bundle X — <Titel>`
2. **Letzte Aufgabe jedes Bundle-Chats:** ARCHITECTURE.md + CHANGELOG.md
   aktualisieren, dann Upload-Ordner refreshen.
3. **Cross-cutting Bundles** (🔒 markiert) bleiben in einem langen Chat,
   weil sie viele Module gleichzeitig anfassen.
4. **Faustregel:** Bundle berührt ≥ 4 Files in verschiedenen Modulen → 🔒.

---

## Phase 1 — Resilienz-Layer (Foundation der Datensicherheit)

### Bundle 1 — Resilienz Basis ✅
- Schema-Versionierung (`"v": 1` in Cloud-Einträgen)
- Offline-Outbox (Cloud-Saves überleben Verbindungsausfälle)
- Auto-Backup-Thread (alle 6h, behalte 7 Snapshots)

### Bundle 2 — State-Recovery ✅
- Session-Recovery (Crash → letzten Modus wiederherstellen)
- Bio-Recovery aus Cloud (Profil verloren → aus Cloud zurück)

### Bundle 3 — Plugin-Architektur ✅
- ✅ Feature 1: Skill-Plugin-System mit Auto-Discovery
- ✅ Feature 2: UI-Adapter-Layer (UIRenderer ABC, TerminalRenderer, ui_factory)
- ✅ Feature 3: Provider-Stubs (Local-LLM-Stub, PCControl-Stub)

---

## Phase 2 — Robustheit & Infrastruktur

### Bundle 4 — System-Test-Funktion ✅
- Selbst-Diagnose aller Subsysteme (Cloud, LLM, STT, TTS, Vision, Mic, FS)
- `system test` Befehl + `system test <subsystem>`
- Grün/Gelb/Rot pro Komponente mit konkretem Reparatur-Hinweis
- Migration-Validator: läuft auf neuem PC nach Umzug, zeigt was kaputt ist

### Bundle 4.5 — GitHub-Backup ✅
- Privates Repo, Auto-Commit alle 6h falls Code-Änderungen
- `.gitignore` schützt `.env`, `temp/`, `logs/`, `backups/`, Client-Daten
- Push zu Remote als Off-Site-Sicherung
- Wiederherstellungs-Workflow dokumentiert (`docs/RECOVERY.md`)
- 13. Subsystem in `system test`: konfiguriert? Remote erreichbar? .env getrackt?

### Bundle 5 — Tenant-Pattern ✅
- `tenant_id` in allen Datenstrukturen (History, Cloud, Profile)
- Workspace-Switch: `tenant switch self` / `tenant switch client-schmidt`
- Cloud-Listen pro Tenant: `zuki:memories:{tenant}` + Audit `zuki:audit:{tenant}`
- LLM-Provider per Tenant konfigurierbar
  (Privat → Gemini Free OK, Business → nur DSGVO-konforme Provider)
- Audit-Log-Foundation pro Tenant (Foundation, UI kommt später)
- Einmalige Migration: user_profile.txt → user_profile_self.txt + Cloud-Key-Migration
- 14. Subsystem "tenant" in system test

### Bundle 6 — Router-Agent ⬜
- Multi-Skill-Orchestrierung (LLM entscheidet welche Skills)
- Cloud-Listen pro Skill: `zuki:skill:{name}:conversations`
- Router-Decision-Log für Tuning
- Output zeigt: Endergebnis + "verwendete Skills: X, Y"

### Bundle 7 — Cleanup-Befehle ⬜
- Selektive Lösch-Befehle (`cleanup vision`, `cleanup chats`, `cleanup old`)
- Geschützte Daten (Bio, Code, .env, "system": true Flag)
- UI-Variante (Liste mit Checkboxen) später in Bundle 16
- Cloud-Cleanup via API-Endpunkt

### Bundle 8 — Plattform-Agnostik 🔒⬜
- TTS-Backend-Pattern: WindowsTTS (pyttsx3) / LinuxTTS (Piper)
- Window-Control-Backend: WindowsWindowBackend / LinuxWindowBackend
  (Win32 / xdotool+wmctrl)
- Audio-In-Pfade für Linux validieren
- Linux-Ziel-Distro: Pop!_OS 22.04 oder Ubuntu 24.04 LTS
- **Cross-cutting: berührt TTS, PC-Control, Audio. Daher 🔒.**

---

## Phase 3 — Business-Foundation

### Bundle 8.5 — Web-Scraping-Layer ⬜
- `tools/scraper.py` mit User-Agent-Rotation, Rate-Limiting
- Adapter pro Quelle (Google Business Profile, Instagram Public, etc.)
- Caching damit gleicher Lookup nicht 10× erfolgt
- Wiederverwendbar von Broker, Business, Office Skills

### Bundle 8.6 — PDF-Report-Generator ⬜
- `tools/report.py` mit Template-System
- Branded PDFs (Logo, Footer, Kunden-Daten)
- Templates: Analyse-Report, Steuer-Übersicht, Workflow-Audit
- Library: `reportlab` oder `weasyprint`

### Bundle 8.7 — Knowledge-Base-Pattern ⬜
- Branchen-spezifisches Wissen in `knowledge/` als YAML/JSON
- Erweiterbar: Gastro zuerst, später Friseure, Handwerker, etc.
- Pro Branche: Daten-Quellen, typische Schwachstellen, Tool-Empfehlungen,
  KPIs, Branchen-Glossar

---

## Phase 4 — Skills

### Bundle 9 — Coding-Skill + Scratchpad ⬜
- Multi-Language Scratchpad (Python, JS, TS, Bash, Go, Pine Script)
- Sandbox-Ausführung in isoliertem temp/sandbox/ mit Timeout
- Pine Script: nicht lokal ausführbar → "Copy to TradingView" Button
- Persistente Buffer pro Sprache

### Bundle 10 — Office-Skill mit Google Drive ⬜
- OAuth2 Google API Anbindung
- OCR-Pipeline (Tesseract lokal + Gemini Vision Fallback)
- LLM-Klassifikation (Lohnabrechnung, Rechnung, Vertrag, etc.)
- Tag-System + lokale SQLite-Index
- Retrieval: "Such mir Steuererklärung 2025 raus" → Ordner-Erstellung
- Multi-Tenant: Drive-Subfolder pro Tenant

### Bundle 11 — Music-Practice ⬜
- Pitch-Detection via librosa/aubio
- Instrument-Lern-Modus (Noten vorgegeben, Echtzeit-Feedback)
- Gesangs-Modus (Tonhöhe + Intonation)
- KEIN Voice-Swap und KEINE Beats hier (kommt später als
  separater Sub-Skill in Bundle 19)

### Bundle 12 — Business-Skill MVP (Gastro-Analyzer) ⬜
- Google Business Profile Scraper für eine Adresse
- Konkurrenz-Analyse 1km-Radius
- Social-Media-Public (Instagram, Facebook) Check
- Schwachstellen-Erkennung (Bewertungs-Antwortrate, Post-Frequenz, etc.)
- 1-2 Seiten PDF-Report für Erstgespräch
- Manueller Workflow-Audit-Fragebogen (Zuki führt Interview)
- **Praxistest mit 5-10 echten Restaurants vor Weiterentwicklung**

---

## Phase 5 — UI-Foundation

### Bundle 13 — UI-Foundation (Vite + React + TS + Tailwind) ⬜
- `zuki_ui/` Subprojekt mit Build-System
- Multi-Panel-Shell mit `react-grid-layout`
- WebSocket-Bridge zu Zuki Core (`useZukiSocket` Hook)
- State Management mit `zustand`
- Test-Panel (Status-Anzeige aller Manager) als erstes Panel

### Bundle 14 — Avatar-Panel ⬜
- 3D-Modus: Three.js + three-vrm Library
- 2D-Modus: Live2D Cubism Web SDK
- Switchbar via Settings (`AVATAR_MODE=vrm|live2d` in .env)
- Lip-Sync zu TTS-Audio-Amplitude
- Idle-Animationen (Blink, leichte Kopfbewegung)
- Event-getriggerte Reaktionen (Lauschen, Denken, Sprechen)

### Bundle 15 — Neural-Map-Panel ⬜
- D3.js Force-Directed Graph
- Knoten pro aktivem System (Cloud, Vision, Skills, Provider)
- Pulse-Animation bei aktiver Nutzung
- Verbindungslinien zeigen aktuelle Datenflüsse
- Konfigurierbar: nur aktive Knoten oder Komplett-Übersicht

### Bundle 16 — Skill-Panels ⬜
- Broker-Chart-Panel (lokales Matplotlib/Plotly für News-Preis-Annotation)
- Office-Dokumenten-Panel (Drive-Browser + Suche)
- Business-Dashboard-Panel (Kunden-Liste, Reports, Status)
- Code-Scratchpad-Panel (Monaco Editor)
- Cleanup-Panel mit Checkboxen (löst Bundle 7 UI-Komponente ab)

---

## Phase 6 — Business-Vollausbau

### Bundle 17 — Business Vermittler ⬜
- CRM für Kunden + Leads
- Agentur-Datenbank (deine Partner mit Konditionen)
- Provisions-Tracking pro Vermittlung
- Status-Workflow (Erstkontakt → Analyse → Empfehlung → Vermittlung → Provision)
- E-Mail-Templates pro Stage

### Bundle 18 — Business Optimizer ⬜
- Workflow-Audit-Tool (Zuki interviewt Kunde zu Prozessen)
- Bottleneck-Identifikation
- Tool-Empfehlungs-Engine mit ROI-Rechner
- Implementation-Roadmap pro Kunde
- Retainer-fähig: monatliche Reviews automatisiert

---

## Phase 7 — Erweiterungen

### Bundle 19 — Music-Create 💤
- Beat-Generierung (Suno/Udio API ODER lokales MusicGen)
- Voice-Swap via lokales RVC (privat-only, GEMA-konform)
- Track-Composing-UI

### Bundle 20 — Streaming-Skill 💤
- Twitch/YouTube Chat-Integration
- Donation-Trigger via Streamlabs API
- HTML5-Mini-Games mit Parameter-Steuerung durch Chat
- Voice-Effekte (kein Real-Person-Deepfake)
- Cartoon-Avatar-Swaps

### Smart Home Integration 💤
- Erst wenn Hardware vorhanden
- Home Assistant als zentraler Hub
- Homebridge für Apple-HomeKit-Brücke
- AirPods/iPad/Watch über bestehende Apple-Pfade

---

## Bewusst zurückgestellt

### Verschlüsselung Cloud-Daten 💤
Wartet bis Tenant-Pattern (Bundle 5) steht und echte Business-Daten
fließen. Davor Symbolik ohne realen Schutzgewinn.

### Search-Endpoint (Cloud) 💤
Erst wenn >50 Einträge regelmäßig durchsucht werden müssen.
Bis dahin reicht das `/view?limit=200` Endpoint.

### Multi-Device-Sync 💤
Konfliktauflösung zu komplex für aktuellen Use-Case (ein Rechner).
`session_id` ist als Vorbereitung schon angelegt.

### Onboarding-Wizard 💤
`.env` direkt editieren ist effizienter als Wizard.

---

## Aktueller Fokus

✅ **Bundle 4.5** abgeschlossen (GitHub-Backup, Off-Site Code-Backup via privatem Repo)
⬜ **Nächste Schritte:** Bundle 5 (Tenant-Pattern) — `.env` mit GITHUB_REPO_URL + GITHUB_TOKEN befüllen, dann `system github init`

---

## Pflege dieser Datei

Sonnet pflegt sie am Ende jedes Bundles:
- Bundle-Status auf ✅ setzen
- Notizen ergänzen falls Architektur-Entscheidung sich geändert hat
- Reihenfolge anpassen wenn Bundles getauscht werden müssen
- Beim Vollausbau: deferred Items reaktivieren oder endgültig löschen
