import { lazy, Suspense } from 'react'
import type { AvatarRenderer } from '../../store/workspace.store'

const VrmRenderer = lazy(() => import('./VrmRenderer'))

interface Props {
  renderer: AvatarRenderer
  vrmUrl?: string
}

export default function AvatarPanel({ renderer, vrmUrl }: Props) {
  return (
    <div className="w-full h-full relative pulse-border rounded-[2px] overflow-hidden">
      <Suspense
        fallback={
          <div className="w-full h-full flex items-center justify-center">
            <span className="font-mono text-[0.65rem] text-[var(--text-secondary)] tracking-widest animate-pulse">
              LOADING AVATAR…
            </span>
          </div>
        }
      >
        {renderer === 'vrm' && <VrmRenderer vrmUrl={vrmUrl} />}
        {renderer === 'live2d' && (
          <div className="w-full h-full flex items-center justify-center">
            <span className="font-mono text-[0.65rem] text-[var(--text-secondary)]">LIVE2D — NOT IMPLEMENTED</span>
          </div>
        )}
      </Suspense>

      {/* Status badge */}
      <div className="absolute top-2 right-2 flex items-center gap-1.5 opacity-60">
        <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent-primary)] animate-pulse" />
        <span className="font-mono text-[0.55rem] text-[var(--text-secondary)] uppercase tracking-widest">
          {renderer}
        </span>
      </div>
    </div>
  )
}
