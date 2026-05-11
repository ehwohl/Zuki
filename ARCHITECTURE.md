# Zuki — Architektur-Dokument

> **Zweck dieses Dokuments:** Festhalten von Entscheidungen, Begründungen
> und Konventionen die nicht aus dem Code allein hervorgehen. Code ist
> die Wahrheit über *was* passiert — dieses Dokument ist die Wahrheit
> über *warum*.
>
> **Stand:** Nach Bundle 5 — Tenant-Pattern (Multi-Tenant-Foundation, 14. System-Test-Subsystem).

---

## Modul-Karte

```
D:\Zuki\
├── core/
│   ├── main.py                  ← Hauptschleife, Befehlsrouting
│   ├── tenant.py                ← TenantManager Singleton + TenantConfig
│   ├── llm_manager.py           ← Anthropic + OpenAI direkt (älter)
│   ├── api_manager.py           ← Gemini/Anthropic/OpenAI/Local Multi-Provider (DSGVO-aware)
│   ├── ui_renderer.py           ← UIRenderer ABC (alle Renderer erben hieraus)
│   ├── ui.py                    ← TerminalRenderer(UIRenderer) + Forwarding-API
│   ├── ui_factory.py            ← get_renderer() Singleton, liest ZUKI_UI ENV
│   ├── vision_manager.py        ← mss Screenshot + Cleanup
│   ├── speech_to_text/whisper_engine.py  ← STT
│   ├── text_to_speech/tts_backend.py     ← TTSBackend ABC
│   ├── text_to_speech/windows_tts.py    ← WindowsTTS (pyttsx3/SAPI5)
│   ├── text_to_speech/linux_tts.py      ← LinuxTTS (Piper-Stub)
│   ├── text_to_speech/tts_engine.py     ← Factory + öffentliche TTS-API
│   ├── news_manager.py          ← Broker-News-Inbox
│   ├── calendar_manager.py      ← Termine
│   └── logger.py                ← zentrale Log-Setup
│
├── memory/
│   ├── history_manager.py       ← Chat-Historie mit Broker-Isolation
│   └── user_profile.py          ← Bio-Memory mit Fakten-Extraktion + Cloud-Sync
│
├── skills/
│   ├── base.py                  ← Skill ABC (handle, name, triggers)
│   ├── registry.py              ← Auto-Discovery + get_skill_for() Dispatch
│   ├── professor/professor.py   ← ProfessorSkill (explain [Thema])
│   ├── broker/scraper.py        ← News-Fetch (mock + future live)
│   └── test_skill.py            ← PingSkill (Test/Referenz)
│
├── tools/
│   ├── backup_manager.py        ← Lokale Snapshots + AutoBackup-Thread
│   ├── cloud_memory.py          ← Vercel-Cloud-Memory + Offline-Outbox
│   ├── github_backup.py         ← Off-Site Code-Backup via GitHub + Auto-Commit-Thread
│   ├── instance_guard.py        ← Single-Instance-Lock via Socket
│   ├── session_state.py         ← Crash-Detection + Session-Recovery
│   ├── system_test.py           ← Selbst-Diagnose aller 13 Subsysteme
│   ├── pc_control.py            ← PCControl delegiert ans WindowBackend
│   └── window_control/          ← Window-Backend-Paket
│       ├── backend.py           ← WindowBackend ABC
│       ├── windows_backend.py   ← WindowsWindowBackend (Win32/ctypes)
│       ├── linux_backend.py     ← LinuxWindowBackend (Stub)
│       └── factory.py           ← get_window_backend() Factory
│
├── zuki_cloud/                  ← Vercel Serverless API
│   ├── api/index.py             ← Flask + Redis Endpoint
│   ├── vercel.json              ← URL-Routing
│   └── requirements.txt         ← flask + redis only
│
├── docs/
│   └── RECOVERY.md              ← Disaster-Recovery-Anleitung (5 Schritte)
├── temp/                        ← Vision-Frames, Outbox (kommt)
├── logs/                        ← zuki.log, error.log
├── backups/                     ← lokale Snapshots
├── .gitignore                   ← schützt .env, temp/, logs/, backups/ vor Commit
└── .env                         ← API-Keys, Cloud-URLs (NIEMALS commiten)
```

---

## Architektur-Entscheidungen mit Begründung

