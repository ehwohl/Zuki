export interface SkillCategory {
  id: string
  label: string
  abbr: string
  skills: string[]
}

export const SKILL_CATEGORIES: SkillCategory[] = [
  {
    id: 'broker',
    label: 'BROKER',
    abbr: 'BR',
    skills: ['analyse {symbol}', 'watchlist add {symbol}', 'watchlist remove {symbol}', 'news feed'],
  },
  {
    id: 'business',
    label: 'BUSINESS',
    abbr: 'BU',
    skills: ['business interview {type}', 'business report', 'business score {venue}'],
  },
  {
    id: 'coding',
    label: 'CODING',
    abbr: 'CO',
    skills: ['coding analyse', 'coding depgraph'],
  },
  {
    id: 'os',
    label: 'OS',
    abbr: 'OS',
    skills: ['os status', 'tts test', 'stt start', 'stt stop'],
  },
  {
    id: 'system',
    label: 'SYSTEM',
    abbr: 'SY',
    skills: ['sim on', 'sim off', 'system test github', 'help'],
  },
]
