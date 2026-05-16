# Phase 11: Music-Practice — Research

**Researched:** 2026-05-16
**Domain:** Web Audio API / pitch detection / Canvas 2D / Python skill routing
**Confidence:** HIGH (stack verified via npm registry + MDN + codebase scan)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Pitch Detection Layer — Hybrid model:**
- Browser (Web Audio API + `pitchfinder` or `aubio.js`) detects pitch in real-time
- Browser emits `{ type: "pitch_event", note: "A4", cents: -12, frequency: 440.0 }` over WebSocket
- Python skill receives events, logs session, will score exercises in future bundles
- No raw PCM over WebSocket — events only
- No Python audio dependencies (no aubio, no crepe, no portaudio) for Bundle 11

**Learning Mode Target — Both voice and instrument:**
- Same detection core for both
- Toggle stored in Zustand: `mode: "voice" | "instrument"`
- Different exercise sets and feedback text per mode (deferred to future bundle)
- Bundle 11: free practice only; toggle is structural scaffolding

**UI — Piano Roll:**
- Scrolling chromatic piano roll (Canvas or D3, TBD by researcher — see recommendation below)
- Y-axis: piano key layout (MIDI range ~C2–C6 default), label each semitone
- X-axis: time scrolling left (newest on right)
- Color: cyan = ±10 cents (in tune), amber = ±10–25 cents, magenta/red = >25 cents off
- Cyan glow with additive blending to match CityScene aesthetic

**UI — Panel Layout (Alt+6):**
- `id="pitch-roll"` — main full-width panel, scrolling piano roll
- `id="tuner"` — compact: current note name large, cents offset, in-tune indicator glow
- `id="session-log"` — Python-side log of note events; recent pitch_event stream

**Exercise Structure:**
- Free practice only for Bundle 11
- Mic always listening when workspace active
- No structured exercises, no scale trainer

**Python Skill:**
- Location: `workspaces/music/music_skill.py`
- Triggers: `"musik"`, `"music"`, `"music start"`, `"musik start"`
- Handles: `pitch_event` WebSocket messages, `navigate` to music workspace
- Emits: `music_session_stats` (note count, avg cents deviation, time active)
- `tenant_aware = True`
- Uses `APIManager` (not `LLMManager`)

**WebSocket Bridge:**
- New emitter: `emit_music_session(stats: dict)` → sends `{ type: "music_session_stats", ... }`

**Keyboard Shortcut:** Alt+6 → Music workspace

### Claude's Discretion
- Canvas 2D vs D3 for piano roll (researcher decides — see § Piano Roll below)

### Deferred Ideas (OUT OF SCOPE)
- Scale trainer (Zuki speaks next note in German, target bars on roll)
- Session history / progress tracking across days
- Interval training, chord detection
- LLM-generated feedback on session performance
</user_constraints>

---

## Summary

Bundle 11 adds a Music-Practice workspace to Zuki-OS with three panels: a scrolling chromatic piano roll, a compact real-time tuner, and a session log. The architecture splits cleanly: the browser handles all audio processing (zero-latency visual feedback), and Python receives note events for session bookkeeping.

The pitch detection stack is `pitchfinder` (npm, version 2.3.4, last updated December 2025) running inside an `AudioWorklet` processor — the modern replacement for the deprecated `ScriptProcessorNode`. The piano roll is Canvas 2D (not D3); D3 adds no value for pixel-level scrolling and carries DOM overhead that prevents 60fps at 128 semitones. The Python skill is minimal: it receives pitch events, buffers the session, and emits stats.

**Primary recommendation:** `pitchfinder` (YIN algorithm) + AudioWorklet + Canvas 2D requestAnimationFrame loop. This combination is proven, bundle-size acceptable (~229 KB unpacked, tree-shakeable to one algorithm), and slots cleanly into the existing Vite + React + WebSocket architecture.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Mic capture + pitch detection | Browser (Web Audio API) | — | Zero-latency requirement; no PCM over WS |
| Piano roll rendering | Browser (Canvas 2D) | — | 60fps pixel-level draw; DOM would choke |
| Real-time tuner display | Browser (React state) | — | Derived from pitch detection output |
| Session buffering + stats | Python (MusicSkill) | — | Persistence, future scoring |
| Workspace routing (Alt+6) | Browser (Zustand + App.tsx) | Python (navigate event) | Matches existing pattern |
| WebSocket event relay | Browser → Python | Python → Browser (stats) | Events-only, no raw PCM |