### 1. Zwei Provider-Manager (LLMManager + APIManager) — bewusste Trennung
**Was:** `LLMManager` für klassischen Chat (Anthropic/OpenAI direkt), `APIManager`
als neuere Multi-Provider-Schicht mit Gemini-Priorität.

**Warum:** Historisch gewachsen — `LLMManager` war zuerst da, `APIManager` kam mit
der Gemini-Integration. Sie überlappen funktional. Das ist **technische Schuld**, aber
keine die jetzt aufgelöst werden muss.

**Konvention:** Neue Skills nutzen `APIManager` (`api.chat()`, `api.chat_messages()`).
`LLMManager` wird nur noch in `main.py` für den Standard-Chat-Loop verwendet, weil
das so funktioniert und kein Anlass zu refactoren besteht.

**Falls je refactor:** `LLMManager` durch `APIManager` ersetzen. Aber niemand hat
gerade Schmerzen damit.

### 2. Cloud-Memory ist UNABHÄNGIG vom Simulations-Modus
**Was:** `cloud.enabled` ist nur an URL/Token gekoppelt, nicht an `llm.simulation`
oder `api_mgr.simulation`.

**Warum:** Cloud-Speichern soll auch funktionieren wenn Zuki im SIM-Modus läuft
(z.B. wenn das Gemini-Limit erreicht ist). Sonst geht Material verloren bei dem
Modus den der User am ehesten nutzt.

**Folge:** Niemals `if not simulation:` vor `cloud.save()` setzen. Das wurde
explizit so entschieden und in den Kommentaren von `cloud_memory.py` und
`main.py` festgehalten.

### 3. `REDIS_URL` statt `KV_REST_API_URL`
**Was:** `zuki_cloud/api/index.py` nutzt das `redis`-Python-Paket mit `REDIS_URL`,
nicht `upstash-redis` mit `KV_REST_API_URL`.

**Warum:** Vercel KV setzt automatisch beide Variablen. `REDIS_URL` ist eine
standard `redis://`-URL (TCP) und funktioniert mit jedem Redis-Client.
`KV_REST_API_URL` ist HTTP-REST und braucht das spezielle Upstash-Paket. Wir hatten
zu Beginn beides drin und haben in der Aufräumung entschieden: ein Paket reicht.

**Falls je geändert:** `upstash-redis` ist die "officially recommended" Lösung
für Vercel KV. Aber `redis`-Paket funktioniert genauso und wir haben weniger
Dependencies.

### 4. Friendly Errors statt Stack-Traces im Terminal
**Was:** `_friendly_error()` in `api_manager.py` wandelt technische Fehler in
deutsche User-Sätze um. Technische Details landen in `logs/error.log`.

**Warum:** Stack-Traces sind kryptisch und unterbrechen den Flow. Aber sie
müssen für Debugging erreichbar bleiben → daher die Log-Datei.

**Konvention:** Bei jedem User-facing Fehler:
1. `_write_error_log(context, exc)` für die technischen Details
2. `_friendly_error(provider, exc)` für die Terminal-Anzeige

Pattern in `cloud_memory.py` ähnlich (siehe `_post()` return-Strings).

### 5. Background-Threads als Daemon, mit `atexit`-Cleanup
**Pattern für alle Hintergrund-Prozesse** (Scraper, Cloud-Saves, kommender
Auto-Backup):

```python
event = threading.Event()
thread = threading.Thread(
    target=_loop_function,
    args=(event,),
    daemon=True,
    name="...",
)
thread.start()
atexit.register(event.set)
```

**Warum daemon:** Stirbt automatisch wenn Hauptprozess endet, kein Hängen.
**Warum atexit + Event:** Sauberer Shutdown bei normalem Exit, ohne dass der
Thread den Prozess am Ende blockiert.

### 6. Single-Instance via Socket (kein PID-File)
**Was:** `tools/instance_guard.py` belegt Port 65432 auf 127.0.0.1.

**Warum:** Lock-Files können bei Crashes liegenbleiben und müssen manuell
aufgeräumt werden. Sockets gibt das OS automatisch frei wenn der Prozess
endet — egal ob sauber oder per Absturz.

### 7. UI-Konvention: ANSI Box-UI
**Was:** `core/ui.py` definiert Farben (`R`, `BOLD`, `CYAN`, etc.) und
Box-Helpers (`_btop`, `_bsep`, `_bbot`, `_bline`).

