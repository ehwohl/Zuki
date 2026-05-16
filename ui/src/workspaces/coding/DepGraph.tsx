import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

export interface DepNode {
  id: string
  label: string
  type: 'local' | 'builtin' | 'third-party'
}

export interface DepEdge {
  source: string
  target: string
}

interface SimNode extends DepNode, d3.SimulationNodeDatum {}
interface SimEdge {
  source: SimNode
  target: SimNode
}

// Read design tokens at call-time so the graph respects the active theme.
// D3 SVG attributes can't use CSS variables directly — we pull computed values.
function readTokens() {
  const s = getComputedStyle(document.documentElement)
  return {
    accent:  s.getPropertyValue('--accent-primary').trim(),
    warning: s.getPropertyValue('--accent-warning').trim(),
    fog:     s.getPropertyValue('--text-secondary').trim(),
    border:  s.getPropertyValue('--border-color').trim(),
  }
}

type Tokens = ReturnType<typeof readTokens>

function nodeColor(type: string, t: Tokens): string {
  if (type === 'local')       return t.accent
  if (type === 'third-party') return t.warning
  return t.fog
}

interface GraphState {
  sim:   ReturnType<typeof d3.forceSimulation<SimNode>>
  link:  d3.Selection<SVGLineElement, SimEdge, SVGGElement, unknown>
  nodeG: d3.Selection<SVGGElement,    SimNode,  SVGGElement, unknown>
}

export default function DepGraph({ nodes, edges }: { nodes: DepNode[]; edges: DepEdge[] }) {
  const svgRef   = useRef<SVGSVGElement>(null)
  const stateRef = useRef<GraphState | null>(null)

  // Full rebuild when node/edge data changes
  useEffect(() => {
    const svgEl = svgRef.current
    if (!svgEl) return

    stateRef.current?.sim.stop()
    stateRef.current = null

    const svg = d3.select(svgEl)
    svg.selectAll('*').remove()

    const W = svgEl.parentElement?.clientWidth  ?? 300
    const H = svgEl.parentElement?.clientHeight ?? 200
    svg.attr('width', W).attr('height', H)

    const t = readTokens()

    if (nodes.length === 0) {
      svg
        .append('text')
        .attr('x', W / 2).attr('y', H / 2)
        .attr('text-anchor', 'middle')
        .attr('font-family', 'JetBrains Mono, monospace')
        .attr('font-size', '9px')
        .attr('fill', t.accent)
        .attr('fill-opacity', 0.2)
        .text('[ run code to map imports ]')
      return
    }

    const simNodes: SimNode[] = nodes.map((n) => ({ ...n }))
    const byId = new Map(simNodes.map((n) => [n.id, n]))

    const simEdges: SimEdge[] = edges
      .map((e) => ({ source: byId.get(e.source)!, target: byId.get(e.target)! }))
      .filter((e) => e.source && e.target)

    // Scale label size to available width — unreadable below 7px, capped at 10px
    const labelSize = Math.max(7, Math.min(10, W / 60))

    const sim = d3
      .forceSimulation<SimNode>(simNodes)
      .force('link',      d3.forceLink<SimNode, SimEdge>(simEdges).distance(72).strength(0.9))
      .force('charge',    d3.forceManyBody<SimNode>().strength(-200))
      .force('center',    d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide<SimNode>(20))

    const g = svg.append('g')

    const link = g
      .append('g')
      .selectAll<SVGLineElement, SimEdge>('line')
      .data(simEdges)
      .join('line')
      .attr('stroke', t.border)
      .attr('stroke-width', 1)

    const nodeG = g
      .append('g')
      .selectAll<SVGGElement, SimNode>('g')
      .data(simNodes)
      .join('g')
      .attr('tabindex', '0')
      .attr('role', 'listitem')
      .attr('aria-label', (d) => `${d.label}, ${d.type}`)

    nodeG
      .append('circle')
      .attr('r', (d) => d.type === 'local' ? 9 : 5)
      .attr('fill', (d) => nodeColor(d.type, t))
      .attr('fill-opacity', 0.12)
      .attr('stroke', (d) => nodeColor(d.type, t))
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.75)

    nodeG
      .append('text')
      .text((d) => d.label)
      .attr('text-anchor', 'middle')
      .attr('y', -12)
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-size', `${labelSize}px`)
      .attr('fill', (d) => nodeColor(d.type, t))
      .attr('fill-opacity', 0.65)
      .attr('pointer-events', 'none')

    // Arrow-key nudge: pin while focused, release on blur
    nodeG
      .on('keydown.nav', (event, d) => {
        const ke = event as KeyboardEvent
        const delta: Record<string, [number, number]> = {
          ArrowLeft: [-10, 0], ArrowRight: [10, 0],
          ArrowUp:   [0, -10], ArrowDown:  [0, 10],
        }
        const move = delta[ke.key]
        if (!move) return
        ke.preventDefault()
        d.fx = (d.x ?? 0) + move[0]
        d.fy = (d.y ?? 0) + move[1]
        sim.alpha(0.1).restart()
      })
      .on('blur.nav', (_, d) => {
        d.fx = null
        d.fy = null
      })

    sim.on('tick', () => {
      link
        .attr('x1', (d) => (d.source as SimNode).x ?? 0)
        .attr('y1', (d) => (d.source as SimNode).y ?? 0)
        .attr('x2', (d) => (d.target as SimNode).x ?? 0)
        .attr('y2', (d) => (d.target as SimNode).y ?? 0)
      nodeG.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`)
    })

    nodeG.call(
      d3.drag<SVGGElement, SimNode>()
        .on('start', (event, d) => {
          if (!event.active) sim.alphaTarget(0.3).restart()
          d.fx = d.x; d.fy = d.y
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
        .on('end', (event, d) => {
          // alphaTarget(0).alpha(0.1) accelerates cooldown vs just alphaTarget(0)
          if (!event.active) sim.alphaTarget(0).alpha(0.1)
          d.fx = null; d.fy = null
        }),
    )

    stateRef.current = { sim, link, nodeG }
    return () => { sim.stop() }
  }, [nodes, edges])

  // Resize: update SVG dimensions + nudge center force — no full rebuild
  useEffect(() => {
    const svgEl = svgRef.current
    if (!svgEl) return
    const ro = new ResizeObserver(() => {
      const W = svgEl.parentElement?.clientWidth  ?? 300
      const H = svgEl.parentElement?.clientHeight ?? 200
      d3.select(svgEl).attr('width', W).attr('height', H)
      stateRef.current?.sim
        .force('center', d3.forceCenter(W / 2, H / 2))
        .alpha(0.15)
        .restart()
    })
    if (svgEl.parentElement) ro.observe(svgEl.parentElement)
    return () => ro.disconnect()
  }, [])

  // Theme switch: re-patch D3 element colors without rebuilding the graph
  useEffect(() => {
    const obs = new MutationObserver(() => {
      const state = stateRef.current
      if (!state) return
      const t = readTokens()
      state.link.attr('stroke', t.border)
      state.nodeG
        .selectAll<SVGCircleElement, SimNode>('circle')
        .attr('fill',   (d) => nodeColor(d.type, t))
        .attr('stroke', (d) => nodeColor(d.type, t))
      state.nodeG
        .selectAll<SVGTextElement, SimNode>('text')
        .attr('fill', (d) => nodeColor(d.type, t))
    })
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => obs.disconnect()
  }, [])

  return (
    <svg
      ref={svgRef}
      role="img"
      aria-labelledby="dep-graph-title"
      className="w-full h-full"
    >
      <title id="dep-graph-title">Module dependency graph — import relationships between files</title>
    </svg>
  )
}
