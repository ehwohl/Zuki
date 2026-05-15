import { useEffect } from 'react'
import { Panel } from '../../panels/Panel'
import { bridge } from '../../bridge/ws'

export default function OSWorkspace() {
  useEffect(() => {
    bridge.send('navigate', { workspace: 'os' })
  }, [])

  return (
    <>
      <Panel id="terrain" title="System Core — Terrain Monitor" noPad>
        <div className="w-full h-full flex items-center justify-center opacity-40">
          <span className="font-mono text-[0.65rem] text-[var(--text-secondary)] tracking-widest uppercase">
            Bundle 15 — 3D Terrain (CPU/RAM mesh)
          </span>
        </div>
      </Panel>
      <Panel id="process-list" title="Processes">
        <div className="terminal opacity-40 text-[0.65rem]">
          Waiting for metrics stream…
        </div>
      </Panel>
    </>
  )
}
