import { create } from 'zustand'
import type { ThemeId } from '../themes'

interface UIStore {
  commandInputOpen: boolean
  presentationMode: boolean
  theme: ThemeId
  openCommandInput: () => void
  closeCommandInput: () => void
  togglePresentationMode: () => void
  setTheme: (id: ThemeId) => void
}

export const useUIStore = create<UIStore>((set) => ({
  commandInputOpen: false,
  presentationMode: false,
  theme: 'cyberpunk',
  openCommandInput: () => set({ commandInputOpen: true }),
  closeCommandInput: () => set({ commandInputOpen: false }),
  togglePresentationMode: () => set((s) => ({ presentationMode: !s.presentationMode })),
  setTheme: (theme) => set({ theme }),
}))
