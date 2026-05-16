# Zuki — CONTEXT.md
> Current project state and active constraints. Updated per bundle.
> Last updated: 2026-05 (post-Bundle 13)

---

## Current Focus

**Prio 1: Bundle 10 — Office Skill + Google Drive.**

Bundle 14 (Business 3D city + Coding dep graph) is complete. CityScene (Three.js) and DepGraph
(D3 force-directed) are implemented and wired end-to-end: React components, workspace panels,
bridge emitters, skill calls. Migration plan phases 1–4 also done. Pending commit.

---

## What "Done" Looks Like Right Now

- Broker workspace renders live data in the UI (WorldMap, NewsFeed, Watchlist panels populated via WebSocket)
- Business workspace shows interview flow, score output, and 3D city model in the UI
- Coding workspace shows scratchpad output and D3 dependency graph in the UI
- OS workspace exposes system status (TTS, STT, platform) in the UI
- All panels communicate exclusively via `ui_bridge.py` WebSocket — no direct Python↔React imports

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

---

## Backlog (in rough priority order)

| Item | Status | Blocked on |
|---|---|---|
| Bundle 14 — Business 3D city + Coding dep graph | **Done** (pending commit) | — |
| Bundle 10 — Office Skill + Google Drive | **Active** | — |
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
