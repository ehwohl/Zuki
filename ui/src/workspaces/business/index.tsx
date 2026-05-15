import { useEffect } from 'react'
import { Panel } from '../../panels/Panel'
import { bridge } from '../../bridge/ws'

export default function BusinessWorkspace() {
  useEffect(() => {
    bridge.send('navigate', { workspace: 'business' })
  }, [])

  return (
    <Panel id="city-scene" title="Field Intelligence — City Model" noPad>
      <div className="w-full h-full flex flex-col items-center justify-center gap-3 opacity-40">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <rect x="4" y="20" width="8" height="24" stroke="#00F5FF" strokeWidth="1" />
          <rect x="16" y="12" width="8" height="32" stroke="#00F5FF" strokeWidth="1" />
          <rect x="28" y="8" width="12" height="36" stroke="#00F5FF" strokeWidth="1" />
          <rect x="6" y="28" width="2" height="4" fill="#FF00A0" opacity="0.6" />
          <rect x="18" y="18" width="2" height="4" fill="#FF00A0" opacity="0.6" />
          <rect x="30" y="14" width="2" height="4" fill="#FFB300" opacity="0.6" />
        </svg>
        <span className="font-mono text-[0.65rem] text-[var(--text-secondary)] tracking-widest uppercase">
          Bundle 14 — 3D City Model
        </span>
      </div>
    </Panel>
  )
}
