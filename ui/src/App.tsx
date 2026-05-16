import { useEffect } from 'react'
import { useWorkspaceStore } from './store/workspace.store'
import { useUIStore } from './store/ui.store'
import { applyTheme } from './themes'
import { bridge } from './bridge/ws'
import { PanelManager } from './panels/PanelManager'
import SkillSidebar from './components/SkillSidebar'
import WindowControls from './components/WindowControls'

export function App() {
  const theme = useUIStore((s) => s.theme)
  const isTransitioning = useWorkspaceStore((s) => s.isTransitioning)
  const endTransition = useWorkspaceStore((s) => s.endTransition)
  const presentationMode = useUIStore((s) => s.presentationMode)
  const focusTerminal = useUIStore((s) => s.focusTerminal)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const togglePresentation = useUIStore((s) => s.togglePresentationMode)
  const navigate = useWorkspaceStore((s) => s.navigate)

  useEffect(() => { applyTheme(theme) }, [theme])

  useEffect(() => {
    bridge.connect()
    return () => bridge.disconnect()
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.code === 'Space') { e.preventDefault(); focusTerminal() }
      if (e.ctrlKey && e.key === '\\') { e.preventDefault(); toggleSidebar() }
      if (e.altKey && e.key === 'p') { e.preventDefault(); togglePresentation() }
      if (e.altKey && e.key === 'a') { e.preventDefault() /* avatar collapse via store */ }
      if (e.altKey && e.key === 'n') { e.preventDefault() /* neural-map collapse via store */ }
      if (e.altKey && e.key === '1') navigate('broker')
      if (e.altKey && e.key === '2') navigate('business')
      if (e.altKey && e.key === '3') navigate('coding')
      if (e.altKey && e.key === '4') navigate('os')
      if (e.altKey && e.key === '5') navigate('office')
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [focusTerminal, toggleSidebar, togglePresentation, navigate])

  return (
    <div
      className={[
        'fixed inset-0 overflow-hidden scanlines drag-region',
        presentationMode ? 'presentation-mode' : '',
      ].join(' ')}
      data-glitch={isTransitioning ? '1' : '0'}
      style={{
        background: 'var(--bg-base)',
        fontFamily: '"Chakra Petch", sans-serif',
      }}
      onAnimationEnd={isTransitioning ? endTransition : undefined}
    >
      {/* Procedural grain overlay */}
      <div
        className="fixed inset-0 pointer-events-none z-[9996]"
        style={{
          backgroundImage: 'var(--noise-url)',
          opacity: 'var(--grain-opacity)',
          backgroundRepeat: 'repeat',
        }}
      />

      {/* Skill sidebar — fixed, outside panel system, z-index 8 */}
      <SkillSidebar />

      {/* Window controls — opacity 0, reveals on root hover */}
      {!presentationMode && <WindowControls />}

      {/* Zuki watermark in presentation mode */}
      {presentationMode && (
        <div className="fixed bottom-4 right-6 z-[9990] pointer-events-none opacity-15">
          <span className="font-display text-[0.7rem] text-[var(--accent-primary)] tracking-[0.3em] uppercase">
            Zuki-OS
          </span>
        </div>
      )}

      {/* Panel system — includes persistent Terminal panel */}
      <PanelManager />

      {/* Glitch overlay — applies class when transitioning */}
      {isTransitioning && (
        <div
          className="workspace-glitch fixed inset-0 pointer-events-none z-[9995]"
          data-glitch="1"
          style={{ background: 'var(--bg-base)', mixBlendMode: 'overlay' }}
          onAnimationEnd={endTransition}
        />
      )}
    </div>
  )
}
