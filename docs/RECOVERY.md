# Zuki — Disaster Recovery

> Dieses Dokument beschreibt die vollständige Wiederherstellung von Zuki
> auf einem neuen oder zurückgesetzten System.
>
> **Voraussetzung:** Zugang zum privaten GitHub-Repository und zum
> Passwort-Manager (für .env-Werte).

---

## Überblick: Was liegt wo?

| Komponente | Speicherort | Recovery |
|---|---|---|
| **Code** | GitHub (privates Repo) | `git clone` |
| **Cloud-Gedächtnis** | Vercel KV (Redis) | Automatisch nach Start |
| **Nutzer-Profil** | Cloud + lokal | Bio-Recovery beim Start |
| **API-Keys / Tokens** | Eigene Sicherung (Passwort-Manager) | Manuell |
| **Lokale Logs** | `logs/` — nicht gesichert | Nicht wiederherstellbar |
| **Lokale Backups** | `backups/` — nicht gesichert | Nicht wiederherstellbar |

---

## Wiederherstellung Schritt für Schritt

### Schritt 1 — Code klonen

```bash
git clone https://<GITHUB_TOKEN>@github.com/<user>/<repo>.git D:/Zuki
cd D:/Zuki
```

Ersetze `<GITHUB_TOKEN>` mit dem Personal Access Token (scope: `repo`) und
`<user>/<repo>` mit dem Repo-Pfad aus dem Passwort-Manager.

Alternativ via SSH (wenn SSH-Key auf neuem System eingerichtet):
```bash
git clone git@github.com:<user>/<repo>.git D:/Zuki
```

---

### Schritt 2 — .env manuell wiederherstellen

Die `.env`-Datei ist **niemals im Repository** (durch `.gitignore` geschützt).
Sie muss manuell aus der eigenen Sicherung wiederhergestellt werden.

Vorlage mit allen erforderlichen Variablen:

```dotenv
# LLM API-Keys
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GEMINI_API_KEY=...

# Gemini-Modell
GEMINI_MODEL=gemini-1.5-flash-latest

# Whisper (STT)
WHISPER_MODEL=tiny
RECORD_SECONDS=5

# Text-to-Speech
TTS_VOICE=Katja
TTS_RATE=165
TTS_VOLUME=1.0

# Scraper
NEWSAPI_KEY=...
SCRAPER_INTERVAL=600

# Cloud-Gedächtnis (Vercel)
CLOUD_MEMORY_URL=https://<projekt>.vercel.app/api/memory
CLOUD_MEMORY_TOKEN=...

# GitHub-Backup
GITHUB_REPO_URL=https://github.com/<user>/<repo>.git
GITHUB_TOKEN=...
GITHUB_AUTOBACKUP=on
GITHUB_INTERVAL_HOURS=6

# UI-Renderer
ZUKI_UI=terminal
```

Alle Werte aus dem Passwort-Manager (KeePass, Bitwarden o.ä.) übertragen.

---

### Schritt 3 — Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

Falls `requirements.txt` fehlt oder veraltet ist, Mindest-Abhängigkeiten:

```bash
pip install anthropic openai google-generativeai pyttsx3 whisper sounddevice mss Pillow python-dotenv
```

---

### Schritt 4 — Zuki starten

```bash
python core/main.py
```

Beim Start prüft Zuki automatisch:
- Cloud-Verbindung (Vercel KV)
- Ob lokales Profil leer → Bio-Recovery aus Cloud anbieten
- Ob letzte Session sauber beendet wurde

---

### Schritt 5 — System-Test durchführen

Im Zuki-Terminal:

```
system test
```

Erwartetes Ergebnis: Alle 13 Subsysteme grün (OK).

Häufige Warn-/Fehlermeldungen nach Neuinstallation:

| Subsystem | Meldung | Lösung |
|---|---|---|
| `cloud` | Verbindung fehlgeschlagen | CLOUD_MEMORY_URL + TOKEN in .env prüfen |
| `llm` | SIM-Modus | Gültigen GEMINI_API_KEY eintragen |
| `tts` | Stimme nicht gefunden | Windows SAPI5-Sprachpaket "Katja" installieren |
| `mic` | Kein Eingabegerät | Mikrofon anschließen / Treiber prüfen |
| `github` | Remote nicht erreichbar | GITHUB_TOKEN abgelaufen? Neuen PAT erstellen |
| `backup` | Noch kein Snapshot | Normal — einmal `system backup` aufrufen |

---

## Cloud-Memory: Automatische Wiederherstellung

Das Cloud-Gedächtnis liegt **unabhängig auf Vercel KV**.
Es ist nicht im GitHub-Backup enthalten und wird nicht durch Code-Backups beeinflusst.

Nach dem Start mit korrekter `.env` (CLOUD_MEMORY_URL + TOKEN):

1. Zuki verbindet sich automatisch mit Vercel KV
2. Falls lokales Profil leer → Bio-Recovery wird angeboten
3. Alle gespeicherten Memories sind sofort wieder verfügbar

**Keine manuelle Aktion nötig** — solange CLOUD_MEMORY_URL und
CLOUD_MEMORY_TOKEN in der `.env` korrekt eingetragen sind.

---

## GitHub-Backup: Neuen PAT erstellen

Personal Access Tokens laufen ab. Bei `github`-Test-Fehler "Remote nicht erreichbar":

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Neuen Token erstellen: Repository-Zugriff auf das Zuki-Repo, Scope: `Contents (Read & Write)`
3. Token in `.env` bei `GITHUB_TOKEN=` eintragen
4. `system github status` → sollte "Remote erreichbar" zeigen

---

## Notfall: .env wurde versehentlich committet

Sofortmaßnahmen:

1. API-Keys und Tokens **sofort rotieren** (GitHub, Gemini, Anthropic, Vercel)
2. `.env` aus Git-History entfernen:

```bash
# BFG Repo-Cleaner (empfohlen, schneller als filter-branch)
java -jar bfg.jar --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

3. `system test github` → Prüft ob .env noch in History: muss FAIL zeigen
4. Nach Cleanup: erneut prüfen → muss OK zeigen

---

## Zusammenfassung: Recovery-Checkliste

```
[ ] git clone mit Personal Access Token
[ ] .env aus Passwort-Manager wiederherstellen
[ ] pip install -r requirements.txt
[ ] python core/main.py starten
[ ] Bio-Recovery anbieten lassen (falls Profil leer)
[ ] system test → alle 13 Subsysteme grün
[ ] system github status → Remote erreichbar, Token gültig
```
