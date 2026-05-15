import { useEffect } from 'react'
import { Panel } from '../../panels/Panel'
import { bridge } from '../../bridge/ws'

export default function CodingWorkspace() {
  useEffect(() => {
    bridge.send('navigate', { workspace: 'coding' })
  }, [])

  return (
    <>
      <Panel id="dep-graph" title="Circuit Board — Dependency Graph" noPad>
        <div className="w-full h-full flex items-center justify-center opacity-40">
          <span className="font-mono text-[0.65rem] text-[var(--text-secondary)] tracking-widest uppercase">
            Bundle 14 — 3D Dep Graph
          </span>
        </div>
      </Panel>
      <Panel id="code-buffer" title="Code Buffer">
        <div className="font-mono text-xs text-[var(--text-secondary)] opacity-40">
          # No active buffer
        </div>
      </Panel>
    </>
  )
}
