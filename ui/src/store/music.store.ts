import { create } from 'zustand'

export interface PitchEvent {
  type: 'pitch_event'
  note: string
  midi: number
  frequency: number
  cents: number
  confidence: number
  ts: number
}

interface MusicStore {
  mode: 'voice' | 'instrument'
  isListening: boolean
  currentNote: string
  currentCents: number
  setMode: (mode: 'voice' | 'instrument') => void
  setListening: (v: boolean) => void
  setPitch: (note: string, cents: number) => void
}

export const useMusicStore = create<MusicStore>((set) => ({
  mode: 'voice',
  isListening: false,
  currentNote: '',
  currentCents: 0,
  setMode: (mode) => set({ mode }),
  setListening: (isListening) => set({ isListening }),
  setPitch: (currentNote, currentCents) => set({ currentNote, currentCents }),
}))

export function freqToMidi(freq: number): number {
  return Math.round(12 * Math.log2(freq / 440) + 69)
}

export function midiToName(midi: number): string {
  const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  return NOTE_NAMES[midi % 12] + Math.floor(midi / 12 - 1)
}

export function freqToCents(freq: number, midi: number): number {
  const refFreq = 440 * Math.pow(2, (midi - 69) / 12)
  return 1200 * Math.log2(freq / refFreq)
}
