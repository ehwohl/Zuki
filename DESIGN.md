# Zuki-OS — Design System

> Components read tokens. They never hardcode hex values, font names, or animation durations.
> Theme swap = CSS custom property reassignment on `:root`. Zero React re-renders.
> When in doubt: darker, sharper, denser. Legibility is earned, not assumed.

---

## Aesthetic Foundation

**Gothic / Occult High-Tech**

The interface is built around one underlying idea: *hidden systems made legible*. Data flows are not sanitized into friendly charts — they are exposed as graphs of provenance, decision trees, terrain. The visual grammar reflects this:

- **Darkness is the default state**, not a "dark mode". Light is reserved for signal — a glowing node, an active border, a pulsing accent.
- **Borders are traces**, not containers. At 15% opacity, they suggest structure without asserting it.
- **Glitch is intentional disclosure**. The workspace transition tears the frame apart briefly because the system is showing you that it is switching, not hiding it behind a smooth crossfade.
- **Data is always visible**. No loading skeletons with friendly animations. Data either exists or the panel shows a raw status string.
- **Nothing is decorative**. If a visual element does not carry information or reinforce hierarchy, it is removed.

---

## Color Tokens

All tokens are CSS custom properties set on `:root` by `applyTheme()`. Components reference only the token name.

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

### Color Intent

| Color | Hex | Meaning in context |
|---|---|---|
| Void | `#0A0C10` | Base — the absence from which all signal emerges |
| Ether / Cyan | `#00F5FF` | Primary signal — active data, live connections, selected state |
| Blood / Magenta | `#FF00A0` | Secondary signal — warnings, source nodes, secondary attention |
| Ember / Amber | `#FFB300` | Caution, financial data, urgency without alarm |
| Fog | `#607080` | Inactive text — present but not demanding attention |
| Gain | `#00C896` | Positive delta — green without being generic |
| Loss | `#FF3B5C` | Negative delta — red with weight |

### Atmospheric Tokens

| Token | Description |
|---|---|
| `--grain-opacity` | Procedural noise overlay intensity. Cyberpunk: `0.04`. Minimal/Presentation: `0`. Generated at runtime by `lib/noise.ts` via canvas API — no image assets. |
| `--glitch-enabled` | `1` = glitch transitions active (Cyberpunk default). `0` = 150ms cross-fade (Minimal/Presentation). |
| `--pulse-intensity` | `0.0–1.0`. Written directly to `:root` by WebSocket `tts_amplitude` handler at ~30Hz. No React state involved. |

### Theme Usage Guide

| Theme | When |
|---|---|
| `cyberpunk` | Default. Private operator use. Full grain, glitch, glow active. |
| `minimal` | Focused deep-work sessions. Glitch and grain disabled. Glow off. Borders subtler. |
| `presentation` | Client-facing sessions. Higher contrast, no atmospheric effects, Zuki watermark shown. |

---

## Typography

**Rule**: No system fonts. No Inter. No Roboto. No rounded sans-serifs.

The typeface selection reinforces the Gothic/Occult framing:
- `Orbitron` — geometric and angular, like a machined sigil
- `JetBrains Mono` — the language of machines; all data lives here
- `Chakra Petch` — compressed, utilitarian, slightly otherworldly

| Role | Family | Weights | Usage |
|---|---|---|---|
| Display / headers | `Orbitron` | 400 500 700 900 | Workspace titles, panel IDs, score numbers, major labels |
| Monospace / data | `JetBrains Mono` | 400 500 | **Every number, timestamp, price, percentage, terminal output** |
| Body / labels | `Chakra Petch` | 300 400 500 600 | UI labels, descriptions, body text, status strings |

All sizes in `rem`. Minimum readable size: `0.6rem` (9.6px at 16px base).

### Type Scale

| Name | Size | Font | Usage |
|---|---|---|---|
| `display-xl` | `2.5rem` | Orbitron 900 | Large score numbers, dominant metrics |
| `display-lg` | `1.5rem` | Orbitron 700 | Workspace name, primary headings |
| `display-sm` | `0.875rem` | Orbitron 500 | Panel titles — always uppercase + letter-spaced |
| `data-lg` | `1.125rem` | JetBrains Mono | Prices, large percentages, primary data |
| `data-sm` | `0.75rem` | JetBrains Mono | Timestamps, small numbers, deltas |
| `label` | `0.8rem` | Chakra Petch 500 | UI control labels, ticker symbols |
| `body` | `0.875rem` | Chakra Petch 400 | Descriptive text, news headlines |
| `micro` | `0.6rem` | JetBrains Mono | Badge labels, status indicators, panel sub-labels |

---

## Motion

Motion is not decoration. Every animated element either conveys state change or provides spatial grounding.

### Glitch Transition (mandatory, CSS-only)

The workspace switch tears the frame apart and reassembles it. This is the system revealing its mechanical nature.

- **Trigger**: every workspace navigation event
- **Duration**: 350ms
- **Mechanism**: CSS `@keyframes` with `clip-path: inset()`, `filter: hue-rotate() saturate() brightness()`, and `transform: skewX() translateX()`
- **Easing**: `steps(4)` — discrete frame jumps, not a smooth curve
- **No JS animation library involved** — this is a hard constraint
- **Disabled in Minimal/Presentation**: controlled by `--glitch-enabled`. When `0`, a 150ms `opacity` fade plays instead.

