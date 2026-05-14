# Zuki — CLAUDE.md

Role: Senior Software Architect. Code first, bullets after. No small talk.

## Routing

| Task | Workspace | Location |
|---|---|---|
| Main loop, providers, UI, routing, vision | Core | `core/` |
| News, watchlist, sentiment, reports | Broker Suite | `workspaces/broker/` |
| Gastro analysis, PDF reports, interviews | Business Services | `workspaces/business/` |
| TTS, STT, window control, platform backends | OS Layer | `core/text_to_speech/` `tools/window_control/` `workspaces/os/voice/` |
| Vercel KV, outbox, audit, tenant sync | Cloud Memory | `tools/cloud_memory.py` `zuki_cloud/` |

## Language
- Code, docs, comments → **English**
- Terminal output, logs → **German** (via `ui.*` methods only — never `print()`)

## On conflict
REFERENCES.md wins over this file. This file is the map, REFERENCES.md is the truth.
