# \# Zuki-OS — UI Product Requirements Document

# > Version 1.0 · May 2026 · Bundle 13 Scope

# > Status: Draft — Authoritative design contract

# 

# \---

# 

# \## 1. Purpose \& Scope

# 

# This PRD defines the visual system, interaction model, and technical architecture for \*\*Zuki-OS\*\*: a personal operating center and business intelligence tool. It covers the React PWA frontend, the WebSocket bridge to the Python backend, and all workspace-specific views.

# 

# This document is the single source of truth for Bundle 13 and all subsequent UI bundles. Implementation decisions that contradict this PRD must be resolved here first, not in code.

# 

# \*\*Out of scope:\*\* Backend logic, LLM provider selection, cloud schema, TTS/STT internals.

# 

# \---

# 

# \## 2. Aesthetic Contract

# 

# \*\*Name:\*\* Zuki-OS

# \*\*Style:\*\* High Tech – Low Life

# \*\*Reference:\*\* A netrunner's personal deck. Functionally dense, atmospherically hostile to anything clean or corporate.

# 

# \### 2.1 Visual Language

# 

# | Token | Value |

# |---|---|

# | Background | Near-black matte (`#0A0C10`) with subtle noise/grain overlay |

# | Primary accent | Cyan (`#00F5FF`) |

# | Secondary accent | Magenta (`#FF00A0`) |

# | Warning / financial | Amber (`#FFB300`) |

# | Text primary | Off-white (`#E8EAF0`) |

# | Text secondary | Dim cyan-grey (`#607080`) |

# | Borders | 1px, `rgba(0,245,255,0.15)` — low-opacity glow lines |

# | Panel background | `rgba(10,15,20,0.85)` — frosted dark glass |

# 

# \### 2.2 Typography

# 

# | Role | Font | Notes |

# |---|---|---|

# | Display / headers | `Orbitron` or `Rajdhani` | Geometric, angular, tech |

# | Monospace / data | `JetBrains Mono` | All numbers, terminal output, code |

# | Body / labels | `Chakra Petch` | Compressed, readable at small sizes |

# 

# All font sizes in `rem`. No system fonts. No Inter. No Roboto.

# 

# \### 2.3 Motion — Must-Have

# 

# Two atmospheric effects are \*\*mandatory\*\* (non-negotiable across all views):

# 

# 1\. \*\*Glitch Transition\*\* — Every workspace switch triggers a 200–400ms glitch: horizontal scan-line tear, brief RGB channel separation, then snap to new view. Implemented via CSS `clip-path` + `filter` animation chain. No JS animation library dependency for this effect.

# 

# 2\. \*\*Glow-Pulse\*\* — When Zuki speaks (TTS active), the avatar border, the active panel's glow border, and the chat input accent all pulse synchronously at the TTS amplitude envelope. WebSocket emits amplitude ticks; React drives CSS custom property `--pulse-intensity` in real time.

# 

# \*\*Nice-to-have (not blocking v1):\*\* Per-workspace sound profiles (ambient audio, AudioContext, activates on first user interaction per browser policy).

# 

# \---

# 

# \## 3. Layout Architecture

# 

# \### 3.1 Core Principle: Free-Floating Panel System

# 

# There is \*\*no fixed layout\*\*. Every panel is:

# \- Freely positionable (drag by header bar)

# \- Resizable (corner/edge handles)

# \- Independently collapsible

# 

# Panel layout is persisted per workspace to `localStorage` under the key `zuki:layout:{workspaceId}`. On first launch, each workspace loads a \*\*default layout preset\*\* (defined in `layout\_presets.ts`). The user can reset to preset at any time.

# 

# \*\*Implementation:\*\* Use a lightweight panel manager (e.g. `react-grid-layout` or custom drag logic with Zustand state). Every panel has: `id`, `x`, `y`, `w`, `h`, `collapsed: bool`, `zIndex`.

# 

# \### 3.2 Persistent Panels (all workspaces)

# 

# Two panels exist across every workspace. They are never destroyed — only their visual state changes.

# 

# \#### Avatar Panel

# \- Default position: left edge, bottom quarter of screen

# \- Default size: \~280px wide, \~320px tall

# \- Content: VRM 3D avatar rendered via `@pixiv/three-vrm` + Three.js canvas

# \- Reacts to TTS amplitude (mouth/body animation driven by `--pulse-intensity`)

# \- \*\*Renderer abstraction required:\*\* Avatar panel accepts a `renderer: 'vrm' | 'live2d'` prop. Implementation must not assume VRM — the prop controls which renderer is mounted. Default: `vrm`. This allows drop-in Live2D swap without layout changes.

# \- Collapses to a 48×48px icon via hotkey `Alt+A`

# 

# \#### Neural Map Panel

