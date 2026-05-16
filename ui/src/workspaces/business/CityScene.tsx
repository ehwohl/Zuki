import { useEffect, useRef } from 'react'
import * as THREE from 'three'

export interface Building {
  id: string
  label: string
  score: number
  flagship: boolean
}

// Numeric equivalents of --accent-primary / --accent-secondary / --accent-warning
// Three.js needs numbers; these are the Cyberpunk defaults and stay valid under theme swaps
// because the 3D scene colour intent (cyan=active, amber=caution, magenta=warn) is semantic.
const C_CYAN    = 0x00F5FF
const C_AMBER   = 0xFFB300
const C_MAGENTA = 0xFF00A0
const C_VOID    = 0x010a10

const PLACEHOLDER: Building = { id: 'ph', label: 'ZUKI', score: 60, flagship: true }

function scoreColor(score: number, flagship: boolean): number {
  if (flagship) return C_CYAN
  if (score >= 70) return C_CYAN
  if (score >= 40) return C_AMBER
  return C_MAGENTA
}

function scoreHeight(score: number): number {
  return 0.5 + (score / 100) * 3.5
}

// Canvas-texture sprite for holographic data label above each venue node
function makeLabelSprite(text: string, score: number, color: number): THREE.Sprite {
  const canvas = document.createElement('canvas')
  canvas.width  = 256
  canvas.height = 80
  const ctx = canvas.getContext('2d')!

  const r = (color >> 16) & 0xff
  const g = (color >>  8) & 0xff
  const b =  color        & 0xff
  const cssColor = `rgb(${r},${g},${b})`

  ctx.fillStyle = 'rgba(0,8,16,0.8)'
  ctx.fillRect(0, 0, 256, 80)

  ctx.strokeStyle = cssColor
  ctx.globalAlpha = 0.45
  ctx.lineWidth = 1
  ctx.strokeRect(1, 1, 254, 78)

  ctx.globalAlpha = 0.9
  ctx.font = 'bold 13px "JetBrains Mono", monospace'
  ctx.fillStyle = cssColor
  ctx.textAlign = 'center'
  ctx.fillText(text.toUpperCase().slice(0, 18), 128, 30)

  ctx.globalAlpha = 0.65
  ctx.font = '10px "JetBrains Mono", monospace'
  ctx.fillText(`SCORE ${score}`, 128, 52)

  const texture = new THREE.CanvasTexture(canvas)
  return new THREE.Sprite(
    new THREE.SpriteMaterial({
      map:         texture,
      transparent: true,
      depthWrite:  false,
      blending:    THREE.AdditiveBlending,
    }),
  )
}

function addBuilding(
  scene: THREE.Scene,
  b: Building,
  x: number,
  z: number,
): { x: number; z: number; h: number } {
  const h   = scoreHeight(b.score)
  const dim = b.flagship ? 1.2 : 0.8
  const col = scoreColor(b.score, b.flagship)

  const geo = new THREE.BoxGeometry(dim, h, dim)

  // Dark metallic core
  const solid = new THREE.Mesh(
    geo,
    new THREE.MeshStandardMaterial({
      color:       C_VOID,
      transparent: true,
      opacity:     0.88,
      roughness:   0.1,
      metalness:   0.95,
    }),
  )
  solid.position.set(x, h / 2, z)
  solid.userData.isBuilding = true
  scene.add(solid)

  // Primary neon wireframe — additive blending gives real glow without post-processing
  const lines = new THREE.LineSegments(
    new THREE.EdgesGeometry(geo),
    new THREE.LineBasicMaterial({
      color:       col,
      transparent: true,
      opacity:     b.flagship ? 0.95 : 0.7,
      blending:    THREE.AdditiveBlending,
      depthWrite:  false,
    }),
  )
  lines.position.set(x, h / 2, z)
  lines.userData.isBuilding = true
  scene.add(lines)

  // Outer diffuse glow — scaled up slightly, very low opacity
  const glowLines = new THREE.LineSegments(
    new THREE.EdgesGeometry(geo),
    new THREE.LineBasicMaterial({
      color:       col,
      transparent: true,
      opacity:     b.flagship ? 0.28 : 0.12,
      blending:    THREE.AdditiveBlending,
      depthWrite:  false,
    }),
  )
  glowLines.position.set(x, h / 2, z)
  glowLines.scale.setScalar(1.07)
  glowLines.userData.isBuilding = true
  scene.add(glowLines)

  // Holographic data label floating above the building
  const sprite = makeLabelSprite(b.label, b.score, col)
  sprite.scale.set(b.flagship ? 1.5 : 1.15, b.flagship ? 0.47 : 0.36, 1)
  sprite.position.set(x, h + 0.85, z)
  sprite.userData.isBuilding = true
  scene.add(sprite)

  // Per-building point light for local glow pooling on the floor
  const light = new THREE.PointLight(col, b.flagship ? 1.0 : 0.5, b.flagship ? 8 : 4)
  light.position.set(x, h * 0.6, z)
  light.userData.isBuilding = true
  scene.add(light)

  return { x, z, h }
}