---

## Recommended Library Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pitchfinder` | 2.3.4 | Browser pitch detection (YIN/AMDF/Mcleod) | Operates on Float32Array directly; no WASM; tree-shakeable; last updated Dec 2025 [VERIFIED: npm registry] |
| Web Audio API (built-in) | — | `getUserMedia` → `AudioContext` → `AudioWorklet` | Native browser API; no install needed [CITED: developer.mozilla.org] |
| Canvas 2D API (built-in) | — | Piano roll 60fps scrolling render | Pixel-level GPU-accelerated draw; bypass DOM [CITED: developer.mozilla.org] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `requestAnimationFrame` (built-in) | — | Canvas animation loop | Sync to display refresh; cancel on unmount |
| Zustand (already installed) | 4.5.4 | `mode`, `isListening`, `currentNote` state | Use existing store pattern, add `music.store.ts` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pitchfinder` (YIN) | `aubio.js` WASM | aubio npm package last updated 2022 — stale, no active maintenance [VERIFIED: npm registry 2022-06-13]; not recommended |
| `pitchfinder` (YIN) | `ml5.js` PitchDetection | ml5 1.3.1 (Nov 2025) is maintained but pulls TensorFlow.js (~2.5 MB gzipped) — excessive for tuner use case [VERIFIED: npm registry] |
| Canvas 2D | D3.js SVG | D3 SVG DOM manipulation caps at ~30fps for 128+ moving elements; Canvas 2D suitable for this pixel-level case [CITED: web.dev/articles/canvas-performance] |
| AudioWorklet | ScriptProcessorNode | ScriptProcessorNode is deprecated; runs on main thread causing jank; AudioWorklet runs in audio thread [CITED: developer.mozilla.org/en-US/docs/Web/API/ScriptProcessorNode] |

**Installation (one new package):**
```bash
cd ui && npm install pitchfinder
```
```bash
npm view pitchfinder version   # verified: 2.3.4 (2025-12-16)
```

---

## Pitch Detection Setup (Web Audio API)

### Signal Flow

```
getUserMedia({ audio: true })
  └─> MediaStream
        └─> AudioContext.createMediaStreamSource(stream)
              └─> AudioWorkletNode("pitch-processor")
                    └─> port.onmessage → { frequency, note, midi, cents, confidence }
                          └─> React state → Zustand → Canvas / Tuner panel
                                └─> bridge.send("pitch_event", payload) → Python
```

### AudioWorklet Approach (preferred over ScriptProcessorNode)

**Why AudioWorklet:** ScriptProcessorNode is deprecated per the W3C specification and runs on the main thread, causing audio glitching and UI jank. AudioWorklet runs in the dedicated audio rendering thread. [CITED: developer.mozilla.org/en-US/docs/Web/API/ScriptProcessorNode]

**Vite integration pattern for AudioWorklet module:**

The safest pattern for Vite is placing the worklet processor file in `ui/public/` and referencing it by path. The `?url` import suffix in Vite has a known bug where TypeScript files are not transpiled before being passed to `addModule()`. [VERIFIED: github.com/vitejs/vite/issues/9952]

```
ui/public/pitch-processor.js   ← plain JS, no TypeScript, referenced by path
```

```javascript
// pitch-processor.js (in ui/public/)
// pitchfinder cannot be imported inside AudioWorkletGlobalScope directly
// (no import support in worklet scope without bundling)
// Solution: implement ACF (autocorrelation) inline, OR use postMessage
// to send Float32Array chunks back to main thread for pitchfinder to process.