# \- Default position: right edge, upper half of screen

# \- Default size: \~340px wide, \~400px tall

# \- Content: D3.js force-directed graph

# \- \*\*Mode is workspace-driven:\*\* the active workspace pushes a `NeuralMapMode` to Zustand:

# &#x20; - `'routing'` — shows which workspace/skill handled the last input and why (node graph of router decisions)

# &#x20; - `'provenance'` — shows where data came from (Cloud → Redis, Scraper → SerpAPI, LLM → Gemini, etc.)

# &#x20; - `'both'` — provenance graph with routing overlay (default for most workspaces)

# \- Nodes are clickable: clicking a node opens a tooltip with raw metadata

# \- Collapses to a 48×48px icon via hotkey `Alt+N`

# 

# \### 3.3 Workspace Content Area

# 

# The area between (and around) the persistent panels is the workspace canvas. This is where workspace-specific panels render. Workspaces do not share panel state.

# 

# \---

# 

# \## 4. Input Model

# 

# \### 4.1 Floating Command Input

# 

# There is \*\*no persistent input bar\*\*. The command input is a floating overlay that appears on demand.

# 

# \*\*Trigger:\*\* Global hotkey `Ctrl+Space` (or user-configurable). When triggered:

# 1\. A centered floating panel slides up from bottom with a glitch-in effect (\~150ms)

# 2\. Zuki's avatar subtly "activates" (eye glow, posture shift)

# 3\. Input accepts text or streams from Whisper STT (backend emits partial transcripts over WebSocket)

# 4\. `Enter` / `Escape` dismisses

# 

# \*\*Design:\*\* The input is not a chat window. It is a command palette — single line, full-width of the floating panel, monospace font. Below the input line: last Zuki response, scrollable, max 3 lines visible before scroll.

# 

# \*\*Chat history:\*\* Accessible as a collapsible panel (`Alt+H`) showing full conversation in terminal-log style — not a messenger UI, not bubbles. Pure chronological monospace log with timestamps.

# 

# \### 4.2 Stream Deck Integration (Primary Navigation)

# 

# Stream Deck is the primary workspace switcher. The backend maps Stream Deck key events to WebSocket messages (`type: 'navigate', workspace: 'broker'`). The frontend subscribes and triggers the workspace switch + glitch transition.

# 

# Mouse/keyboard navigation is fully supported as fallback. Touch (stylus panel) is supported via standard pointer events — no special touch-only code path needed.

# 

# \---

# 

# \## 5. Workspace Views

# 

# \### 5.1 Broker — "War Room"

# 

# The most defined workspace. Inspired by a military command center.

# 

# \*\*Center panel:\*\* Dynamic world SVG map. Data-source nodes pulse at update frequency. Clicking a node drills into that asset/region. Map uses a dark-projected Mercator — no color fill, only glow-line coastlines in `rgba(0,245,255,0.1)`.

# 

# \*\*Right sidebar panel\*\* (separate from Neural Map): News feed as a terminal log. New items scroll in from bottom. Each line: `\[HH:MM] SOURCE · Headline`. Urgent items flash amber for 3s.

# 

# \*\*Top bar panel:\*\* Watchlist — horizontal strip of tickers with price, delta, mini-sparkline. All numbers in `JetBrains Mono`. Green/red via `--color-up` / `--color-down` tokens (not hardcoded).

# 

# \*\*External display routing:\*\* The broker workspace emits `window\_profile: 'broker'` over WebSocket. The Python backend reads `window\_profiles.json` and routes TradingView to the wall display via `wmctrl`. This is purely a backend concern — the frontend fires and forgets.

# 

# \*\*Neural Map mode in Broker:\*\* `'provenance'` — shows live data flow: SerpAPI → Scraper → News → UI.

# 

# \*\*3D element:\*\* None in v1. The SVG world map is the visual centerpiece. 3D is reserved for other workspaces.

# 

# \### 5.2 Business — "Field Intelligence"

# 

# Context: Gastro analysis tool. Used both privately and in client-facing presentation mode.

# 

# \*\*3D Scene: City Model\*\*

# \- A stylized low-poly 3D city rendered in Three.js

# \- Restaurant/venue locations are nodes on the map — pulled from the last `AnalysisResult`

# \- Nodes are color-coded by score (cyan = strong, amber = medium, magenta = weak)

# \- \*\*Fully interactive:\*\* rotate, zoom, drag. Click a node to open the venue's analysis panel

# \- Scene is not realistic — it is deliberately abstract and stylized (cyberpunk city grid, no textures, only glow-outlined geometry)

# 

# \*\*Analysis panels (floating):\*\*

# \- Score panel: large number, severity breakdown

# \- Weakness list: expandable, each item shows severity badge

