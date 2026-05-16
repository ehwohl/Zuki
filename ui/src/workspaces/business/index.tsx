import { useEffect, useState } from 'react'
import { Panel } from '../../panels/Panel'
import { bridge } from '../../bridge/ws'
import { useWSStore } from '../../store/ws.store'
import CityScene, { type Building } from './CityScene'

// ── Score gauge ────────────────────────────────────────────────────────────────

function ScoreGauge({ score }: { score: number }) {
  // Arc from 220° to -40° (total 280° sweep), filled by score/100
  const R = 54
  const CX = 70
  const CY = 72
  const START_DEG = 220
  const SWEEP_DEG = 280

  function polarToXY(cx: number, cy: number, r: number, deg: number) {
    const rad = ((deg - 90) * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }

  function arc(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
    const start = polarToXY(cx, cy, r, startDeg)
    const end   = polarToXY(cx, cy, r, endDeg)
    const large = endDeg - startDeg > 180 ? 1 : 0
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`
  }

  const trackEnd = START_DEG + SWEEP_DEG  // 500° → normalised
  const fillEnd  = START_DEG + (score / 100) * SWEEP_DEG

  const color =
    score >= 70 ? 'var(--color-up)' :
    score >= 40 ? 'var(--accent-warning)' :
    'var(--color-down)'

  const trackPath = arc(CX, CY, R, START_DEG, trackEnd)
  const fillPath  = arc(CX, CY, R, START_DEG, fillEnd)

  return (
    <svg viewBox="0 0 140 96" className="w-full" style={{ maxWidth: 160 }}>
      {/* track */}
      <path
        d={trackPath}
        fill="none"
        stroke="var(--border-color)"
        strokeWidth="8"
        strokeLinecap="round"
      />
      {/* fill */}
      {score > 0 && (
        <path
          d={fillPath}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 4px ${color})` }}
        />
      )}
      {/* score text */}
      <text
        x={CX}
        y={CY + 6}
        textAnchor="middle"
        dominantBaseline="middle"
        fill={color}
        style={{ fontFamily: '"Chakra Petch", sans-serif', fontSize: 22, fontWeight: 600 }}
      >
        {score}
      </text>
      <text
        x={CX}
        y={CY + 22}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="var(--text-secondary)"
        style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 7 }}
      >
        / 100
      </text>
    </svg>
  )
}

// ── Report history ─────────────────────────────────────────────────────────────

interface ReportEntry {
  name: string
  path: string
  ts: string
  client?: string
  score?: number
}

function ReportsPanel({ reports }: { reports: ReportEntry[] }) {
  if (reports.length === 0) {
    return (
      <div className="font-mono text-[0.65rem] text-[var(--text-secondary)] opacity-40">
        Kein Report — Analyse starten: business analyse &lt;Name&gt;
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto flex flex-col gap-1">
      {reports.map((r, i) => (
        <div
          key={i}
          className="flex items-center gap-2 py-1.5 border-b border-[var(--border-color)] last:border-0"
        >
          {r.score !== undefined && (
            <span
              className="font-display text-sm shrink-0 w-7 text-right"
              style={{
                color:
                  r.score >= 70 ? 'var(--color-up)' :
                  r.score >= 40 ? 'var(--accent-warning)' :
                  'var(--color-down)',
              }}
            >
              {r.score}
            </span>
          )}
          <div className="min-w-0 flex-1">
            <div className="font-mono text-[0.65rem] text-[var(--text-primary)] truncate">
              {r.client || r.name}
            </div>
            <div className="font-mono text-[0.55rem] text-[var(--text-secondary)] opacity-60">{r.ts}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Workspace root ─────────────────────────────────────────────────────────────

export default function BusinessWorkspace() {
  const [buildings, setBuildings]   = useState<Building[]>([])
  const [prompt, setPrompt]         = useState<string>('')
  const [score, setScore]           = useState<number | null>(null)
  const [reportPath, setReportPath] = useState<string>('')
  const [reports, setReports]       = useState<ReportEntry[]>([])
  const lastMessage = useWSStore((s) => s.lastMessage)

  useEffect(() => {
    bridge.send('navigate', { workspace: 'business' })
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'business_interview_prompt') {
      setPrompt((lastMessage.text as string) ?? '')
    }
    if (lastMessage?.type === 'business_score') {
      const s = (lastMessage.score as number) ?? null
      const path = (lastMessage.report_path as string) ?? ''
      setScore(s)
      setReportPath(path)
    }
    if (lastMessage?.type === 'business_city_data') {
      setBuildings((lastMessage.buildings as Building[]) ?? [])
    }
    if (lastMessage?.type === 'business_reports') {
      setReports((lastMessage.reports as ReportEntry[]) ?? [])
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
          <div className="flex flex-col gap-3">
            <ScoreGauge score={score} />
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

      <Panel id="business-reports" title="Report History">
        <ReportsPanel reports={reports} />
      </Panel>
    </>
  )
}
