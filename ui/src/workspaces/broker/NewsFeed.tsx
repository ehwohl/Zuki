import { useState, useEffect, useRef } from 'react'
import { useWSStore } from '../../store/ws.store'

interface NewsItem {
  id: string
  source: string
  headline: string
  timestamp: string
  urgent: boolean
}

const MOCK_FEED: NewsItem[] = [
  { id: '1', source: 'BLOOMBERG', headline: 'Fed holds rates, signals two cuts possible in 2026', timestamp: '09:41', urgent: false },
  { id: '2', source: 'REUTERS', headline: 'NVIDIA breaks $150 resistance — GPU order surge cited', timestamp: '09:38', urgent: true },
  { id: '3', source: 'WSJ', headline: 'ECB inflation data: core CPI at 2.1%, in-target', timestamp: '09:22', urgent: false },
  { id: '4', source: 'FT', headline: 'German industrial output -0.8% MoM — weak Q1 confirmed', timestamp: '09:15', urgent: false },
  { id: '5', source: 'CNBC', headline: 'Bitcoin ETF flows turn negative for third session', timestamp: '09:02', urgent: false },
]

export default function NewsFeed() {
  const [items, setItems] = useState<NewsItem[]>(MOCK_FEED)
  const [urgentId, setUrgentId] = useState<string | null>(null)
  const lastMessage = useWSStore((s) => s.lastMessage)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (lastMessage?.type === 'news_item') {
      const msg = lastMessage as { type: string; source: string; headline: string; timestamp: string }
      const newItem: NewsItem = {
        id: Date.now().toString(),
        source: msg.source ?? 'WIRE',
        headline: msg.headline ?? '',
        timestamp: msg.timestamp ?? new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' }),
        urgent: false,
      }
      setItems((prev) => [newItem, ...prev.slice(0, 49)])
      listRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }, [lastMessage])

  // Urgent flash for 3s
  useEffect(() => {
    const urgent = items.find((i) => i.urgent)
    if (urgent && urgentId !== urgent.id) {
      setUrgentId(urgent.id)
      const t = setTimeout(() => setUrgentId(null), 3000)
      return () => clearTimeout(t)
    }
  }, [items, urgentId])

  return (
    <div ref={listRef} className="h-full overflow-y-auto terminal space-y-0">
      {items.map((item) => (
        <div
          key={item.id}
          className="flex gap-2 px-3 py-1.5 border-b border-[var(--border-color)] hover:bg-[rgba(0,245,255,0.03)] transition-colors"
          style={urgentId === item.id ? { color: 'var(--accent-warning)' } : undefined}
        >
          <span className="shrink-0 text-[var(--text-secondary)] text-[0.65rem]">[{item.timestamp}]</span>
          <span
            className="shrink-0 text-[0.55rem] tracking-widest uppercase"
            style={{ color: item.urgent ? 'var(--accent-warning)' : 'var(--accent-secondary)' }}
          >
            {item.source}
          </span>
          <span className="text-[0.7rem] text-[var(--text-primary)] leading-tight">{item.headline}</span>
        </div>
      ))}
    </div>
  )
}
