# Arbeitsanweisungen für Zuki

## Rolle
Senior Software Architekt, pragmatischer Entwickler.

## Kommunikation
- Antworten so kurz wie möglich, kein Smalltalk
- Bei Coding-Tasks: Code zuerst, dann stichpunktartige Erklärungen
- Inline Code-Kommentare: Englisch
- User-facing Strings (UI, Logs, Print): Deutsch
- Variablennamen: Deutsch wo natürlich, Englisch sonst

## Coding-Strategie
- Strikt modular (Plug-and-Play)
- Provider-Pattern für LLMs (austauschbar)
- UI-agnostisch (Core läuft headless, UI ist Layer obendrauf)
- Status-APIs auf jedem Manager (siehe ARCHITECTURE.md)

## Persistenz
- Cloud-Memory: Vercel KV (Redis HTTP) — siehe zuki_cloud/
- Lokal: JSON in memory/ + Snapshots in backups/
- NICHT Supabase, NICHT Postgres — bewusste Entscheidung

## Stack (aktuell)
- Python 3.14, Windows 11
- Cloud-LLMs: Gemini primär (gemini-1.5-flash-latest), Claude, GPT
- STT: Whisper (lokal), TTS: pyttsx3 (Windows SAPI5)
- Cloud-Backend: Vercel Serverless (Flask + redis-py)

## Stack (geplant, später)
- **Lokales LLM via RTX 5090** als zusätzlicher Provider in
  APIManager. Geplante Strategie:
    - Private/Bulk-Anfragen → lokal (kostenlos, schnell)
    - Vision/komplex → Cloud (Quality matters)
    - Cloud-Limit-Fallback → lokal statt SIM
- Web-UI via lokalem Flask-Server (siehe ARCHITECTURE.md UI-Roadmap)

## Tenant-Guard — Pflicht für neue Skills

Jeder neue Skill der potenziell Kunden-Daten verarbeitet MUSS:
- `tenant_aware = True` haben (ist der Default in `Skill` ABC — nichts tun reicht)
- NICHT `tenant_aware = False` setzen außer der Skill hat garantiert keinen Kundenbezug

Der Guard läuft automatisch in `main.py` vor jedem Skill-Call.
Steuerung via `.env`: `SKILL_TENANT_GUARD=warn|auto|off`

Reine Utility-/Test-Skills (kein Kundenbezug) → `tenant_aware = False` explizit setzen.
Beispiele: PingSkill, ProfessorSkill.

## WICHTIG: Vorrang-Regel
Bei Widersprüchen zwischen CLAUDE.md und ARCHITECTURE.md
hat ARCHITECTURE.md Vorrang. CLAUDE.md ist Zusammenfassung,
ARCHITECTURE.md ist die Wahrheit über Entscheidungen und
Begründungen.
