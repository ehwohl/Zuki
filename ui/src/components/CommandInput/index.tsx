import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useUIStore } from '../../store/ui.store'
import { useWSStore } from '../../store/ws.store'
import { useWorkspaceStore } from '../../store/workspace.store'
import { bridge } from '../../bridge/ws'

export default function CommandInput() {
  const open = useUIStore((s) => s.commandInputOpen)
  const close = useUIStore((s) => s.closeCommandInput)
  const lastResponse = useWSStore((s) => s.lastResponse)
  const wsStatus = useWSStore((s) => s.status)
  const active = useWorkspaceStore((s) => s.active)

  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50)
    } else {
      setInput('')
    }
  }, [open])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) close()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, close])

  const submit = () => {
    const text = input.trim()
    if (!text) return
    bridge.sendCommand(text, active)
    setInput('')
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') submit()
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-[1000]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={close}
          />

          {/* Input panel */}
          <motion.div
            className="fixed left-1/2 z-[1001] no-drag"
            style={{ bottom: '12%', width: 640, x: '-50%' }}
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 24, opacity: 0 }}
            transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="panel-glass overflow-hidden" style={{ boxShadow: '0 0 32px rgba(0,245,255,0.15), var(--glow-primary)' }}>
              {/* Input row */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--border-color)]">
                <span className="font-mono text-[var(--accent-primary)] text-sm select-none shrink-0">›</span>
                <input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={onKeyDown}
                  className="flex-1 bg-transparent outline-none font-mono text-sm text-[var(--text-primary)] placeholder-[var(--text-secondary)]"
                  placeholder="Command…"
                  spellCheck={false}
                  autoComplete="off"
                />
                <div className="flex items-center gap-1.5 shrink-0">
                  <div
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ background: wsStatus === 'open' ? 'var(--color-up)' : 'var(--color-down)' }}
                  />
                  <span className="font-mono text-[0.55rem] text-[var(--text-secondary)] uppercase tracking-widest">
                    {wsStatus}
                  </span>
                </div>
              </div>

              {/* Last response */}
              {lastResponse && (
                <div className="px-4 py-2.5 max-h-24 overflow-y-auto">
                  <p className="font-mono text-xs text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
                    {lastResponse}
                  </p>
                </div>
              )}
            </div>

            {/* Hint */}
            <div className="flex justify-between px-1 mt-1.5 opacity-40">
              <span className="font-mono text-[0.55rem] text-[var(--text-secondary)]">Enter → send</span>
              <span className="font-mono text-[0.55rem] text-[var(--text-secondary)]">Esc → close</span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