**Warum:** Optisch konsistent, alle Status-Ausgaben sehen gleich aus.

**Konvention:** Neue Status-Anzeigen nutzen `_bline()` mit den vorhandenen
Farben. Niemals raw `print()` mit eigenen ANSI-Codes — das wird inkonsistent.

### 8. Logging-Hierarchie
- **`log.debug(...)`** für Entwickler-Details (z.B. "Gemini-Modell xyz erfolgreich")
- **`log.info(...)`** für normale Ereignisse (z.B. "Cloud gespeichert")
- **`log.warning(...)`** für nicht-kritische Probleme (z.B. "Gemini 404, Fallback aktiv")
- **`log.error(...)`** für ernste Fehler

Niemals `print()` in Modulen unterhalb von `core/main.py` und `core/ui.py`.
Wenn ein Modul etwas im Terminal anzeigen will → `ui.system_msg()`,
`ui.error_msg()` etc. nutzen.

### 9. Schema-Versionierung (implementiert — Resilienz-Feature 1)
Jeder Cloud-Eintrag hat `"v": 1`. Beim ersten Schema-Wechsel prüft der Server
`entry.get("v", 1)` und kann alte Einträge migrieren oder fallback-handhaben.

### 10. UIRenderer ABC — Renderer-Pattern (Bundle 3, Feature 2)
**Was:** `core/ui_renderer.py` definiert `UIRenderer` als ABC. `TerminalRenderer`
in `core/ui.py` ist die einzige aktuelle Implementierung. `core/ui_factory.py`
gibt via `get_renderer()` den konfigurierten Renderer zurück (Singleton).

**Warum:** Zuki braucht langfristig mehrere UI-Schichten (Terminal jetzt,
Web-React später, ggf. Headless für Tests). Das ABC erzwingt eine konsistente
Methodenmenge und macht neue Renderer zu einer reinen Drop-In-Aufgabe.

**Konvention für neuen Renderer:**
1. Klasse erstellen, von `UIRenderer` erben, alle `@abstractmethod`s implementieren.
2. In `_build_registry()` in `ui_factory.py` unter neuem Key eintragen.
3. `ZUKI_UI=<key>` in `.env` setzen — alles andere ist automatisch.

**Abwärtskompatibilität:** `core/ui.py` exponiert Modul-Level-Forwarding-Funktionen
(`speak_zuki`, `system_msg`, etc.) damit alter Code `from core import ui; ui.speak_zuki()`
weiter läuft bis auf `ui_factory` umgestellt ist.

**ENV-Reihenfolge:** `ui = _get_renderer()` wird in `run()` nach `load_env()` gesetzt,
damit `ZUKI_UI` aus `.env` wirkt. Modul-Level-Fallback existiert als Safety-Net für
Hilfsfunktionen die vor `run()` aufgerufen werden könnten.

### 12. Code-Backup via Git — getrennt von Daten-Backup (Bundle 4.5)
**Was:** `tools/github_backup.py` (`GitHubBackup`) sichert den **Code** in einem
privaten GitHub-Repo (Auto-Commit alle 6h, Push zu Remote). Lokale Snapshots
(`AutoBackup`) und Cloud-Memory (Vercel KV) bleiben davon vollständig unabhängig.

**Warum drei Backup-Ebenen:**
- **GitHub (Code):** Versioniert, Off-Site, Disaster-Recovery auf neuem Rechner.
  Git puffert Commits nativ — bei Offline entsteht kein Datenverlust.
- **Lokale Snapshots (Daten + Code, `backups/`):** Schneller Rollback auf letzten
  Stand ohne Netzwerk. Behalte 7 Snapshots, ältere werden automatisch gelöscht.
- **Cloud-Memory (Vercel KV):** User-Gedächtnis und Bio — unabhängig von Code-Backup,
  kommt automatisch zurück sobald Zuki mit der Cloud verbunden ist.

**Konvention: `.env` wird niemals committet.**
`.gitignore` schützt `.env`, `temp/`, `logs/`, `backups/`, `memory/clients/`
und `claude_project_upload/`. Der `_test_github()`-Test in `SystemTest` prüft
aktiv ob `.env` in der Git-History ist und meldet FAIL falls ja.

**Token-Sicherheit:** GITHUB_TOKEN wird in `_auth_url()` in die HTTPS-URL
eingebettet (Push ohne interaktive Prompt), aber niemals geloggt. Der Token
wird aus allen Log-Outputs durch `_safe_output()` maskiert.

