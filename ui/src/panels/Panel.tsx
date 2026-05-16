import React, { useRef, useCallback } from 'react'
import { useLayoutStore } from '../store/layout.store'
import { cn } from '../lib/cn'

interface PanelProps {
  id: string
  title: string
  children: React.ReactNode
  className?: string
  headerExtra?: React.ReactNode
  noPad?: boolean
}

type ResizeEdge = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw'

interface DragState {
  kind: 'move' | 'resize'
  edge: ResizeEdge | ''
  x0: number
  y0: number
  px0: number
  py0: number
  w0: number
  h0: number
}

const MIN_W = 180
const MIN_H = 100

export function Panel({ id, title, children, className, headerExtra, noPad }: PanelProps) {
  const panel = useLayoutStore((s) => s.panels[id])
  const update = useLayoutStore((s) => s.updatePanel)
  const bringToFront = useLayoutStore((s) => s.bringToFront)
  const collapse = useLayoutStore((s) => s.collapsePanel)
  const persist = useLayoutStore((s) => s.persistToStorage)

  const drag = useRef<DragState | null>(null)
  const hasMoved = useRef(false)
  const persistTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const debouncedPersist = useCallback(() => {
    const wsId = (document.body.dataset.workspace ?? 'broker')
    if (persistTimer.current) clearTimeout(persistTimer.current)
    persistTimer.current = setTimeout(() => persist(wsId), 500)
  }, [persist])

  const startDrag = useCallback(
    (e: React.PointerEvent, kind: 'move' | 'resize', edge: ResizeEdge | '' = '') => {
      e.preventDefault()
      e.stopPropagation()
      hasMoved.current = false
      bringToFront(id)
      drag.current = { kind, edge, x0: e.clientX, y0: e.clientY, px0: panel.x, py0: panel.y, w0: panel.w, h0: panel.h }
      ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    },
    [id, panel, bringToFront],
  )

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      const d = drag.current
      if (!d) return
      const dx = e.clientX - d.x0
      const dy = e.clientY - d.y0

      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) hasMoved.current = true

      if (d.kind === 'move') {
        update(id, { x: d.px0 + dx, y: d.py0 + dy })
        return
      }

      let x = d.px0, y = d.py0, w = d.w0, h = d.h0
      const edge = d.edge
      if (edge.includes('e')) w = Math.max(MIN_W, d.w0 + dx)
      if (edge.includes('s')) h = Math.max(MIN_H, d.h0 + dy)
      if (edge.includes('w')) { w = Math.max(MIN_W, d.w0 - dx); x = d.px0 + d.w0 - w }
      if (edge.includes('n')) { h = Math.max(MIN_H, d.h0 - dy); y = d.py0 + d.h0 - h }
      update(id, { x, y, w, h })
    },
    [id, update],
  )

  const onPointerUp = useCallback(() => {
    drag.current = null
    debouncedPersist()
  }, [debouncedPersist])

  if (!panel) return null

  if (panel.collapsed) {
    return (
      <div
        className="absolute no-drag w-12 h-12 flex items-center justify-center panel-glass hover:border-[var(--accent-primary)] transition-colors cursor-grab active:cursor-grabbing select-none"
        style={{ left: panel.x, top: panel.y, zIndex: panel.zIndex }}
        title={`Expand ${title}`}
        onPointerDown={(e) => startDrag(e, 'move')}
        onPointerMove={onPointerMove}
        onPointerUp={() => {
          if (!hasMoved.current) collapse(id)
          drag.current = null
          debouncedPersist()
        }}
      >
        <span className="font-display text-xs text-[var(--accent-primary)] tracking-widest pointer-events-none">
          {title.slice(0, 2).toUpperCase()}
        </span>
      </div>
    )
  }

  return (
    <div
      className={cn('absolute no-drag', className)}
      style={{ left: panel.x, top: panel.y, width: panel.w, height: panel.h, zIndex: panel.zIndex }}
      onPointerDown={() => bringToFront(id)}
    >
      <div className="flex flex-col w-full h-full panel-glass overflow-hidden">
        {/* Header — drag handle */}
        <div
          className="flex items-center justify-between px-3 flex-shrink-0 border-b border-[var(--border-color)] cursor-grab active:cursor-grabbing"
          style={{ height: 28 }}
          onPointerDown={(e) => startDrag(e, 'move')}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
        >
          <span className="font-display text-[0.6rem] text-[var(--text-secondary)] tracking-widest uppercase select-none">
            {title}
          </span>
          <div className="flex items-center gap-1.5" onPointerDown={(e) => e.stopPropagation()}>
            {headerExtra}
            <button
              className="w-4 h-4 flex items-center justify-center opacity-40 hover:opacity-100 text-[var(--text-secondary)] hover:text-[var(--accent-primary)] transition-opacity"
              onClick={() => collapse(id)}
              title="Collapse"
            >
              <svg width="10" height="2" viewBox="0 0 10 2" fill="none">
                <path d="M1 1h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className={cn('flex-1 overflow-hidden', !noPad && 'p-3')}>
          {children}
        </div>
      </div>

      {/* Resize handles — edges */}
      {(['n','s','e','w'] as const).map((edge) => (
        <div
          key={edge}
          className={cn(
            'absolute',
            edge === 'n' && 'inset-x-3 top-0 h-2 cursor-n-resize',
            edge === 's' && 'inset-x-3 bottom-0 h-2 cursor-s-resize',
            edge === 'w' && 'inset-y-3 left-0 w-2 cursor-w-resize',
            edge === 'e' && 'inset-y-3 right-0 w-2 cursor-e-resize',
          )}
          onPointerDown={(e) => startDrag(e, 'resize', edge)}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
        />
      ))}
      {/* Resize handles — corners */}
      {(['ne','nw','se','sw'] as const).map((corner) => (
        <div
          key={corner}
          className={cn(
            'absolute w-3 h-3',
            corner === 'nw' && 'top-0 left-0 cursor-nw-resize',
            corner === 'ne' && 'top-0 right-0 cursor-ne-resize',
            corner === 'sw' && 'bottom-0 left-0 cursor-sw-resize',
            corner === 'se' && 'bottom-0 right-0 cursor-se-resize',
          )}
          onPointerDown={(e) => startDrag(e, 'resize', corner)}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
        />
      ))}
    </div>
  )
}