### Glow-Pulse (mandatory, WebSocket-driven)

When Zuki speaks, the interface breathes.

- **Source**: `tts_amplitude` WebSocket messages at ~30Hz
- **Targets**: Avatar panel border, active panel box-shadow, command input left-border accent
- **Mechanism**: `document.documentElement.style.setProperty('--pulse-intensity', value)` — direct DOM write, bypasses React entirely
- **CSS**: `box-shadow: 0 0 calc(8px + 16px * var(--pulse-intensity)) rgba(0,245,255, calc(0.3 + 0.5 * var(--pulse-intensity)))`
- **Transition on the property**: `box-shadow 33ms linear` — smooth per-frame interpolation

### Panel Micro-Animations

| Interaction | Animation | Duration |
|---|---|---|
| Command input open | `y: 40 → 0`, `opacity: 0 → 1` (Framer Motion) | 150ms, easeOut |
| Panel collapse | `height` CSS transition | 200ms |
| Bring to front | Instant `z-index` change | 0ms — no animation |
| Collapsed icon hover | `opacity: 0.6 → 1.0` | 150ms |
| Window controls reveal | `opacity: 0 → 1` on root hover | 200ms |

### Timing Reference

| Variable | Value | Usage |
|---|---|---|
| `--transition-fast` | `150ms` | Hover states, opacity reveals |
| `--transition-mid` | `200ms` | Panel collapse, structural changes |
| `--easing-snap` | `cubic-bezier(0.16, 1, 0.3, 1)` | Spring-feel — used for slide-ups |
| `--easing-standard` | `cubic-bezier(0.4, 0, 0.2, 1)` | Standard easing — used for collapses |

---

## Panel Anatomy

Every panel in Zuki-OS shares the same structural contract. Content is injected — the shell never changes.

```
┌─────────────────────────────────────────────────────┐  ← 1px border, --border-color (15% opacity)
│ PANEL TITLE                              [−]         │  ← header 28px tall, drag surface, Orbitron 0.6rem
├─────────────────────────────────────────────────────┤  ← 1px border, --border-color
│                                                     │
│  content area (flex-1, overflow: hidden)            │
│                                                     │
└─────────────────────────────────────────────────────┘

Resize handles: 8px transparent zones at N, S, E, W edges + NE, NW, SE, SW corners
Collapsed state: 48×48px icon showing first 2 chars of title, same panel-glass style
```

| Property | Value |
|---|---|
| Background | `var(--bg-panel)` + `backdrop-filter: blur(8px)` |
| Border | `1px solid var(--border-color)` |
| Box-shadow | `var(--glow-primary)` |
| Border-radius | `2px` — sharp corners, not rounded |
| Header height | `28px` |
| Inner content padding | `12px` (overrideable per panel via `noPad` prop) |

### Z-Index Layers

| Layer | Z-Index | Contents |
|---|---|---|
| Workspace content | 5–6 | Workspace-specific panels |
| Persistent panels | 10 | Avatar, Neural Map (always on top of content) |
| Active panel (dragging) | `maxZ + 1` | Whichever panel was last touched |
| Command input | 1001 | Floating command palette |
| Grain overlay | 9996 | Noise texture |
| Glitch overlay | 9995 | Transition effect |
| Window controls | 9999 | Close/minimize buttons |

---

## Grid & Spacing

Base unit: `4px`. All margin, padding, and gap values are multiples of 4.

| Token | Value | Notes |
|---|---|---|
| Panel gap minimum | `8px` | Panels may overlap — this is the visual minimum when side-by-side |
| Panel header height | `28px` | Fixed — never adjusted per panel |
| Panel inner padding | `12px` | Default. Panels with canvas/graph content use `noPad` |
| Collapsed icon size | `48×48px` | |
| Resize handle zone | `8px` | Transparent — overlaps panel border |
| Window control button | `20×20px` | |

---

## Aesthetic Enforcement Rules

These are hard rules, not preferences. Apply them in every code review.

1. **No white or near-white backgrounds.** The darkest acceptable background value is `#111318`. There is no light mode.

2. **No border-radius above 2px on panels or containers.** Sharp edges only. `rounded-sm` (2px) is the ceiling.

3. **No box-shadow without a glow color.** Shadows use `--accent-primary` or `--accent-secondary` as the shadow color, at opacity. Black drop-shadows are forbidden.

4. **Every number, price, timestamp, percentage, and delta must use JetBrains Mono.** This is non-negotiable. `Chakra Petch` is for words, not data.

5. **Panel titles are always: uppercase + `tracking-widest` + Orbitron.** Not title-case. Not sentence-case. All caps.

6. **Borders are always semi-transparent.** Maximum opacity: 20% (`rgba(..., 0.2)`). Solid-color borders are never used.

7. **Hover states change opacity, not color.** A resting element at `opacity: 0.5` becomes `opacity: 1.0` on hover. Color does not shift.

8. **No loading spinners.** Raw text status strings only: `LOADING AVATAR…`, `Waiting for metrics stream…`. No animated SVG loaders.

9. **No placeholder illustrations.** Empty or future panels show a minimal wireframe icon and a status string. No friendly empty-state graphics.

10. **Grain and glow are part of the render budget.** They are not optional in the Cyberpunk theme. Removing them to "clean things up" is a design regression.
