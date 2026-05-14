# Zuki — REFERENCES.md

> Silent archive. Read only when you need the *why* behind a decision,
> the roadmap spec for a bundle, or a naming convention.
> Not read upfront — only on demand.

---

## Stack

- Python 3.14, Windows 11 → Linux migration planned (Pop!_OS / Ubuntu 24.04)
- LLM: Gemini primary (`gemini-1.5-flash-latest`), Claude, GPT via `APIManager`
- STT: Whisper (local) · TTS: pyttsx3/SAPI5 (Windows), Piper stub (Linux)
- Cloud: Vercel Serverless (Flask + redis-py + Vercel KV) — `zuki_cloud/`
- Future: local LLM via RTX 5090 as additional `APIManager` provider

## Top-Level Files

| File | Purpose |
|---|---|
| `PERSONA.md` | Zuki's identity and character definition — loaded as system prompt by `core/llm_manager.py` |
| `CLAUDE.md` | Workspace routing map for AI assistants |
| `REFERENCES.md` | Architecture decisions, naming conventions, tech debt, roadmap |
| `CONTEXT.md` | Current project state and active constraints |

---

## Architecture Decisions

### 1. Two Provider Managers (LLMManager + APIManager)
Known overlap. `LLMManager` stays in `main.py` chat loop only.
All new skills use `APIManager`. Merge deferred until there is real pain.

### 2. Cloud Saves Are Independent of Simulation Mode
`cloud.save()` is never wrapped in `if not simulation:`.
Cloud integrity must survive LLM quota limits. This is a hard rule.

### 3. REDIS_URL over KV_REST_API_URL
`zuki_cloud/api/index.py` uses `redis` package with `REDIS_URL` (TCP standard).
`upstash-redis` removed — fewer dependencies, same result.

### 4. Friendly Errors, Not Stack Traces
Every user-facing error: `_write_error_log(context, exc)` → `logs/error.log`,
then `_friendly_error(provider, exc)` → German terminal sentence.

### 5. Background Threads: Daemon + atexit
```python
stop_event = threading.Event()
thread = threading.Thread(target=_loop, args=(stop_event,), daemon=True)
thread.start()
atexit.register(stop_event.set)
```

### 6. Single Instance via Socket (not PID file)
Port 65432 on 127.0.0.1. OS auto-releases on crash — no stale lock files.

### 7. ANSI Box UI Convention
All status output via `_bline()` with defined colors. Never raw `print()` with custom ANSI.

### 8. Logging Hierarchy
`debug` → dev details · `info` → normal events · `warning` → non-critical · `error` → serious.
No `print()` below `core/main.py` and `core/ui.py`.

### 9. Cloud Schema Versioning
Every cloud entry has `"v": 1`. Server checks `entry.get("v", 1)` for migration.

### 10. UIRenderer ABC
`core/ui_renderer.py` defines `UIRenderer` ABC. `TerminalRenderer` is current impl.
New renderer: inherit ABC → register in `ui_factory._build_registry()` → set `ZUKI_UI=<key>` in `.env`.

### 11. Stub Convention: NotImplementedError Propagates
Stubs log `[XYZ-STUB] method() called` and raise `NotImplementedError`.
Never caught in generic `except Exception` — stub errors are programmer errors.

### 12. Three-Layer Backup
GitHub (code, 6h auto-commit) · Local snapshots in `backups/` (7 kept) · Cloud-Memory (user data).
`.env` is never committed — `system test github` actively checks for this.

### 13. Tenant Pattern
Data isolation per workspace: `zuki:memories:{tenant}`, `user_profile_{tenant}.txt`, history filtered by `tenant_id`.
DSGVO constraint: `require_dsgvo=True` blocks Gemini Free, enforces Anthropic/OpenAI.
New features: every cloud endpoint reads `tenant` from body/query (default `"self"`).

### 14. Two-Stage Skill Routing
1. Fast-path: `skill_registry.get_skill_for(cmd)` — exact trigger match, 0 tokens.
2. Router: `RouterAgent.route()` — LLM call if no trigger matches (~80 token output).
SIM mode: router returns `[]` immediately, no API call.
Skills without `description` are invisible to the router.

### 15. Platform Backend Pattern (TTS + Window Control)
ABC backends, factory selects via `sys.platform`.
Linux migration: only fill `LinuxTTS` (Piper) and `LinuxWindowBackend` (xdotool+wmctrl).
Every backend must implement `get_status() → dict` with `backend`, `platform`, `ready`/`available`.

