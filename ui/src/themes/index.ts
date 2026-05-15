import { cyberpunk } from './cyberpunk'
import { minimal } from './minimal'
import { presentation } from './presentation'

export type ThemeId = 'cyberpunk' | 'minimal' | 'presentation'

const themes: Record<ThemeId, Record<string, string>> = { cyberpunk, minimal, presentation }

export function applyTheme(id: ThemeId) {
  const root = document.documentElement
  for (const [k, v] of Object.entries(themes[id])) {
    root.style.setProperty(k, v)
  }
}
