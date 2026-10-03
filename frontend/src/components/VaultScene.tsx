import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { createVaultModel } from '../lib/vaultModel'
import { createVaultTextures } from '../lib/vaultTextures'
import { fitVaultCamera } from '../lib/vaultFraming'
import type { SafeState } from '../types'

const display: Record<SafeState, [string, string]> = {
  locked: ['LOCKED', '#ffc46b'], listening: ['LISTENING', '#81c7ff'],
  processing: ['PROCESSING', '#c6b5ff'], denied: ['ACCESS DENIED', '#ff9588'],
  granted: ['ACCESS GRANTED', '#82e7b3'], unlocked: ['UNLOCKED', '#82e7b3'],
}

export default function VaultScene({ state, name, preview = false, backView = false }: { state: SafeState; name?: string; preview?: boolean; backView?: boolean }) {
  const container = useRef<HTMLDivElement>(null)
  const current = useRef({ state, name, preview, backView })
  const [failed, setFailed] = useState(false)
  useEffect(() => { current.current = { state, name, preview, backView } }, [state, name, preview, backView])

  useEffect(() => {
    const host = container.current
    if (!host) return
    let renderer: THREE.WebGLRenderer
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }) }
    catch { setFailed(true); return }
    renderer.setPixelRatio(Math.min(Math.max(window.devicePixelRatio, 2), 2.5))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.0
    renderer.domElement.setAttribute('aria-label', 'Mô hình két sắt 3D; kéo để xoay góc nhìn')
    renderer.domElement.setAttribute('role', 'img')
    host.appendChild(renderer.domElement)
    const onContextLost = (event: Event) => { event.preventDefault(); renderer.setAnimationLoop(null); setFailed(true) }
    renderer.domElement.addEventListener('webglcontextlost', onContextLost)
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50)
    const environment = new RoomEnvironment()
    const pmrem = new THREE.PMREMGenerator(renderer)
    const envTarget = pmrem.fromScene(environment, 0.06)
    scene.environment = envTarget.texture
    environment.dispose()
    pmrem.dispose()
    scene.add(new THREE.HemisphereLight(0xffffff, 0x657466, 1.3))
    const key = new THREE.DirectionalLight(0xfff8e8, 2.8)
    key.position.set(-3, 6, 5)
    key.castShadow = true
    key.shadow.mapSize.set(1024, 1024)
    Object.assign(key.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: 0.1, far: 20 })
    key.shadow.normalBias = 0.03
    scene.add(key)
    const fill = new THREE.DirectionalLight(0xd9e8ff, 1.2)
    fill.position.set(5, 2, -3)
    scene.add(fill)
    const interiorLight = new THREE.PointLight(0xc4ffda, 0, 4)
    interiorLight.position.set(0, 0.9, 0.35)
    scene.add(interiorLight)
    const floorGeometry = new THREE.PlaneGeometry(200, 200)
    const floorMaterial = new THREE.ShadowMaterial({ opacity: 0.16 })
    const floor = new THREE.Mesh(floorGeometry, floorMaterial)
    floor.rotation.x = -Math.PI / 2
    floor.position.y = -1.65
    floor.receiveShadow = true
    scene.add(floor)
    const model = createVaultModel()
    const textures = createVaultTextures(renderer.capabilities.getMaxAnisotropy())
    model.banknoteMaterial.map = textures.banknote
    model.moneyLabelMaterial.map = textures.moneyLabel
    model.brandMaterial.map = textures.brand
    scene.add(model.root)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(0, -0.02, 0.1)
    controls.enablePan = false
    controls.enableZoom = false
    controls.enableDamping = true
    controls.minPolarAngle = Math.PI / 3
    controls.maxPolarAngle = Math.PI / 2 - 0.04
    let fitDistance = 6
    const positionCamera = () => {
      const angle = current.current.backView ? Math.PI + 0.08 : 0.24
      camera.position.set(Math.sin(angle) * fitDistance, fitDistance * 0.28, Math.cos(angle) * fitDistance + 0.1)
      controls.update()
    }
    const resize = () => {
      const width = host.clientWidth
      const height = host.clientHeight
      if (!width || !height) return
      renderer.setSize(width, height)
      camera.aspect = width / height
      // Fit the actual safe, not the old oversized empty scene around it.
      const halfFov = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))
      fitDistance = Math.max(3.95 / (2 * halfFov), 3.35 / (2 * halfFov * camera.aspect))
      positionCamera()
      camera.updateProjectionMatrix()
      controls.update()
    }
    const observer = new ResizeObserver(resize)
    observer.observe(host)
    resize()
    const screen = document.createElement('canvas')
    screen.width = 1536; screen.height = 512
    const ctx = screen.getContext('2d')!
    ctx.scale(2, 2)
    const screenTexture = new THREE.CanvasTexture(screen)
    screenTexture.colorSpace = THREE.SRGBColorSpace
    screenTexture.anisotropy = renderer.capabilities.getMaxAnisotropy()
    screenTexture.generateMipmaps = false
    screenTexture.minFilter = THREE.LinearFilter
    model.screenMaterial.map = screenTexture
    const plate = document.createElement('canvas')
    plate.width = 1024; plate.height = 160
    const plateCtx = plate.getContext('2d')!
    plateCtx.scale(2, 2)
    plateCtx.fillStyle = '#ccd4ca'; plateCtx.fillRect(0, 0, 512, 80)
    plateCtx.fillStyle = '#142e20'; plateCtx.textAlign = 'center'; plateCtx.font = 'bold 45px Arial'
    plateCtx.fillText('KÉT SẮT TUẤN ĐẶNG', 256, 56)
    const plateTexture = new THREE.CanvasTexture(plate)
    plateTexture.colorSpace = THREE.SRGBColorSpace
    plateTexture.generateMipmaps = false
    plateTexture.minFilter = THREE.LinearFilter
    plateTexture.anisotropy = renderer.capabilities.getMaxAnisotropy()
    model.nameplateMaterial.map = plateTexture
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let progress = 0
    let lastFrame = 0
    let lastLabel = ''
    let lastBackView = current.current.backView
    const modelBounds = new THREE.Box3()
    renderer.setAnimationLoop((time: number) => {
      const props = current.current
      if (props.backView !== lastBackView) {
        lastBackView = props.backView
        positionCamera()
      }
      const open = props.preview || props.state === 'granted' || props.state === 'unlocked'
      const delta = lastFrame ? Math.min((time - lastFrame) / 1000, 0.05) : 0
      lastFrame = time
      progress = reducedMotion.matches ? Number(open) : THREE.MathUtils.clamp(progress + (open ? 1 : -1) * delta / 2.4, 0, 1)
      model.applyPose(progress)
      interiorLight.intensity = THREE.MathUtils.smoothstep(progress, 0.4, 0.9) * 2.5
      const labelKey = `${props.state}|${props.name}|${props.preview}`
      if (labelKey !== lastLabel) {
        lastLabel = labelKey
        const [label, color] = props.preview ? ['XEM THỬ', '#81c7ff'] : display[props.state]
        ctx.fillStyle = '#14251f'; ctx.fillRect(0, 0, 768, 256)
        ctx.textAlign = 'center'
        ctx.fillStyle = '#ffffff'; ctx.font = 'bold 41px Arial'; ctx.fillText('KÉT SẮT TUẤN ĐẶNG', 384, 49)
        ctx.fillStyle = color; ctx.font = `bold ${label.length > 10 ? 66 : 88}px Arial`; ctx.fillText(label, 384, 151, 726)
        ctx.fillStyle = '#ffffff'; ctx.font = 'bold 37px Arial'
        ctx.fillText(props.preview ? 'Chỉ xem thử chuyển động' : (props.name || 'Chưa có mẫu giọng').slice(0, 35), 384, 205, 690)
        screenTexture.needsUpdate = true
        model.indicatorMaterial.color.set(color)
        model.indicatorMaterial.emissive.set(color)
      }
      controls.update()
      model.root.updateMatrixWorld(true)
      modelBounds.setFromObject(model.root)
      fitVaultCamera(camera, controls.target, modelBounds)
      renderer.render(scene, camera)
    })
    return () => {
      renderer.setAnimationLoop(null)
      renderer.domElement.removeEventListener('webglcontextlost', onContextLost)
      observer.disconnect(); controls.dispose(); model.dispose()
      screenTexture.dispose(); plateTexture.dispose(); envTarget.dispose()
      textures.dispose()
      floorGeometry.dispose(); floorMaterial.dispose(); key.shadow.map?.dispose()
      renderer.dispose()
      renderer.forceContextLoss()
      renderer.domElement.remove()
    }
  }, [])

  return <div className="vault-webgl" ref={container}>
    {failed && <div className="vault-render-error">Không thể hiển thị 3D. Hãy bật tăng tốc đồ họa trong trình duyệt rồi tải lại trang. Két vẫn xác thực theo trạng thái bên dưới.</div>}
  </div>
}
