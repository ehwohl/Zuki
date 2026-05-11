# Zuki — Vision & Hintergrund

> **Zweck:** Das **Warum** hinter Zuki. Geschäftsmodell, Hardware-Ziel,
> strategische Entscheidungen, Skill-Vision. Für **Was/Wann** siehe
> ROADMAP.md. Für **Wie/Begründungen** siehe ARCHITECTURE.md.
>
> **Zielpublikum:** Neue Claude-Code-Chats die verstehen müssen worauf
> sie hinarbeiten — und der Nutzer selbst zum Nachschlagen.

---

## Wer ist der Nutzer

Privatperson aus Deutschland. Plant Selbstständigkeit als Dienstleister
für KMU. Startet mit Gastronomie als Branchen-Fokus (hohe lokale
Marktdichte). Hat eingekaufte Agentur-Partner-Liste für Vermittlungs-
Geschäft.

Aktuell: Windows 11. Plant: PC-Upgrade und Linux-Migration sobald Zuki
stabil ist. Apple-Ökosystem (iPhone, plant iPad/Watch/AirPods).

Single-User-System. Multi-Device-Sync ist bewusst KEIN Ziel.

---

## Was ist Zuki am Ende

Persönlicher KI-Assistent ähnlich Jarvis. Lebt auf dem PC, nutzbar für
Privates UND Geschäftliches.

**Konkret:**
- Spracheingabe + Hotword ("Zuki, ...")
- 2D- oder 3D-Avatar in moderner Web-UI
- Steuert den PC (Fenster, Programme, später auch fremde Apps)
- Cloud-Memory für Erinnerungen + Bio
- Multiple Skills: Coding, Office, Music, Business, etc.
- Trennt Privat-Daten von Kunden-Daten (Multi-Tenant)
- Läuft langfristig auf Linux (Pop!_OS oder Ubuntu)

**NICHT:** Cloud-gehostet, Multi-User-fähig, kommerzielles SaaS.

---

## Geschäftsmodell

Selbstständigkeit mit drei Einnahme-Strömen:

### 1. Analyse (Türöffner)
Kostenlos/symbolisch. Schnelle Vor-Ort-Analyse eines KMU in 10-20 Min.
"Hier ist was wir sehen, hier ist was wir empfehlen." Schafft Vertrauen,
dreht den Bittsteller-Frame um — Kunde fragt nach Service statt umgekehrt.

### 2. Vermittlung von Agenturdienstleistungen (einmalige Provision)
SEO, Mitarbeitergewinnung, Online-Auftritt. Aus eingekaufter Partner-
Liste. Niedrigere Bindung, gute Marge ohne Eigenarbeit.

### 3. Workflow-Optimierung (Retainer)
Bestehende Prozesse analysieren und optimieren. Höchste Kundenbindung
weil "Ich verstehe deine Firma jetzt". Wiederholbar, höhere Margen.

**Branchen-Fokus zum Start:** Gastronomie.
Solo-Selbstständige bis kleine Restaurants. Bekannte Pain-Points
(Bewertungs-Management, Personalplanung, Online-Sichtbarkeit), klares
Tool-Ökosystem (Resmio, Gastronovi, OpenTable, etc.).

Zuki ist das Werkzeug das alle drei Pfade möglich macht — die Analyse
muss beim Erstgespräch beeindrucken können.

---

## Strategische Architektur-Entscheidungen

### Multi-Tenant von Anfang an
Privat-Modus "self" und Business-Tenants ("client-schmidt") strikt
getrennt. Daten + LLM-Provider-Wahl pro Tenant. Business-Daten brauchen
DSGVO-konforme Provider — Gemini-Free-Tier ist da kritisch.

### Provider-Agnostik
LLMs (Gemini, Claude, GPT, später lokales LLM via RTX 5090) sind
austauschbar via APIManager. Keine Vendor-Lock-ins.

### UI-Agnostik
Core läuft headless. UI ist Schicht obendrauf — Terminal jetzt,
React-Web-UI später. UIRenderer-ABC erlaubt Wechsel ohne Core-Touch.

