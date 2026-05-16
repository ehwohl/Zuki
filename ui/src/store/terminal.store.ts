import { create } from 'zustand'

export interface Message {
  id: string
  ts: number
  role: 'operator' | 'zuki'
  text: string
  workspace: string
}

interface TerminalStore {
  messages: Message[]
  history: string[]
  historyIndex: number
  addMessage: (role: Message['role'], text: string, workspace: string) => void
  addToHistory: (cmd: string) => void
  navigateHistory: (dir: 'up' | 'down') => string | null
  clear: () => void
}

export const useTerminalStore = create<TerminalStore>((set, get) => ({
  messages: [],
  history: [],
  historyIndex: -1,

  addMessage: (role, text, workspace) =>
    set((s) => ({
      messages: [
        ...s.messages,
        { id: crypto.randomUUID(), ts: Date.now(), role, text, workspace },
      ],
    })),

  addToHistory: (cmd) =>
    set((s) => ({
      history: [cmd, ...s.history.filter((h) => h !== cmd)].slice(0, 100),
      historyIndex: -1,
    })),

  navigateHistory: (dir) => {
    const { history, historyIndex } = get()
    if (history.length === 0) return null
    const next =
      dir === 'up'
        ? Math.min(historyIndex + 1, history.length - 1)
        : Math.max(historyIndex - 1, -1)
    set({ historyIndex: next })
    return next === -1 ? '' : history[next]
  },

  clear: () => set({ messages: [], history: [], historyIndex: -1 }),
}))
