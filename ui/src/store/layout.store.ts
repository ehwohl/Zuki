import { create } from 'zustand'

export interface PanelState {
  id: string
  x: number
  y: number
  w: number
  h: number
  collapsed: boolean
  zIndex: number
}

interface LayoutStore {
  panels: Record<string, PanelState>
  maxZ: number
  updatePanel: (id: string, patch: Partial<PanelState>) => void
  bringToFront: (id: string) => void
  collapsePanel: (id: string) => void
  loadPreset: (preset: PanelState[]) => void
  loadFromStorage: (workspaceId: string, preset: PanelState[]) => void
  persistToStorage: (workspaceId: string) => void
}

const storageKey = (id: string) => `zuki:layout:${id}`

export const useLayoutStore = create<LayoutStore>((set, get) => ({
  panels: {},
  maxZ: 10,

  updatePanel: (id, patch) =>
    set((s) => ({ panels: { ...s.panels, [id]: { ...s.panels[id], ...patch } } })),

  bringToFront: (id) =>
    set((s) => {
      const z = s.maxZ + 1
      return { maxZ: z, panels: { ...s.panels, [id]: { ...s.panels[id], zIndex: z } } }
    }),

  collapsePanel: (id) =>
    set((s) => ({
      panels: { ...s.panels, [id]: { ...s.panels[id], collapsed: !s.panels[id].collapsed } },
    })),

  loadPreset: (preset) =>
    set({ panels: Object.fromEntries(preset.map((p) => [p.id, p])) }),

  loadFromStorage: (workspaceId, preset) => {
    try {
      const raw = localStorage.getItem(storageKey(workspaceId))
      if (raw) {
        const parsed: PanelState[] = JSON.parse(raw)
        if (Array.isArray(parsed) && parsed.length > 0) {
          // Preset is the source of truth for which panels exist.
          // Stored positions override defaults only for panels already in the preset.
          // This ensures panels added to the preset after a workspace was saved
          // (e.g. the Terminal) always appear rather than being silently dropped.
          const storedById = Object.fromEntries(parsed.map((p) => [p.id, p]))
          const merged = preset.map((p) => storedById[p.id] ?? p)
          set({ panels: Object.fromEntries(merged.map((p) => [p.id, p])) })
          return
        }
      }
    } catch {
      // corrupt — fall through
    }
    get().loadPreset(preset)
  },

  persistToStorage: (workspaceId) => {
    const panels = Object.values(get().panels)
    localStorage.setItem(storageKey(workspaceId), JSON.stringify(panels))
  },
}))
