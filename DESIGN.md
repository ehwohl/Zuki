# Zuki-OS — Design System

> All values here are CSS custom property names.
> Components read tokens — never hardcode hex values in component files.
> Theme swap = CSS var reassignment. Zero re-renders.

---

## Color Tokens

| Token | Cyberpunk | Minimal | Presentation |
|---|---|---|---|
| `--bg-base` | `#0A0C10` | `#111318` | `#0D0F14` |
| `--bg-panel` | `rgba(10,15,20,0.85)` | `rgba(20,22,28,0.95)` | `rgba(15,18,24,0.98)` |
| `--accent-primary` | `#00F5FF` | `#E8EAF0` | `#20FFFF` |
| `--accent-secondary` | `#FF00A0` | `#8090A0` | `#FF20B0` |
| `--accent-warning` | `#FFB300` | `#E8B040` | `#FFBE00` |
| `--text-primary` | `#E8EAF0` | `#E8EAF0` | `#F0F2F8` |
| `--text-secondary` | `#607080` | `#607080` | `#8090A8` |
| `--border-color` | `rgba(0,245,255,0.15)` | `rgba(255,255,255,0.08)` | `rgba(0,245,255,0.2)` |
| `--glow-primary` | `0 0 8px rgba(0,245,255,0.4)` | `none` | `0 0 12px rgba(0,245,255,0.3)` |
| `--glow-secondary` | `0 0 8px rgba(255,0,160,0.4)` | `none` | `none` |
| `--color-up` | `#00C896` | `#40C880` | `#00E0A0` |
| `--color-down` | `#FF3B5C` | `#E04040` | `#FF4060` |

### Atmospheric Tokens
| Token | Description |
|---|---|
| `--grain-opacity` | Noise overlay opacity. Cyberpunk: `0.04`. Minimal/Presentation: `0` |
| `--glitch-enabled` | `1` = glitch transitions active, `0` = disabled |
| `--pulse-intensity` | `0.0–1.0`. Set by WebSocket `tts_amplitude` ticks at ~30Hz |

---

## Typography

**Rule**: No system fonts. No Inter. No Roboto.

| Role | Family | Weights | Usage |
|---|---|---|---|
| Display / headers | `Orbitron` | 400 500 700 900 | Workspace titles, panel IDs, large labels |
| Monospace / data | `JetBrains Mono` | 400 500 | All numbers, terminal output, timestamps, code |
| Body / labels | `Chakra Petch` | 300 400 500 600 | UI labels, descriptions, body text |

All sizes in `rem`. Minimum readable size: `0.6rem` (9.6px).

### Type Scale
| Name | Size | Font | Usage |
|---|---|---|---|
| `display-xl` | `2.5rem` | Orbitron 900 | Score numbers, large metrics |
| `display-lg` | `1.5rem` | Orbitron 700 | Workspace name, major headings |
| `display-sm` | `0.875rem` | Orbitron 500 | Panel titles (uppercase, tracked) |
| `data-lg` | `1.125rem` | JetBrains Mono | Prices, percentages |
| `data-sm` | `0.75rem` | JetBrains Mono | Timestamps, small numbers |
| `label` | `0.8rem` | Chakra Petch 500 | UI labels |
| `body` | `0.875rem` | Chakra Petch 400 | Body text |

---

## Motion

### Glitch Transition (mandatory, CSS-only)
- Trigger: every workspace switch
- Duration: 350ms
- Mechanism: `clip-path` + `filter: hue-rotate() saturate() brightness()` animation chain
- Easing: `steps(4)` — frame-by-frame digital artifact aesthetic
- Controlled by `--glitch-enabled`. When `0`, transition uses a 150ms cross-fade instead.

### Glow-Pulse (mandatory, WebSocket-driven)
- Source: `tts_amplitude` messages at ~30Hz
- Targets: avatar panel border, active panel glow, command input accent
- Mechanism: CSS custom property `--pulse-intensity` (0.0–1.0) set via `element.style.setProperty`
- No React state update — direct DOM write for performance

### Panel Animations
- Slide-up (CommandInput): Framer Motion `y: 40 → 0`, `opacity: 0 → 1`, 150ms, easeOut
- Collapse: `height` CSS transition, 200ms
- Bring-to-front: instant z-index change, no animation

### Timing Reference
| Variable | Value | Usage |
|---|---|---|
| `--transition-fast` | `150ms` | Hover states, opacity |
| `--transition-mid` | `200ms` | Panel collapse, micro-animations |
| `--easing-snap` | `cubic-bezier(0.16, 1, 0.3, 1)` | Spring-like snap feel |
| `--easing-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | Material-like standard |

---

## Panel Anatomy

```
┌─────────────────────────────────────────────────────┐ ← 1px border, --border-color
│ PANEL TITLE                              [−]         │ ← header: 28px, drag surface
├─────────────────────────────────────────────────────┤
│                                                     │
│  content area                                       │ ← flex-1, overflow-hidden
│                                                     │
└─────────────────────────────────────────────────────┘
```

- Background: `--bg-panel` + `backdrop-filter: blur(8px)`
- Border: `1px solid var(--border-color)`
- Box-shadow: `var(--glow-primary)`
- Border-radius: `2px` — sharp, not rounded
- Resize handles: 8px transparent zones at all 4 corners and 4 edges

---

## Grid & Spacing

Base unit: `4px`. All spacing values are multiples of 4.

| Token | Value |
|---|---|
| Panel gap minimum | `8px` |
| Panel header height | `28px` |
| Panel inner padding | `12px` |
| Collapsed icon size | `48×48px` |
| Resize handle size | `8px` |

---

## Aesthetic Rules (for code review)

1. **No white backgrounds** — even in "light" states, minimum brightness is `#111318`
2. **No rounded corners > 2px** on panels — sharp edges only
3. **No box-shadow without glow color** — shadows use `--accent-primary` or `--accent-secondary` as the color
4. **Numbers always in JetBrains Mono** — including prices, timestamps, percentages
5. **Uppercase + letter-spacing for panel titles** — `font-display text-xs tracking-widest uppercase`
6. **Borders at 15% opacity max** — never solid-colored borders
7. **Hover states via opacity** — not color change. Hover = opacity 1.0 on a base of 0.5–0.7
