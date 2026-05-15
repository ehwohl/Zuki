import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import type { NeuralMapMode } from '../../store/workspace.store'

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

const MOCK_DATA: Record<NeuralMapMode, { nodes: GraphNode[]; links: GraphLink[] }> = {
  provenance: {
    nodes: [
      { id: 'serpapi', label: 'SerpAPI', type: 'source' },
      { id: 'scraper', label: 'Scraper', type: 'skill' },
      { id: 'redis', label: 'Redis', type: 'source' },
      { id: 'news', label: 'News', type: 'skill' },
      { id: 'gemini', label: 'Gemini', type: 'source' },
      { id: 'ui', label: 'UI', type: 'output' },
    ],
    links: [
      { source: 'serpapi', target: 'scraper' },
      { source: 'scraper', target: 'news' },
      { source: 'redis', target: 'news' },
      { source: 'gemini', target: 'ui' },
      { source: 'news', target: 'ui' },
    ],
  },
  routing: {
    nodes: [
      { id: 'input', label: 'Input', type: 'source' },
      { id: 'router', label: 'Router', type: 'skill' },
      { id: 'broker', label: 'Broker', type: 'skill' },
      { id: 'cloud', label: 'Cloud', type: 'skill' },
      { id: 'output', label: 'Response', type: 'output' },
    ],
    links: [
      { source: 'input', target: 'router' },
      { source: 'router', target: 'broker' },
      { source: 'router', target: 'cloud' },
      { source: 'broker', target: 'output' },
    ],
  },
  both: {
    nodes: [
      { id: 'input', label: 'Input', type: 'source' },
      { id: 'router', label: 'Router', type: 'skill' },
      { id: 'serpapi', label: 'SerpAPI', type: 'source' },
      { id: 'scraper', label: 'Scraper', type: 'skill' },
      { id: 'gemini', label: 'Gemini', type: 'source' },
      { id: 'output', label: 'UI', type: 'output' },
    ],
    links: [
      { source: 'input', target: 'router' },
      { source: 'router', target: 'scraper' },
      { source: 'serpapi', target: 'scraper' },
      { source: 'gemini', target: 'output' },
      { source: 'scraper', target: 'output' },
    ],
  },
}

const NODE_COLOR: Record<GraphNode['type'], string> = {
  source: '#FF00A0',
  skill: '#00F5FF',
  output: '#FFB300',
}

export default function NeuralMapPanel({ mode }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const svg = d3.select(svgRef.current!)
    svg.selectAll('*').remove()

    const el = svgRef.current!.parentElement!
    const W = el.clientWidth
    const H = el.clientHeight

    svg.attr('width', W).attr('height', H)

    const data = MOCK_DATA[mode]
    const nodes: GraphNode[] = data.nodes.map((n) => ({ ...n }))
    const links: GraphLink[] = data.links.map((l) => ({ ...l }))

    const sim = d3
      .forceSimulation<GraphNode>(nodes)
      .force('link', d3.forceLink<GraphNode, GraphLink>(links).id((d) => d.id).distance(70))
      .force('charge', d3.forceManyBody().strength(-180))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide(28))

    const g = svg.append('g')

    // Zoom
    svg.call(
      d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.4, 3]).on('zoom', (event) => {
        g.attr('transform', event.transform)
      }),
    )

    // Links
    const link = g
      .append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', 'rgba(0,245,255,0.2)')
      .attr('stroke-width', 1)

    // Nodes
    const node = g
      .append('g')
      .selectAll<SVGGElement, GraphNode>('g')
      .data(nodes)
      .join('g')
      .style('cursor', 'pointer')
      .call(
        d3
          .drag<SVGGElement, GraphNode>()
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

    node
      .append('circle')
      .attr('r', 14)
      .attr('fill', 'rgba(10,15,20,0.9)')
      .attr('stroke', (d) => NODE_COLOR[d.type])
      .attr('stroke-width', 1.5)

    node
      .append('text')
      .text((d) => d.label)
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', (d) => NODE_COLOR[d.type])
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('font-size', '7px')

    // Glow on hover
    node.on('mouseenter', function (_) {
      d3.select(this).select('circle').attr('stroke-width', 2.5).attr('filter', 'url(#glow)')
    }).on('mouseleave', function () {
      d3.select(this).select('circle').attr('stroke-width', 1.5).attr('filter', null)
    })

    // SVG defs for glow filter
    svg.append('defs').append('filter').attr('id', 'glow')
      .append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur')
    svg.select('#glow').append('feMerge').selectAll('feMergeNode')
      .data(['blur', 'SourceGraphic'])
      .join('feMergeNode')
      .attr('in', (d) => d)

    sim.on('tick', () => {
      link
        .attr('x1', (d) => (d.source as GraphNode).x!)
        .attr('y1', (d) => (d.source as GraphNode).y!)
        .attr('x2', (d) => (d.target as GraphNode).x!)
        .attr('y2', (d) => (d.target as GraphNode).y!)
      node.attr('transform', (d) => `translate(${d.x},${d.y})`)
    })

    return () => { sim.stop() }
  }, [mode])

  return (
    <div className="w-full h-full relative">
      <svg ref={svgRef} className="w-full h-full" />
      <div className="absolute bottom-2 left-2 opacity-40">
        <span className="font-mono text-[0.55rem] text-[var(--text-secondary)] uppercase tracking-widest">
          mode: {mode}
        </span>
      </div>
    </div>
  )
}
