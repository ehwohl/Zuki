import { memo } from 'react'
import { motion } from 'framer-motion'
import type { Message } from '../../store/terminal.store'

function fmt(ts: number): string {
  return new Date(ts).toTimeString().slice(0, 8)
}

export const MessageRow = memo(function MessageRow({ message }: { message: Message }) {
  const isOp = message.role === 'operator'

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.1, ease: 'easeOut' }}
      style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 6 }}
    >
      <span
        style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: '0.65rem',
          color: 'var(--text-secondary)',
          flexShrink: 0,
          lineHeight: 1.6,
          userSelect: 'none',
        }}
      >
        {fmt(message.ts)}
      </span>

      <span
        style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: '0.75rem',
          color: isOp ? 'var(--accent-primary)' : 'var(--accent-secondary)',
          flexShrink: 0,
          lineHeight: 1.6,
          userSelect: 'none',
        }}
      >
        {isOp ? '›' : '◆'}
      </span>

      <span
        style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: '0.75rem',
          color: isOp ? 'var(--text-primary)' : 'var(--text-secondary)',
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          userSelect: 'text',
        }}
      >
        {message.text}
      </span>
    </motion.div>
  )
})
