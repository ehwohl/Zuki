import { useWSStore } from '../store/ws.store'
import { useUIStore } from '../store/ui.store'
import { useWorkspaceStore, type WorkspaceId } from '../store/workspace.store'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8765'
const MAX_RECONNECT_MS = 30_000

class ZukiBridge {
  private ws: WebSocket | null = null
  private retryDelay = 1_000
  private retryTimer: ReturnType<typeof setTimeout> | null = null

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return
    useWSStore.getState().setStatus('connecting')
    try {
      this.ws = new WebSocket(WS_URL)
      this.ws.onopen = this.onOpen
      this.ws.onclose = this.onClose
      this.ws.onerror = this.onError
      this.ws.onmessage = this.onMessage
    } catch {
      useWSStore.getState().setStatus('error')
      this.scheduleRetry()
    }
  }

  send(type: string, payload: Record<string, unknown> = {}) {
    if (this.ws?.readyState !== WebSocket.OPEN) return
    this.ws.send(JSON.stringify({ type, ...payload }))
  }

  sendCommand(text: string, workspace: string, tenant = 'self') {
    this.send('command', { text, workspace, tenant })
  }

  private onOpen = () => {
    useWSStore.getState().setStatus('open')
    this.retryDelay = 1_000
  }

  private onClose = () => {
    useWSStore.getState().setStatus('closed')
    this.scheduleRetry()
  }

  private onError = () => {
    useWSStore.getState().setStatus('error')
  }

  private onMessage = (event: MessageEvent<string>) => {
    let msg: { type: string; [k: string]: unknown }
    try {
      msg = JSON.parse(event.data)
    } catch {
      return
    }
    useWSStore.getState().setMessage(msg)
    this.dispatch(msg)
  }

  private dispatch(msg: { type: string; [k: string]: unknown }) {
    switch (msg.type) {
      case 'tts_amplitude':
        document.documentElement.style.setProperty(
          '--pulse-intensity',
          String(Math.max(0, Math.min(1, (msg.value as number) ?? 0))),
        )
        break
      case 'workspace_change':
        useWorkspaceStore.getState().navigate(msg.workspace as WorkspaceId)
        break
      case 'presentation_mode':
        if (msg.active !== useUIStore.getState().presentationMode) {
          useUIStore.getState().togglePresentationMode()
        }
        break
    }
  }

  private scheduleRetry() {
    if (this.retryTimer) return
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null
      this.retryDelay = Math.min(this.retryDelay * 2, MAX_RECONNECT_MS)
      this.connect()
    }, this.retryDelay)
  }
}

export const bridge = new ZukiBridge()
