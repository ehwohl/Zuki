import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import type { NeuralMapMode } from '../../store/workspace.store'
import { useNeuralStore } from '../../store/neural.store'

interface Props {
  mode: NeuralMapMode
}

interface GraphNode extends d3.SimulationNodeDatum {
  id: string
  label: string
  type: 'source' | 'skill' | 'output'
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  label?: string
}

interface AmbientParticle {
  linkIdx: number
  t: number
  speed: number
  color: string
}

interface TaskParticle {
  linkIdx: number
  t: number
  speed: number
  color: string
}

const MOCK_DATA: Record<NeuralMapMode, { nodes: GraphNode[]; links: GraphLink[] }> = {
  // Broker workspace — data provenance: n8n/SerpAPI feed → webhook → BrokerSkill → Router → UI
  provenance: {
    nodes: [
      { id: 'serpapi', label: 'SerpAPI', type: 'source' },
      { id: 'n8n',     label: 'n8n',     type: 'source' },
      { id: 'redis',   label: 'Redis',   type: 'source' },
      { id: 'broker',  label: 'Broker',  type: 'skill'  },
      { id: 'router',  label: 'Router',  type: 'skill'  },
      { id: 'ui',      label: 'UI',      type: 'output' },
    ],
    links: [
      { source: 'serpapi', target: 'n8n'    },
      { source: 'n8n',     target: 'broker' },
      { source: 'redis',   target: 'broker' },
      { source: 'broker',  target: 'router' },
      { source: 'router',  target: 'ui'     },
    ],
  },
  // OS / Office workspaces — skill routing pipeline
  routing: {
    nodes: [
      { id: 'input',  label: 'Input',    type: 'source' },
      { id: 'router', label: 'Router',   type: 'skill'  },
      { id: 'skill',  label: 'Skill',    type: 'skill'  },
      { id: 'cloud',  label: 'Cloud',    type: 'skill'  },
      { id: 'output', label: 'Response', type: 'output' },
    ],
    links: [
      { source: 'input',  target: 'router' },
      { source: 'router', target: 'skill'  },
      { source: 'router', target: 'cloud'  },
      { source: 'skill',  target: 'output' },
    ],
  },
  // Business workspace — analysis flow: interview → knowledge base + LLM → score → PDF report
  business: {
    nodes: [
      { id: 'input',  label: 'Input',     type: 'source' },
      { id: 'bskill', label: 'Business',  type: 'skill'  },
      { id: 'kb',     label: 'Knowledge', type: 'source' },
      { id: 'llm',    label: 'LLM',       type: 'source' },
      { id: 'score',  label: 'Score',     type: 'skill'  },
      { id: 'report', label: 'Report',    type: 'output' },
    ],
    links: [
      { source: 'input',  target: 'bskill' },
      { source: 'kb',     target: 'bskill' },
      { source: 'bskill', target: 'llm'    },
      { source: 'bskill', target: 'score'  },
      { source: 'score',  target: 'report' },
    ],
  },
}

const NODE_COLOR: Record<GraphNode['type'], string> = {
  source: '#FF00A0',
  skill:  '#00F5FF',
  output: '#FFB300',
}

// Ambient: always present, 2 per link, subtle
const AMBIENT_PER_LINK = 2
const AMBIENT_SPEED    = 0.00032

// Task: only visible when a real task uses that link, 4 per link, fast + large
const TASK_PER_LINK = 4
const TASK_SPEED    = AMBIENT_SPEED * 1.8

function clamp(v: number, lo: number, hi: number) { return v < lo ? lo : v > hi ? hi : v }
function clamp01(v: number)                        { return clamp(v, 0, 1) }

function deriveScale(W: number, H: number) {
  const s = clamp(Math.min(W, H) / 320, 0.45, 2.6)
  return {
    s,
    nodeR:      Math.round(14 * s),
    haloR:      Math.round(20 * s),
    coreR:      2.5 * s,
    linkDist:   Math.round(75 * s),
    charge:     -200 * s,
    collision:  Math.round(32 * s),
    fontSize:   Math.max(6, Math.round(7 * s)),
    particleR:  clamp(1.8 * s, 1.2, 4),
    taskR:      clamp(4.5 * s, 3,   9),   // task dots: visibly larger than ambient
    showLabel:  s >= 0.6,
  }
}