### Plattform-Agnostik
Backend-Patterns für TTS und Window-Control mit Windows + Linux
Implementierungen. Pfade über pathlib. Linux-Migration als geplante
Phase, nicht Refactor.

### Resilienz vor Features
Bevor neue Skills gebaut werden: Datensicherheit (Schema-Versioning,
Offline-Outbox, Auto-Backup, Session-Recovery, Bio-Recovery,
GitHub-Backup). Robustes Fundament mit 5 Skills > wackliges mit 50.

### Cloud für Daten, lokal für Assets
Cloud-Memory speichert Erinnerungen + Bio. UI-Assets (Avatare, Icons,
Schriftarten) bleiben lokal — bessere Latenz, Offline-Robust.

### Token-Bewusstsein
UI verbraucht 0 LLM-Tokens. Avatar reagiert lokal auf TTS-Amplitude,
Neural Map auf lokale Events. Tokens nur durch User-Aktionen.

---

## Hardware-Ziel-Setup (langfristig)

```
        ┌────────────────────────────────────┐
        │  Wall: Samsung SH37F Stretched     │
        │  (TradingView ambient, gebraucht   │
        │   wegen EOL)                       │
        └────────────────────────────────────┘
        ┌────────────────────────────────────┐
        │  Hauptmonitor: 49" Odyssey OLED G9 │
        │  ← Job-Laptop via HDMI             │
        └────────────────────────────────────┘
             ┌──────┬─────────┬──────┐
             │Xeneon│  ASUS   │Xeneon│
             │Avatar│ Stylus  │ Map  │
             │      │  Notes  │      │
             └──────┴─────────┴──────┘
        ┌────────────────────────────────────┐
        │  Galleon SD Tastatur               │
        │  (Stream-Deck für Zuki-Befehle)    │
        └────────────────────────────────────┘
              Corsair Platform:6 Tisch
```

**Dual-Use-Setup:**
- Hauptmonitor → Job-Laptop (saubere Trennung Privat/Arbeit)
- 3 kleine Displays → Zuki (Avatar, Stylus-Workzone, Neural Map)
- Wall-Displays → TradingView-Ambient
- Galleon-Stream-Deck → Zuki-Hotkeys ohne Tippen

Zuki ist parallel zum Arbeitsalltag verfügbar ohne den Job-Bildschirm
zu berühren. Eingabe-Sharing zwischen PC und Laptop via KVM oder
Software-Lösung (je nach IT-Compliance des Arbeitgebers).

---

## Skill-Vision

Skills sind plug-and-play. Auto-Discovery aus `skills/`. Jeder Skill
hat eigene Konversationen pro Tenant in der Cloud.

### Vorhanden
- **Professor** — strukturierte Erklärungen (`explain [Thema]`)
- **Broker** — News-Inbox, Watchlist (ausbaubar)

### Geplant (Priorisierung in ROADMAP)
1. **Coding-Skill + Scratchpad** — Multi-Language Editor mit Sandbox.
   Sprachen: Python, JS, TS, Bash, Go, Pine Script. Pine Script
   ist nicht lokal ausführbar → "Copy to TradingView" Button.

2. **Office-Skill + Google Drive** — Dokumenten-Management mit OCR
   (Tesseract + Gemini Vision) und LLM-Klassifikation. Use Case:
   "Such mir alles für Steuererklärung 2025 raus" → Ordner mit
   relevanten Dokumenten. Multi-Tenant: Drive-Subfolder pro Tenant.

3. **Music-Practice** — Instrument + Gesang lernen mit Echtzeit-Pitch-
   Feedback. KEIN Voice-Swap, KEINE Beat-Generation hier (separater
   Skill später wegen GEMA/Copyright-Grauzone).

4. **Business-Skill MVP (Gastro-Analyzer)** — Google Business Profile
   Scraper, Konkurrenz 1km-Radius, Social-Media-Public, Schwachstellen-
   Erkennung, 1-2 Seiten PDF für Erstgespräch. Praxistest mit 5-10
   echten Restaurants vor Weiterentwicklung.