class PitchProcessor extends AudioWorkletProcessor {
  constructor() { super() }
  process(inputs) {
    const channel = inputs[0]?.[0]
    if (channel?.length) {
      // Send 128-sample block to main thread for pitchfinder
      this.port.postMessage(channel.slice())
    }
    return true
  }
}
registerProcessor('pitch-processor', PitchProcessor)
```

**IMPORTANT: pitchfinder cannot be imported inside AudioWorkletGlobalScope.** AudioWorklet runs in a separate global scope without `import` support (unless you bundle the worklet — complex with Vite). The simplest correct pattern: send `Float32Array` chunks via `port.postMessage` back to the main thread, accumulate into a larger buffer (1024–4096 samples), then run pitchfinder on the main thread in the `port.onmessage` handler. This introduces ~1–3 frame latency (negligible for a tuner). [ASSUMED — based on Web Audio API module scope restrictions; verify with a minimal prototype]

**Alternative (if postMessage overhead is unacceptable):** Inline ACF (autocorrelation) implementation in the worklet itself without importing pitchfinder — simple autocorrelation is ~30 lines of plain JS and sufficient for tuner accuracy.

### React Hook Pattern

```typescript
// usePitchDetector.ts (pseudocode pattern)
export function usePitchDetector(onPitch: (event: PitchEvent) => void) {
  const streamRef = useRef<MediaStream | null>(null)
  const ctxRef    = useRef<AudioContext | null>(null)
  const nodeRef   = useRef<AudioWorkletNode | null>(null)

  useEffect(() => {
    let active = true
    async function start() {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (!active) { stream.getTracks().forEach(t => t.stop()); return }
      const ctx = new AudioContext()
      await ctx.audioWorklet.addModule('/pitch-processor.js')
      const src  = ctx.createMediaStreamSource(stream)
      const node = new AudioWorkletNode(ctx, 'pitch-processor')
      // Accumulate 128-sample blocks → detect pitch on main thread
      let buf: Float32Array[] = []
      node.port.onmessage = (e) => {
        buf.push(e.data)
        if (buf.length >= 16) { // ~1024 samples at 48kHz = ~21ms window
          const merged = mergeBuffers(buf)
          buf = []
          const freq = detectPitch(merged)  // pitchfinder YIN
          if (freq) onPitch(toNoteEvent(freq))
        }
      }
      src.connect(node)
      // Do NOT connect node to ctx.destination — we only analyze, not play back
      streamRef.current = stream
      ctxRef.current    = ctx
      nodeRef.current   = node
    }
    start().catch(console.error)
    return () => {
      active = false
      nodeRef.current?.disconnect()
      streamRef.current?.getTracks().forEach(t => t.stop())
      ctxRef.current?.close()
    }
  }, [])
}
```

**Key cleanup rules:**
1. `stream.getTracks().forEach(t => t.stop())` — releases mic indicator in browser tab
2. `ctx.close()` — releases system audio resources
3. Check `active` flag before async setup completes to handle strict-mode double-effect

### Pitch-to-Note Conversion (no extra library needed)

```typescript
// Verified formulas [CITED: musicdsp.org, subsynth.sourceforge.net]
function freqToMidi(freq: number): number {
  return Math.round(12 * Math.log2(freq / 440) + 69)
}
function midiToFreq(midi: number): number {
  return 440 * Math.pow(2, (midi - 69) / 12)
}
function freqToCents(freq: number, refFreq: number): number {
  return 1200 * Math.log2(freq / refFreq)
}
const NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
function midiToName(midi: number): string {
  return NOTE_NAMES[midi % 12] + Math.floor(midi / 12 - 1)
}
```

### Permission Handling

Browser requires user gesture before `AudioContext` can resume and before `getUserMedia` is granted. The workspace activation (Alt+6 or click) counts as a user gesture. No special extra prompts needed — wrap the `start()` call in the workspace mount `useEffect`, which fires after user navigation. [CITED: developer.mozilla.org/en-US/docs/Web/API/AudioContext]

---

## Piano Roll Implementation

### Decision: Canvas 2D (not D3)

**Reason:** The piano roll requires per-pixel scrolling of ~128 rows at 60fps. D3 binds data to SVG/DOM nodes; each update re-renders DOM elements. At 128 semitones × time dimension, D3 SVG creates hundreds of elements that must be repositioned per frame — this saturates the layout engine before reaching 60fps on most machines. Canvas 2D draws directly to a pixel buffer; with `requestAnimationFrame` and `ctx.drawImage` shifting the existing buffer, each frame costs a single `ctx.drawImage` call + one new column of pixels — negligible GPU cost. [CITED: web.dev/articles/canvas-performance]

D3 is already used in `DepGraph.tsx` for a force-directed graph (irregular updates, sparse nodes) — appropriate there. Piano roll is continuous 60fps animation — Canvas is the right tool. This matches the CONTEXT.md "Canvas or D3, TBD by researcher" discretion.

### Render Architecture

```
canvasRef (useRef<HTMLCanvasElement>)
  ├─ offscreen canvas (static grid — redrawn only on resize)
  └─ main canvas (animated — draws grid from offscreen, then pitch trail)

