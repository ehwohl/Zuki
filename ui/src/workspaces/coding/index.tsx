import { useEffect, useState } from 'react'
import { Panel } from '../../panels/Panel'
import { bridge } from '../../bridge/ws'
import { useWSStore } from '../../store/ws.store'
import DepGraph, { type DepNode, type DepEdge } from './DepGraph'

interface CodeOutput {
  text: string
  language: string
  ts: string
}

export default function CodingWorkspace() {
  const [outputs, setOutputs]   = useState<CodeOutput[]>([])
  const [depNodes, setDepNodes] = useState<DepNode[]>([])
  const [depEdges, setDepEdges] = useState<DepEdge[]>([])
  const lastMessage = useWSStore((s) => s.lastMessage)

  useEffect(() => {
    bridge.send('navigate', { workspace: 'coding' })
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'coding_output') {
      const entry: CodeOutput = {
        text:     (lastMessage.text as string) ?? '',
        language: (lastMessage.language as string) ?? '',
        ts:       new Date().toLocaleTimeString('de-DE', {
          hour: '2-digit', minute: '2-digit', second: '2-digit',
        }),
      }
      setOutputs((prev) => [entry, ...prev.slice(0, 19)])
    }
    if (lastMessage?.type === 'coding_dep_graph') {
      setDepNodes((lastMessage.nodes as DepNode[]) ?? [])
      setDepEdges((lastMessage.edges as DepEdge[]) ?? [])
    }
  }, [lastMessage])

  return (
    <>
      <Panel id="dep-graph" title="Circuit Board — Dependency Graph" noPad>
        <DepGraph nodes={depNodes} edges={depEdges} />
      </Panel>

      <Panel id="code-buffer" title="Code Buffer">
        {outputs.length > 0 ? (
          <div className="h-full overflow-y-auto space-y-3">
            {outputs.map((o, i) => (
              <div key={i} className="border-b border-[var(--border-color)] pb-3 last:border-0">
                <div className="flex items-center gap-2 mb-1">
                  {o.language && (
                    <span className="font-mono text-[0.6rem] tracking-widest uppercase text-[var(--accent-secondary)]">
                      {o.language}
                    </span>
                  )}
                  <span className="font-mono text-[0.6rem] text-[var(--text-secondary)]">{o.ts}</span>
                </div>
                <pre className="font-mono text-xs text-[var(--text-primary)] whitespace-pre-wrap leading-relaxed">
                  {o.text}
                </pre>
              </div>
            ))}
          </div>
        ) : (
          <div className="font-mono text-xs text-[var(--text-secondary)] opacity-40">
            # No active buffer — run: code python run
          </div>
        )}
      </Panel>
    </>
  )
}
