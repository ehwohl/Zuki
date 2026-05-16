import { useEffect, useState } from 'react'
import { Panel } from '../../panels/Panel'
import { bridge } from '../../bridge/ws'
import { useWSStore } from '../../store/ws.store'

interface TtsStatus {
  voice?: string
  ready?: boolean
  [k: string]: unknown
}

interface SttStatus {
  mode?: string
  ready?: boolean
}

interface OsStatus {
  tts: TtsStatus
  stt: SttStatus
  platform: string
}

function StatusRow({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center gap-3 py-1 border-b border-[var(--border-color)] last:border-0">
      <span className="font-mono text-[0.6rem] tracking-widest uppercase text-[var(--text-secondary)] w-20 shrink-0">
        {label}
      </span>
      <span className="font-mono text-xs text-[var(--text-primary)] flex-1 truncate">{value}</span>
      {ok !== undefined && (
        <span
          className="font-mono text-[0.55rem] tracking-widest"
          style={{ color: ok ? 'var(--color-up)' : 'var(--color-down)' }}
        >
          {ok ? 'READY' : 'OFFLINE'}
        </span>
      )}
    </div>
  )
}

export default function OSWorkspace() {
  const [status, setStatus] = useState<OsStatus | null>(null)
  const lastMessage = useWSStore((s) => s.lastMessage)

  useEffect(() => {
    bridge.send('navigate', { workspace: 'os' })
    // Request status on mount
    bridge.send('command', { text: 'os', workspace: 'os', tenant: 'self' })
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'os_status') {
      setStatus({
        tts:      (lastMessage.tts as TtsStatus) ?? {},
        stt:      (lastMessage.stt as SttStatus) ?? {},
        platform: (lastMessage.platform as string) ?? '—',
      })
    }
  }, [lastMessage])

  return (
    <>
      <Panel id="terrain" title="System Core — Terrain Monitor" noPad>
        <div className="w-full h-full flex items-center justify-center opacity-40">
          <span className="font-mono text-[0.65rem] text-[var(--text-secondary)] tracking-widest uppercase">
            Bundle 15 — 3D Terrain (CPU/RAM mesh)
          </span>
        </div>
      </Panel>

      <Panel id="process-list" title="System Status">
        {status ? (
          <div className="h-full overflow-y-auto">
            <StatusRow label="Platform" value={status.platform} />
            <StatusRow
              label="TTS"
              value={status.tts.voice ?? '—'}
              ok={status.tts.ready}
            />
            <StatusRow
              label="STT"
              value={status.stt.mode ?? '—'}
              ok={status.stt.ready}
            />
            {Object.entries(status.tts)
              .filter(([k]) => k !== 'voice' && k !== 'ready')
              .map(([k, v]) => (
                <StatusRow key={k} label={k} value={String(v)} />
              ))}
          </div>
        ) : (
          <div className="terminal opacity-40 text-[0.65rem]">
            Waiting for status stream… (type: os)
          </div>
        )}
      </Panel>
    </>
  )
}