requestAnimationFrame loop:
  1. drawImage(offscreenCanvas) → paste static grid (semitone lines, octave labels)
  2. Shift existing pitch data left by N pixels (ctx.drawImage self-shift)
  3. Paint new rightmost column based on latest detected note + color
  4. Draw active pitch line (horizontal glow)
```

**Offscreen grid pattern** from `DepGraph.tsx` analogy — read CSS tokens at init via `getComputedStyle`, repaint grid on theme change via `MutationObserver` on `data-theme`. [VERIFIED: codebase — DepGraph.tsx uses identical readTokens() pattern]

### Y-Axis Layout

- MIDI 36 (C2) to MIDI 84 (C6) = 49 semitones (default visible range)
- Each semitone row height: `canvasHeight / visibleSemitones` (typically 6–12px)
- White keys: slightly lighter background, Black keys: darker strip
- Label C notes only (C2, C3, C4 = middle C, C5, C6) — consistent with real piano layout

### Color Coding (from CONTEXT.md — locked)

```typescript
function pitchColor(cents: number): string {
  const abs = Math.abs(cents)
  if (abs <= 10)  return 'rgba(0,255,255,0.9)'   // cyan  — in tune
  if (abs <= 25)  return 'rgba(255,176,0,0.9)'   // amber — close
  return             'rgba(255,0,128,0.9)'         // magenta — off
}
// Glow effect via ctx.shadowColor + ctx.shadowBlur (additive feel)
```

### React Integration Pattern

Identical to `DepGraph.tsx` — `useRef<HTMLCanvasElement>` + `useEffect` for data changes + `ResizeObserver` for container size changes. No React state updates during animation loop — only `useRef` for the animation frame ID.

```tsx
// PitchRollPanel.tsx
const canvasRef = useRef<HTMLCanvasElement>(null)
const rafRef    = useRef<number>(0)
const pitchBuf  = useRef<PitchSample[]>([])  // ring buffer, not React state

useEffect(() => {
  // start rAF loop
  function frame() {
    drawFrame(canvasRef.current!, pitchBuf.current)
    rafRef.current = requestAnimationFrame(frame)
  }
  rafRef.current = requestAnimationFrame(frame)
  return () => cancelAnimationFrame(rafRef.current)
}, [])

// When new pitch arrives (from usePitchDetector):
// DO NOT setStateState() — push to pitchBuf.current directly
pitchBuf.current.push(sample)
```

**No React state in hot path.** State updates trigger re-renders which block the frame budget. Pitch data flows: `pitchBuf.current` (ref) → read by rAF loop. Only the Tuner panel (large note name + cents number) uses React state — it updates at ~5–10Hz which is fine for DOM.

---

## WebSocket Event Design

### Browser → Python: `pitch_event`

```typescript
// Sent from browser when pitch is detected
interface PitchEvent {
  type: "pitch_event"
  note: string       // e.g. "A4" — note name + octave
  midi: number       // 0–127, e.g. 69 for A4
  frequency: number  // Hz, e.g. 440.0
  cents: number      // offset from nearest note, e.g. -12
  confidence: number // 0.0–1.0 (set to 1.0 if pitchfinder gives no confidence)
  ts: number         // Date.now() milliseconds
}
```

**What Python actually needs:**
- `note` + `midi`: for session log display and future exercise scoring
- `cents`: for average deviation stats
- `ts`: for time-active calculation (session duration)
- `frequency` + `confidence`: useful for future scoring; include now, cost is negligible

**Throttle before sending:** Browser detects pitch at ~30–60Hz (one per rAF). Python does not need every frame — throttle WebSocket sends to ~5Hz (every 200ms) or only on note change. This keeps the WS channel uncluttered and Python's event loop un-flooded. [ASSUMED — 5Hz is a reasonable default; can be made configurable]

```typescript
// Throttle pattern in usePitchDetector:
const lastSend = useRef(0)
// Inside onPitch callback:
const now = Date.now()
if (now - lastSend.current > 200) {
  bridge.send('pitch_event', pitchPayload)
  lastSend.current = now
}
```

**Handling in ui_bridge.py:** The `pitch_event` type is not currently in `_handle_message`. It needs to be routed to `MusicSkill.handle_pitch_event()` — see Python Skill section.

### Python → Browser: `music_session_stats`

```python
# Emitted by emit_music_session() in ui_bridge.py
{
  "type": "music_session_stats",
  "note_count": 142,
  "avg_cents_deviation": 8.3,
  "time_active_seconds": 47,
  "last_note": "A4",
  "session_started": "2026-05-16T14:23:00"
}
```

**Browser consumer:** `MusicWorkspace` listens on `lastMessage` for `music_session_stats` type (identical to `coding_output` / `coding_dep_graph` pattern in `CodingWorkspace/index.tsx`).

---

## Python Skill Structure

### File: `workspaces/music/music_skill.py`

Extends `Skill` from `workspaces/base.py`. Follows exact pattern of `CodingSkill`.

```python
import logging
import threading
import time
from datetime import datetime
from collections import deque