function buildGraph(
  svgEl: SVGSVGElement,
  mode: NeuralMapMode,
  activeNodesRef: React.MutableRefObject<Set<string>>,
): () => void {
  const svg = d3.select(svgEl)
  svg.selectAll('*').remove()

  const W = svgEl.parentElement!.clientWidth  || 240
  const H = svgEl.parentElement!.clientHeight || 400
  svg.attr('width', W).attr('height', H)

  const sc = deriveScale(W, H)

  const data  = MOCK_DATA[mode]
  const nodes: GraphNode[] = data.nodes.map(n => ({ ...n }))
  const links: GraphLink[] = data.links.map(l => ({ ...l }))

  // ── Defs ─────────────────────────────────────────────────────────────────────

  const defs = svg.append('defs')

  // Node hover glow
  const ng = defs.append('filter').attr('id', 'ng')
    .attr('x', '-60%').attr('y', '-60%').attr('width', '220%').attr('height', '220%')
  ng.append('feGaussianBlur').attr('in', 'SourceGraphic').attr('stdDeviation', 4 * sc.s).attr('result', 'b')
  const ngm = ng.append('feMerge')
  ngm.append('feMergeNode').attr('in', 'b')
  ngm.append('feMergeNode').attr('in', 'SourceGraphic')

  // Ambient particle glow — tight
  const apg = defs.append('filter').attr('id', 'apg')
    .attr('x', '-300%').attr('y', '-300%').attr('width', '700%').attr('height', '700%')
  apg.append('feGaussianBlur').attr('in', 'SourceGraphic').attr('stdDeviation', clamp(2 * sc.s, 1.2, 4)).attr('result', 'b')
  const apgm = apg.append('feMerge')
  apgm.append('feMergeNode').attr('in', 'b')
  apgm.append('feMergeNode').attr('in', 'SourceGraphic')

  // Task particle glow — wide, dramatic
  const tpg = defs.append('filter').attr('id', 'tpg')
    .attr('x', '-400%').attr('y', '-400%').attr('width', '900%').attr('height', '900%')
  tpg.append('feGaussianBlur').attr('in', 'SourceGraphic').attr('stdDeviation', clamp(5 * sc.s, 3, 10)).attr('result', 'b')
  const tpgm = tpg.append('feMerge')
  tpgm.append('feMergeNode').attr('in', 'b')
  tpgm.append('feMergeNode').attr('in', 'SourceGraphic')

  // ── Simulation ───────────────────────────────────────────────────────────────

  const sim = d3.forceSimulation<GraphNode>(nodes)
    .force('link',      d3.forceLink<GraphNode, GraphLink>(links).id(d => d.id).distance(sc.linkDist))
    .force('charge',    d3.forceManyBody().strength(sc.charge))
    .force('center',    d3.forceCenter(W / 2, H / 2))
    .force('collision', d3.forceCollide(sc.collision))

  const g = svg.append('g')

  svg.call(
    d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.4, 4])
      .on('zoom', e => g.attr('transform', e.transform)),
  )

  // ── Links ────────────────────────────────────────────────────────────────────

  const linkSel = g.append('g')
    .selectAll<SVGLineElement, GraphLink>('line')
    .data(links)
    .join('line')
    .attr('stroke-width', clamp(1.2 * sc.s, 0.8, 2.5))
    .attr('stroke-opacity', 0.20)
    .attr('stroke', d => NODE_COLOR[(d.source as GraphNode).type] ?? '#00F5FF')

  // ── Nodes ────────────────────────────────────────────────────────────────────

  const nodeSel = g.append('g')
    .selectAll<SVGGElement, GraphNode>('g')
    .data(nodes)
    .join('g')
    .style('cursor', 'pointer')
    .call(
      d3.drag<SVGGElement, GraphNode>()
        .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag',  (e, d) => { d.fx = e.x; d.fy = e.y })
        .on('end',   (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null }),
    )

  nodeSel.append('circle').attr('class', 'halo')
    .attr('r', sc.haloR)
    .attr('fill', 'none')
    .attr('stroke', d => NODE_COLOR[d.type])
    .attr('stroke-width', clamp(0.5 * sc.s, 0.4, 1.2))
    .attr('stroke-opacity', 0.22)
    .attr('pointer-events', 'none')

  nodeSel.append('circle').attr('class', 'shell')
    .attr('r', sc.nodeR)
    .attr('fill', 'rgba(10,12,18,0.95)')
    .attr('stroke', d => NODE_COLOR[d.type])
    .attr('stroke-width', clamp(1.5 * sc.s, 1, 3))

  nodeSel.append('circle').attr('class', 'core')
    .attr('r', sc.coreR)
    .attr('fill', d => NODE_COLOR[d.type])
    .attr('fill-opacity', 0.55)
    .attr('pointer-events', 'none')

  if (sc.showLabel) {
    nodeSel.append('text')
      .text(d => d.label)
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', d => NODE_COLOR[d.type])
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-size', `${sc.fontSize}px`)
      .attr('pointer-events', 'none')
  }

  nodeSel
    .on('mouseenter', function () {
      d3.select(this).select<SVGCircleElement>('.shell').attr('stroke-width', clamp(2.5 * sc.s, 1.5, 4)).attr('filter', 'url(#ng)')
      d3.select(this).select<SVGCircleElement>('.halo').attr('stroke-opacity', 0.6)
    })
    .on('mouseleave', function () {
      d3.select(this).select<SVGCircleElement>('.shell').attr('stroke-width', clamp(1.5 * sc.s, 1, 3)).attr('filter', null)
      d3.select(this).select<SVGCircleElement>('.halo').attr('stroke-opacity', 0.22)
    })

  // ── Ambient particles — always on, thin, slow ─────────────────────────────

  const ambient: AmbientParticle[] = links.flatMap((lnk, i) => {
    const color = NODE_COLOR[(lnk.source as GraphNode).type] ?? '#00F5FF'
    return Array.from({ length: AMBIENT_PER_LINK }, (_, j) => ({
      linkIdx: i,
      t: j / AMBIENT_PER_LINK,
      speed: AMBIENT_SPEED * (0.78 + Math.random() * 0.44),
      color,
    }))
  })

  const ambientSel = g.append('g').attr('class', 'ambient-particles')
    .selectAll<SVGCircleElement, AmbientParticle>('circle')
    .data(ambient)
    .join('circle')
    .attr('r', sc.particleR)
    .attr('filter', 'url(#apg)')
    .attr('fill', d => d.color)
    .attr('opacity', 0)

  // ── Task particles — per link, invisible until that link is hot ───────────

  const taskParticles: TaskParticle[] = links.flatMap((lnk, i) => {
    const color = NODE_COLOR[(lnk.source as GraphNode).type] ?? '#00F5FF'
    return Array.from({ length: TASK_PER_LINK }, (_, j) => ({
      linkIdx: i,
      t: (j / TASK_PER_LINK) + Math.random() * 0.05,
      speed: TASK_SPEED * (0.85 + Math.random() * 0.3),
      color,
    }))
  })

  const taskSel = g.append('g').attr('class', 'task-particles')
    .selectAll<SVGCircleElement, TaskParticle>('circle')
    .data(taskParticles)
    .join('circle')
    .attr('r', sc.taskR)
    .attr('filter', 'url(#tpg)')
    .attr('fill', d => d.color)
    .attr('opacity', 0)

  // ── Sim tick ─────────────────────────────────────────────────────────────────

  sim.on('tick', () => {
    linkSel
      .attr('x1', d => (d.source as GraphNode).x!)
      .attr('y1', d => (d.source as GraphNode).y!)
      .attr('x2', d => (d.target as GraphNode).x!)
      .attr('y2', d => (d.target as GraphNode).y!)
    nodeSel.attr('transform', d => `translate(${d.x},${d.y})`)
  })

  // ── Animation ────────────────────────────────────────────────────────────────

  function lerpPos(d: { linkIdx: number; t: number }, axis: 'x' | 'y') {
    const { source: src, target: tgt } = links[d.linkIdx]
    const s = src as GraphNode
    const t = tgt as GraphNode
    if (s[axis] == null || t[axis] == null) return 0
    return s[axis]! + (t[axis]! - s[axis]!) * d.t
  }

  function fadeCurve(t: number) {
    // Sharp emergence from source, sustained, quick arrival at target
    return clamp01(t * 9) * clamp01((1 - t) * 9)
  }

  let prev = 0
  const mainTimer = d3.timer(elapsed => {
    const dt = elapsed - prev
    prev = elapsed

    // Advance ambient
    ambient.forEach(p => { p.t += p.speed * dt; if (p.t >= 1) p.t -= 1 })
    ambientSel
      .attr('cx', d => lerpPos(d, 'x'))
      .attr('cy', d => lerpPos(d, 'y'))
      .attr('opacity', d => fadeCurve(d.t) * 0.72)

    // Advance task particles, show only on hot links
    const active = activeNodesRef.current
    const now    = Date.now()

    taskParticles.forEach(p => { p.t += p.speed * dt; if (p.t >= 1) p.t -= 1 })
    taskSel
      .attr('cx', d => lerpPos(d, 'x'))
      .attr('cy', d => lerpPos(d, 'y'))
      .attr('opacity', d => {
        const { source: src, target: tgt } = links[d.linkIdx]
        const srcId = (src as GraphNode).id
        const tgtId = (tgt as GraphNode).id
        // Link is hot when BOTH endpoints are in the active set and tasks haven't expired
        if (!active.has(srcId) || !active.has(tgtId)) return 0
        // Verify at least one non-expired task covers both nodes
        return fadeCurve(d.t)
      })

    // Highlight active nodes — brighter halo + shell
    nodeSel.select<SVGCircleElement>('.halo')
      .attr('r', (d, i) => {
        const base = sc.haloR + Math.sin(elapsed * 0.001 * 1.35 + i * 0.9) * (2.5 * sc.s)
        return active.has(d.id) ? base + sc.s * 3 : base
      })
      .attr('stroke-opacity', (d, i) => {
        const base = 0.18 - Math.sin(elapsed * 0.001 * 1.35 + i * 0.9) * 0.06
        return active.has(d.id) ? 0.7 : base
      })
      .attr('stroke-width', d => active.has(d.id) ? clamp(1.2 * sc.s, 0.8, 2.5) : clamp(0.5 * sc.s, 0.4, 1.2))

    nodeSel.select<SVGCircleElement>('.shell')
      .attr('filter', d => active.has(d.id) ? 'url(#ng)' : null)

    nodeSel.select<SVGCircleElement>('.core')
      .attr('r', (d, i) => {
        const base = sc.coreR * (0.8 + Math.sin(elapsed * 0.001 * 0.7 + i * 1.3) * 0.48)
        return active.has(d.id) ? base * 1.6 : base
      })
      .attr('fill-opacity', (d, i) => {
        const base = 0.45 + Math.sin(elapsed * 0.001 * 0.7 + i * 1.3) * 0.25
        return active.has(d.id) ? 1.0 : base
      })

    // Keep active set clean of expired tasks — cheap check each frame
    if (now % 1000 < 20) {
      // Roughly once per second: prune expired task nodes from the ref
      // (store auto-expires, but we also clear the ref so the map reacts immediately)
      // Nothing to do here — activeNodesRef is updated externally by the subscription
    }
  })

  return () => {
    sim.stop()
    mainTimer.stop()
  }
}

