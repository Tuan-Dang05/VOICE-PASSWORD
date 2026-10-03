import { describe, expect, it } from 'vitest'
import { Box3, PerspectiveCamera, Vector3 } from 'three'
import { createVaultModel } from './vaultModel'
import { fitVaultCamera } from './vaultFraming'

describe('camera framing', () => {
  it('keeps the entire safe and moving door inside desktop and mobile viewports through a full orbit', () => {
    const model = createVaultModel()
    const target = new Vector3(0, -0.02, 0.1)
    try {
      for (const aspect of [0.65, 1, 1.45]) {
        const camera = new PerspectiveCamera(38, aspect, 0.1, 50)
        for (const progress of [0, 0.4, 0.65, 1]) {
          model.applyPose(progress)
          const bounds = new Box3().setFromObject(model.root)
          for (let i = 0; i < 12; i++) {
            const angle = i * Math.PI / 6
            camera.position.set(Math.sin(angle) * 6, 2.5, Math.cos(angle) * 6)
            camera.lookAt(target)
            fitVaultCamera(camera, target, bounds)
            for (const x of [bounds.min.x, bounds.max.x]) {
              for (const y of [bounds.min.y, bounds.max.y]) {
                for (const z of [bounds.min.z, bounds.max.z]) {
                  const projected = new Vector3(x, y, z).project(camera)
                  expect(Math.abs(projected.x)).toBeLessThanOrEqual(0.861)
                  expect(Math.abs(projected.y)).toBeLessThanOrEqual(0.861)
                  expect(projected.z).toBeGreaterThan(-1)
                  expect(projected.z).toBeLessThan(1)
                }
              }
            }
          }
        }
      }
    } finally { model.dispose() }
  })
})