import ui_bridge
from workspaces.base import Skill

log = logging.getLogger("music.skill")

class MusicSkill(Skill):
    name        = "music"
    triggers    = {"musik", "music", "music start", "musik start"}
    description = (
        "Music practice workspace: real-time pitch detection with piano roll. "
        "Handles voice and instrument practice sessions."
    )
    tenant_aware = True

    def __init__(self) -> None:
        self._session_start: datetime | None = None
        self._note_count: int = 0
        self._cents_sum: float = 0.0
        self._last_note: str = ""
        self._lock = threading.Lock()

    def handle(self, context: dict) -> str | None:
        cmd = context.get("cmd", "").strip()
        # Handle pitch_event WebSocket messages (dispatched via _handle_pitch_event)
        if cmd == "_pitch_event":
            return self._handle_pitch_event(context)
        # Navigate to music workspace
        ui_bridge.emit_workspace_change("music")
        return "Musikpraktice-Bereich geöffnet."

    def _handle_pitch_event(self, context: dict) -> None:
        data = context.get("data", {})
        with self._lock:
            if self._session_start is None:
                self._session_start = datetime.utcnow()
            self._note_count += 1
            self._cents_sum += abs(data.get("cents", 0))
            self._last_note = data.get("note", "")
        self._emit_stats()

    def _emit_stats(self) -> None:
        with self._lock:
            elapsed = (
                (datetime.utcnow() - self._session_start).seconds
                if self._session_start else 0
            )
            avg = self._cents_sum / self._note_count if self._note_count else 0.0
            ui_bridge.emit_music_session(
                note_count=self._note_count,
                avg_cents_deviation=round(avg, 1),
                time_active_seconds=elapsed,
                last_note=self._last_note,
                session_started=self._session_start.isoformat() if self._session_start else "",
            )
```

### Routing `pitch_event` from WebSocket to MusicSkill

**Problem:** `_handle_message` in `ui_bridge.py` currently handles `"command"` and `"navigate"` types. `pitch_event` is a new message type that must reach `MusicSkill` without going through the terminal command parser.

**Solution:** Add a dedicated `pitch_event_handler` callback to the bridge (analogous to `command_handler`):

```python
# In ui_bridge.py — add alongside _command_handler:
_pitch_event_handler: Any = None

def set_pitch_event_handler(handler) -> None:
    global _pitch_event_handler
    _pitch_event_handler = handler

# In _handle_message — add new elif branch:
elif msg_type == "pitch_event":
    if _pitch_event_handler:
        asyncio.get_event_loop().run_in_executor(
            None, _pitch_event_handler, msg
        )
```

Then in `main.py` (at bridge startup):
```python
ui_bridge.set_pitch_event_handler(music_skill.handle_pitch_event)
```

**Alternative (simpler):** Dispatch `pitch_event` through the existing `_command_handler` with a synthetic command string like `"_pitch_event"` and the event data in a context key. This avoids adding a second callback to ui_bridge.py. **Recommended for Bundle 11** — minimal bridge changes.

### New emitter in `ui_bridge.py`

```python
def emit_music_session(
    note_count: int,
    avg_cents_deviation: float,
    time_active_seconds: int,
    last_note: str,
    session_started: str,
) -> None:
    emit(
        "music_session_stats",
        note_count=note_count,
        avg_cents_deviation=avg_cents_deviation,
        time_active_seconds=time_active_seconds,
        last_note=last_note,
        session_started=session_started,
    )
