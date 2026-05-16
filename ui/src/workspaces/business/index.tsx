import { useEffect, useState } from 'react'
import { Panel } from '../../panels/Panel'
import { bridge } from '../../bridge/ws'
import { useWSStore } from '../../store/ws.store'
import CityScene, { type Building } from './CityScene'

export default function BusinessWorkspace() {
  const [buildings, setBuildings] = useState<Building[]>([])
  const [prompt, setPrompt]       = useState<string>('')
  const [score, setScore]         = useState<number | null>(null)
  const [reportPath, setReportPath] = useState<string>('')
  const lastMessage = useWSStore((s) => s.lastMessage)

  useEffect(() => {
    bridge.send('navigate', { workspace: 'business' })
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'business_interview_prompt') {
      setPrompt((lastMessage.text as string) ?? '')
    }
    if (lastMessage?.type === 'business_score') {
      setScore((lastMessage.score as number) ?? null)
      setReportPath((lastMessage.report_path as string) ?? '')
    }
    if (lastMessage?.type === 'business_city_data') {
      setBuildings((lastMessage.buildings as Building[]) ?? [])
    }
  }, [lastMessage])

  return (
    <>
      <Panel id="city-scene" title="Field Intelligence — City Model" noPad>
        <CityScene buildings={buildings} />
      </Panel>

      <Panel id="business-interview" title="Interview">
        {prompt ? (
          <div className="font-mono text-xs text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">
            {prompt}
          </div>
        ) : (
          <div className="font-mono text-[0.65rem] text-[var(--text-secondary)] opacity-40">
            Wartet auf Fragebogen… (business interview &lt;Name&gt;)
          </div>
        )}
      </Panel>

      <Panel id="business-score" title="Score">
        {score !== null ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-baseline gap-2">
              <span
                className="font-display text-4xl"
                style={{
                  color: score >= 70
                    ? 'var(--color-up)'
                    : score >= 40
                    ? 'var(--accent-warning)'
                    : 'var(--color-down)',
                }}
              >
                {score}
              </span>
              <span className="font-mono text-[0.65rem] text-[var(--text-secondary)]">/ 100</span>
            </div>
            {reportPath && (
              <div
                className="font-mono text-[0.6rem] text-[var(--text-secondary)] truncate"
                title={reportPath}
              >
                {reportPath}
              </div>
            )}
          </div>
        ) : (
          <div className="font-mono text-[0.65rem] text-[var(--text-secondary)] opacity-40">
            Kein Score — Analyse starten: business analyse &lt;Name&gt;
          </div>
        )}
      </Panel>
    </>
  )
}
