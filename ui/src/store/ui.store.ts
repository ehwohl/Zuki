import { create } from 'zustand'
import type { ThemeId } from '../themes'

interface UIStore {
  terminalFocusSignal: number
  terminalInject: string | null
  sidebarExpanded: boolean
  presentationMode: boolean
  theme: ThemeId
  focusTerminal: () => void
  setTerminalInject: (cmd: string | null) => void
  toggleSidebar: () => void
  togglePresentationMode: () => void
  setTheme: (id: ThemeId) => void
}

export const useUIStore = create<UIStore>((set) => ({
  terminalFocusSignal: 0,
  terminalInject: null,
  sidebarExpanded: false,
  presentationMode: false,
  theme: 'cyberpunk',
  focusTerminal: () => set((s) => ({ terminalFocusSignal: s.terminalFocusSignal + 1 })),
  setTerminalInject: (cmd) => set({ terminalInject: cmd }),
  toggleSidebar: () => set((s) => ({ sidebarExpanded: !s.sidebarExpanded })),
  togglePresentationMode: () => set((s) => ({ presentationMode: !s.presentationMode })),
  setTheme: (theme) => set({ theme }),
}))
