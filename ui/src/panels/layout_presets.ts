import type { PanelState } from '../store/layout.store'

export type WorkspacePreset = PanelState[]

function preset(W: number, H: number): Record<string, WorkspacePreset> {
  const AVATAR: PanelState = { id: 'avatar', x: 16, y: H - 356, w: 280, h: 320, collapsed: false, zIndex: 10 }
  const NEURAL: PanelState = { id: 'neural-map', x: W - 360, y: 16, w: 340, h: 400, collapsed: false, zIndex: 10 }
  const TERMINAL: PanelState = {
    id: 'terminal',
    x: Math.round((W - 640) / 2),
    y: Math.round(H * 0.88 - 280),
    w: 640,
    h: 280,
    collapsed: false,
    zIndex: 7,
  }

  return {
    broker: [
      AVATAR,
      NEURAL,
      TERMINAL,
      { id: 'world-map', x: 312, y: 16, w: W - 688, h: H - 200, collapsed: false, zIndex: 5 },
      { id: 'news-feed', x: W - 360, y: 432, w: 340, h: H - 464, collapsed: false, zIndex: 6 },
      { id: 'watchlist', x: 312, y: H - 172, w: W - 688, h: 156, collapsed: false, zIndex: 6 },
    ],
    business: [
      AVATAR,
      NEURAL,
      TERMINAL,
      { id: 'city-scene', x: 312, y: 16, w: W - 688, h: H - 32, collapsed: false, zIndex: 5 },
      { id: 'business-interview', x: W - 360, y: 432, w: 340, h: Math.floor((H - 472) * 0.6), collapsed: false, zIndex: 6 },
      { id: 'business-score', x: W - 360, y: 432 + Math.floor((H - 472) * 0.6) + 8, w: 340, h: Math.floor((H - 472) * 0.4) - 8, collapsed: false, zIndex: 6 },
    ],
    coding: [
      AVATAR,
      NEURAL,
      TERMINAL,
      { id: 'dep-graph', x: 312, y: 16, w: W - 688, h: Math.floor(H / 2) - 8, collapsed: false, zIndex: 5 },
      { id: 'code-buffer', x: 312, y: Math.floor(H / 2) + 8, w: W - 688, h: Math.floor(H / 2) - 32, collapsed: false, zIndex: 6 },
    ],
    os: [
      AVATAR,
      NEURAL,
      TERMINAL,
      { id: 'terrain', x: 312, y: 16, w: W - 688, h: H - 224, collapsed: false, zIndex: 5 },
      { id: 'process-list', x: 312, y: H - 200, w: W - 688, h: 184, collapsed: false, zIndex: 6 },
    ],
  }
}

export function getPreset(workspaceId: string): WorkspacePreset {
  const map = preset(window.innerWidth, window.innerHeight)
  return map[workspaceId] ?? map.broker
}
