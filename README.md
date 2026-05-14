# Zuki

Personal AI assistant — voice, vision, broker data, and business analysis.
Runs on Windows today; Linux migration path (Pop!_OS / Ubuntu 24.04) is built in.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python core/main.py
```

## Workspace Map

| Workspace | Path | Responsibility |
|---|---|---|
| Core | `core/` | Main loop, LLM providers, UI, routing, vision, STT/TTS |
| Broker Suite | `workspaces/broker/` | News, watchlist, sentiment, market reports |
| Business Services | `workspaces/business/` | Gastro analysis, PDF reports, client interviews |
| OS Layer | `core/text_to_speech/` `tools/window_control/` `workspaces/os/` | TTS, STT, window control, platform backends |
| Cloud Memory | `tools/cloud_memory.py` `zuki_cloud/` | Vercel KV, outbox, audit, tenant sync |

## Key Files

| File | Purpose |
|---|---|
| `PERSONA.md` | Zuki's identity — loaded as system prompt |
| `CLAUDE.md` | Workspace routing map for AI assistants |
| `REFERENCES.md` | Architecture decisions, naming conventions, tech debt, roadmap |
| `CONTEXT.md` | Active project state and constraints |
| `.env` | Secrets and tunables — never committed |

## Stack

- **Language**: Python 3.14
- **LLM**: Gemini (primary), Claude, GPT — all via `APIManager`
- **STT**: Whisper (local) · **TTS**: pyttsx3/SAPI5 (Windows), Piper stub (Linux)
- **Cloud**: Vercel Serverless + Redis KV (`zuki_cloud/`)
- **UI**: Terminal renderer today; React PWA (`Bundle 13`) planned

## Security Notes

`.env` is gitignored. `system test github` actively verifies it is never committed.
No secrets in code — all credentials loaded via `python-dotenv`.
