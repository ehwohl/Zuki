# Bundle 11 — Music-Practice: CONTEXT.md
> Date: 2026-05-16
> Status: Decisions locked — ready for planning

---

## Domain

New workspace delivering real-time pitch detection + visual feedback for vocal and instrument practice.
No LLM calls in the detection loop — detection is browser-side. Python skill only receives note events.

---

## Decisions

### Pitch Detection Layer

**Hybrid model:**
- Browser (Web Audio API + `pitchfinder` or `aubio.js`) detects pitch in real-time (zero latency for visual feedback)
- Browser emits `{ type: "pitch_event", note: "A4", cents: -12, frequency: 440.0 }` over WebSocket to Python
- Python skill receives events, logs session, will score exercises in future bundles
- No raw PCM sent over WebSocket — events only
- No Python audio dependencies (no aubio, no crepe, no portaudio) for Bundle 11

### Learning Mode Target

**Both — Voice + Instrument toggle in the panel**
- Same detection core for both
- Toggle stored in Zustand: `mode: "voice" | "instrument"`
- Different exercise sets and feedback text per mode (exercises deferred to future bundle)
- Bundle 11 ships with free practice only; the toggle is structural scaffolding

### UI — Piano Roll

**Scrolling chromatic piano roll (Canvas or D3, TBD by researcher)**
- Y-axis: piano key layout (MIDI range ~C2–C6 default), label each semitone
- X-axis: time scrolling left (newest on right)
- Free practice: chromatic grid lines at each semitone + live pitch line (cyan glow, additive blending to match CityScene aesthetic)
- Exercise mode (future): target note blocks appear as colored bars; pitch line must pass through them
- Color coding: cyan = within ±10 cents (in tune), amber = ±10–25 cents, magenta/red = >25 cents off

### UI — Panel Layout

Three panels in the Music workspace (Alt+6):
1. **Pitch Roll** (`id="pitch-roll"`) — main full-width panel, scrolling piano roll
2. **Tuner** (`id="tuner"`) — compact panel: current note name large, cents offset number, in-tune indicator glow
3. **Session Log** (`id="session-log"`) — Python-side log of note events; shows recent pitch_event stream

### Exercise Structure

**Free practice only for Bundle 11.**
- Mic always listening when workspace is active
- Piano roll running continuously
- No structured exercises, no scale trainer in this bundle
- Scale trainer deferred to future bundle

### Python Skill

- Location: `workspaces/music/music_skill.py`
- Trigger: `"musik"`, `"music"`, `"music start"`, `"musik start"`
- Handles: `pitch_event` WebSocket messages (store in session buffer), `navigate` to music workspace
- Emits: `music_session_stats` (note count, average cents deviation, time active) — for session log panel
- `tenant_aware = True`
- Uses `APIManager` (not `LLMManager`)

### WebSocket Bridge

New emitter in `ui_bridge.py`:
- `emit_music_session(stats: dict)` → sends `{ type: "music_session_stats", ... }`

### Keyboard Shortcut

- `Alt+6` → Music workspace (consistent with Alt+1–5 pattern)

---

## Canonical Refs

- `REFERENCES.md §10` — UIRenderer ABC + WebSocket bridge pattern
- `REFERENCES.md §14` — Two-stage skill routing (music_skill needs `description` set)
- `REFERENCES.md §18` — HTML as primary output, WebSocket message format
- `ui/src/workspaces/coding/DepGraph.tsx` — D3 pattern already in use (closest analog for pitch roll)
- `ui/src/panels/Panel.tsx` — Panel component (all three new panels use this)
- `ui/src/panels/layout_presets.ts` — add MUSIC workspace preset here
- `ui_bridge.py` — add `emit_music_session` here
- `workspaces/base.py` — base skill class to extend

---

## Deferred Ideas

- Scale trainer (Zuki speaks next note in German, target bars on roll) — future bundle
- Session history / progress tracking across days — future bundle
- Interval training, chord detection — future bundle
- LLM-generated feedback on session performance — future bundle

---

## Code Context (reusable)

| Asset | File | How it applies |
|---|---|---|
| Panel component | `ui/src/panels/Panel.tsx` | Wrap all 3 new panels |
| Workspace pattern | `ui/src/workspaces/coding/index.tsx` | Copy structure: navigate on mount, WSStore for messages |
| D3 usage | `ui/src/workspaces/coding/DepGraph.tsx` | Reference for D3 in React via useEffect + useRef |
| ui_bridge emitters | `ui_bridge.py` | Add `emit_music_session` following existing emit pattern |
| Base skill | `workspaces/base.py` | Extend for `MusicSkill` |
| Layout presets | `ui/src/panels/layout_presets.ts` | Add MUSIC workspace with 3-panel preset |
| App routing | `ui/src/App.tsx` | Add `case 'music'` + Alt+6 shortcut |