**Offline-Verhalten:** Commit lokal erstellen ist immer möglich. Push schlägt
bei Netzwerkausfall fehl (Log: `[GITHUB-FAIL]`), wird beim nächsten Cycle
automatisch erneut versucht. Kein Outbox-Pattern nötig — Git puffert nativ.

### 11. Stub-Konvention: NotImplementedError propagiert, nicht geschluckt (Bundle 3, Feature 3)
**Was:** `_call_local()` in `api_manager.py` wirft `NotImplementedError`.
`chat()` und `chat_messages()` fangen `NotImplementedError` explizit **nicht** —
`except NotImplementedError: raise` steht vor dem generischen `except Exception`.

**Warum:** Stub-Fehler sind Programmierfehler (fehlende Implementierung), keine
Runtime-Fehler. Sie dürfen nicht in friendly-error-Strings verwandelt werden,
weil der Entwickler sonst nicht merkt, dass der Stub noch leer ist.

**Konvention:** Jede Stub-Methode:
- `log.info("[XYZ-STUB] method() aufgerufen — ...")`
- `raise NotImplementedError("... LIVE UPGRADE-Kommentar ...")`

Aufrufer die mit Stubs umgehen müssen, fangen `NotImplementedError` selbst ab.

### 13. Tenant-Pattern — Daten-Isolation pro Workspace (Bundle 5)
**Was:** Jeder Tenant (z.B. "self", "client-schmidt") hat isolierte Daten:
- Cloud-Gedächtnis: `zuki:memories:{tenant}` / Audit: `zuki:audit:{tenant}`
- Profil-Datei: `memory/user_profile_{tenant}.txt`
- Chat-History: ein File, Einträge mit `tenant_id`-Feld, `get_context()` filtert

**Warum:** Langfristig kommt Business-Nutzung mit echten Kunden-Daten.
Privates und Berufliches darf niemals vermischt werden. Das Tenant-Konzept
legt die Foundation ohne bestehende Logik umzuschreiben — alle Änderungen
sind additive Tags und Umschalter.

**DSGVO-Constraint:** `TenantConfig.require_dsgvo = True` blockiert Gemini Free
(nicht DSGVO-konform) und schaltet auf Anthropic/OpenAI um. Ist kein kompatibler
Provider vorhanden, meldet `APIManager` eine klare Fehlermeldung statt still
zu simulieren.

**Migration:** Einmalig beim ersten Start nach Bundle 5:
1. `user_profile.txt` → `user_profile_self.txt` (lokal, vor UserProfile-Init)
2. `POST /api/memory/migrate` → kopiert `zuki:memories` → `zuki:memories:self`
3. Marker `__migration_v1_done__` in `temp/tenants.json` — idempotent

**Legacy-Fallback:** GET /api/memory liest für tenant=self auch `zuki:memories`
falls der neue Key leer ist. Kommentar markiert: *TODO: nach 2026-05-25 entfernen*.

**Konvention für neue Features:**
- Jeder neue Cloud-Endpoint muss `tenant` aus Body/Query lesen (default "self")
- Jede Datei die pro-User gespeichert wird: `{name}_{tenant}.{ext}` Muster
- History-Einträge immer mit `tenant_id` schreiben
- Vor Zugriff auf TenantManager: `try/except` als Safety-Net (Import könnte früh scheitern)

**Audit-Log:** Jeder Cloud-Save erzeugt einen Eintrag in `zuki:audit:{tenant}`.
Max. 500 Einträge, kein UI dafür im MVP — Foundation für spätere Compliance-Ansicht.

### 15. Plattform-Backend-Pattern für TTS + Window-Control (Bundle 8)

**Was:** Plattform-spezifischer Code ist hinter ABC-Backends versteckt.
Factories wählen per `sys.platform` das richtige Backend:

```
core/text_to_speech/
  tts_backend.py      ← TTSBackend ABC
  windows_tts.py      ← WindowsTTS  (pyttsx3, voll implementiert)
  linux_tts.py        ← LinuxTTS    (Piper-Stub, bereit für Live-Upgrade)
  tts_engine.py       ← Factory + öffentliche API (delegiert ans Backend)

tools/window_control/
  backend.py          ← WindowBackend ABC
  windows_backend.py  ← WindowsWindowBackend (Win32/ctypes, voll implementiert)
  linux_backend.py    ← LinuxWindowBackend (xdotool+wmctrl-Stub)
  factory.py          ← get_window_backend() Factory
tools/pc_control.py   ← delegiert ans WindowBackend (war Monolith-Stub)
```