# \- KPI snapshot: horizontal bar charts, target vs actual

# \- Recommendations: bulleted, tool-mapped

# 

# \*\*Presentation Mode\*\* (`Alt+P` or Stream Deck key):

# \- Hides: avatar panel, neural map panel, command history, all dev-facing info

# \- Shows: full-screen city model + analysis panels only, with higher contrast

# \- A discrete "EXIT PRESENTATION" button appears in the corner (40% opacity until hover)

# \- Presentation mode state is not persisted — always resets to normal on app restart

# 

# \*\*Neural Map mode in Business:\*\* `'routing'` — shows how the analyzer assembled the result (Place fetch → Instagram → Weakness detection → Score calc).

# 

# \### 5.3 Coding — "Circuit Board"

# 

# \*\*3D Scene: Dependency Graph\*\*

# \- The active `CodeBuffer` content is parsed for imports/calls

# \- Rendered as a 3D force-directed graph in Three.js (nodes = modules/functions, edges = dependencies)

# \- Graph updates live as the buffer changes (debounced 800ms after last keystroke)

# \- \*\*Fully interactive:\*\* rotate, zoom, drag nodes to reposition

# \- Node color: language-coded (Python = cyan, JS = amber, Bash = magenta)

# \- Clicking a node highlights all edges and opens a detail tooltip

# 

# \*\*Editor panels (floating):\*\*

# \- Buffer panel: syntax-highlighted code editor (read-only display of current buffer, `CodeMirror` or simple `pre` with highlight.js)

# \- Run result panel: stdout/stderr in terminal style, exit code badge

# \- Language switcher: tab strip for all active language buffers

# 

# \*\*Neural Map mode in Coding:\*\* `'provenance'` — shows execution path: Buffer → Sandbox → RunResult → UI.

# 

# \### 5.4 OS Layer — "System Core"

# 

# \*\*3D Scene: Terrain Monitor\*\*

# A 3D terrain mesh where elevation = system load. Surface generated from live metrics:

# \- CPU per-core usage → terrain peaks

# \- RAM usage → terrain color gradient (cool = low, hot = high)

# \- Disk I/O → ripple animation on the surface

# 

# Implemented via Three.js `PlaneGeometry` with per-vertex displacement updated on each metrics tick (WebSocket pushes metrics at \~2Hz). The terrain is \*\*fully interactive\*\*: rotate, zoom, drag — so the user can inspect specific "mountains" (high-load cores).

# 

# This is the most technically demanding 3D scene. v1 may ship with a static terrain that updates every 5s instead of per-frame vertex animation — this is an acceptable phased delivery.

# 

# \*\*System panels (floating):\*\*

# \- Process list: top-N processes, sortable by CPU/RAM

# \- TTS/STT status: backend, voice, ready state

# \- Window control: list of managed windows, focus buttons

# \- Platform test results: color-coded subsystem grid (mirrors `system test` output)

# 

# \*\*Neural Map mode in OS:\*\* `'routing'` — shows which backend subsystem handled the last command.

# 

# \---

# 

# \## 6. Presentation Mode (Cross-Workspace)

# 

# Triggered by `Alt+P` or dedicated Stream Deck key.

# 

# \*\*What it does:\*\*

# \- Hides: avatar, neural map, command history, all system status, debug info

# \- Maximizes: the primary workspace content panel

# \- Applies `theme-presentation` CSS class to root: slightly higher text contrast, removes grain overlay, disables glitch transitions (too distracting for clients)

# \- Shows a discrete "ZUKI-OS" watermark in the corner (`opacity: 0.15`)

# 

# \*\*What it does not do:\*\*

# \- Does not change data — the analysis showing is always real data

# \- Does not persist — exits on app restart or `Alt+P` toggle

# 

# \---

# 

# \## 7. Theme System

# 

# Three themes ship with v1. Switching is instant (CSS custom property swap, no re-render).

# 

# | Theme | Description | Primary Use |

# |---|---|---|

# | `cyberpunk` | Default. Dark matte, cyan/magenta/amber accents, grain, glitch | Private use |

# | `minimal` | Dark grey, white text, no glow, no grain, subtle transitions | Focused work |

# | `presentation` | High contrast, no effects, Zuki watermark | Client-facing |

# 

# Each theme is a flat object of CSS custom property overrides loaded into `:root`. Zero component code changes needed for theme swap.

# 

# \---

# 

# \## 8. Technical Constraints

# 

# \### 8.1 Frontend Stack

# 

# | Package | Role | Constraint |

# |---|---|---|

# | Vite | Build | — |

# | React 18 + TypeScript | Framework | Strict mode on |

# | Tailwind CSS | Utility styling | Only for layout/spacing; theme tokens via CSS vars |

# | Zustand | State | No Redux, no Context for shared state |

