import { useRef, useEffect } from 'react'
import { useMusicStore } from '../../store/music.store'
import { Panel } from '../../panels/Panel'

const MIDI_MIN = 36
const MIDI_MAX = 84
const VISIBLE_SEMITONES = MIDI_MAX - MIDI_MIN + 1
const C_NOTES = [36, 48, 60, 72, 84]
const NOTE_NAMES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

function pitchColor(cents: number): string {
  if (Math.abs(cents) <= 10) return 'rgba(0,255,255,0.9)'
  if (Math.abs(cents) <= 25) return 'rgba(255,176,0,0.9)'
  return 'rgba(255,0,128,0.9)'
}

function midiToRow(midi: number, physH: number): number {
  const rowH = physH / VISIBLE_SEMITONES
  return (MIDI_MAX - midi) * rowH
}

function nameToMidi(name: string): number {
  const octave = parseInt(name.slice(-1))
  const noteName = name.slice(0, -1)
  return NOTE_NAMES_SHARP.indexOf(noteName) + (octave + 1) * 12
}

export default function PitchRollPanel() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rafRef = useRef<number>(0)
  const offscreenRef = useRef<HTMLCanvasElement | null>(null)
  const trailRef = useRef<HTMLCanvasElement | null>(null)
  const physWRef = useRef<number>(0)
  const physHRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    offscreenRef.current = document.createElement('canvas')
    trailRef.current = document.createElement('canvas')

    function drawGrid(physW: number, physH: number) {
      const off = offscreenRef.current!
      off.width = physW
      off.height = physH
      const gCtx = off.getContext('2d')!

      const style = getComputedStyle(document.documentElement)
      // --bg-elevated does not exist in themes; use --bg-base as the dark base
      const bgBase = style.getPropertyValue('--bg-base').trim() || '#0A0C10'
      const borderColor = style.getPropertyValue('--border-color').trim() || 'rgba(0,245,255,0.15)'
      const textSecondary = style.getPropertyValue('--text-secondary').trim() || '#607080'
      const rowH = physH / VISIBLE_SEMITONES

      // Solid opaque background so canvas is never transparent
      gCtx.fillStyle = bgBase
      gCtx.fillRect(0, 0, physW, physH)

      for (let midi = MIDI_MIN; midi <= MIDI_MAX; midi++) {
        const semitone = midi % 12
        const isBlack = [1, 3, 6, 8, 10].includes(semitone)
        const y = midiToRow(midi, physH)
        // White key rows get a subtle brightness lift over the solid background
        if (!isBlack) {
          gCtx.fillStyle = 'rgba(255,255,255,0.05)'
          gCtx.fillRect(0, y, physW, rowH)
        }
        gCtx.strokeStyle = borderColor
        gCtx.lineWidth = 0.5
        gCtx.beginPath()
        gCtx.moveTo(0, y)
        gCtx.lineTo(physW, y)
        gCtx.stroke()
      }

      for (const midi of C_NOTES) {
        const y = midiToRow(midi, physH)
        gCtx.strokeStyle = 'rgba(0,245,255,0.2)'
        gCtx.lineWidth = 1
        gCtx.beginPath()
        gCtx.moveTo(0, y)
        gCtx.lineTo(physW, y)
        gCtx.stroke()

        const octave = Math.floor(midi / 12) - 1
        gCtx.fillStyle = textSecondary
        gCtx.font = `${Math.max(8, Math.round(rowH * 0.8))}px JetBrains Mono, monospace`
        gCtx.textAlign = 'left'
        gCtx.fillText(`C${octave}`, 4, y + rowH * 0.75)
      }
    }

    function drawFrame() {
      const cv = canvasRef.current
      if (!cv || !offscreenRef.current || !trailRef.current) return
      const ctx = cv.getContext('2d')!
      const physW = physWRef.current
      const physH = physHRef.current
      if (physW === 0 || physH === 0) {
        rafRef.current = requestAnimationFrame(drawFrame)
        return
      }

      const trail = trailRef.current
      const trailCtx = trail.getContext('2d')!

      // Shift trail left 1 physical pixel, clear rightmost column
      trailCtx.drawImage(trail, -1, 0)
      trailCtx.clearRect(physW - 1, 0, 1, physH)

      // Read pitch synchronously from store — safe in rAF, no React subscription
      const s = useMusicStore.getState()
      const currentNote = s.currentNote
      const currentCents = s.currentCents

      if (currentNote) {
        const midi = nameToMidi(currentNote)
        if (midi >= MIDI_MIN && midi <= MIDI_MAX) {
          const color = pitchColor(currentCents)
          const rowH = physH / VISIBLE_SEMITONES
          const y = midiToRow(midi, physH)
          trailCtx.shadowColor = color
          trailCtx.shadowBlur = 6
          trailCtx.fillStyle = color
          trailCtx.fillRect(physW - 2, Math.floor(y), 2, Math.max(1, Math.ceil(rowH)))
          trailCtx.shadowBlur = 0
        }
      }

      ctx.drawImage(offscreenRef.current, 0, 0)
      ctx.drawImage(trail, 0, 0)

      rafRef.current = requestAnimationFrame(drawFrame)
    }

    const resizeObs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const dpr = window.devicePixelRatio || 1
        const cssW = entry.contentRect.width
        const cssH = entry.contentRect.height
        const physW = Math.round(cssW * dpr)
        const physH = Math.round(cssH * dpr)

        physWRef.current = physW
        physHRef.current = physH

        canvas.width = physW
        canvas.height = physH
        canvas.style.width = cssW + 'px'
        canvas.style.height = cssH + 'px'

        if (trailRef.current) {
          trailRef.current.width = physW
          trailRef.current.height = physH
        }

        if (physW > 0 && physH > 0) drawGrid(physW, physH)
      }
    })
    resizeObs.observe(canvas)

    const mutObs = new MutationObserver(() => {
      if (physWRef.current > 0 && physHRef.current > 0) {
        drawGrid(physWRef.current, physHRef.current)
      }
    })
    mutObs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })

    rafRef.current = requestAnimationFrame(drawFrame)

    return () => {
      cancelAnimationFrame(rafRef.current)
      resizeObs.disconnect()
      mutObs.disconnect()
    }
  }, [])

  return (
    <Panel id="pitch-roll" title="Pitch Roll" noPad>
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
    </Panel>
  )
}
