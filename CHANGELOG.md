# CHANGELOG — Zuki AI Assistant

Alle Änderungen chronologisch dokumentiert. Neueste Einträge oben.

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

- `skills/base.py` — neu: `Skill` ABC
- `skills/registry.py` — neu: Auto-Discovery + `get_skill_for()` + Status-API
- `skills/professor/professor.py` — `ProfessorSkill` angehängt
- `skills/test_skill.py` — neu: `PingSkill` (ping → pong)
- `skills/__init__.py`, `skills/professor/__init__.py`, `skills/broker/__init__.py`, `skills/business/__init__.py` — neu: leere Package-Marker
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
**Dateien:** `skills/base.py` (neu), `skills/registry.py` (neu), `skills/professor/professor.py`, `skills/test_skill.py` (neu), `skills/__init__.py`, mehrere `__init__.py`-Marker, `core/main.py`

- **`Skill` ABC** (`skills/base.py`):
  - `name: str` — eindeutiger Skill-Name (Pflicht).
  - `triggers: set[str]` — Befehlswörter die den Skill auslösen.
  - `handle(context: dict) -> str | None` — abstrakt; `None` = Skill hat nichts zu sagen.
  - Context-Dict enthält: `user_input`, `cmd`, `api_mgr`, `llm`, `profile`.

- **`registry.py`** (`skills/registry.py`):
  - `discover_skills()` — `pkgutil.walk_packages` scannt `skills/`-Paket, importiert alle Module, instantiiert alle `Skill`-Subklassen, registriert nach Trigger (lowercase).
  - `get_skill_for(cmd)` — erstes Wort von `cmd` als Lookup-Key.
  - Status-API: `skill_count()`, `list_names()`.
  - Log-Marker: `[SKILL-DISCOVER]`.

- **`ProfessorSkill`** (ans Ende von `skills/professor/professor.py` angehängt):
  - `triggers = {"explain", "erklaer", "erklaere", "erkläre"}`.
  - `handle()` — ruft bestehende `build_sim_response()` / `build_live_prompt()` + `api_mgr.chat()` auf.

- **`PingSkill`** (`skills/test_skill.py`):
  - Trigger: `"ping"` → Antwort: `"pong  ·  Skill-System funktioniert."`.

- **Package-Marker** `__init__.py`:
  - `skills/__init__.py`, `skills/professor/__init__.py`, `skills/broker/__init__.py`, `skills/business/__init__.py` — leer, für `pkgutil.walk_packages`.

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
