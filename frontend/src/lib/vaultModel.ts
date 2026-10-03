import * as THREE from 'three'
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js'

const smooth = (value: number) => {
  const x = THREE.MathUtils.clamp(value, 0, 1)
  return x * x * (3 - 2 * x)
}

// One reversible mechanical sequence: turn the handle, retract bolts, swing door.
export function vaultPose(progress: number) {
  return {
    handle: smooth(progress / 0.22) * Math.PI / 2,
    bolts: smooth((progress - 0.18) / 0.16),
    door: -smooth((progress - 0.34) / 0.66) * THREE.MathUtils.degToRad(105),
  }
}

export function createVaultModel() {
  const root = new THREE.Group()
  root.name = 'VoiceVault'
  const geometries = new Set<THREE.BufferGeometry>()
  const materials = new Set<THREE.Material>()
  const metal = (color: number, roughness = 0.35, metalness = 0.65) => {
    const material = new THREE.MeshStandardMaterial({ color, roughness, metalness })
    materials.add(material)
    return material
  }
  const enamel = metal(0xaebdb2, 0.32, 0.48)
  const silver = metal(0xdce2df, 0.2, 0.92)
  const darkMetal = metal(0x35443e, 0.32, 0.72)
  const felt = metal(0x314b40, 0.95, 0)
  const rubber = metal(0x192922, 0.86, 0)
  const paper = metal(0xf3eee0, 0.85, 0)
  const banknoteMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.85, metalness: 0 })
  const moneyLabelMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false })
  const brandMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false })
  materials.add(banknoteMaterial); materials.add(moneyLabelMaterial); materials.add(brandMaterial)
  const indicatorMaterial = metal(0xffc46b, 0.4, 0.1)
  indicatorMaterial.emissive.set(0xffc46b)
  indicatorMaterial.emissiveIntensity = 0.65

  function mesh(geometry: THREE.BufferGeometry, material: THREE.Material, parent: THREE.Object3D, x: number, y: number, z: number) {
    geometries.add(geometry)
    const item = new THREE.Mesh(geometry, material)
    item.position.set(x, y, z)
    item.castShadow = true
    item.receiveShadow = true
    parent.add(item)
    return item
  }
  function box(parent: THREE.Object3D, size: [number, number, number], pos: [number, number, number], material: THREE.Material, radius = 0.04) {
    return mesh(new RoundedBoxGeometry(...size, 3, Math.min(radius, ...size.map(n => n / 3))), material, parent, ...pos)
  }
  function cylinder(parent: THREE.Object3D, radius: number, length: number, pos: [number, number, number], material: THREE.Material, axis: 'x' | 'y' | 'z' = 'z') {
    const part = mesh(new THREE.CylinderGeometry(radius, radius, length, 32), material, parent, ...pos)
    if (axis === 'z') part.rotation.x = Math.PI / 2
    if (axis === 'x') part.rotation.z = Math.PI / 2
    return part
  }

  // Hollow shell: each wall is a separate solid, so the door exposes a real cavity.
  box(root, [0.19, 3.04, 1.7], [-1.14, 0, 0], enamel)
  box(root, [0.19, 3.04, 1.7], [1.14, 0, 0], enamel)
  box(root, [2.29, 0.19, 1.7], [0, 1.43, 0], enamel)
  box(root, [2.29, 0.19, 1.7], [0, -1.43, 0], enamel)
  box(root, [2.16, 2.69, 0.16], [0, 0, -0.77], enamel)
  box(root, [2.09, 2.64, 0.025], [0, 0, -0.674], felt, 0.006)
  box(root, [2.09, 0.035, 1.38], [0, -1.31, -0.02], felt)
  box(root, [2.08, 0.075, 1.35], [0, -0.22, -0.02], darkMetal)
  box(root, [2.06, 0.018, 1.32], [0, -0.17, -0.02], felt)
  // Recessed frame and door seal.
  for (const x of [-1.065, 1.065]) box(root, [0.055, 2.75, 0.10], [x, 0, 0.77], rubber, 0.012)
  for (const y of [-1.34, 1.34]) box(root, [2.14, 0.055, 0.10], [0, y, 0.77], rubber, 0.012)
  for (const x of [-0.88, 0.88]) {
    for (const z of [-0.55, 0.55]) cylinder(root, 0.16, 0.15, [x, -1.57, z], darkMetal, 'y')
  }
  // USD bundles, with accurate banknote proportions and fine paper edges.
  const money = new THREE.Group()
  money.name = 'USD cash bundles'
  root.add(money)
  const strap = metal(0xe5d3a9, 0.95, 0)
  const paperEdge = metal(0xb4b9a6, 0.95, 0)
  for (const shelf of [-1.285, -0.152]) {
    for (const x of [-0.51, 0.51]) {
      for (let level = 0; level < 2; level++) {
        const bundle = new THREE.Group()
        bundle.position.set(x + level * 0.018, shelf + level * 0.125, 0.22 + level * 0.013)
        bundle.rotation.y = x < 0 ? 0.06 : -0.04
        money.add(bundle)
        box(bundle, [0.94, 0.11, 0.397], [0, 0.055, 0], paper, 0.003)
        for (let line = 1; line < 22; line++) {
          box(bundle, [0.939, 0.0009, 0.398], [0, line * 0.005, 0], paperEdge, 0.0002)
        }
        const note = mesh(new THREE.PlaneGeometry(0.94, 0.397), banknoteMaterial, bundle, 0, 0.112, 0)
        note.rotation.x = -Math.PI / 2
        box(bundle, [0.135, 0.116, 0.402], [0.20, 0.058, 0], strap, 0.002)
        const bandLabel = mesh(new THREE.PlaneGeometry(0.25, 0.09), moneyLabelMaterial, bundle, 0.20, 0.118, 0)
        bandLabel.rotation.x = -Math.PI / 2
        bandLabel.rotation.z = Math.PI / 2
      }
    }
  }
  // Branded metal plaque on the exterior rear; a second plaque lines the cavity.
  box(root, [2.00, 1.20, 0.045], [0, 0.35, -0.876], silver)
  const rearBrand = mesh(new THREE.PlaneGeometry(1.91, 1.075), brandMaterial, root, 0, 0.35, -0.901)
  rearBrand.rotation.y = Math.PI
  rearBrand.name = 'Két sắt Tuấn Đặng rear plaque'
  mesh(new THREE.PlaneGeometry(1.78, 1.00), brandMaterial, root, 0, 0.79, -0.651)

  const hinge = new THREE.Group()
  hinge.name = 'Door hinge'
  hinge.position.set(-1.035, 0, 0.88)
  root.add(hinge)
  box(hinge, [2.07, 2.60, 0.20], [1.035, 0, 0], enamel, 0.065)
  box(hinge, [1.97, 2.50, 0.036], [1.035, 0, 0.115], silver, 0.055)
  box(hinge, [1.91, 2.44, 0.045], [1.035, 0, 0.145], enamel, 0.048)
  box(hinge, [1.86, 2.36, 0.065], [1.035, 0, -0.13], darkMetal)
  // Lock mechanism on the inside face of the door.
  box(hinge, [0.65, 0.73, 0.09], [1.035, -0.15, -0.20], enamel)
  box(hinge, [1.63, 0.055, 0.075], [1.05, -0.14, -0.22], silver)
  box(hinge, [0.07, 1.80, 0.055], [1.04, 0, -0.23], silver)
  const bolts: THREE.Mesh[] = []
  for (const y of [-0.88, 0, 0.88]) bolts.push(cylinder(hinge, 0.085, 0.32, [2.06, y, -0.055], silver, 'x'))
  for (const y of [-0.9, 0.9]) {
    cylinder(root, 0.085, 0.37, [-1.06, y, 0.9], silver, 'y')
    for (const offset of [-0.13, 0.13]) cylinder(root, 0.088, 0.025, [-1.06, y + offset, 0.9], darkMetal, 'y')
  }
  for (const x of [0.15, 1.92]) {
    for (const y of [-1.13, 1.13]) {
      cylinder(hinge, 0.025, 0.02, [x, y, 0.18], silver)
      box(hinge, [0.03, 0.005, 0.007], [x, y, 0.194], darkMetal, 0.001)
    }
  }

  box(hinge, [1.73, 0.69, 0.075], [1.035, 0.72, 0.207], darkMetal)
  const screenMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false })
  materials.add(screenMaterial)
  mesh(new THREE.PlaneGeometry(1.62, 0.59), screenMaterial, hinge, 1.035, 0.72, 0.247)
  cylinder(hinge, 0.43, 0.095, [1.035, -0.23, 0.22], silver)
  cylinder(hinge, 0.375, 0.025, [1.035, -0.23, 0.278], darkMetal)
  for (let i = 0; i < 40; i++) {
    const angle = i / 40 * Math.PI * 2
    const tick = box(hinge, [0.012, i % 5 === 0 ? 0.046 : 0.025, 0.01], [1.035 + Math.sin(angle) * 0.345, -0.23 + Math.cos(angle) * 0.345, 0.30], silver, 0.002)
    tick.rotation.z = -angle
  }
  const handle = new THREE.Group()
  handle.position.set(1.035, -0.23, 0.325)
  hinge.add(handle)
  for (let i = 0; i < 3; i++) {
    const arm = new THREE.Group()
    arm.rotation.z = i * Math.PI * 2 / 3
    handle.add(arm)
    box(arm, [0.068, 0.33, 0.07], [0, 0.14, 0], silver, 0.025)
    cylinder(arm, 0.045, 0.12, [0, 0.29, 0.035], silver)
  }
  cylinder(handle, 0.115, 0.12, [0, 0, 0.035], silver)
  cylinder(handle, 0.075, 0.015, [0, 0, 0.103], darkMetal)
  cylinder(hinge, 0.025, 0.012, [1.035, -0.80, 0.177], indicatorMaterial)
  // Small label below the handle.
  box(hinge, [1.30, 0.24, 0.024], [1.035, -1.025, 0.176], silver, 0.01)
  const nameplateMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false })
  materials.add(nameplateMaterial)
  mesh(new THREE.PlaneGeometry(1.24, 0.194), nameplateMaterial, hinge, 1.035, -1.025, 0.191)

  function applyPose(progress: number) {
    const pose = vaultPose(progress)
    hinge.rotation.y = pose.door
    handle.rotation.z = pose.handle
    bolts.forEach(bolt => { bolt.position.x = 2.06 - pose.bolts * 0.19 })
  }
  return {
    root, hinge, handle, bolts, screenMaterial, nameplateMaterial, banknoteMaterial, moneyLabelMaterial, brandMaterial, indicatorMaterial, applyPose,
    dispose() { geometries.forEach(geometry => geometry.dispose()); materials.forEach(material => material.dispose()) },
  }
}