function rebuildBuildings(
  scene: THREE.Scene,
  buildings: Building[],
  streamParticles: THREE.Mesh[],
): void {
  // Dispose and remove all building-tagged objects
  const dead = scene.children.filter((c) => c.userData.isBuilding)
  dead.forEach((c) => {
    scene.remove(c)
    if (c instanceof THREE.Sprite) {
      const sm = c.material as THREE.SpriteMaterial
      sm.map?.dispose()
      sm.dispose()
    } else {
      const o = c as THREE.Mesh
      o.geometry?.dispose()
      if (o.material) {
        const mats = Array.isArray(o.material) ? o.material : [o.material]
        mats.forEach((m) => m.dispose())
      }
    }
  })
  streamParticles.length = 0

  const list = buildings.length > 0 ? buildings : [PLACEHOLDER]
  const flagship = list.find((b) => b.flagship)
  const rest     = list.filter((b) => !b.flagship)

  const fpPos = flagship ? addBuilding(scene, flagship, 0, 0) : null

  const R = 4
  rest.forEach((b, i) => {
    const a  = (i / rest.length) * Math.PI * 2
    const bx = Math.cos(a) * R
    const bz = Math.sin(a) * R
    const { h } = addBuilding(scene, b, bx, bz)

    if (fpPos) {
      // Faint static connection line: outer node → flagship
      const pts = [
        new THREE.Vector3(bx, h / 2, bz),
        new THREE.Vector3(0, fpPos.h / 2, 0),
      ]
      const edge = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({
          color:       scoreColor(b.score, false),
          transparent: true,
          opacity:     0.07,
          blending:    THREE.AdditiveBlending,
          depthWrite:  false,
        }),
      )
      edge.userData.isBuilding = true
      scene.add(edge)

      // Animated data stream particle travelling outer → flagship
      const particle = new THREE.Mesh(
        new THREE.SphereGeometry(0.055, 4, 4),
        new THREE.MeshBasicMaterial({
          color:       scoreColor(b.score, false),
          transparent: true,
          opacity:     0.9,
          blending:    THREE.AdditiveBlending,
          depthWrite:  false,
        }),
      )
      particle.userData.isBuilding  = true
      particle.userData.streamFrom  = new THREE.Vector3(bx, h / 2, bz)
      particle.userData.streamTo    = new THREE.Vector3(0, fpPos.h / 2, 0)
      particle.userData.streamT     = Math.random() // stagger offsets per particle
      scene.add(particle)
      streamParticles.push(particle)
    }
  })
}

