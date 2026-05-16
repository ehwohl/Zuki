import { useRef, useEffect } from 'react'
import { useTerminalStore } from '../../store/terminal.store'

export function useTerminalScroll() {
  const scrollRef = useRef<HTMLDivElement>(null)
  const isLocked = useRef(false)
  const messages = useTerminalStore((s) => s.messages)

  const onScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    isLocked.current = distFromBottom > 40
  }

  useEffect(() => {
    const el = scrollRef.current
    if (!el || isLocked.current) return
    el.scrollTop = el.scrollHeight
  }, [messages])

  return { scrollRef, onScroll }
}
