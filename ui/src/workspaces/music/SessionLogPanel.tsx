import { Panel } from '../../panels/Panel'

export interface SessionStats {
  note_count: number
  avg_cents_deviation: number
  time_active_seconds: number
  last_note: string
  session_started: string
}

interface SessionLogPanelProps {
  stats: SessionStats | null
}

export default function SessionLogPanel({ stats }: SessionLogPanelProps) {
  return (
    <Panel id="session-log" title="Session Log">
      {stats === null ? (
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
          }}
        >
          Warte auf Noten...
        </div>
      ) : (
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.75rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.4rem',
          }}
        >
          <div>Noten: {stats.note_count}</div>
          <div>Ø Abweichung: {stats.avg_cents_deviation} ¢</div>
          <div>
            Zeit: {Math.floor(stats.time_active_seconds / 60)}:
            {String(stats.time_active_seconds % 60).padStart(2, '0')}
          </div>
          <div>Letzter Ton: {stats.last_note || '—'}</div>
          <div style={{ color: 'var(--text-secondary)' }}>
            Session:{' '}
            {stats.session_started
              ? new Date(stats.session_started).toLocaleTimeString('de-DE')
              : '—'}
          </div>
        </div>
      )}
    </Panel>
  )
}
