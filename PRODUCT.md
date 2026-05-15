# Zuki-OS — Product Contract

> Authoritative spec for Bundle 13 (Shell) and all subsequent UI bundles.
> Implementation decisions that contradict this document must be resolved here first.
> `REFERENCES.md` wins on architecture conflicts. This document wins on UI decisions.

---

## Identity

**Name**: Zuki-OS
**Concept**: A personal operations deck built for a lone operator. The interface of a practitioner — someone who works with hidden systems, real-time data, and precision tools in the dark.
**Style**: Gothic / Occult High-Tech
**Target user**: Solo operator (Paul). Not a SaaS product. No onboarding flows. No empty states with friendly illustrations.

### What "Gothic / Occult High-Tech" means in practice

The aesthetic sits at the intersection of three things:

- **Gothic**: weight, depth, darkness as atmosphere — not decoration. Interfaces feel like manuscripts: dense, intentional, slightly hostile to the uninitiated.
- **Occult**: hidden structure made visible. The Neural Map is a ritual diagram of data provenance. The router decision graph is a sigil of machine logic. Data flows are not sanitized — they are shown as they are.
- **High-Tech**: precision, speed, no wasted pixels. Glitch transitions are not errors — they are the system revealing its seams on purpose.

The reference is not a game UI or a sci-fi movie prop. It is the terminal of someone who actually uses it.

---

## Bundle 13 — The Shell (COMPLETE)

All Phase 1 deliverables are shipped and pushed to GitHub.

| Deliverable | Status |
|---|---|
| PWA scaffold, frameless, `window-controls-overlay` | ✓ Done |
| Gothic/Occult theme tokens (CSS custom properties, 3 themes) | ✓ Done |
| Glitch workspace transition (CSS-only, 350ms, `steps(4)`) | ✓ Done |
| Free-floating panel system — drag, resize, collapse, localStorage persist | ✓ Done |
| Floating command input (`Ctrl+Space`, Framer Motion slide-up) | ✓ Done |
| WebSocket bridge — Python `ui_bridge.py` ↔ React `bridge/ws.ts` | ✓ Done |
| Avatar panel (Three.js + `@pixiv/three-vrm`, placeholder scene) | ✓ Done |
| Neural Map panel (D3 v7 force-directed, all 3 modes) | ✓ Done |
| Broker workspace — WorldMap (D3+TopoJSON) + NewsFeed + Watchlist | ✓ Done |
| Business / Coding / OS workspaces — extension-point placeholders | ✓ Done |
| One-click launcher (`zuki_start.bat`) | ✓ Done |

---

## Bundle 14 — Business & Coding (NEXT)

| Deliverable | Notes |
|---|---|
| Business 3D city scene | Three.js low-poly grid city. Venue nodes color-coded by score. |
| Coding 3D dependency graph | Three.js force-directed. Nodes = modules. Edges = imports. |
| Presentation mode | `Alt+P` — hides avatar/neural map, maximizes workspace content. |
| Glow-pulse full integration | TTS amplitude → avatar border + active panel + command input sync. |

---

## Bundle 15 — OS Layer & Polish (PLANNED)

| Deliverable | Notes |
|---|---|
| OS terrain scene | Three.js `PlaneGeometry`. CPU per-core → vertex displacement. RAM → surface color. |
| Sound profile architecture | AudioContext wrapper. Silent by default. Activates on first interaction. |
| Theme switcher UI | Runtime swap via `applyTheme()`. No re-render. |
| Stream Deck key mapping | Hardcoded `window_profiles.json` → config UI. |
| Performance audit | 300MB RAM target validation. |

---

## Hard Constraints

### Performance
- Cold load: < 3s on target machine
- Workspace switch (including glitch transition): < 400ms
- 3D scene frame rate: ≥ 30fps during interaction, ≥ 60fps at idle
- **Total RAM (Python process + UI browser combined): < 300MB**
- All 3D scenes lazy-loaded — never bundled into the initial chunk

### Architecture
- **No Redux. No React Context for shared state.** Zustand only.
- **Tailwind for layout and spacing only.** All visual tokens live in CSS custom properties.
- **No OrbitControls from Three.js.** Custom pointer-event camera control in every 3D scene.
- **Glitch transition: CSS-only.** No JS animation library involved in this effect.
- **Avatar renderer: prop-driven.** `renderer: 'vrm' | 'live2d'` prop controls which renderer mounts. Layout code never assumes VRM.
- **Theme swap: CSS var reassignment only.** Zero React re-renders when switching themes.
- **Glow-pulse: direct DOM write.** `document.documentElement.style.setProperty('--pulse-intensity', value)` — not React state.

### PWA
- `display_override: window-controls-overlay` — no OS chrome
- Entire root element: `WebkitAppRegion: drag`
- All interactive elements: `WebkitAppRegion: no-drag`
- Close/minimize controls: custom SVG, `opacity: 0` until root hover

### Panel Persistence
- Storage key: `zuki:layout:{workspaceId}` in localStorage
- Schema: `PanelState[]` — `{ id, x, y, w, h, collapsed, zIndex }`
- Debounced write: 500ms after drag/resize end
- Corrupt or missing state: falls back to workspace default preset, silently

### WebSocket Protocol
- All messages: JSON
- Default port: `8765` — configurable via `VITE_WS_URL` env var
- Reconnect strategy: exponential backoff starting at 1s, capped at 30s
- See `REFERENCES.md §WebSocket Message Contract` for full type definitions

---

## What Zuki-OS Is Not

- Not a chat interface. The command input is a command palette — single line, monospace, no bubbles.
- Not a dashboard with a fixed grid. Every panel is free-floating and independently collapsible.
- Not a corporate tool. No light backgrounds. No Inter. No border-radius above 2px on panels.
- Not a game UI. The aesthetic is operational, not decorative. Every visual element earns its presence.
