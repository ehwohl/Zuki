import { create } from 'zustand'

export interface NeuralTask {
  id: string
  nodes: string[]   // node IDs involved — any link connecting two of these becomes "hot"
  expiresAt: number // ms timestamp — auto-expires even if clear is never called
}

interface NeuralStore {
  tasks: NeuralTask[]
  addTask: (id: string, nodes: string[], ttl: number) => void
  clearTask: (id: string) => void
  clearAll: () => void
}

export const useNeuralStore = create<NeuralStore>((set) => ({
  tasks: [],
  addTask: (id, nodes, ttl) =>
    set((s) => ({
      tasks: [
        ...s.tasks.filter((t) => t.id !== id),
        { id, nodes, expiresAt: Date.now() + ttl * 1_000 },
      ],
    })),
  clearTask: (id) =>
    set((s) => ({ tasks: s.tasks.filter((t) => t.id !== id) })),
  clearAll: () => set({ tasks: [] }),
}))