### 16. Knowledge Base Pattern
`knowledge/*.yaml` per industry. Lazy-loaded, cached. Schema: `branch`, `weaknesses`, `kpis`, `tools`, `glossary`.
New industry = new YAML file. No code change needed.

### 17. Business Skill — Inline Interview Pattern
`BusinessSkill.handle()` calls `ui.user_prompt()` directly. No state machine in `main.py`.
Score: 100 minus severity deductions (high: -20, medium: -10, low: -5). Reports in `temp/business_reports/`.

### 18. HTML as Primary Output for Web UI (future)
WebSocket sends `{ "type": "response", "html": "..." }`. Terminal renderer stays plaintext.
UI rules: never trigger LLM calls. Avatar reacts to local TTS amplitude only. 0 tokens for UI.

---

## Naming Conventions

| Type | Pattern |
|---|---|
| Tenant profile files | `user_profile_{tenant}.txt` |
| Cloud keys | `zuki:{type}:{tenant}` |
| Skill conversation keys | `zuki:skill:{name}:conversations:{tenant}` |
| Log event markers | `[COMPONENT-ACTION]` e.g. `[CLOUD-SAVE]`, `[TENANT-GUARD]` |
| Business reports | `temp/business_reports/` (gitignored) |

---

## Tenant Guard Convention

```python
tenant_aware: bool = True   # default — all new skills
tenant_aware: bool = False  # explicit opt-out — test/utility skills only (PingSkill, ProfessorSkill)
```
Guard mode controlled by `SKILL_TENANT_GUARD=warn|auto|off` in `.env`.

---

## Known Technical Debt

| # | Item | Risk | Action |
|---|---|---|---|
| 1 | `LLMManager` + `APIManager` overlap | Low | Merge when there is pain |
| 2 | `core/news_manager.py` + `workspaces/broker/scraper.py` both inactive | Low | Consolidate into `workspaces/broker/fetch.py` when live scraper starts |
| 3 | Legacy `zuki:memories` cloud key without tenant suffix | Low | Remove after 2026-05-25 |

---

## Roadmap Summary

### Done
- Bundles 1–12: Resilience layer, state recovery, plugin architecture, system tests,
  GitHub backup, tenant pattern, router agent, cleanup commands, platform agnosticism,
  web scraping layer, PDF reports, knowledge base, coding scratchpad, business skill MVP.

### Next (no active bundle)
- **Bundle 10** — Office Skill + Google Drive (OAuth2, OCR, LLM classification, SQLite index)
- **Bundle 13** — UI Foundation (Vite + React + TS + Tailwind, WebSocket bridge, zustand)

### Blocked
- Bundle 17+ (Business full build) — blocked on praxis test with 5–10 real restaurants first.

### Deferred
- Music-Create (Beat gen, Voice-Swap RVC)
- Streaming Skill (Twitch/YouTube)
- Smart Home (Home Assistant, when hardware arrives)
- Cloud encryption (after real business data flows)
- Multi-device sync (single machine, not needed)

---

## Business Model (context for skill priorities)

Three revenue streams for planned solo self-employment:
1. **Analysis** (free/symbolic) — fast on-site analysis, trust builder, reverses the pitch dynamic
2. **Agency referrals** (one-time commission) — SEO, hiring, web presence via partner list
3. **Workflow optimization** (retainer) — highest margin, highest retention

Industry focus: **Gastro** (dense local market, known pain points, clear tool ecosystem).
Zuki is the tool that makes all three streams possible — the analysis must impress in the first meeting.

---

## Hardware Target (long-term)

Three small displays below main 49" Odyssey OLED G9:
- Left: Avatar panel (Live2D or VRM)
- Center: Stylus notes / ASUS Stylus
- Right: Neural Map (D3.js force-directed graph, live data provenance)

Galleon SD keyboard with Stream Deck for Zuki hotkeys.
Wall display: Samsung SH37F stretched (TradingView ambient).
RAM target: Zuki + full UI under 300 MB (lazy-loading, web architecture).

---

## Linux Migration Checklist

Only two files need real implementation:
- [ ] `core/text_to_speech/linux_tts.py` — implement Piper TTS
- [ ] `tools/window_control/linux_backend.py` — implement xdotool + wmctrl
- [ ] Verify `portaudio19-dev` installed on target machine
- [ ] Run `system test platform` and fix red/yellow results
- [ ] Follow `docs/RECOVERY.md` for full disaster-recovery validation
