---
phase: 11
plan: "02"
subsystem: ui-wiring
tags: [typescript, zustand, react, workspace-routing, layout-presets]
dependency_graph:
  requires: []
  provides: [WorkspaceId-music, music-layout-preset, Alt6-shortcut, MusicWorkspace-lazy-import]
  affects: [ui/src/store/workspace.store.ts, ui/src/store/layout.store.ts, ui/src/panels/layout_presets.ts, ui/src/panels/PanelManager.tsx, ui/src/App.tsx]
tech_stack:
  added: []
  patterns: [zustand-store-extension, lazy-import, keyboard-shortcut-handler, layout-preset-geometry]
key_files:
  created: []
  modified:
    - ui/src/store/workspace.store.ts
    - ui/src/store/layout.store.ts
    - ui/src/panels/layout_presets.ts
    - ui/src/panels/PanelManager.tsx
    - ui/src/App.tsx
decisions:
  - music Neural Map mode set to 'provenance' (same as coding — dependency flow is closest semantic match)
  - LAYOUT_VERSION bumped 2→3 to force localStorage reset for all users on next load
  - session-log height uses Math.max(0, RH - 168) to prevent negative height edge case
metrics:
  duration: "~10 minutes"
  completed: "2026-05-16"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 5
  commits: 3
---

# Phase 11 Plan 02: UI Type Wiring — Stores, Presets, Router Summary

## One-liner

Wired the music workspace into the React system: TypeScript union extended, Alt+6 shortcut added, 3-panel layout preset defined, MusicWorkspace lazy-imported.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| T1 | Extend workspace.store.ts and layout.store.ts | a0d1aae | workspace.store.ts, layout.store.ts |
| T2 | Add music preset to layout_presets.ts and bump LAYOUT_VERSION | 2d561cf | layout_presets.ts |
| T3 | Register MusicWorkspace in PanelManager.tsx and add Alt+6 in App.tsx | 240f200 | PanelManager.tsx, App.tsx |

## What Was Done

**T1 — Store extensions:**
- `WorkspaceId` union extended: `'broker' | 'business' | 'coding' | 'os' | 'office' | 'music'`
- `NEURAL_MAP_MODES` record extended with `music: 'provenance'`
- `ALL_WORKSPACES` array extended with `'music'` for localStorage cleanup coverage

**T2 — Layout preset:**
- `LAYOUT_VERSION` bumped from 2 to 3 — forces all users to get fresh panel positions on next load
- Music preset added with 6 panels total: AVATAR, NEURAL, TERMINAL (shared) + pitch-roll, tuner, session-log (workspace-specific)
- Geometry: pitch-roll fills the entire centre column (maximum vertical space for visualization); tuner sits at top of right column at fixed 160px; session-log fills remaining right-column height

**T3 — Routing wiring:**
- `PanelManager.tsx` — lazy import added: `const MusicWorkspace = lazy(() => import('../workspaces/music'))`
- `PanelManager.tsx` — `WORKSPACE_PANELS` record extended with `music: MusicWorkspace`
- `App.tsx` — Alt+6 shortcut added: `if (e.altKey && e.key === '6') navigate('music')` — consistent with Alt+1–5 pattern, no `preventDefault()` (matches existing shortcuts)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

- `MusicWorkspace` lazy import points to `../workspaces/music` which does not exist yet — this is intentional. The import is a runtime-only reference (Vite/React lazy); it does not cause build failure. Plan 04 will create the component.

## Self-Check: PASSED

Files created/modified:
- FOUND: ui/src/store/workspace.store.ts (WorkspaceId | 'music', NEURAL_MAP_MODES music entry)
- FOUND: ui/src/store/layout.store.ts (ALL_WORKSPACES 'music')
- FOUND: ui/src/panels/layout_presets.ts (LAYOUT_VERSION 3, music preset with pitch-roll/tuner/session-log)
- FOUND: ui/src/panels/PanelManager.tsx (MusicWorkspace lazy import, WORKSPACE_PANELS music entry)
- FOUND: ui/src/App.tsx (Alt+6 navigate('music'))

Commits verified:
- FOUND: a0d1aae — feat(11-02): extend WorkspaceId union and ALL_WORKSPACES with 'music'
- FOUND: 2d561cf — feat(11-02): add music preset to layout_presets.ts, bump LAYOUT_VERSION to 3
- FOUND: 240f200 — feat(11-02): register MusicWorkspace in PanelManager and add Alt+6 shortcut
