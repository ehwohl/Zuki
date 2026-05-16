# Zuki — CONTEXT.md
> Current project state and active constraints. Updated per bundle.
> Last updated: 2026-05-16 (post Bundle 16 — Skill-Panels)

---

## Current Focus

**Bundle 16 complete (pending commit).** Monaco editor, Office workspace (Alt+5), Business dashboard (SVG arc gauge + report history) all shipped. Next: Bundle 11 — Music-Practice (pitch detection, instrument/vocal learning mode).

Bundles 1–13 complete. Bundle 16 (Skill-Panels) complete. Business 3D sci-fi polish done. Coding workspace audit done.

---

## What "Done" Looks Like Right Now

- Broker workspace renders live data in the UI (WorldMap, NewsFeed, Watchlist panels populated via WebSocket)
- Business workspace shows interview flow, score output, and 3D city model in the UI
- Coding workspace: Monaco editor (Ctrl+Enter run), code output panel, D3 dependency graph
- OS workspace exposes system status (TTS, STT, platform) in the UI
- All panels communicate exclusively via `ui_bridge.py` WebSocket — no direct Python↔React imports
- **Terminal panel** replaces the old CommandInput — persistent scrollable log, bottom-center, 640×280px default
- **SkillSidebar** — collapsible left sidebar (40px / 240px), z-index 8, 5 categories, 16 commands
- **Office workspace** (Alt+5) — Drive index stats, search panel, auth/reports panel
- **Business dashboard** — SVG arc score gauge (green/amber/red), report history panel (up to 20 PDFs)

---

## UI Architecture (current, post-overhaul)

| Component | File | Notes |
|---|---|---|
| Terminal panel | `ui/src/components/Terminal/index.tsx` | Persistent panel, all workspaces. Operator `›` cyan, Zuki `◆` magenta. |
| Terminal store | `ui/src/store/terminal.store.ts` | Messages + history. `crypto.randomUUID()` for IDs. |
| Skill sidebar | `ui/src/components/SkillSidebar/index.tsx` | Fixed, not a floating panel. `Ctrl+\` toggles. |
| Skill config | `ui/src/components/SkillSidebar/skills.config.ts` | Edit this to add/rename commands. |
| Panel presets | `ui/src/panels/layout_presets.ts` | TERMINAL added to all 4 workspace presets. |
| UI store | `ui/src/store/ui.store.ts` | `terminalFocusSignal`, `terminalInject`, `sidebarExpanded`. No more `commandInputOpen`. |

**Keyboard shortcuts:**
- `Ctrl+Space` — focus terminal input
- `Ctrl+\` — toggle skill sidebar
- `Alt+1–5` — workspace switch (5 = Office)
- `Alt+P` — presentation mode

---

## Active Constraints

- Windows 11 is the current platform — Linux migration is planned but not active
- All new skills use `APIManager`, not `LLMManager`
- No new scraping code in Python — n8n will replace `scraper.py` when data sources are chosen
- `cloud.save()` is never gated by simulation mode — this is a hard rule, not a preference

---

## What to Avoid Right Now

- Starting new Workspaces or Skills before existing ones are UI-connected
- Implementing Linux stubs beyond what already exists
- Choosing APIs or data sources for n8n — that research hasn't happened yet
- Adding Redux, React Context, or any state solution besides Zustand to the UI
- Re-adding a modal/overlay command input — the Terminal panel is the permanent replacement

---

## Backlog (in rough priority order)

| Item | Status | Blocked on |
|---|---|---|
| Commit Bundle 16 | **Immediate** | — |
| Bundle 11 — Music-Practice | **Next** | Pitch detection research needed |
| n8n integration — Trading alerts | Planned, not active | API research (no timeline) |
| n8n integration — RSS news pre-filter | Planned, not active | API research (no timeline) |
| Linux migration — Piper TTS + xdotool | Planned | Hardware (Pop!_OS not yet active) |
| Bundle 17+ — Business full build | Blocked | 5–10 real restaurant tests first |
| Music-Create, Smart Home, Multi-device sync | Deferred | — |

---

## Infrastructure Status

| Service | Status | Notes |
|---|---|---|
| Vercel KV / Redis | Active | `REDIS_URL` in `.env` |
| Vercel Serverless | Active | `zuki_cloud/api/` |
| n8n | Installed locally, not active | No workflows built yet — APIs not chosen |
| RTX 5090 local LLM | Future | Hardware not yet in use |

---

## Known Dead Code (delete when n8n goes active)

| File | Reason |
|---|---|
| `core/news_manager.py` | Inactive — n8n RSS replaces this entirely |
| `workspaces/broker/scraper.py` | Inactive — n8n replaces this entirely |
| `zuki:memories` cloud key (no tenant suffix) | Legacy — remove after 2026-05-25 |