// ── GridHelper material helper ─────────────────────────────────────────────────
// THREE types material as Material | Material[]; in practice GridHelper is always
// a single LineBasicMaterial, but we guard for the array case to keep TS happy.
function gridMaterial(grid: THREE.GridHelper): THREE.LineBasicMaterial {
  return (
    Array.isArray(grid.material) ? grid.material[0] : grid.material
  ) as THREE.LineBasicMaterial
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function CityScene({ buildings }: { buildings: Building[] }) {
  const mountRef = useRef<HTMLDivElement>(null)

  const ctxRef = useRef<{
    renderer:        THREE.WebGLRenderer
    scene:           THREE.Scene
    camera:          THREE.PerspectiveCamera
    frameId:         number
    angle:           number
    clock:           THREE.Clock
    gridMat:         THREE.LineBasicMaterial
    streamParticles: THREE.Mesh[]
  } | null>(null)

  // ── Mount: create renderer + scene (runs once) ─────────────────────────────
  useEffect(() => {
    const el = mountRef.current
    if (!el) return

    const W = el.clientWidth  || 400
    const H = el.clientHeight || 300

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(W, H)
    renderer.setClearColor(0x000000, 0)
    el.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    // Exponential fog: pulls distant buildings into the void
    scene.fog = new THREE.FogExp2(0x000408, 0.035)

    const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 100)
    camera.position.set(8, 6, 8)
    camera.lookAt(0, 1, 0)

    // Outer grid — very faint, sets the scale of the city
    const gridOuter = new THREE.GridHelper(22, 22, C_CYAN, 0x001020)
    const goMat = gridMaterial(gridOuter)
    goMat.opacity = 0.05; goMat.transparent = true; goMat.depthWrite = false
    scene.add(gridOuter)

    // Inner grid — pulsed in animation loop for heartbeat effect
    const gridInner = new THREE.GridHelper(14, 14, C_CYAN, C_CYAN)
    const giMat = gridMaterial(gridInner)
    giMat.opacity    = 0.18
    giMat.transparent = true
    giMat.blending   = THREE.AdditiveBlending
    giMat.depthWrite = false
    scene.add(gridInner)

    // Ambient: very dim cyan so dark panels catch colour
    scene.add(new THREE.AmbientLight(C_CYAN, 0.12))
    scene.add(new THREE.HemisphereLight(C_CYAN, 0x000610, 0.15))

    const clock           = new THREE.Clock()
    const streamParticles: THREE.Mesh[] = []

    const ctx = {
      renderer, scene, camera,
      frameId: 0, angle: Math.PI / 4,
      clock, gridMat: giMat, streamParticles,
    }
    ctxRef.current = ctx

    const animate = () => {
      ctx.frameId = requestAnimationFrame(animate)
      const t = clock.getElapsedTime()

      // Slow orbit — operator view, not a demo spin
      ctx.angle += 0.0025
      const r = 10
      camera.position.x = Math.cos(ctx.angle) * r
      camera.position.z = Math.sin(ctx.angle) * r
      camera.lookAt(0, 1, 0)

      // Grid pulse: sine-driven opacity creates a subtle heartbeat on the floor
      ctx.gridMat.opacity = 0.11 + 0.08 * Math.sin(t * 0.65)

      // Stream particles: travel from ring node → flagship, fade in/out at endpoints
      for (const p of ctx.streamParticles) {
        p.userData.streamT = (p.userData.streamT + 0.005) % 1.0
        const tt: number = p.userData.streamT
        p.position.lerpVectors(
          p.userData.streamFrom as THREE.Vector3,
          p.userData.streamTo   as THREE.Vector3,
          tt,
        )
        ;(p.material as THREE.MeshBasicMaterial).opacity = Math.sin(tt * Math.PI) * 0.9
      }

      renderer.render(scene, camera)
    }
    animate()

    const ro = new ResizeObserver(() => {
      const W2 = el.clientWidth
      const H2 = el.clientHeight
      camera.aspect = W2 / H2
      camera.updateProjectionMatrix()
      renderer.setSize(W2, H2)
    })
    ro.observe(el)

    return () => {
      cancelAnimationFrame(ctx.frameId)
      ro.disconnect()
      renderer.dispose()
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement)
      ctxRef.current = null
    }
  }, [])

  // ── Data: rebuild venue nodes when buildings prop changes ──────────────────
  useEffect(() => {
    const ctx = ctxRef.current
    if (!ctx) return
    rebuildBuildings(ctx.scene, buildings, ctx.streamParticles)
  }, [buildings])

  return <div ref={mountRef} className="w-full h-full" />
}