**Warum:** Wenn Zuki auf Linux migriert, müssen nur `LinuxTTS` (Piper befüllen)
und `LinuxWindowBackend` (xdotool+wmctrl befüllen) implementiert werden.
Core, Skills, History, Cloud — nichts davon muss angefasst werden.

**Konvention für neue Backends:**
1. Klasse erstellen die von `TTSBackend` oder `WindowBackend` erbt, alle `@abstractmethod`s implementieren.
2. In der Factory-Funktion unter dem passenden `sys.platform`-Zweig eintragen.
3. `get_status() → dict` muss immer `backend`, `platform`, `ready`/`available` liefern.

**Stub-Konvention:** Linux-Stubs folgen derselben Konvention wie `pc_control.py` (Bundle 3):
`log.info("[...-STUB] method() aufgerufen")` + `raise NotImplementedError(...)`.
Stubs sind nie "verfügbar" (`available() = False`, `ready = False`).

**Audio-In:** `sounddevice` ist plattform-neutral (portiert PortAudio). Auf Linux
muss `portaudio19-dev` via apt installiert sein. `whisper_engine.py` prüft dies
über `_SD_AVAILABLE` Flag und gibt plattformbewusste Fix-Hints wenn sounddevice fehlt.

### 14. Zweistufiges Skill-Routing — Fast-Path + LLM-Router (Bundle 6)

**Was:** Der Skill-Dispatch in `core/main.py` läuft zweistufig:
1. **Fast-Path:** `skill_registry.get_skill_for(cmd)` — exakter Match auf erstem Wort.
   Kosten: 0 Token. Latenz: microseconds.
2. **Router-Pfad:** `RouterAgent.route(user_input, skills_info)` — LLM-Call wenn kein
   Trigger passt. Kosten: 1 kleiner LLM-Call (max. 80 Tokens Output). Latenz: ~1-2s.

**Warum zweistufig:**
- Exakte Trigger-Matches sind deterministisch und kostenlos — kein Grund sie durchs LLM zu jagen.
- Router deckt semantische Anfragen ab: "Erkläre mir X" trifft `explain`-Trigger, aber
  "Was ist X?" trifft keinen Trigger und kommt über den Router.
- SIM-Modus-sicher: Im SIM-Modus gibt der Router sofort `[]` zurück — kein API-Call.

**Skill-Sichtbarkeit:**
- Nur Skills mit `description != ""` sind für den Router sichtbar.
- Test-Stubs (PingSkill) haben keine description → werden ignoriert.
- Neue Skills müssen `description` setzen um für Nutzer erreichbar zu sein.

**Cloud-Persistenz:**
- Skill-Antworten werden in `zuki:skill:{name}:conversations:{tenant}` gespeichert.
- Separate Endpunkte `POST/GET /api/skill/conversations` in der Cloud-API.
- Ermöglicht spätere Analyse pro Skill (häufig genutzt? welche Antworten waren gut?).

**Konsequenz für neue Skills:**
- `description` setzen (1 Satz, klar formuliert)
- Trigger für häufige Wörter definieren (Schnellpfad)
- `handle()` gibt `None` zurück wenn Skill nicht zuständig ist (Router-Robustheit)

---

## Was bewusst NICHT gemacht wurde

### Business/CRM-Modul
**Was:** Es gab einen Anlauf eine Business-Suite mit CRM-Bridge, Mail, Termine,
HTML-Dashboard zu integrieren.

**Status:** Hard-Reset. Aus aktivem Code entfernt. `CRM_HTML_PATH` steht noch
in `.env` aber wird nirgends gelesen. Die alten Files könnten noch auf der Platte
liegen aber sind nicht aktiv.

**Warum entfernt:** Scope-Creep. Zuki sollte sich auf Kern-Skills konzentrieren.

### Multi-Device-Sync
Wurde diskutiert und verworfen. Konflikt-Auflösung ist komplex, der User
nutzt Zuki an einem Rechner. Wenn das mal kommt: Cloud-Memory-Schicht
hat schon `session_id`-Felder als Vorbereitung.

