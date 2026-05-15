import { useState, useEffect } from 'react'
import { useWSStore } from '../../store/ws.store'

interface Ticker {
  symbol: string
  price: number
  delta: number
  sparkline: number[]
}

const MOCK_TICKERS: Ticker[] = [
  { symbol: 'SPX', price: 5842.3, delta: 0.72, sparkline: [5780, 5800, 5790, 5820, 5835, 5842] },
  { symbol: 'NDX', price: 20_891.4, delta: 1.14, sparkline: [20400, 20500, 20600, 20700, 20800, 20891] },
  { symbol: 'NVDA', price: 151.8, delta: 2.41, sparkline: [140, 142, 145, 148, 150, 151.8] },
  { symbol: 'BTC', price: 67_420.0, delta: -1.83, sparkline: [70000, 69000, 68500, 68000, 67800, 67420] },
  { symbol: 'EUR/USD', price: 1.0824, delta: -0.12, sparkline: [1.085, 1.084, 1.083, 1.083, 1.082, 1.0824] },
  { symbol: 'GOLD', price: 2352.5, delta: 0.38, sparkline: [2330, 2335, 2340, 2345, 2350, 2352] },
]

function MiniSparkline({ data, up }: { data: number[]; up: boolean }) {
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const W = 48, H = 20
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * W},${H - ((v - min) / range) * H}`)
    .join(' ')

  return (
    <svg width={W} height={H} className="shrink-0">
      <polyline
        points={pts}
        fill="none"
        stroke={up ? 'var(--color-up)' : 'var(--color-down)'}
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Watchlist() {
  const [tickers, setTickers] = useState<Ticker[]>(MOCK_TICKERS)
  const lastMessage = useWSStore((s) => s.lastMessage)

  useEffect(() => {
    if (lastMessage?.type === 'broker_tick') {
      const msg = lastMessage as { type: string; symbol: string; price: number; delta: number; sparkline: number[] }
      setTickers((prev) =>
        prev.map((t) =>
          t.symbol === msg.symbol
            ? { ...t, price: msg.price, delta: msg.delta, sparkline: msg.sparkline ?? t.sparkline }
            : t,
        ),
      )
    }
  }, [lastMessage])

  return (
    <div className="h-full flex items-center gap-2 px-2 overflow-x-auto">
      {tickers.map((t) => {
        const up = t.delta >= 0
        return (
          <div
            key={t.symbol}
            className="flex-shrink-0 flex flex-col gap-0.5 px-3 py-2 panel-glass rounded-[2px] min-w-[112px]"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-display text-[0.6rem] tracking-widest text-[var(--text-secondary)] uppercase">
                {t.symbol}
              </span>
              <span
                className="font-mono text-[0.6rem]"
                style={{ color: up ? 'var(--color-up)' : 'var(--color-down)' }}
              >
                {up ? '+' : ''}{t.delta.toFixed(2)}%
              </span>
            </div>
            <div className="flex items-end justify-between gap-2">
              <span className="font-mono text-sm text-[var(--text-primary)]">
                {t.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <MiniSparkline data={t.sparkline} up={up} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
