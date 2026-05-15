import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Orbitron', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        body: ['"Chakra Petch"', 'sans-serif'],
      },
      borderRadius: {
        panel: '2px',
      },
    },
  },
  plugins: [],
} satisfies Config
