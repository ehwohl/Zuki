import { useMusicStore } from '../../store/music.store'
import { Panel } from '../../panels/Panel'

export default function TunerPanel() {
  const note = useMusicStore((s) => s.currentNote)
  const cents = useMusicStore((s) => s.currentCents)
  const mode = useMusicStore((s) => s.mode)
  const setMode = useMusicStore((s) => s.setMode)
  const isListening = useMusicStore((s) => s.isListening)

  const inTune = Math.abs(cents) <= 10

  let color: string
  if (!note) {
    color = 'var(--text-secondary)'
  } else if (inTune) {
    color = 'rgba(0,255,255,0.9)'
  } else if (Math.abs(cents) <= 25) {
    color = 'rgba(255,176,0,0.9)'
  } else {
    color = 'rgba(255,0,128,0.9)'
  }

  const centsOffset = Math.max(-50, Math.min(50, cents)) / 50

  return (
    <Panel id="tuner" title="Tuner">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setMode('voice')}
            style={{
              flex: 1,
              padding: '0.25rem',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.7rem',
              border: `1px solid ${mode === 'voice' ? 'var(--accent-primary)' : 'var(--border-color)'}`,
              background: mode === 'voice' ? 'rgba(0,255,255,0.08)' : 'transparent',
              color: mode === 'voice' ? 'var(--accent-primary)' : 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            Voice
          </button>
          <button
            onClick={() => setMode('instrument')}
            style={{
              flex: 1,
              padding: '0.25rem',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.7rem',
              border: `1px solid ${mode === 'instrument' ? 'var(--accent-primary)' : 'var(--border-color)'}`,
              background: mode === 'instrument' ? 'rgba(0,255,255,0.08)' : 'transparent',
              color: mode === 'instrument' ? 'var(--accent-primary)' : 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            Instrument
          </button>
        </div>

        <div
          style={{
            fontSize: '3rem',
            fontFamily: 'JetBrains Mono, monospace',
            color,
            textAlign: 'center',
            lineHeight: 1,
            ...(inTune && note ? { textShadow: '0 0 12px rgba(0,255,255,0.6)' } : {}),
          }}
        >
          {note || '—'}
        </div>

        <div
          style={{
            textAlign: 'center',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.75rem',
            color,
          }}
        >
          {note ? (cents >= 0 ? '+' : '') + cents + ' ¢' : ''}
        </div>

        <div style={{ position: 'relative', height: 6, background: 'var(--border-color)', borderRadius: 3 }}>
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: `calc(50% + ${centsOffset * 50}%)`,
              transform: 'translate(-50%, -50%)',
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: color,
            }}
          />
        </div>

        {inTune && note && (
          <div
            style={{
              textAlign: 'center',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.65rem',
              letterSpacing: '0.15em',
              color: 'rgba(0,255,255,0.9)',
            }}
          >
            IN TUNE
          </div>
        )}

        {/* Mic status indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center', marginTop: 'auto', paddingTop: '0.5rem' }}>
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: isListening ? 'rgba(0,255,255,0.9)' : 'rgba(96,112,128,0.5)',
              boxShadow: isListening ? '0 0 6px rgba(0,255,255,0.6)' : 'none',
              flexShrink: 0,
            }}
          />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.6rem', color: 'var(--text-secondary)', letterSpacing: '0.1em' }}>
            {isListening ? 'MIC ACTIVE' : 'NO MIC'}
          </span>
        </div>
      </div>
    </Panel>
  )
}
