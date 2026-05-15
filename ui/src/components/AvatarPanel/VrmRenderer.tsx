import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm'
import type { VRM } from '@pixiv/three-vrm'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

interface Props {
  vrmUrl?: string
}

export default function VrmRenderer({ vrmUrl }: Props) {
  const mountRef = useRef<HTMLDivElement>(null)
  const stateRef = useRef<{
    renderer: THREE.WebGLRenderer
    scene: THREE.Scene
    camera: THREE.PerspectiveCamera
    vrm: VRM | null
    animId: number
  } | null>(null)

  useEffect(() => {
    const el = mountRef.current
    if (!el) return

    const W = el.clientWidth
    const H = el.clientHeight

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(W, H)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    el.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(35, W / H, 0.1, 100)
    camera.position.set(0, 1.3, 2.2)
    camera.lookAt(0, 1.1, 0)

    const ambientLight = new THREE.AmbientLight(0x00f5ff, 0.3)
    const dirLight = new THREE.DirectionalLight(0xe8eaf0, 1.2)
    dirLight.position.set(1, 2, 2)
    scene.add(ambientLight, dirLight)

    let vrm: VRM | null = null

    if (vrmUrl) {
      const loader = new GLTFLoader()
      loader.register((p) => new VRMLoaderPlugin(p))
      loader.load(vrmUrl, (gltf) => {
        vrm = gltf.userData.vrm as VRM
        VRMUtils.rotateVRM0(vrm)
        scene.add(vrm.scene)
      })
    } else {
      // Placeholder: stylized avatar silhouette
      const headGeo = new THREE.SphereGeometry(0.18, 16, 16)
      const mat = new THREE.MeshPhongMaterial({
        color: 0x00f5ff,
        emissive: 0x003040,
        transparent: true,
        opacity: 0.85,
        wireframe: false,
      })
      const head = new THREE.Mesh(headGeo, mat)
      head.position.set(0, 1.55, 0)

      const bodyGeo = new THREE.CylinderGeometry(0.12, 0.18, 0.5, 12)
      const body = new THREE.Mesh(bodyGeo, mat)
      body.position.set(0, 1.1, 0)

      const wireGeo = new THREE.SphereGeometry(0.185, 12, 12)
      const wireMat = new THREE.MeshBasicMaterial({ color: 0x00f5ff, wireframe: true, transparent: true, opacity: 0.3 })
      const wireframe = new THREE.Mesh(wireGeo, wireMat)
      wireframe.position.copy(head.position)

      scene.add(head, body, wireframe)
    }

    let animId = 0
    const clock = new THREE.Clock()
    const animate = () => {
      animId = requestAnimationFrame(animate)
      const delta = clock.getDelta()
      vrm?.update(delta)
      renderer.render(scene, camera)
    }
    animate()

    stateRef.current = { renderer, scene, camera, vrm, animId }

    return () => {
      cancelAnimationFrame(animId)
      renderer.dispose()
      el.removeChild(renderer.domElement)
    }
  }, [vrmUrl])

  // Apply pulse-intensity as emissive modulation via CSS var read
  useEffect(() => {
    const frame = requestAnimationFrame(function loop() {
      const intensity = parseFloat(
        getComputedStyle(document.documentElement).getPropertyValue('--pulse-intensity') || '0',
      )
      const state = stateRef.current
      if (state && intensity > 0) {
        state.scene.traverse((obj) => {
          if ((obj as THREE.Mesh).isMesh) {
            const mat = (obj as THREE.Mesh).material
            if (mat instanceof THREE.MeshPhongMaterial) {
              mat.emissiveIntensity = intensity * 0.8
            }
          }
        })
      }
      requestAnimationFrame(loop)
    })
    return () => cancelAnimationFrame(frame)
  }, [])

  return <div ref={mountRef} className="w-full h-full" />
}
