import { useEffect, useRef } from 'react'
import Pitchfinder from 'pitchfinder'
import { bridge } from '../bridge/ws'
import { useMusicStore, freqToMidi, midiToName, freqToCents, type PitchEvent } from '../store/music.store'

// 16 worklet frames × 128 samples = 2048 samples (~43ms at 48kHz)
// Larger buffer gives YIN enough cycles even at low bass frequencies
const FRAMES_PER_ANALYSIS = 16
const SAMPLES_PER_FRAME = 128
const BUF_SIZE = FRAMES_PER_ANALYSIS * SAMPLES_PER_FRAME

export function usePitchDetector(): void {
  const streamRef = useRef<MediaStream | null>(null)
  const ctxRef = useRef<AudioContext | null>(null)
  const nodeRef = useRef<AudioWorkletNode | null>(null)
  const bufRef = useRef<Float32Array[]>([])
  const lastSendRef = useRef<number>(0)

  useEffect(() => {
    let active = true

    async function start() {
      // Disable all browser audio processing — echo cancellation and noise
      // suppression destroy the harmonic content that pitch detectors rely on
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
        video: false,
      })
      if (!active) {
        stream.getTracks().forEach((t) => t.stop())
        return
      }
      const ctx = new AudioContext()
      // Match Pitchfinder sample rate to the actual AudioContext rate (44100 or 48000)
      const detectPitch = Pitchfinder.YIN({ sampleRate: ctx.sampleRate })

      await ctx.audioWorklet.addModule('/pitch-processor.js')
      const src = ctx.createMediaStreamSource(stream)
      const node = new AudioWorkletNode(ctx, 'pitch-processor')

      node.port.onmessage = (e: MessageEvent<Float32Array>) => {
        bufRef.current.push(e.data)
        if (bufRef.current.length >= FRAMES_PER_ANALYSIS) {
          const merged = new Float32Array(BUF_SIZE)
          let offset = 0
          for (const chunk of bufRef.current) {
            merged.set(chunk, offset)
            offset += chunk.length
          }
          bufRef.current = []
          const freq = detectPitch(merged)

          // Mode-aware frequency range: voice = human singing, instrument = full
          const { mode } = useMusicStore.getState()
          const freqMin = mode === 'voice' ? 80 : 60
          const freqMax = mode === 'voice' ? 1000 : 2000

          if (freq && freq > freqMin && freq < freqMax) {
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

    start().catch((err) => {
      console.error('[usePitchDetector]', err)
      useMusicStore.getState().setListening(false)
    })

    return () => {
      active = false
      nodeRef.current?.disconnect()
      streamRef.current?.getTracks().forEach((t) => t.stop())
      ctxRef.current?.close()
      useMusicStore.getState().setListening(false)
    }
  }, [])
}
