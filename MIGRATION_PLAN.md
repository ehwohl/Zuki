# Zuki — MIGRATION_PLAN.md
> Step-by-step checklist to align the existing codebase with the new CLAUDE.md structure.
> Work top to bottom. Do not skip sections. Mark each item ✓ when done.

---

## Phase 1 — Delete Dead Code ✓ DONE (2026-05-16)

These files have no active callers and will be replaced by n8n when that becomes active.
Deleting them now removes noise from every future AI assistant session.

- [x] Delete `core/news_manager.py` — inactive, replaced by n8n RSS in the future
- [x] Delete `workspaces/broker/scraper.py` — inactive, replaced by n8n in the future
- [ ] After 2026-05-25: remove legacy `zuki:memories` cloud key (no tenant suffix) from Redis
- [x] Verify nothing imports `news_manager` or `scraper` anywhere — confirmed clean

---

## Phase 2 — Connect Existing Workspaces to UI Shell ✓ DONE (2026-05-16)

This is the current active priority. Each workspace needs a WebSocket message contract and a React panel that renders it.

### 2a — Broker Workspace ✓

- [x] Define WebSocket message types in `ui_bridge.py`:
  - `broker_map_nodes` — `{ "type": "broker_map_nodes", "nodes": [...] }`
  - `news_item` — already existed (`emit_news_item`) — used by NewsFeed
  - `broker_tick` — already existed (`emit_broker_tick`) — used by Watchlist
- [x] Created `workspaces/broker/skill.py` — `BrokerSkill` emits map nodes on activation
- [x] `WorldMap.tsx` subscribes to `broker_map_nodes` and updates markers live
- [x] NewsFeed and Watchlist already subscribed to `news_item` / `broker_tick` (n8n provides live data when active)

### 2b — Business Workspace ✓

- [x] `business_interview_prompt` — emitted before each interview question
- [x] `business_score` — emitted after analysis + interview completion
- [x] `BusinessWorkspace` now renders Interview panel (prompts) + Score panel
- [x] Score colour-coded: ≥70 green, ≥40 amber, <40 red

### 2c — Coding Workspace ✓

- [x] `coding_output` — emitted in `CodingSkill._run_lang()` after execution
- [x] `CodingWorkspace` Code Buffer panel shows live output with language + timestamp

### 2d — OS Layer Workspace ✓

- [x] `os_status` — `{ "tts": {...}, "stt": {...}, "platform": "win32" }`
- [x] Created `workspaces/os/os_skill.py` — `OsSkill` reads tts/stt from context + emits
- [x] `OsWorkspace` System Status panel renders TTS/STT status with READY/OFFLINE indicator
- [x] OS workspace auto-requests status on mount via WebSocket command

### Cross-cutting changes ✓

- [x] `core/main.py`: imports + starts `ui_bridge` with `_ui_command_handler` closure
- [x] `core/main.py`: `_make_context()` injects `tts` + `stt` into every skill dispatch
- [x] `core/main.py`: broker_mode + BROKER_TRIGGERS/BROKER_EXIT removed — broker is now a proper skill
- [x] `workspaces/base.py`: context docstring updated with tts + stt keys

---

## Phase 3 — Prepare n8n Entry Point (stub only, no active workflows) ✓ DONE (2026-05-16)

Do this once, then leave it until API research is done.

- [x] Create `workspaces/broker/webhook_receiver.py` — minimal Flask endpoint
  ```python
  # POST /webhook/n8n
  # Accepts: { "type": "news_item" | "price_alert", "payload": {...} }
  # Forwards to RouterAgent
  # No business logic here — routing only
  ```
- [x] Register the endpoint in `core/main.py` startup (disabled by default via `.env` flag `N8N_WEBHOOK_ENABLED=false`)
- [x] Document expected payload schemas in a comment block at the top of the file — even though no n8n workflows exist yet

---

## Phase 4 — Architecture Cleanup ✓ DONE (2026-05-16)

Small fixes that make the codebase match CLAUDE.md exactly.

- [x] Audit all files in `core/` for any `print()` calls outside `main.py` and `ui.py` — one violation fixed: `core/text_to_speech/windows_tts.py` mute notification → `get_renderer().system_msg()`
- [x] Audit all skills in `workspaces/` — every skill has `description` set (BrokerSkill, BusinessSkill, CodingSkill, OsSkill, ProfessorSkill all confirmed)
- [x] Audit all skills in `workspaces/` — `tenant_aware` now explicitly set on all skills; added `tenant_aware = True` to `BusinessSkill` (was missing, handles customer DSGVO data)
- [x] Verify all new skills added since Bundle 12 use `APIManager`, not `LLMManager` — confirmed clean (only docstring reference in `base.py`)
- [x] Check `workspaces/os/` — no platform-specific code leaked into `core/`; `sys.platform` usage in `OsSkill` is read-only reporting, not implementation

---

## Phase 5 — Linux Migration Prep (do not start until on Pop!_OS)

Leave these items untouched until you are physically running on the Linux machine.

- [ ] `core/text_to_speech/linux_tts.py` — implement Piper TTS (stub exists)
- [ ] `tools/window_control/linux_backend.py` — implement xdotool + wmctrl (stub exists)
- [ ] Verify `portaudio19-dev` is installed on target machine
- [ ] Run `system test platform` — fix all red/yellow results before proceeding
- [ ] Validate `docs/RECOVERY.md` disaster-recovery procedure end-to-end

---

## What Does NOT Change

These work correctly and require no migration action:

| Thing | Why it stays |
|---|---|
| `tools/cloud_memory.py` | Correct, active, well-structured |
| `zuki_cloud/api/index.py` | REDIS_URL pattern is correct |
| `knowledge/*.yaml` | Pattern is correct, lazy-loaded, no code change needed for new industries |
| `memory/user_profile_{tenant}.txt` | Naming convention is correct |
| `core/router_agent.py` | Two-stage routing works correctly |
| `ui/` scaffold (Bundle 13) | Complete and correct — only needs workspace wiring (Phase 2) |
| `.env` / secret handling | Already correct, never committed |

---

## RAM Budget (revised)

| Process | Target |
|---|---|
| Zuki Python backend | < 150 MB |
| React UI (browser) | < 150 MB |
| **Zuki total** | **< 300 MB** |
| n8n (separate process) | Not counted against Zuki budget — scales independently |
| Future cloud services | Paid tier if needed — not a constraint |

n8n RAM is external infrastructure, not part of Zuki's process budget.
