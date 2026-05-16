# Zuki

Personal AI assistant — a local Python core with a React PWA shell. Zuki lives on your PC, speaks German, controls windows, remembers context across sessions, and routes tasks to skill-specific workspaces.

Not a SaaS. Not multi-user. One machine, one principal.

---

## What it does

- **Natural language interface** — type or speak; Zuki routes to the right skill automatically via two-stage routing (exact trigger → LLM router)
- **Voice I/O** — Whisper STT + platform-native TTS (pyttsx3/SAPI5 on Windows, Piper stub for Linux)
- **Cloud memory** — persists facts, bio, and skill conversations in Vercel KV/Redis; offline outbox buffers writes when cloud is unavailable
- **Multi-tenant isolation** — private data (`self`) and client data (`client-xyz`) are strictly separated; DSGVO-aware provider selection per tenant
- **Provider-agnostic LLM** — Gemini, Claude, OpenAI switchable via `APIManager`; no vendor lock-in
- **Window control** — focus, resize, and switch apps via Win32 (Linux stubs ready for `xdotool`/`wmctrl`)
- **React UI shell** — browser-based dashboard with resizable panels, terminal log, neural map, VRM avatar, and workspace views

---

## Skill Workspaces

| Workspace | What it does |
|-----------|-------------|
| **Professor** | Structured explanations (`explain <topic>`) |
| **Broker** | News inbox, watchlist, n8n webhook receiver for market data ingestion |
| **Business** | Gastro analyzer — competitor mapping, weakness detection, PDF report for client meetings |
| **Coding** | Monaco editor panel + sandboxed code buffer (Python, JS, TS, Bash, Go) |
| **Office** | Google Drive indexer, OCR document classifier (`explain me all 2025 tax docs`) |
| **Music** | Real-time pitch detection, chromatic tuner, session log (AudioWorklet + pitchfinder) |
| **OS** | PC control, window management, voice config |

---

## Quick Start

### Python backend

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
python core/main.py
```

### Zuki-OS Shell (React UI)

```bash
cd ui
npm install      # first time only
npm run dev      # http://localhost:5173
```

Then start the WebSocket bridge in a second terminal:

```bash
python ui_bridge.py  # ws://localhost:8765
```

Or use **`zuki_start.bat`** at the project root to launch all three at once.

---

## Hotkeys (Zuki-OS Shell)

| Key | Action |
|---|---|
| `Ctrl+Space` | Open floating command input |
| `Alt+1` | Broker workspace |
| `Alt+2` | Business workspace |
| `Alt+3` | Coding workspace |
| `Alt+4` | OS Layer workspace |
| `Alt+5` | Office workspace |
| `Alt+6` | Music workspace |
| `Alt+P` | Toggle presentation mode |
| `Alt+A` | Collapse / expand Avatar panel |
| `Alt+N` | Collapse / expand Neural Map panel |

---

## Folder Structure

```
Zuki/
├── core/                        # Python backend
│   ├── main.py                  # Entry point — main loop + command dispatch
│   ├── api_manager.py           # Multi-provider LLM (Gemini/Claude/OpenAI)
│   ├── router_agent.py          # Two-stage skill routing
│   ├── tenant.py                # TenantManager + DSGVO-aware provider selection
│   ├── ui.py / ui_renderer.py   # TerminalRenderer (UIRenderer ABC)
│   ├── speech_to_text/          # Whisper STT engine
│   └── text_to_speech/          # TTSBackend ABC → WindowsTTS / LinuxTTS (stub)
│
├── workspaces/                  # Skill workspaces (auto-discovered)
│   ├── broker/                  # News inbox, watchlist, webhook receiver
│   ├── business/                # Gastro analyzer, PDF reports, CRM
│   ├── coding/                  # Code buffer, Monaco integration
│   ├── music/                   # Pitch detection, tuner, session log
│   ├── office/                  # Drive indexer, OCR classifier
│   ├── os/                      # Window control, voice settings
│   └── professor/               # Structured explanation skill
│
├── ui/                          # React PWA (Vite + TypeScript + Tailwind)
│   └── src/
│       ├── bridge/              # WebSocket client (ws.ts)
│       ├── components/
│       │   ├── AvatarPanel/     # Three.js + @pixiv/three-vrm
│       │   ├── NeuralMapPanel/  # D3 v7 force-directed graph
│       │   └── Terminal/        # Persistent scrollable command log
│       ├── panels/              # Panel system — drag, resize, layout presets
│       ├── store/               # Zustand stores
│       └── workspaces/          # Workspace views per skill
│
├── tools/                       # Shared utilities
│   ├── cloud_memory.py          # Vercel KV client + offline outbox
│   ├── backup_manager.py        # Local snapshots (7-rotation, 6h auto)
│   ├── github_backup.py         # Off-site code backup (auto-commit thread)
│   ├── instance_guard.py        # Single-instance lock via socket
│   ├── session_state.py         # Crash detection + recovery
│   ├── system_test.py           # 14-subsystem self-diagnostic
│   └── window_control/          # WindowBackend ABC → Win32 / xdotool stub
│
├── zuki_cloud/                  # Vercel serverless API (Flask + Redis)
├── memory/                      # Chat history + user profiles (per tenant)
├── knowledge/                   # Industry YAML knowledge bases
├── docs/                        # RECOVERY.md, MIGRATION.md
├── logs/                        # zuki.log, error.log (gitignored)
├── backups/                     # Local snapshots (gitignored)
├── temp/                        # Vision frames, cloud outbox (gitignored)
│
├── ui_bridge.py                 # asyncio WebSocket bridge (port 8765)
├── PERSONA.md                   # Zuki identity — loaded as system prompt
└── .env                         # Secrets — never committed
```

---

## Stack

### Python Backend

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| LLM | Gemini (primary), Claude, OpenAI via `APIManager` |
| STT | Whisper (local, on-demand load) |
| TTS | pyttsx3/SAPI5 (Windows) · Piper stub (Linux) |
| Cloud | Vercel Serverless + Redis KV |

### React UI

| Layer | Technology |
|---|---|
| Framework | React 18 + TypeScript (strict) |
| Build | Vite 5 + PWA plugin |
| Styling | Tailwind CSS (layout) + CSS custom properties (all tokens) |
| State | Zustand — no Redux, no Context API |
| 3D | Three.js + `@pixiv/three-vrm` (Avatar panel) |
| Graph | D3 v7 + TopoJSON (Neural Map, World Map) |
| Editor | Monaco Editor (Coding workspace) |
| Audio | Web Audio API + AudioWorklet (Music workspace) |
| Motion | Framer Motion (command input) |
| IPC | WebSocket (`ui_bridge.py` ↔ `ws.ts`) |

---

## Environment Variables (`.env`)

```
# LLM providers
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Cloud memory (Vercel KV)
REDIS_URL=redis://...
ZUKI_CLOUD_URL=https://your-deployment.vercel.app
ZUKI_TOKEN=