### Onboarding-Wizard
Verworfen. `.env` direkt editieren ist für den User schneller als ein
Wizard durchzuklicken.

### `vercel_kv` Python-Package
Existiert nicht. War in einer frühen Version von `zuki_cloud/api/index.py`
drin und hat zu Build-Failures geführt. Ersetzt durch `redis` (siehe Punkt 3 oben).

### `upstash-redis` Python-Package
War als Fallback drin, in der Aufräumung entfernt. Funktioniert, aber wir
nutzen `redis` mit `REDIS_URL` und brauchen es nicht.

---

## Stil-Konventionen

| Regel | Beispiel |
|---|---|
| Deutsche Variablennamen wo natürlich | `_save_count`, `letzte_antwort` (gemischt mit Englisch ok) |
| Englische Funktionsnamen | `def save_memory():`, `def acquire():` |
| Knappe Kommentare nur wo sie helfen | Kein "increment counter" über `i += 1` |
| Box-Drawing Trennlinien in Modul-Headern | `# ── Section ────────────────────────────...` |
| Type-Hints in öffentlichen Funktionen | `def ping(self, timeout: int = 5) -> tuple[bool, str]:` |
| f-Strings für alle String-Formatierungen | nicht `.format()`, nicht `%`-Style |
| User-facing Strings auf Deutsch | "Zuki: Cloud-Verbindung steht" |
| Log-Strings auf Deutsch | `log.info("APIManager initialisiert...")` |

---

## Test-Workflow (manuell, kein pytest)

Standard-Pattern:
```bash
python -c "
import sys; sys.path.insert(0, 'D:/Zuki')
import os
os.environ['...'] = '...'
from tools.xyz import Foo
# ... testen ...
"
```

Cloud-Tests via `curl`:
```bash
curl -s -X POST "https://zuki-cloud.vercel.app/api/memory" \
  -H "Content-Type: application/json" \
  -H "x-zuki-token: ZukiGeheim2024" \
  -d '{"text":"...","source":"manual","session_id":"..."}'
```

Es gibt keine pytest-Suite. Tests sind ad-hoc, validieren Verhalten direkt.

---

## Aktuelle Roadmap (Resilienz-Layer)

In Reihenfolge:
1. **Schema-Versionierung** (`"v": 1` in jeden Cloud-Eintrag)
2. **Offline-Outbox** (`temp/cloud_outbox.jsonl` als Puffer wenn Cloud offline)
3. **Auto-Backup-Thread** (alle 6h, behalte 7)

Spätere mögliche Features (nicht eingeplant, nur dokumentiert):
- Verschlüsselung der Cloud-Daten (Fernet/AES, Schlüssel in `.env`)
- Bio-Recovery aus Cloud (User-Profile aus Cloud-Backup wiederherstellbar)
- Search-Endpoint (`/api/memory/search?q=...`)
- Hotword-Detection (Picovoice Porcupine)
- PC-Kontrolle (Window-Management, App-Steuerung)

---

## UI-Roadmap (Langzeit-Vision)

Zuki bekommt langfristig eine moderne grafische Oberfläche mit:
- **Live2D- oder CSS-Avatar** mit Lip-Sync zur TTS-Stimme
- **Neural Map** die in Echtzeit zeigt welche Quellen Zuki gerade nutzt
  (Gemini, Cloud-Memory, Vision, etc.) — als Provenance-Visualizer
- **Status-Widgets** für Cloud-Verbindung, aktiver Provider, Outbox-Größe,
  letztes Backup, etc.
- Anzeige auf den geplanten 3× kleinen Displays unter dem Hauptmonitor

**Gewählter Architektur-Pfad:** Web-basiert über lokalen Flask-Server.

```
Zuki Core (Headless)
    ↓ optional, on-demand
Lokaler Flask-Server (localhost:5000)
    ↓ WebSocket für Live-Events
Browser-Tab (nutzt bereits laufenden Browser)
```

**Warum Web statt PyQt/Electron:**
- Browser läuft eh bereits → keine zusätzlichen 200-500 MB Bloat
- Beliebige moderne Designs umsetzbar (HTML/CSS/JS)
- Wiederverwendung des bereits bestehenden `/api/memory/view` Patterns
- UI-Updates ohne Code-Redeploy möglich

