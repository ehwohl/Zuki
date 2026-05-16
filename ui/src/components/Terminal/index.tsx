import { useEffect, useRef, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { useTerminalStore } from '../../store/terminal.store'
import { useUIStore } from '../../store/ui.store'
import { useWorkspaceStore } from '../../store/workspace.store'
import { bridge } from '../../bridge/ws'
import { MessageRow } from './MessageRow'
import { useTerminalScroll } from './useTerminalScroll'

export default function TerminalContent() {
  const messages = useTerminalStore((s) => s.messages)
  const addMessage = useTerminalStore((s) => s.addMessage)
  const addToHistory = useTerminalStore((s) => s.addToHistory)
  const navigateHistory = useTerminalStore((s) => s.navigateHistory)

  const terminalFocusSignal = useUIStore((s) => s.terminalFocusSignal)
  const terminalInject = useUIStore((s) => s.terminalInject)
  const setTerminalInject = useUIStore((s) => s.setTerminalInject)

  const active = useWorkspaceStore((s) => s.active)

  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const activeRef = useRef(active)
  const { scrollRef, onScroll } = useTerminalScroll()

  useEffect(() => { activeRef.current = active }, [active])

  // Focus terminal when signal fires
  useEffect(() => {
    if (terminalFocusSignal > 0) inputRef.current?.focus()
  }, [terminalFocusSignal])

  // Inject command from SkillSidebar
  useEffect(() => {
    if (terminalInject === null) return
    setInput(terminalInject)
    setTerminalInject(null)
    inputRef.current?.focus()
  }, [terminalInject, setTerminalInject])

  const submit = () => {
    const text = input.trim()
    if (!text) return
    addMessage('operator', text, activeRef.current)
    addToHistory(text)
    bridge.sendCommand(text, activeRef.current)
    setInput('')
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') { submit(); return }
    if (e.key === 'Escape') { inputRef.current?.blur(); return }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      const cmd = navigateHistory('up')
      if (cmd !== null) setInput(cmd)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const cmd = navigateHistory('down')
      if (cmd !== null) setInput(cmd)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Scrollable log */}
      <div
        ref={scrollRef}
        onScroll={onScroll}
        className="flex-1 overflow-y-auto"
        style={{ padding: '12px 16px' }}
      >
        <AnimatePresence initial={false}>
          {messages.map((m) => (
            <MessageRow key={m.id} message={m} />
          ))}
        </AnimatePresence>

        {messages.length === 0 && (
          <span
            style={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              opacity: 0.4,
            }}
          >
            TERMINAL READY
          </span>
        )}
      </div>

      {/* Input row */}
      <div
        className="no-drag shrink-0 flex items-center gap-2"
        style={{
          height: 36,
          borderTop: '1px solid var(--border-color)',
          padding: '0 16px',
        }}
      >
        <span
          style={{
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: '0.8rem',
            color: 'var(--accent-primary)',
            flexShrink: 0,
            userSelect: 'none',
          }}
        >
          ›
        </span>

        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          className="terminal-input flex-1 bg-transparent outline-none"
          style={{
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: '0.8rem',
            color: 'var(--text-primary)',
          }}
          placeholder="command…"
          spellCheck={false}
          autoComplete="off"
        />

        <span
          className="shrink-0 uppercase"
          style={{
            fontFamily: '"Chakra Petch", sans-serif',
            fontSize: '0.6rem',
            color: 'var(--text-secondary)',
            letterSpacing: '0.1em',
          }}
        >
          {active}
        </span>
      </div>
    </div>
  )
}
