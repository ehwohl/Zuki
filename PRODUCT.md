# Zuki-OS — Product Contract

> Authoritative spec for Bundle 13 (Shell) and all subsequent UI bundles.
> Implementation decisions that contradict this document must be resolved here first.

---

## Identity

**Name**: Zuki-OS  
**Concept**: A netrunner's personal operations deck. Atmospherically hostile to anything clean or corporate.  
**Style**: High Tech – Low Life  
**Target user**: Solo operator (Paul). Not a SaaS product. No onboarding flows.

---

## Phase 1 Scope (Bundle 13 — The Shell)

| Deliverable | Status |
|---|---|
| PWA scaffold, frameless, window-controls-overlay | Phase 1 |
| Cyberpunk theme tokens (CSS custom properties) | Phase 1 |
| Glitch workspace transition (CSS-only, 350ms) | Phase 1 |
| Free-floating panel system with localStorage persistence | Phase 1 |
| Floating command input (Ctrl+Space, Framer Motion slide-up) | Phase 1 |
| WebSocket bridge to Python backend (port 8765) | Phase 1 |
| Avatar panel (Three.js + @pixiv/three-vrm, placeholder model) | Phase 1 |
| Neural Map panel (D3 force-directed, mock router data) | Phase 1 |
| Broker workspace — WorldMap + NewsFeed + Watchlist | Phase 1 |
| Business / Coding / OS workspaces — placeholder panels | Phase 1 |

---

## Hard Constraints

### Performance
- Cold load: < 3s
- Workspace switch (including glitch): < 400ms
- 3D frame rate: ≥ 30fps during interaction, ≥ 60fps at idle
- **Total RAM (Python + UI combined): < 300MB** — lazy-load all 3D scenes

### Architecture
- **No Redux, no Context for shared state** — Zustand only
- **Tailwind for layout/spacing only** — all theme tokens via CSS custom properties
- **No OrbitControls from Three.js** — custom camera control implementations
- **Glitch transition: CSS-only** — no JS animation library dependency for this effect
- **Avatar renderer: prop-driven** — `renderer: 'vrm' | 'live2d'` prop. Never assume VRM in layout code
- **Theme swap: CSS var swap only** — zero React re-renders for theme changes

### PWA
- `display_override: window-controls-overlay` — frameless
- Entire root: `WebkitAppRegion: drag`
- Interactive elements: `WebkitAppRegion: no-drag`
- Window controls (close/minimize): appear on hover only

### State Persistence
- Panel layout key: `zuki:layout:{workspaceId}` in localStorage
- Schema: `PanelState[]` — `{ id, x, y, w, h, collapsed, zIndex }`
- Write: debounced 500ms after drag/resize end
- Corrupt state: silently falls back to workspace preset

### WebSocket Contract
- All messages: JSON
- Backend port: 8765 (configurable via `VITE_WS_URL`)
- Reconnect: exponential backoff, max 30s

---

## What Zuki-OS Is Not

- Not a chat interface. The command input is a palette, not a messenger.
- Not a dashboard with fixed layout. Every panel is freely positionable.
- Not a corporate tool. No clean whites, no Inter font, no border-radius > 4px on panels.