**Token-Garantie:** UI-Features dürfen NIEMALS LLM-Calls auslösen.
Avatar reagiert lokal auf TTS-Audio-Amplitude. Neural Map visualisiert
lokale Events. Beides 100% gratis. Tokens entstehen nur durch
User-Aktionen (Fragen, Vision, Cloud-Save), nicht durch die UI.

**RAM-Ziel:** Zuki mit voller UI unter 300 MB total. Erreichbar durch
Lazy-Loading (Whisper, Vision nur on-demand) und Web-Architektur.

**Asset-Strategie:** Avatare, Icons, CSS, Schriftarten — alle lokal im
Repo. Cloud speichert nur User-State (Theme-Wahl, Layout-Präferenzen),
niemals Asset-Files. Grund: Latenz, Offline-Robustheit, Vercel KV ist
für kleine Daten, nicht für Blobs.

### Was das JETZT für Code-Entscheidungen bedeutet

Diese Prinzipien sollen schon jetzt beachtet werden, damit der spätere
UI-Ausbau ohne Refactor möglich ist:

1. **UI-Agnostik bewahren:** `core/ui.py` ist die einzige Render-Schicht.
   Module unterhalb dürfen NIEMALS direkt `print()` aufrufen — nur via
   `ui.system_msg()`, `ui.error_msg()`, `ui.speak_zuki()` etc. Damit
   kann `ui.py` später durch einen HTTP/WebSocket-Emitter ersetzt werden,
   ohne dass die Module darunter angefasst werden müssen.

2. **Status-Abfragen exponieren:** Jeder Manager (`CloudMemory`,
   `APIManager`, kommende Outbox, Auto-Backup) sollte eine Methode
   `get_status() -> dict` oder eine `status` Property haben, die den
   aktuellen Zustand als serialisierbares Dict zurückgibt. Damit sind
   spätere UI-Widgets trivial (1-Zeilen-Aufruf statt Refactor).

3. **Lazy-Loading wo möglich:** Schwere Komponenten (Whisper-Modell,
   Vision-Capture, später Live2D-Renderer) werden erst geladen wenn
   sie tatsächlich genutzt werden. So bleibt der Idle-Footprint klein.

4. **Event-fähig denken:** Wo Manager wichtige Ereignisse haben
   (Cloud-Save erfolgreich, Outbox-Flush, Backup erstellt), sollte
   das so geloggt sein, dass ein zukünftiger Event-Bus daran
   andocken kann. Konkret: `log.info()` mit konsistent formatiertem
   Strukturen-Marker (z.B. `"[CLOUD-SAVE]"`, `"[OUTBOX-FLUSH]"`).

5. **Keine UI-Annahmen im Core:** Der Core soll auch ohne UI laufen
   können (Headless-Modus). UI ist eine Schicht obendrauf, nie eine
   Voraussetzung.

### Konkrete Konsequenzen für den Resilienz-Layer

| Feature | Status-API die exponiert werden sollte |
|---|---|
| Schema-Versionierung | `"v"`-Field in Einträgen — ermöglicht UI-Filter nach Version |
| Offline-Outbox | `outbox.size()`, `outbox.is_flushing()`, `outbox.last_flush_time()` |
| Auto-Backup | `backup_manager.last_snapshot_time()`, `backup_manager.snapshot_count()`, `backup_manager.next_scheduled()` |

Damit sind alle drei Features zukunfts-fest und können später ohne
Refactor in eine UI integriert werden.

---

## Bekannte technische Schuld

1. `LLMManager` und `APIManager` überlappen (siehe Entscheidung 1).
2. `core/ui.py` enthält Modul-Level-Forwarding-Funktionen zur Abwärtskompatibilität —
   Cleanup wenn `main.py` vollständig auf `ui_factory` umgestellt ist.
3. `news_manager.py` und `skills/broker/scraper.py` sind nicht aktiv —
   die Broker-Skill ist eingebaut aber kein echter Live-Scraper.
4. `.env` enthält Keys für News/SerpAPI/AlphaVantage die nirgends gelesen werden
   (Reservation für Live-Scraper-Upgrade).
5. `skills/test_skill.py` (`PingSkill`) liegt produktiv im `skills/`-Ordner und
   wird bei jedem `discover_skills()` mitregistriert — kann nach finalen
   Skill-Tests gelöscht werden, schadet aber nicht.

Keine dieser Schulden behindert aktuell — Cleanup nur bei Anlass.
