import type { PanelState } from '../store/layout.store'

export type WorkspacePreset = PanelState[]

// Bump this when layout geometry changes — forces a reset of saved positions.
export const LAYOUT_VERSION = 2

function preset(W: number, H: number): Record<string, WorkspacePreset> {
  // Terminal — anchored to bottom centre, always visible above the fold
  const TERM_H = 280
  const TERM_W = 640
  const TERM_Y = H - TERM_H - 8    // 8 px gap from screen bottom
  const SAFE   = TERM_Y - 8        // workspace panels must end at or above this line

  const AVATAR:   PanelState = { id: 'avatar',     x: 16,      y: H - 356, w: 280,    h: 320,    collapsed: false, zIndex: 10 }
  const NEURAL:   PanelState = { id: 'neural-map', x: W - 360, y: 16,      w: 340,    h: 400,    collapsed: false, zIndex: 10 }
  const TERMINAL: PanelState = { id: 'terminal',   x: Math.round((W - TERM_W) / 2), y: TERM_Y, w: TERM_W, h: TERM_H, collapsed: false, zIndex: 7 }

  // Shared geometry
  const CX = 312          // centre-column left edge (right of avatar + gap)
  const CW = W - 688      // centre-column width (leaves 16 px gap to right column)
  const RX = W - 360      // right-column left edge
  const RW = 340          // right-column width
  const NY = 432          // first y below neural-map (16 + 400 + 16)
  const RH = SAFE - NY    // right-column available height

  // Business right-column sub-heights
  const BIZ_SCORE_H = Math.min(180, Math.max(80, Math.floor(RH * 0.4)))
  const BIZ_REST    = Math.max(0, RH - BIZ_SCORE_H - 8)
  const BIZ_INTV_H  = Math.floor(BIZ_REST * 0.55)
  const BIZ_RPT_H   = Math.max(0, BIZ_REST - BIZ_INTV_H - 8)

  // Coding vertical split
  const CODE_AVAIL  = SAFE - 16
  const MONACO_H    = Math.floor(CODE_AVAIL * 0.62) - 8
  const OUTPUT_Y    = 16 + MONACO_H + 16
  const OUTPUT_H    = SAFE - OUTPUT_Y

  return {
    broker: [
      AVATAR, NEURAL, TERMINAL,
      { id: 'world-map', x: CX, y: 16,         w: CW, h: SAFE - 16 - 8 - 156, collapsed: false, zIndex: 5 },
      { id: 'watchlist', x: CX, y: SAFE - 156,  w: CW, h: 156,                 collapsed: false, zIndex: 6 },
      { id: 'news-feed', x: RX, y: NY,           w: RW, h: RH,                  collapsed: false, zIndex: 6 },
    ],

    business: [
      AVATAR, NEURAL, TERMINAL,
      { id: 'city-scene',         x: CX, y: 16,                           w: CW, h: SAFE - 16,     collapsed: false, zIndex: 5 },
      { id: 'business-score',     x: RX, y: NY,                           w: RW, h: BIZ_SCORE_H,   collapsed: false, zIndex: 6 },
      { id: 'business-interview', x: RX, y: NY + BIZ_SCORE_H + 8,        w: RW, h: BIZ_INTV_H,    collapsed: false, zIndex: 6 },
      { id: 'business-reports',   x: RX, y: NY + BIZ_SCORE_H + 8 + BIZ_INTV_H + 8, w: RW, h: BIZ_RPT_H, collapsed: false, zIndex: 6 },
    ],

    coding: [
      AVATAR, NEURAL, TERMINAL,
      { id: 'monaco-editor', x: CX, y: 16,       w: CW, h: MONACO_H, collapsed: false, zIndex: 5 },
      { id: 'code-output',   x: CX, y: OUTPUT_Y,  w: CW, h: OUTPUT_H, collapsed: false, zIndex: 6 },
      { id: 'dep-graph',     x: RX, y: NY,        w: RW, h: RH,       collapsed: false, zIndex: 6 },
    ],

    office: [
      AVATAR, NEURAL, TERMINAL,
      { id: 'office-index',  x: CX,                              y: 16, w: Math.floor(CW * 0.55),      h: SAFE - 16, collapsed: false, zIndex: 5 },
      { id: 'office-search', x: CX + Math.floor(CW * 0.55) + 8, y: 16, w: Math.floor(CW * 0.45) - 8,  h: Math.floor((SAFE - 16) * 0.65), collapsed: false, zIndex: 6 },
      { id: 'office-drive',  x: CX + Math.floor(CW * 0.55) + 8, y: 16 + Math.floor((SAFE - 16) * 0.65) + 8, w: Math.floor(CW * 0.45) - 8, h: Math.floor((SAFE - 16) * 0.35) - 8, collapsed: false, zIndex: 6 },
    ],

    os: [
      AVATAR, NEURAL, TERMINAL,
      { id: 'terrain',      x: CX, y: 16,          w: CW, h: SAFE - 16 - 8 - 184, collapsed: false, zIndex: 5 },
      { id: 'process-list', x: CX, y: SAFE - 184,  w: CW, h: 184,                 collapsed: false, zIndex: 6 },
    ],
  }
}

export function getPreset(workspaceId: string): WorkspacePreset {
  const map = preset(window.innerWidth, window.innerHeight)
  return map[workspaceId] ?? map.broker
}
