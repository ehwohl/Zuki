# Zuki

Personal AI assistant and business intelligence tool — voice, vision, broker data, and field analysis.
Runs on Windows today; Linux migration path (Pop!_OS / Ubuntu 24.04) is built in.

---

## Quick Start

### Python Backend (terminal + voice)

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your API keys
python core/main.py
```

### Zuki-OS Shell (full UI)

Double-click **`zuki_start.bat`** from the project root.

This opens three things in parallel:
- A terminal window running the Vite dev server (`http://localhost:5173`)
- A terminal window running the Python WebSocket bridge (`ws://localhost:8765`)
- Your default browser pointed at the UI

> Requires Node.js installed. Run `npm install` inside `ui/` once before first launch.

```powershell
cd ui
npm install      # first time only
```

---

## Hotkeys (Zuki-OS Shell)

| Key | Action |
|---|---|
| `Ctrl+Space` | Open floating command input |
| `Alt+1` | Broker workspace (War Room) |
| `Alt+2` | Business workspace (Field Intelligence) |
| `Alt+3` | Coding workspace (Circuit Board) |
| `Alt+4` | OS Layer workspace (System Core) |
| `Alt+P` | Toggle presentation mode |
| `Alt+A` | Collapse / expand Avatar panel |
| `Alt+N` | Collapse / expand Neural Map panel |

---

## Folder Structure

```
d:\Zuki\
├── core/                        # Python backend core
│   ├── main.py                  # Entry point — main loop
│   ├── llm_manager.py           # Chat loop LLM (Gemini primary)
│   ├── api_manager.py           # Multi-provider API (all skills use this)
│   ├── router_agent.py          # Two-stage skill routing
│   ├── ui.py / ui_renderer.py   # Terminal renderer (UIRenderer ABC)
│   ├── speech_to_text/          # Whisper STT
│   └── text_to_speech/          # pyttsx3/SAPI5 (Windows), Piper stub (Linux)
│
├── workspaces/                  # Python skill workspaces
│   ├── broker/                  # News, watchlist, market reports
│   ├── business/                # Gastro analysis, PDF reports, interviews
│   ├── coding/                  # Code buffer, scratchpad
│   ├── os/                      # Voice, window control, system tests
│   └── professor/               # Teaching / explanation skill
│
├── ui/                          # Zuki-OS Shell — React PWA (Bundle 13)
│   ├── src/
│   │   ├── bridge/              # WebSocket client (ws.ts)
│   │   ├── components/
│   │   │   ├── AvatarPanel/     # Three.js + @pixiv/three-vrm
│   │   │   ├── NeuralMapPanel/  # D3 v7 force-directed graph
│   │   │   └── CommandInput/    # Floating palette (Framer Motion)
│   │   ├── panels/              # Panel system — drag, resize, persist
│   │   ├── store/               # Zustand stores (workspace, layout, ui, ws)
│   │   ├── themes/              # CSS token definitions (cyberpunk/minimal/presentation)
│   │   └── workspaces/          # Workspace views (broker, business, coding, os)
│   ├── package.json
│   └── vite.config.ts
│
├── ui_bridge.py                 # Python asyncio WebSocket server (port 8765)
│                                # Bridges frontend commands → Python backend
│
├── tools/                       # Shared Python utilities
│   ├── cloud_memory.py          # Vercel KV client
│   ├── window_control/          # wmctrl / win32gui backends
│   └── scraper.py               # Web scraping layer
│
├── knowledge/                   # Industry YAML knowledge bases (lazy-loaded)
├── zuki_cloud/                  # Vercel serverless API + Redis KV
├── memory/                      # User profile + conversation history
├── logs/                        # zuki.log, error.log
├── temp/                        # Reports, cache, vision captures (gitignored)
│
├── zuki_start.bat               # One-click launcher (UI dev server + bridge + browser)
├── Zuki_starten.bat             # Python-only terminal launcher
├── PRODUCT.md                   # UI product contract (Bundle 13+)
├── DESIGN.md                    # Design system — tokens, typography, motion
├── REFERENCES.md                # Architecture decisions, roadmap, tech debt
├── CLAUDE.md                    # Workspace routing map for AI assistants
└── .env                         # Secrets — never committed
```

---

## Stack

### Python Backend
| Layer | Technology |
|---|---|
| Language | Python 3.14 |
| LLM | Gemini 1.5 Flash (primary), Claude, GPT via `APIManager` |
| STT | Whisper (local) |
| TTS | pyttsx3 / SAPI5 (Windows) · Piper stub (Linux) |
| Cloud | Vercel Serverless + Redis KV (`zuki_cloud/`) |

### Zuki-OS Shell (Bundle 13)
| Layer | Technology |
|---|---|
| Framework | React 18 + TypeScript (strict) |
| Build | Vite 5 + PWA plugin |
| Styling | Tailwind CSS (layout only) + CSS custom properties (all tokens) |
| State | Zustand — no Redux, no Context |
| 3D | Three.js + `@pixiv/three-vrm` (Avatar) |
| Graph | D3 v7 + TopoJSON (Neural Map + World Map) |
| Motion | Framer Motion (command input only) |
| IPC | WebSocket (`ui_bridge.py` ↔ `ui/src/bridge/ws.ts`) |

---

## Key Files

| File | Purpose |
|---|---|
| `PERSONA.md` | Zuki's identity and character — loaded as system prompt |
| `CLAUDE.md` | Workspace routing map for AI assistants |
| `REFERENCES.md` | Architecture decisions, naming conventions, tech debt, roadmap |
| `PRODUCT.md` | UI product contract — scope, constraints, WebSocket protocol |
| `DESIGN.md` | Design system — color tokens, typography, motion, aesthetic rules |
| `.env` | Secrets and tunables — never committed |

---

## Security

`.env` is gitignored. `system test github` actively verifies it is never committed.
No secrets in code — all credentials loaded via `python-dotenv`.
Three-layer backup: GitHub auto-commit (6h) · local `backups/` snapshots · Vercel KV cloud memory.
