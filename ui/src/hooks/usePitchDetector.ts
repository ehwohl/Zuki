import { useEffect, useRef } from 'react'
import Pitchfinder from 'pitchfinder'
import { bridge } from '../bridge/ws'
import { useMusicStore, freqToMidi, midiToName, freqToCents, type PitchEvent } from '../store/music.store'

export function usePitchDetector(): void {
  const streamRef = useRef<MediaStream | null>(null)
  const ctxRef = useRef<AudioContext | null>(null)
  const nodeRef = useRef<AudioWorkletNode | null>(null)
  const bufRef = useRef<Float32Array[]>([])
  const lastSendRef = useRef<number>(0)

  useEffect(() => {
    let active = true
    const detectPitch = Pitchfinder.YIN({ sampleRate: 48000 })

    async function start() {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      if (!active) {
        stream.getTracks().forEach((t) => t.stop())
        return
      }
      const ctx = new AudioContext()
      await ctx.audioWorklet.addModule('/pitch-processor.js')
      const src = ctx.createMediaStreamSource(stream)
      const node = new AudioWorkletNode(ctx, 'pitch-processor')

      node.port.onmessage = (e: MessageEvent<Float32Array>) => {
        bufRef.current.push(e.data)
        if (bufRef.current.length >= 8) {
          const merged = new Float32Array(1024)
          let offset = 0
          for (const chunk of bufRef.current) {
            merged.set(chunk, offset)
            offset += chunk.length
          }
          bufRef.current = []
          const freq = detectPitch(merged)
          if (freq && freq > 60 && freq < 2000) {
            const midi = freqToMidi(freq)
            const note = midiToName(midi)
            const cents = Math.round(freqToCents(freq, midi))
            useMusicStore.getState().setPitch(note, cents)
            const now = Date.now()
            if (now - lastSendRef.current > 200) {
              lastSendRef.current = now
              const payload: PitchEvent = {
                type: 'pitch_event',
                note,
                midi,
                frequency: freq,
                cents,
                confidence: 1.0,
                ts: now,
              }
              bridge.send('pitch_event', payload as unknown as Record<string, unknown>)
            }
          }
        }
      }

      src.connect(node)
      streamRef.current = stream
      ctxRef.current = ctx
      nodeRef.current = node
      useMusicStore.getState().setListening(true)
    }

    start().catch((err) => console.error('[usePitchDetector]', err))

    return () => {
      active = false
      nodeRef.current?.disconnect()
      streamRef.current?.getTracks().forEach((t) => t.stop())
      ctxRef.current?.close()
      useMusicStore.getState().setListening(false)
    }
  }, [])
}