# | Three.js r128 | 3D scenes | No `OrbitControls` import — implement custom camera control |

# | `@pixiv/three-vrm` | Avatar | Behind `renderer === 'vrm'` guard |

# | D3.js | Neural Map | v7 |

# | `websockets` (Python) | IPC bridge | — |

# 

# \### 8.2 Performance Targets

# 

# \- Initial load (cold): < 3s on target machine

# \- Workspace switch (including glitch transition): < 400ms

# \- 3D scene frame rate: ≥ 30fps during interaction, ≥ 60fps at idle

# \- Total RAM (Zuki process + UI): < 300MB

# \- WebSocket message latency: < 50ms on localhost

# 

# \### 8.3 PWA Requirements

# 

# \- `display\_override: window-controls-overlay` — frameless

# \- Window drag surface: entire root element, marked with `app-region: drag`

# \- Interactive elements: explicitly marked `app-region: no-drag`

# \- Close/minimize controls: custom SVG icons, appear only on hover (opacity 0 → 1 on root hover)

# 

# \### 8.4 Panel Persistence Schema

# 

# ```typescript

# interface PanelState {

# &#x20; id: string;

# &#x20; x: number;        // px from left

# &#x20; y: number;        // px from top

# &#x20; w: number;        // px

# &#x20; h: number;        // px

# &#x20; collapsed: boolean;

# &#x20; zIndex: number;

# }

# 

# // localStorage key: zuki:layout:{workspaceId}

# // Value: PanelState\[]

# ```

# 

# Panel state is written on every drag/resize end (debounced 500ms). Corrupt state falls back to default preset silently.

# 

# \---

# 

# \## 9. WebSocket Message Contract

# 

# All messages are JSON. The Python backend emits, the React frontend subscribes (and vice versa for input).

# 

# \### Backend → Frontend

# 

# | `type` | Payload | Description |

# |---|---|---|

# | `response` | `{ text, html?, workspace }` | Zuki's reply |

# | `tts\_amplitude` | `{ value: 0.0–1.0 }` | Drives glow-pulse at \~30Hz |

# | `router\_decision` | `{ skill, reason, sources\[] }` | Neural Map update |

# | `metrics` | `{ cpu\[], ram, disk\_io }` | OS terrain update at \~2Hz |

# | `news\_item` | `{ source, headline, timestamp }` | Broker news feed |

# | `broker\_tick` | `{ symbol, price, delta, sparkline\[] }` | Watchlist update |

# | `workspace\_change` | `{ workspace }` | Backend-initiated nav (Stream Deck) |

# 

# \### Frontend → Backend

# 

# | `type` | Payload | Description |

# |---|---|---|

# | `command` | `{ text, workspace, tenant }` | User text/voice input |

# | `navigate` | `{ workspace }` | Workspace switch |

# | `presentation\_mode` | `{ active: bool }` | Toggle presentation |

# 

# \---

# 

# \## 10. Open Decisions (Not Blocking v1)

# 

# These are intentionally deferred. Do not implement stubs — leave extension points in the architecture.

# 

# | # | Topic | Current stance |

# |---|---|---|

# | 1 | Live2D avatar renderer | `renderer` prop exists; Live2D implementation deferred until a character model exists |

# | 2 | Sound profiles per workspace | AudioContext wrapper stubbed but silent in v1 |

# | 3 | Coding 3D: parser depth | v1 parses only top-level imports; full call-graph deferred |

# | 4 | OS terrain: per-frame vertex animation | v1 may use 5s polling; upgrade to `requestAnimationFrame` when performance validated |

# | 5 | Multi-device sync | Single machine. No sync. Not in scope. |

# | 6 | Stream Deck key mapping UI | v1 uses hardcoded `window\_profiles.json`; configuration UI deferred |

# 

# \---

# 

# \## 11. Delivery Phases

# 

# \### Phase 1 — Shell (Bundle 13)

# \- PWA scaffold, frameless, draggable

# \- Panel system with persistence

# \- Floating command input + WebSocket bridge

# \- Cyberpunk theme tokens

# \- Glitch transition (CSS only)

# \- Avatar panel (VRM, placeholder model)

# \- Neural Map panel (static mock data)

# \- Broker workspace (map + news feed + watchlist)

# 

# \### Phase 2 — Business \& Coding (Bundle 14)

# \- Business 3D city scene

# \- Coding 3D dependency graph

# \- Presentation mode

# \- Glow-pulse (TTS amplitude integration)

# 

# \### Phase 3 — OS Layer \& Polish (Bundle 15)

# \- OS terrain scene

# \- Sound profile architecture (silent by default)

# \- Theme switcher UI

# \- Stream Deck key mapping

# \- Performance profiling pass (300MB RAM target validation)