```

### `workspaces/music/__init__.py`

Empty file required for Python package discovery by `skill_registry.discover_skills()`.

---

## Existing Patterns (from codebase scan)

### Workspace Routing (App.tsx + PanelManager.tsx)

**Current state:** `WorkspaceId` type is `'broker' | 'business' | 'coding' | 'os' | 'office'` — union literal in `workspace.store.ts` line 4. `WORKSPACE_PANELS` in `PanelManager.tsx` is a plain `Record<string, React.ComponentType>`. `NEURAL_MAP_MODES` in `workspace.store.ts` maps each workspace to a neural map mode. [VERIFIED: codebase]

**Changes needed:**
1. `workspace.store.ts`: Add `'music'` to `WorkspaceId` union and `NEURAL_MAP_MODES`
2. `PanelManager.tsx`: Add lazy import for `MusicWorkspace` and entry in `WORKSPACE_PANELS`
3. `App.tsx`: Add `if (e.altKey && e.key === '6') navigate('music')` — next number after `'5'`
4. `layout.store.ts` line 27: Add `'music'` to `ALL_WORKSPACES` array (controls localStorage cleanup)
5. `layout_presets.ts`: Add `music` key to the presets `Record`
6. `LAYOUT_VERSION` bump: adding a new workspace changes geometry expectations — bump `LAYOUT_VERSION` from `2` to `3` to force preset reset for all users

### Panel Component (`Panel.tsx`)

Accepts `id`, `title`, `children`, `className`, `headerExtra`, `noPad` props. Reads position/size from `useLayoutStore` keyed by `id`. All three new panels wrap `<Panel id="pitch-roll">`, `<Panel id="tuner">`, `<Panel id="session-log">`. [VERIFIED: codebase]

### Layout Presets (`layout_presets.ts`)

`preset()` function uses screen dimensions to compute geometry. Shared constants: `AVATAR`, `NEURAL`, `TERMINAL`, `CX`, `CW`, `RX`, `RW`. New `music` key adds three panels in the same zone as coding/office. [VERIFIED: codebase]

Recommended music preset geometry:
- `pitch-roll`: full centre column (`x: CX, y: 16, w: CW, h: SAFE - 16`) — main viz
- `tuner`: right column upper (`x: RX, y: NY, w: RW, h: ~160`) — compact note display
- `session-log`: right column lower (`x: RX, y: NY + 168, w: RW, h: RH - 168`) — event stream

### WebSocket Store (`ws.store.ts` + `bridge/ws.ts`)

`useWSStore` exposes `lastMessage` (the most recent parsed JSON message). Workspace components subscribe via `useEffect(() => { if (lastMessage?.type === 'music_session_stats') { ... } }, [lastMessage])`. [VERIFIED: codebase — CodingWorkspace pattern]

`bridge.send(type, payload)` sends from browser to Python. For `pitch_event`: `bridge.send('pitch_event', { note, midi, frequency, cents, confidence, ts })`. [VERIFIED: codebase — ws.ts send() method]

`_handle_message` in `ui_bridge.py` needs a new `elif msg_type == "pitch_event":` branch. [VERIFIED: codebase — ui_bridge.py lines 189–213]

### D3 Pattern Reference (`DepGraph.tsx`)

- `useRef<SVGSVGElement>` + `useEffect` for full rebuild on data change
- `ResizeObserver` for container resize — update SVG dimensions + nudge simulation
- `MutationObserver` on `data-theme` attribute for theme-aware color updates via `readTokens()`
- Cleanup: `sim.stop()` in `useEffect` return function

The Canvas 2D piano roll follows the same three-effect structure: `useEffect` for initial setup + rAF loop, `ResizeObserver` for canvas resize, `MutationObserver` for theme token refresh. [VERIFIED: codebase]

### Skill Discovery

`skill_registry.discover_skills()` finds skills by scanning `workspaces/*/` for classes inheriting `Skill`. Requires non-empty `__init__.py` in `workspaces/music/`. `CodingSkill` sets `tenant_aware = False` (utility); `MusicSkill` must set `tenant_aware = True` (processes session data per tenant). [VERIFIED: codebase — base.py, coding_skill.py]

---

## Implementation Risks

### Risk 1: AudioWorklet module scope — pitchfinder import failure

**What goes wrong:** `import * as Pitchfinder from 'pitchfinder'` inside an AudioWorkletProcessor file will fail silently at runtime because AudioWorkletGlobalScope does not support ES module imports without bundler integration.

**Why it happens:** Vite does not bundle files referenced via `audioWorklet.addModule(path)` the same way it bundles main app files. Files in `public/` are served as-is.

**How to avoid:** Use the postMessage pattern (send raw Float32Array chunks from worklet → main thread → run pitchfinder on main thread). OR inline a minimal autocorrelation function in the worklet file (no imports needed). Do not attempt to `import pitchfinder` inside the worklet.

**Warning signs:** `Failed to load module script` in browser console; detector never fires.

### Risk 2: AudioContext requires user gesture

**What goes wrong:** `new AudioContext()` created at module load time (outside a user interaction handler) enters `suspended` state automatically in Chrome/Firefox. `getUserMedia` also requires user interaction.

**How to avoid:** Create `AudioContext` inside the effect that runs on workspace mount — which is always triggered by user navigation (Alt+6 or click). Never instantiate at module top level.

**Warning signs:** `AudioContext.state === "suspended"` in DevTools; no pitch events emitted.

### Risk 3: React strict-mode double-effect mic leak

**What goes wrong:** In development with `React.StrictMode`, `useEffect` runs twice (mount → unmount → mount). If the cleanup function does not stop tracks, two mic streams are opened.

**How to avoid:** Use the `active` flag pattern (see usePitchDetector pseudocode above). Always call `stream.getTracks().forEach(t => t.stop())` in cleanup.

**Warning signs:** Browser tab shows mic indicator even after navigating away from Music workspace.

### Risk 4: Canvas resolution blurriness on HiDPI / OLED target

**What goes wrong:** The project targets a 49" Odyssey OLED G9 (likely HiDPI). Canvas set to CSS pixels without accounting for `devicePixelRatio` will appear blurry.

**How to avoid:**
```typescript
const dpr = window.devicePixelRatio || 1
canvas.width  = cssWidth  * dpr
canvas.height = cssHeight * dpr
ctx.scale(dpr, dpr)
canvas.style.width  = cssWidth  + 'px'
canvas.style.height = cssHeight + 'px'
```

**Warning signs:** Piano roll lines appear soft/blurry at 1:1 scale.

### Risk 5: `pitch_event` flooding the WebSocket

**What goes wrong:** If pitch events are emitted on every rAF tick (60Hz), the WS channel receives ~3,600 messages/minute. Python's asyncio event loop processes each in a thread-pool executor — this degrades terminal responsiveness.

**How to avoid:** Throttle `bridge.send('pitch_event', ...)` to ≤5Hz (200ms interval). Implement in `usePitchDetector` hook, not in the detection callback. Detection frequency (30–60Hz) stays high for visual smoothness; WS send frequency is decoupled.

### Risk 6: WorkspaceId type mismatch

**What goes wrong:** `WorkspaceId` in `workspace.store.ts` is a TypeScript union literal. `PanelManager.tsx` uses `WorkspaceContent = WORKSPACE_PANELS[active]` where active is typed as `WorkspaceId`. Adding `'music'` as a string not in the union causes TypeScript type errors.

**How to avoid:** Add `'music'` to the `WorkspaceId` union in `workspace.store.ts` before adding any other music workspace code. This is the first change to make.

### Risk 7: LAYOUT_VERSION bump wipes user-saved panel positions

**What goes wrong:** Adding `'music'` to `ALL_WORKSPACES` and bumping `LAYOUT_VERSION` causes `loadFromStorage` to call `localStorage.removeItem` for all workspaces, wiping user-customized panel positions.

**Why acceptable:** This is a dev-phase project (single user, Zuki's owner). The CONTEXT.md layout is the authoritative default. Bumping the version is the correct approach per the existing `LAYOUT_VERSION` mechanism. [VERIFIED: codebase — layout.store.ts lines 52–57]

---

## Sources

### Primary (HIGH confidence)
- npm registry: `pitchfinder@2.3.4` — version, description, size, last-modified date [VERIFIED]
- npm registry: `aubio@0.1.0` (2022-06-13) — confirmed stale [VERIFIED]
- npm registry: `ml5@1.3.1` — confirmed active but oversized [VERIFIED]
- `d:\Zuki\ui_bridge.py` — _handle_message dispatch, emit pattern, all existing emitters [VERIFIED]
- `d:\Zuki\ui\src\panels\Panel.tsx` — Panel props interface, drag/resize pattern [VERIFIED]
- `d:\Zuki\ui\src\panels\layout_presets.ts` — preset() geometry, LAYOUT_VERSION [VERIFIED]
- `d:\Zuki\ui\src\panels\PanelManager.tsx` — WORKSPACE_PANELS, lazy imports [VERIFIED]
- `d:\Zuki\ui\src\App.tsx` — Alt+1–5 shortcut pattern [VERIFIED]
- `d:\Zuki\ui\src\bridge\ws.ts` — bridge.send(), dispatch(), message routing [VERIFIED]
- `d:\Zuki\ui\src\store\workspace.store.ts` — WorkspaceId union, NEURAL_MAP_MODES [VERIFIED]
- `d:\Zuki\ui\src\store\layout.store.ts` — ALL_WORKSPACES, loadFromStorage [VERIFIED]
- `d:\Zuki\ui\src\workspaces\coding\DepGraph.tsx` — D3/Canvas integration pattern [VERIFIED]
- `d:\Zuki\ui\src\workspaces\coding\index.tsx` — workspace component pattern [VERIFIED]
- `d:\Zuki\workspaces\base.py` — Skill ABC [VERIFIED]
- `d:\Zuki\workspaces\coding\coding_skill.py` — skill structure to follow [VERIFIED]

### Secondary (MEDIUM confidence)
- [MDN: AudioWorklet](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Using_AudioWorklet) — postMessage pattern, block size 128 samples
- [MDN: ScriptProcessorNode](https://developer.mozilla.org/en-US/docs/Web/API/ScriptProcessorNode) — deprecated status confirmed
- [MDN: AudioContext.close()](https://developer.mozilla.org/en-US/docs/Web/API/AudioContext/close) — cleanup requirement
- [web.dev: canvas-performance](https://web.dev/articles/canvas-performance) — Canvas 2D vs DOM performance
- [peterkhayes/pitchfinder GitHub](https://github.com/peterkhayes/pitchfinder) — algorithm details, Float32Array API
- [musicdsp.org MIDI conversion](https://www.musicdsp.org/en/latest/Other/125-midi-note-frequency-conversion.html) — frequency/MIDI/cents formulas

### Tertiary (LOW confidence)
- AudioWorklet + Vite `?url` import bug (github.com/vitejs/vite/issues/9952) — public/ folder workaround recommended

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | AudioWorklet postMessage pattern avoids pitchfinder import scope issue | Pitch Detection Setup | If wrong: need inline ACF or bundled worklet — more build complexity |
| A2 | 5Hz WS throttle for pitch_event is sufficient for Python session stats | WebSocket Event Design | If too low: coarser stats; if too high: WS flood — easily tunable |
| A3 | `skill_registry.discover_skills()` finds skills in `workspaces/music/` subdirectory | Python Skill Structure | If wrong: need manual registration in main.py |

---

## Open Questions (RESOLVED)

1. **Does skill_registry auto-discover subdirectory skills?**
   - What we know: `CodingSkill` is in `workspaces/coding/coding_skill.py` — already a subdirectory. Registry does discover it.
   - What's unclear: Exact glob pattern used by `discover_skills()` — not read during this research.
   - Recommendation: Read `core/skill_registry.py` at plan time to confirm `workspaces/*/` glob depth.
   - **RESOLVED:** CodingSkill in `workspaces/coding/` is already discovered — `pkgutil.walk_packages` in `registry.py` scans recursively. An empty `workspaces/music/__init__.py` is sufficient. No manual registration needed.

2. **Routing pitch_event to MusicSkill — which approach?**
   - Option A: Add `_pitch_event_handler` callback to `ui_bridge.py` (clean separation)
   - Option B: Route through existing `_command_handler` with synthetic `"_pitch_event"` command
   - Recommendation: Option B for Bundle 11 (zero bridge API changes); Option A is cleaner for Bundle 12+.
   - **RESOLVED:** Option A chosen — separate `_pitch_event_handler` callback in `ui_bridge.py`. Reason: pitch events are not user commands and should not enter the command routing path.

3. **AudioWorklet vs accumulated buffer size**
   - 128 samples per worklet call; ~1024 samples needed for YIN accuracy
   - 8× accumulation on main thread = ~21ms at 48kHz — imperceptible for tuner
   - Verify: pitchfinder YIN works well at 1024-sample buffers (default: Mcleod uses 1024, YIN configurable)
   - **RESOLVED:** 8 blocks × 128 samples = 1024 samples at 44100 Hz = ~23ms analysis window. YIN works reliably at ≥20ms. Sufficient — no change to the accumulation strategy.

---

## RESEARCH COMPLETE
