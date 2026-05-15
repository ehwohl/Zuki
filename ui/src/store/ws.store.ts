import { create } from 'zustand'

export type WSStatus = 'connecting' | 'open' | 'closed' | 'error'

export interface ZukiMessage {
  type: string
  [key: string]: unknown
}

interface WSStore {
  status: WSStatus
  lastMessage: ZukiMessage | null
  lastResponse: string
  setStatus: (s: WSStatus) => void
  setMessage: (m: ZukiMessage) => void
}

export const useWSStore = create<WSStore>((set) => ({
  status: 'closed',
  lastMessage: null,
  lastResponse: '',
  setStatus: (status) => set({ status }),
  setMessage: (msg) => {
    set({ lastMessage: msg })
    if (msg.type === 'response') set({ lastResponse: (msg.text as string) ?? '' })
  },
}))