### Spätere Skill-Erweiterungen
- Business-Vermittler (CRM, Provisions-Tracking)
- Business-Optimizer (Workflow-Audit, Tool-Empfehlungen, ROI)
- Music-Create (Beats, Voice-Swap RVC — privat-only)
- Streaming-Skill (Twitch-Integration, Mini-Games, Voice-Effekte —
  NICHT Real-Person-Deepfakes)

### Skill-Kommunikation via Router-Agent
Router-LLM entscheidet welche Skills relevant sind, orchestriert
Multi-Skill-Workflows, aggregiert Output. User sieht nur Endergebnis
plus Liste beteiligter Skills.

---

## UI-Vision

Multi-Panel-Web-UI im Browser (localhost via Flask-Server).

**Stack:** Vite + React + TypeScript + Tailwind. Multi-Panel via
`react-grid-layout`. State via `zustand`. WebSocket-Bridge zu Zuki Core.

### Geplante Panels
- **Avatar-Panel** — 3D-VRM (Three.js + three-vrm) ODER 2D-Live2D
  (Cubism Web SDK), switchbar via Settings. Lip-Sync zu TTS-Amplitude.
- **Neural-Map-Panel** — D3.js Force-Directed Graph als Provenance-
  Visualizer. Zeigt welche Quellen Zuki gerade anzapft (Cloud, Vision,
  Skills, Provider). Knoten pulsen bei Aktivität.
- **Code-Scratchpad-Panel** — Monaco Editor mit Sprach-Switching.
- **Skill-spezifische Panels** — Broker-Chart, Office-Dokumente,
  Business-Dashboard (CRM), Cleanup-Panel mit Checkboxen.

### Layout
User kann Panels arrangieren, Layouts speichern, zwischen Setups
wechseln ("Trading-Setup", "Office-Setup", "Coding-Setup").

---

## Plattform-Migration

**Phase 1 (aktuell):** Windows 11.

**Phase 2 (geplant):**
1. Neuer PC mit Windows kaufen + setup, Zuki migrieren
2. Wenn alles läuft: Linux-Migration (Pop!_OS 22.04 oder Ubuntu 24.04 LTS)

**Was Linux besser macht:**
- Piper TTS (lokal, deutlich bessere Qualität als pyttsx3)
- xdotool/wmctrl für saubere Window-Kontrolle
- Keine Antivirus-Konflikte mit Whisper/sounddevice
- Native Python-Stack ohne Frickelei

**Was vorbereitet werden muss (Bundle 8):**
- TTS-Backend-Pattern (WindowsTTS / LinuxTTS)
- Window-Control-Backend (Win32 / xdotool+wmctrl)
- Audio-Pfade plattform-agnostisch validieren

**WSL2 ist KEIN Pfad** — es hilft nicht bei GUI-Migration. Echtes Linux nötig.

---

## Apple-Ökosystem (später)

Wenn iPad + Apple Watch + AirPods da sind:

- **Home Assistant** als zentraler Smart-Home-Hub (Raspberry Pi 5 oder NUC)
- **Homebridge** als HomeKit-Brücke — HA-Geräte erscheinen als
  HomeKit-kompatibel auf iPhone/iPad/Watch
- **AirPods** — normales Bluetooth, kein Sonderaufwand
- **iCloud Drive** über `pyicloud` falls Datei-Sync nötig
- **iMessage / HomeKit nativ** — über Mac-Bridge möglich, aber
  komplex. Erstmal verzichten.

---

## Bewusst NICHT gebaut

| Idee | Warum nicht |
|---|---|
| Supabase als Backend | Vercel KV reicht, Zuki muss nicht selbst gehostet sein |
| Multi-Device-Sync | Single-User, einzelner Rechner |
| APILayer-Middleman | Direkte API-Integrationen sind sauberer und günstiger |
| Real-Person-Deepfakes | Rechtliche Grauzone, Plattform-Verstöße auf Twitch/YT |
| "Goldman-Sachs-Niveau"-Tool | Marketing-Sprech — MVP first, dann iterieren |
| Multi-User-Account-System | Tenant-Pattern reicht für Solo-Selbstständigkeit |
| Onboarding-Wizard | .env-Editing ist schneller als Klick-Wizard |
| Search-Endpoint (vorerst) | Erst bei >50 Einträgen relevant |
| Cloud-Verschlüsselung (vorerst) | Foundation existiert, lohnt erst mit echten Business-Daten |
| WSL2 für Linux-Vorbereitung | Hilft nicht bei GUI-Migration |
| Sonnet-Übersetzer-Pattern | Direkt mit Sonnet sprechen ist effizienter als Gemini-Zwischenstation |

