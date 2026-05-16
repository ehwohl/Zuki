import { useEffect, useState, useRef } from 'react'
import { Panel } from '../../panels/Panel'
import { bridge } from '../../bridge/ws'
import { useWSStore } from '../../store/ws.store'

interface CategoryCount {
  label: string
  count: number
}

interface OfficeStatus {
  total: number
  categories: CategoryCount[]
  auth_ready: boolean
  credentials_exist: boolean
  recent_reports: ReportEntry[]
}

interface SearchResult {
  name: string
  category: string
  client: string
  web_link: string
}

interface ReportEntry {
  name: string
  path: string
  ts: string
}

// ── Index panel ────────────────────────────────────────────────────────────────

function OfficeIndexPanel({ status }: { status: OfficeStatus | null }) {
  const maxCount = status
    ? Math.max(1, ...status.categories.map((c) => c.count))
    : 1

  return (
    <div className="h-full overflow-y-auto flex flex-col gap-4">
      {/* Header stats */}
      <div className="flex items-baseline gap-3 pb-3 border-b border-[var(--border-color)]">
        <span
          className="font-display text-5xl"
          style={{ color: 'var(--accent-primary)' }}
        >
          {status?.total ?? '—'}
        </span>
        <span className="font-mono text-[0.65rem] text-[var(--text-secondary)] uppercase tracking-widest">
          files indexed
        </span>
      </div>

      {/* Category bars */}
      {status && status.categories.length > 0 ? (
        <div className="flex flex-col gap-2">
          {status.categories.map(({ label, count }) => (
            <div key={label}>
              <div className="flex justify-between mb-1">
                <span className="font-mono text-[0.6rem] text-[var(--text-secondary)] uppercase tracking-widest">
                  {label}
                </span>
                <span className="font-mono text-[0.6rem] text-[var(--text-primary)]">{count}</span>
              </div>
              <div
                className="h-1 rounded-full"
                style={{ background: 'var(--border-color)' }}
              >
                <div
                  className="h-1 rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.round((count / maxCount) * 100)}%`,
                    background: 'var(--accent-primary)',
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="font-mono text-[0.65rem] text-[var(--text-secondary)] opacity-40">
          Index empty — type: büro index
        </div>
      )}

      {/* Commands */}
      <div className="mt-auto pt-3 border-t border-[var(--border-color)] flex flex-col gap-1">
        {[
          ['büro index', 'Rebuild Drive index'],
          ['büro hochladen', 'Upload latest report'],
        ].map(([cmd, desc]) => (
          <button
            key={cmd}
            onClick={() => bridge.send('command', { text: cmd, workspace: 'office', tenant: 'self' })}
            className="flex items-center gap-3 text-left group"
          >
            <code className="font-mono text-[0.6rem] text-[var(--accent-primary)] group-hover:underline">
              {cmd}
            </code>
            <span className="font-mono text-[0.55rem] text-[var(--text-secondary)] opacity-60">{desc}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Search panel ───────────────────────────────────────────────────────────────

function OfficeSearchPanel() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [searched, setSearched] = useState(false)
  const lastMessage = useWSStore((s) => s.lastMessage)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (lastMessage?.type === 'office_search_results') {
      setResults((lastMessage.results as SearchResult[]) ?? [])
      setSearched(true)
    }
  }, [lastMessage])

  function runSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    bridge.send('command', {
      text: `büro suche ${query.trim()}`,
      workspace: 'office',
      tenant: 'self',
    })
  }

  function runBrief(client: string) {
    bridge.send('command', {
      text: `büro brief ${client}`,
      workspace: 'office',
      tenant: 'self',
    })
  }

  return (
    <div className="flex flex-col h-full gap-3">
      {/* search input */}
      <form onSubmit={runSearch} className="flex gap-2 flex-shrink-0">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Datei oder Kunde suchen…"
          className="flex-1 font-mono text-xs bg-transparent border border-[var(--border-color)] text-[var(--text-primary)] px-2 py-1 rounded-sm focus:outline-none focus:border-[var(--accent-primary)] placeholder:text-[var(--text-secondary)] placeholder:opacity-40 transition-colors"
        />
        <button
          type="submit"
          className="font-mono text-[0.6rem] tracking-widest uppercase px-2 border border-[var(--accent-primary)] text-[var(--accent-primary)] hover:bg-[var(--accent-primary)] hover:text-[var(--bg-base)] transition-colors rounded-sm"
        >
          GO
        </button>
      </form>

      {/* results */}
      <div className="flex-1 overflow-y-auto">
        {results.length > 0 ? (
          <div className="flex flex-col gap-2">
            {results.map((r, i) => (
              <div
                key={i}
                className="border border-[var(--border-color)] rounded-sm p-2 hover:border-[var(--accent-primary)] transition-colors group"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-mono text-[0.7rem] text-[var(--text-primary)] truncate">
                      {r.name}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span
                        className="font-mono text-[0.55rem] uppercase tracking-widest px-1 rounded-sm"
                        style={{ background: 'var(--border-color)', color: 'var(--accent-primary)' }}
                      >
                        {r.category}
                      </span>
                      {r.client && (
                        <button
                          onClick={() => runBrief(r.client)}
                          className="font-mono text-[0.55rem] text-[var(--text-secondary)] hover:text-[var(--accent-primary)] transition-colors"
                        >
                          {r.client} →
                        </button>
                      )}
                    </div>
                  </div>
                  {r.web_link && (
                    <a
                      href={r.web_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-[0.55rem] text-[var(--accent-secondary)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                    >
                      OPEN ↗
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : searched ? (
          <div className="font-mono text-[0.65rem] text-[var(--text-secondary)] opacity-40">
            Keine Ergebnisse für „{query}"
          </div>
        ) : (
          <div className="font-mono text-[0.65rem] text-[var(--text-secondary)] opacity-40">
            Suchbegriff eingeben — z. B. „Rechnung" oder Kundenname
          </div>
        )}
      </div>
    </div>
  )
}

// ── Drive status panel ─────────────────────────────────────────────────────────

function OfficeDrivePanel({ status }: { status: OfficeStatus | null }) {
  const authOk = status?.auth_ready ?? false
  const credOk = status?.credentials_exist ?? false

  return (
    <div className="flex flex-col h-full gap-3">
      <div className="flex items-center gap-2 pb-2 border-b border-[var(--border-color)]">
        <div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ background: authOk ? 'var(--color-up)' : 'var(--color-down)' }}
        />
        <span className="font-mono text-[0.6rem] uppercase tracking-widest text-[var(--text-secondary)]">
          Google Drive
        </span>
        <span
          className="font-mono text-[0.55rem] uppercase tracking-widest ml-auto"
          style={{ color: authOk ? 'var(--color-up)' : 'var(--color-down)' }}
        >
          {authOk ? 'CONNECTED' : credOk ? 'TOKEN NEEDED' : 'NO CREDS'}
        </span>
      </div>

      {/* Recent reports */}
      <div className="flex-1 overflow-y-auto">
        {status?.recent_reports && status.recent_reports.length > 0 ? (
          <div className="flex flex-col gap-1">
            <div className="font-mono text-[0.55rem] uppercase tracking-widest text-[var(--text-secondary)] opacity-60 mb-1">
              Recent reports
            </div>
            {status.recent_reports.map((r, i) => (
              <div
                key={i}
                className="flex items-center gap-2 py-1 border-b border-[var(--border-color)] last:border-0"
              >
                <span className="font-mono text-[0.6rem] text-[var(--text-primary)] flex-1 truncate">
                  {r.name}
                </span>
                <span className="font-mono text-[0.55rem] text-[var(--text-secondary)] shrink-0">
                  {r.ts}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="font-mono text-[0.65rem] text-[var(--text-secondary)] opacity-40">
            No reports yet
          </div>
        )}
      </div>

      {/* Auth commands */}
      <div className="flex gap-2 flex-shrink-0">
        <button
          onClick={() => bridge.send('command', { text: 'büro auth', workspace: 'office', tenant: 'self' })}
          className="font-mono text-[0.55rem] uppercase tracking-widest px-2 py-0.5 border border-[var(--border-color)] text-[var(--text-secondary)] hover:border-[var(--accent-primary)] hover:text-[var(--accent-primary)] transition-colors rounded-sm"
        >
          STATUS
        </button>
        {!authOk && (
          <button
            onClick={() => bridge.send('command', { text: 'büro auth reset', workspace: 'office', tenant: 'self' })}
            className="font-mono text-[0.55rem] uppercase tracking-widest px-2 py-0.5 border border-[var(--accent-secondary)] text-[var(--accent-secondary)] hover:bg-[var(--accent-secondary)] hover:text-[var(--bg-base)] transition-colors rounded-sm"
          >
            AUTH
          </button>
        )}
      </div>
    </div>
  )
}

// ── Root workspace ─────────────────────────────────────────────────────────────

export default function OfficeWorkspace() {
  const [status, setStatus] = useState<OfficeStatus | null>(null)
  const lastMessage = useWSStore((s) => s.lastMessage)

  useEffect(() => {
    bridge.send('navigate', { workspace: 'office' })
    bridge.send('command', { text: 'büro', workspace: 'office', tenant: 'self' })
  }, [])

  useEffect(() => {
    if (lastMessage?.type === 'office_status') {
      setStatus({
        total:            (lastMessage.total as number) ?? 0,
        categories:       (lastMessage.categories as CategoryCount[]) ?? [],
        auth_ready:       (lastMessage.auth_ready as boolean) ?? false,
        credentials_exist:(lastMessage.credentials_exist as boolean) ?? false,
        recent_reports:   (lastMessage.recent_reports as ReportEntry[]) ?? [],
      })
    }
  }, [lastMessage])

  return (
    <>
      <Panel id="office-index" title="Drive Index">
        <OfficeIndexPanel status={status} />
      </Panel>

      <Panel id="office-search" title="Search">
        <OfficeSearchPanel />
      </Panel>

      <Panel id="office-drive" title="Drive — Auth & Reports">
        <OfficeDrivePanel status={status} />
      </Panel>
    </>
  )
}