export default function NeuralMapPanel({ mode }: Props) {
  const svgRef         = useRef<SVGSVGElement>(null)
  const activeNodesRef = useRef<Set<string>>(new Set())

  // Sync active task nodes into the ref without triggering React re-renders.
  // The D3 animation timer reads activeNodesRef.current each frame — same
  // pattern as --pulse-intensity direct DOM writes.
  useEffect(() => {
    return useNeuralStore.subscribe(state => {
      const now    = Date.now()
      const active = new Set<string>()
      state.tasks.forEach(task => {
        if (task.expiresAt > now) {
          task.nodes.forEach(n => active.add(n))
        }
      })
      activeNodesRef.current = active
    })
  }, [])

  useEffect(() => {
    const svgEl     = svgRef.current!
    const container = svgEl.parentElement!

    let destroy: (() => void) | null = null
    let rafId:   number | null = null

    function rebuild() {
      if (destroy) destroy()
      destroy = buildGraph(svgEl, mode, activeNodesRef)
    }

    rebuild()

    const ro = new ResizeObserver(() => {
      if (rafId !== null) cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(rebuild)
    })
    ro.observe(container)

    return () => {
      if (destroy) destroy()
      if (rafId !== null) cancelAnimationFrame(rafId)
      ro.disconnect()
    }
  }, [mode])

  return (
    <div className="w-full h-full relative">
      <svg ref={svgRef} className="w-full h-full" />
      <div className="absolute bottom-2 left-2 opacity-35">
        <span
          className="uppercase tracking-widest"
          style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.55rem', color: 'var(--text-secondary)' }}
        >
          mode: {mode}
        </span>
      </div>
    </div>
  )
}
