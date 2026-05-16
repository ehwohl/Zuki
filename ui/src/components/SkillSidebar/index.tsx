import { useUIStore } from '../../store/ui.store'
import { SKILL_CATEGORIES } from './skills.config'

function stripPlaceholders(skill: string): string {
  return skill.replace(/\s*\{[^}]+\}/g, '').trim() + ' '
}

export default function SkillSidebar() {
  const expanded = useUIStore((s) => s.sidebarExpanded)
  const toggle = useUIStore((s) => s.toggleSidebar)
  const setTerminalInject = useUIStore((s) => s.setTerminalInject)
  const focusTerminal = useUIStore((s) => s.focusTerminal)

  const handleSkillClick = (skill: string) => {
    setTerminalInject(stripPlaceholders(skill))
    focusTerminal()
  }

  return (
    <div
      className="fixed top-0 left-0 h-full no-drag"
      style={{
        width: expanded ? 240 : 40,
        transition: expanded
          ? 'width 200ms cubic-bezier(0.16,1,0.3,1)'
          : 'width 200ms cubic-bezier(0.4,0,0.2,1)',
        background: 'rgba(8,10,14,0.95)',
        borderRight: '1px solid var(--border-color)',
        zIndex: 8,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <div
        style={{
          height: 28,
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: expanded ? 'space-between' : 'center',
          padding: expanded ? '0 8px' : '0',
          flexShrink: 0,
        }}
      >
        {expanded ? (
          <>
            <span
              className="uppercase tracking-widest"
              style={{
                fontFamily: '"Orbitron", sans-serif',
                fontSize: '0.6rem',
                color: 'var(--text-secondary)',
              }}
            >
              SKILLS
            </span>
            <button
              onClick={toggle}
              className="opacity-40 hover:opacity-100 transition-opacity"
              style={{
                fontFamily: '"Orbitron", sans-serif',
                fontSize: '0.6rem',
                color: 'var(--text-secondary)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '2px 4px',
                lineHeight: 1,
              }}
              title="Collapse sidebar (Ctrl+\)"
            >
              ◀
            </button>
          </>
        ) : (
          <button
            onClick={toggle}
            className="opacity-40 hover:opacity-100 transition-opacity"
            style={{
              fontFamily: '"Orbitron", sans-serif',
              fontSize: '0.6rem',
              color: 'var(--accent-primary)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="Expand sidebar (Ctrl+\)"
          >
            ▶
          </button>
        )}
      </div>

      {/* Body */}
      {expanded ? (
        <div
          className="flex-1 overflow-y-auto"
          style={{ padding: '12px 0', minWidth: 240 }}
        >
          {SKILL_CATEGORIES.map((cat) => (
            <div key={cat.id} style={{ marginBottom: 12 }}>
              <div
                className="uppercase tracking-widest"
                style={{
                  fontFamily: '"Orbitron", sans-serif',
                  fontSize: '0.6rem',
                  color: 'var(--accent-primary)',
                  padding: '0 12px',
                  marginBottom: 4,
                }}
              >
                {cat.label}
              </div>
              {cat.skills.map((skill) => (
                <button
                  key={skill}
                  onClick={() => handleSkillClick(skill)}
                  className="w-full text-left transition-colors"
                  style={{
                    fontFamily: '"JetBrains Mono", monospace',
                    fontSize: '0.7rem',
                    color: 'var(--text-secondary)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '3px 12px',
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    transition: 'color 150ms, background 150ms',
                  }}
                  onMouseEnter={(e) => {
                    const el = e.currentTarget
                    el.style.color = 'var(--text-primary)'
                    el.style.background = 'rgba(0,245,255,0.04)'
                  }}
                  onMouseLeave={(e) => {
                    const el = e.currentTarget
                    el.style.color = 'var(--text-secondary)'
                    el.style.background = 'none'
                  }}
                >
                  ▸ {skill}
                </button>
              ))}
            </div>
          ))}
        </div>
      ) : (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            paddingTop: 8,
            minWidth: 40,
          }}
        >
          {SKILL_CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={toggle}
              className="opacity-40 hover:opacity-100 transition-opacity"
              style={{
                fontFamily: '"Orbitron", sans-serif',
                fontSize: '0.55rem',
                color: 'var(--accent-primary)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '6px 0',
                width: '100%',
                textAlign: 'center',
              }}
              title={cat.label}
            >
              {cat.abbr}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
