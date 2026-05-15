import { create } from 'zustand'

export type WorkspaceId = 'broker' | 'business' | 'coding' | 'os'
export type NeuralMapMode = 'routing' | 'provenance' | 'both'
export type AvatarRenderer = 'vrm' | 'live2d'

interface WorkspaceStore {
  active: WorkspaceId
  previous: WorkspaceId | null
  isTransitioning: boolean
  neuralMapMode: NeuralMapMode
  avatarRenderer: AvatarRenderer
  navigate: (to: WorkspaceId) => void
  endTransition: () => void
}

const NEURAL_MAP_MODES: Record<WorkspaceId, NeuralMapMode> = {
  broker: 'provenance',
  business: 'routing',
  coding: 'provenance',
  os: 'routing',
}

export const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  active: 'broker',
  previous: null,
  isTransitioning: false,
  neuralMapMode: 'provenance',
  avatarRenderer: 'vrm',
  navigate: (to) =>
    set((s) => ({
      previous: s.active,
      active: to,
      isTransitioning: s.active !== to,
      neuralMapMode: NEURAL_MAP_MODES[to],
    })),
  endTransition: () => set({ isTransitioning: false }),
}))