---

## Workflow für Claude-Code-Sessions

### Doc-Hierarchie

| Datei | Zweck | Update durch |
|---|---|---|
| **VISION.md** (dieses Dokument) | Warum + Ziele + Strategien | Selten — wenn Vision sich wandelt |
| **ARCHITECTURE.md** | Wie + Begründungen für Code-Entscheidungen | Jedes Bundle das architektonisch was ändert |
| **ROADMAP.md** | Was + Wann + Status pro Bundle | Jedes Bundle |
| **CHANGELOG.md** | Was wurde wann implementiert | Jedes Bundle |
| **CLAUDE.md** | Stil-Konventionen, Kommunikation | Selten |

### Bundle-Workflow

1. **Per-Bundle-Chat** — neuer Claude-Code-Chat pro Bundle
2. Naming: `Zuki Bundle X — <Titel>`
3. Cross-cutting Bundles (🔒 in ROADMAP) bleiben in EINEM langen Chat
4. JIT-Lesen (Files erst lesen wenn relevant) statt upfront
5. Bundle-Abschluss aktualisiert CHANGELOG, ROADMAP, ARCHITECTURE
   (falls nötig), spiegelt Files in `claude_project_upload/`

### Strategie-Chat (separat von Code-Chats)

Ein lang-laufender Chat (NICHT Code-Chat) für:
- Neue Ideen sense-checken
- Architektur-Entscheidungen die mehrere Bundles betreffen
- Roadmap-Anpassungen
- Geschäftsmodell-Fragen

Der Strategie-Chat ist der "Architekt". Die Bundle-Chats sind "Engineers".
Klare Trennung spart Tokens und schärft Fokus.

---

## Startup-Template für neue Bundle-Chats

Den folgenden Prompt als erste Nachricht in einem neuen Code-Chat
einfügen (nach `/model claude-sonnet-4-6` und Project-Auswahl):

```
═══════════════════════════════════════════════════════════
ZUKI BUNDLE X — <TITEL>
═══════════════════════════════════════════════════════════

ONBOARDING (in dieser Reihenfolge im Project Knowledge lesen)
1. VISION.md      → Warum-Kontext, Geschäftsmodell, Strategien
2. ROADMAP.md     → finde Bundle X Spec, lies nur diese Section
3. CHANGELOG.md   → letzter Eintrag für Anschluss-Verständnis
4. ARCHITECTURE.md → JIT bei Bedarf, nicht upfront

Bestätige in 2-3 Sätzen das Verständnis von Bundle X.
Dann starte mit Implementation gemäß ROADMAP-Spec.

KONTEXT-FILES (JIT lesen wenn editiert)
[Hier: konkrete Files die Bundle X anfasst, z.B.
 tools/cloud_memory.py, memory/history_manager.py]

ZIELE & SPEC
[Hier: Bundle-spezifische Anforderungen aus ROADMAP übernommen
 plus eventuelle Zusatzdetails aus Strategie-Chat]

BUNDLE-ABSCHLUSS
1. CHANGELOG.md neuer Eintrag oben (Status, Files, Status-APIs, Notizen)
2. ROADMAP.md: Bundle X auf ✅, "Aktueller Fokus" anpassen
3. ARCHITECTURE.md: nur wenn neue Architektur-Entscheidung
4. Spiegel geänderte Files in D:/Zuki/claude_project_upload/
5. Erst dann finaler Bericht.

Los geht's.
```

---

## Aktueller Stand

Siehe ROADMAP.md → "Aktueller Fokus" Section am Ende für den
genauen Bundle-Status.

Siehe CHANGELOG.md → oberste Einträge für was zuletzt passiert ist.
