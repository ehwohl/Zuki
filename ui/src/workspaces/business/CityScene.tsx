import { useEffect, useRef } from 'react'
import * as THREE from 'three'

export interface Building {
  id: string
  label: string
  score: number
  flagship: boolean
}

const C_CYAN    = 0x00F5FF
const C_AMBER   = 0xFFB300
const C_MAGENTA = 0xFF00A0

function scoreColor(score: number, flagship: boolean): number {
  if (flagship) return C_CYAN
  if (score >= 70) return C_CYAN
  if (score >= 40) return C_AMBER
  return C_MAGENTA
}

function scoreHeight(score: number): number {
  return 0.5 + (score / 100) * 3.5
}

function addBuilding(scene: THREE.Scene, b: Building, x: number, z: number) {
  const h   = scoreHeight(b.score)
  const dim = b.flagship ? 1.2 : 0.8
  const col = scoreColor(b.score, b.flagship)

  const geo  = new THREE.BoxGeometry(dim, h, dim)

  // Dark solid fill
  const solid = new THREE.Mesh(
    geo,
    new THREE.MeshStandardMaterial({ color: 0x010a10, transparent: true, opacity: 0.9 }),
  )
  solid.position.set(x, h / 2, z)
  solid.userData.isBuilding = true
  scene.add(solid)

  // Glowing wireframe edges
  const lines = new THREE.LineSegments(
    new THREE.EdgesGeometry(geo),
    new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: b.flagship ? 0.95 : 0.55 }),
  )
  lines.position.set(x, h / 2, z)
  lines.userData.isBuilding = true
  scene.add(lines)
}

const PLACEHOLDER: Building = { id: 'ph', label: 'ZUKI', score: 60, flagship: true }

export default function CityScene({ buildings }: { buildings: Building[] }) {
  const mountRef = useRef<HTMLDivElement>(null)

  const sceneCtx = useRef<{
    renderer: THREE.WebGLRenderer
    scene: THREE.Scene
    camera: THREE.PerspectiveCamera
    frameId: number
    angle: number
  } | null>(null)

  // ── Mount: create renderer + scene ────────────────────────────────────────
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

    const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 100)
    camera.position.set(8, 6, 8)
    camera.lookAt(0, 1, 0)

    // Grid floor
    const grid = new THREE.GridHelper(14, 14, 0x00F5FF, 0x00121e)
    ;(grid.material as THREE.Material).opacity = 0.12
    ;(grid.material as THREE.Material).transparent = true
    scene.add(grid)

    scene.add(new THREE.AmbientLight(0x00F5FF, 0.25))
    const dir = new THREE.DirectionalLight(0xffffff, 0.6)
    dir.position.set(5, 10, 5)
    scene.add(dir)

    let angle = Math.PI / 4

    const ctx = { renderer, scene, camera, frameId: 0, angle }
    sceneCtx.current = ctx

    const animate = () => {
      ctx.frameId = requestAnimationFrame(animate)
      ctx.angle  += 0.004
      const r = 10
      camera.position.x = Math.cos(ctx.angle) * r
      camera.position.z = Math.sin(ctx.angle) * r
      camera.lookAt(0, 1, 0)
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
      sceneCtx.current = null
    }
  }, [])

  // ── Data: rebuild buildings when prop changes ─────────────────────────────
  useEffect(() => {
    const ctx = sceneCtx.current
    if (!ctx) return

    // Remove old buildings
    const dead = ctx.scene.children.filter((c) => c.userData.isBuilding)
    dead.forEach((c) => {
      ctx.scene.remove(c)
      const m = c as THREE.Mesh | THREE.LineSegments
      m.geometry?.dispose()
    })

    const list = buildings.length > 0 ? buildings : [PLACEHOLDER]
    const flagship = list.find((b) => b.flagship)
    const rest     = list.filter((b) => !b.flagship)

    if (flagship) addBuilding(ctx.scene, flagship, 0, 0)

    const R = 4
    rest.forEach((b, i) => {
      const a = (i / rest.length) * Math.PI * 2
      addBuilding(ctx.scene, b, Math.cos(a) * R, Math.sin(a) * R)
    })
  }, [buildings])

  return <div ref={mountRef} className="w-full h-full" />
}
