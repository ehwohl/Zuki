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

const NODE_COLORS: Record<string, string> = {
  local:           '#00F5FF',
  builtin:         '#445566',
  'third-party':   '#FFB300',
}

export default function DepGraph({ nodes, edges }: { nodes: DepNode[]; edges: DepEdge[] }) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const svgEl = svgRef.current
    if (!svgEl) return

    const svg = d3.select(svgEl)
    svg.selectAll('*').remove()

    const W = svgEl.parentElement?.clientWidth  ?? 300
    const H = svgEl.parentElement?.clientHeight ?? 200
    svg.attr('width', W).attr('height', H)

    if (nodes.length === 0) {
      svg
        .append('text')
        .attr('x', W / 2).attr('y', H / 2)
        .attr('text-anchor', 'middle')
        .attr('font-family', 'JetBrains Mono, monospace')
        .attr('font-size', '9px')
        .attr('fill', 'rgba(0,245,255,0.2)')
        .text('[ run code to map imports ]')
      return
    }

    // Clone into simulation nodes so d3 can mutate x/y
    const simNodes: SimNode[] = nodes.map((n) => ({ ...n }))
    const byId = new Map(simNodes.map((n) => [n.id, n]))

    const simEdges: SimEdge[] = edges
      .map((e) => ({ source: byId.get(e.source)!, target: byId.get(e.target)! }))
      .filter((e) => e.source && e.target)

    const sim = d3
      .forceSimulation<SimNode>(simNodes)
      .force('link',      d3.forceLink<SimNode, SimEdge>(simEdges).distance(72).strength(0.9))
      .force('charge',    d3.forceManyBody<SimNode>().strength(-200))
      .force('center',    d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide<SimNode>(20))

    const g = svg.append('g')

    // Edges
    const link = g
      .append('g')
      .selectAll<SVGLineElement, SimEdge>('line')
      .data(simEdges)
      .join('line')
      .attr('stroke', 'rgba(0,245,255,0.12)')
      .attr('stroke-width', 1)

    // Nodes
    const nodeG = g
      .append('g')
      .selectAll<SVGGElement, SimNode>('g')
      .data(simNodes)
      .join('g')

    nodeG
      .append('circle')
      .attr('r', (d) => d.type === 'local' ? 9 : 5)
      .attr('fill', (d) => NODE_COLORS[d.type] ?? '#888')
      .attr('fill-opacity', 0.12)
      .attr('stroke', (d) => NODE_COLORS[d.type] ?? '#888')
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.75)

    nodeG
      .append('text')
      .text((d) => d.label)
      .attr('text-anchor', 'middle')
      .attr('y', -12)
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-size', '8px')
      .attr('fill', (d) => NODE_COLORS[d.type] ?? '#888')
      .attr('fill-opacity', 0.65)
      .attr('pointer-events', 'none')

    sim.on('tick', () => {
      link
        .attr('x1', (d) => (d.source as SimNode).x ?? 0)
        .attr('y1', (d) => (d.source as SimNode).y ?? 0)
        .attr('x2', (d) => (d.target as SimNode).x ?? 0)
        .attr('y2', (d) => (d.target as SimNode).y ?? 0)

      nodeG.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`)
    })

    // Drag
    nodeG.call(
      d3.drag<SVGGElement, SimNode>()
        .on('start', (event, d) => {
          if (!event.active) sim.alphaTarget(0.3).restart()
          d.fx = d.x; d.fy = d.y
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
        .on('end', (event, d) => {
          if (!event.active) sim.alphaTarget(0)
          d.fx = null; d.fy = null
        }),
    )

    return () => { sim.stop() }
  }, [nodes, edges])

  return <svg ref={svgRef} className="w-full h-full" />
}