# GitHub off-site backup
GITHUB_TOKEN=
GITHUB_REPO=username/zuki-backup

# UI renderer: terminal | web
ZUKI_UI=terminal
```

---

## Architecture Highlights

**Two-stage skill routing**

```
User input
  → Stage 1: exact trigger match  (0 tokens, microseconds)
  → Stage 2: RouterAgent LLM call (~80 token output, ~1-2s)
  → Skill.handle()
```
Skills without a `description` field are invisible to the router.

**Multi-tenant isolation**
- Cloud keys: `zuki:memories:{tenant}`, `zuki:audit:{tenant}`
- Profile files: `memory/user_profile_{tenant}.txt`
- `require_dsgvo = True` blocks non-compliant providers (e.g. Gemini Free) for client tenants

**Platform backends (ABC pattern)**
- TTS: `TTSBackend` → `WindowsTTS` (live) / `LinuxTTS` (Piper stub)
- Window control: `WindowBackend` → `WindowsWindowBackend` (live) / `LinuxWindowBackend` (stub)
- Linux migration touches only the two stub files — core is untouched

**Cloud memory is simulation-independent**
- `cloud.save()` is never gated by LLM simulation mode
- Offline writes buffer to `temp/cloud_outbox.jsonl` and flush on reconnect

---

## System Test

```bash
python -c "
import sys; sys.path.insert(0, '.')
from tools.system_test import SystemTest
SystemTest().run_all()
"
```

Covers 14 subsystems: cloud connectivity, GitHub backup, `.env` leak detection, TTS, STT, tenant isolation, and more.

---

## Security

- `.env` is gitignored; `system test github` actively verifies it was never committed
- All credentials loaded via `python-dotenv` — nothing hardcoded
- Three-layer backup: GitHub auto-commit (6h) · local `backups/` snapshots (7-rotation) · Vercel KV cloud memory

---

## Planned

- Hotword detection (Picovoice Porcupine — `"Zuki, ..."`)
- n8n as data ingestion layer (polls APIs, fires webhooks to `broker/webhook_receiver.py`)
- Linux migration (Pop!_OS or Ubuntu 24.04 LTS)
- 3D VRM avatar with TTS lip-sync amplitude
- Streaming skill (Twitch integration)
