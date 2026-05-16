import { useEffect, useState } from 'react'
import { usePitchDetector } from '../../hooks/usePitchDetector'
import { bridge } from '../../bridge/ws'
import { useWSStore } from '../../store/ws.store'
import PitchRollPanel from './PitchRollPanel'
import TunerPanel from './TunerPanel'
import SessionLogPanel from './SessionLogPanel'
import type { SessionStats } from './SessionLogPanel'

export default function MusicWorkspace() {
  usePitchDetector()

  const lastMessage = useWSStore((s) => s.lastMessage)
  const [stats, setStats] = useState<SessionStats | null>(null)

  useEffect(() => {
    bridge.send('navigate', { workspace: 'music' })
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'music_session_stats') {
      setStats(lastMessage as unknown as SessionStats)
    }
  }, [lastMessage])

  return (
    <>
      <PitchRollPanel />
      <TunerPanel />
      <SessionLogPanel stats={stats} />
    </>
  )
}
