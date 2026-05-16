import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import type { GeoPermissibleObjects } from 'd3'
import * as topojson from 'topojson-client'
import type { Topology, GeometryCollection } from 'topojson-specification'
import { useWSStore } from '../../store/ws.store'

interface DataNode {
  id: string
  coords: [number, number]
  label: string
  active: boolean
}

const DEFAULT_NODES: DataNode[] = [
  { id: 'nyse', coords: [-74, 40.7], label: 'NYSE', active: true },
  { id: 'lse', coords: [-0.1, 51.5], label: 'LSE', active: true },
  { id: 'tse', coords: [139.7, 35.7], label: 'TSE', active: false },
  { id: 'hkex', coords: [114.1, 22.3], label: 'HKEX', active: true },
  { id: 'fwb', coords: [8.7, 50.1], label: 'FWB', active: false },
]

export default function WorldMap() {
  const svgRef = useRef<SVGSVGElement>(null)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; label: string } | null>(null)
  const [nodes, setNodes] = useState<DataNode[]>(DEFAULT_NODES)
  const lastMessage = useWSStore((s) => s.lastMessage)

  // Update nodes when broker_map_nodes arrives from Python
  useEffect(() => {
    if (lastMessage?.type === 'broker_map_nodes') {
      const incoming = (lastMessage.nodes as DataNode[] | undefined) ?? []
      if (incoming.length > 0) setNodes(incoming)
    }
  }, [lastMessage])

  useEffect(() => {
    const el = svgRef.current!.parentElement!
    const W = el.clientWidth
    const H = el.clientHeight
    const svg = d3.select(svgRef.current!).attr('width', W).attr('height', H)
    svg.selectAll('*').remove()

    const projection = d3
      .geoMercator()
      .scale((W / 6.4))
      .translate([W / 2, H / 1.6])
      .center([15, 20])

    const path = d3.geoPath().projection(projection)
    const g = svg.append('g')

    svg.call(
      d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.8, 8]).on('zoom', (e) => {
        g.attr('transform', e.transform)
      }),
    )

    g.append('rect').attr('width', W).attr('height', H).attr('fill', 'transparent')

    const graticule = d3.geoGraticule()()
    g.append('path')
      .datum(graticule as GeoPermissibleObjects)
      .attr('d', path)
      .attr('fill', 'none')
      .attr('stroke', 'rgba(0,245,255,0.04)')
      .attr('stroke-width', 0.5)

    fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
      .then((r) => r.json())
      .then((world: Topology<{ countries: GeometryCollection }>) => {
        const countries = topojson.feature(world, world.objects.countries)

        g.append('g')
          .selectAll('path')
          .data((countries as GeoJSON.FeatureCollection).features)
          .join('path')
          .attr('d', (d) => path(d as GeoPermissibleObjects) ?? '')
          .attr('fill', 'rgba(0,245,255,0.03)')
          .attr('stroke', 'rgba(0,245,255,0.12)')
          .attr('stroke-width', 0.5)
          .attr('stroke-linejoin', 'round')

        nodes.forEach((node) => {
          const pos = projection(node.coords)
          if (!pos) return
          const [px, py] = pos

          const ring = g.append('circle')
            .attr('cx', px).attr('cy', py)
            .attr('r', node.active ? 8 : 5)
            .attr('fill', 'none')
            .attr('stroke', node.active ? 'var(--accent-primary)' : 'var(--accent-warning)')
            .attr('stroke-width', 0.8)
            .attr('opacity', 0.5)

          if (node.active) {
            ring.style('animation', `nodeRing 2s ease-out infinite`)
          }

          g.append('circle')
            .attr('cx', px).attr('cy', py)
            .attr('r', 3)
            .attr('fill', node.active ? 'var(--accent-primary)' : 'var(--accent-warning)')
            .attr('opacity', 0.9)
            .style('cursor', 'pointer')
            .on('mouseenter', (event: MouseEvent) => setTooltip({ x: event.clientX, y: event.clientY, label: node.label }))
            .on('mouseleave', () => setTooltip(null))
        })
      })
      .catch(() => {
        g.append('text')
          .attr('x', W / 2).attr('y', H / 2)
          .attr('text-anchor', 'middle')
          .attr('fill', 'rgba(0,245,255,0.2)')
          .attr('font-family', 'JetBrains Mono')
          .attr('font-size', '11px')
          .text('[ MAP DATA OFFLINE ]')
      })
  }, [nodes])

  return (
    <div className="w-full h-full relative">
      <style>{`
        @keyframes nodeRing {
          from { r: 4; opacity: 0.8; }
          to   { r: 18; opacity: 0; }
        }
      `}</style>
      <svg ref={svgRef} className="w-full h-full" />
      {tooltip && (
        <div
          className="fixed pointer-events-none z-50 px-2 py-1 panel-glass"
          style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
        >
          <span className="font-mono text-[0.65rem] text-[var(--accent-primary)]">{tooltip.label}</span>
        </div>
      )}
    </div>
  )
}
