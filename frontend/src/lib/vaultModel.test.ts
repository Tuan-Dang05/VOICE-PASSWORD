import { describe, expect, it } from 'vitest'
import { Box3, Vector3 } from 'three'
import { createVaultModel, vaultPose } from './vaultModel'

describe('vault mechanical model', () => {
  it('retracts bolts before opening and keeps them retracted until the door closes', () => {
    for (let step = 0; step <= 100; step++) {
      const pose = vaultPose(step / 100)
      if (Math.abs(pose.door) > 0) expect(pose.bolts).toBe(1)
    }
    expect(vaultPose(0)).toEqual({ handle: 0, bolts: 0, door: -0 })
    expect(vaultPose(1).door).toBeCloseTo(-105 * Math.PI / 180)
  })

  it('builds solid geometry and rotates the door around a fixed hinge', () => {
    const model = createVaultModel()
    const anchor = model.hinge.position.clone()
    const bounds = new Box3().setFromObject(model.root).getSize(new Vector3())
    expect(bounds.x).toBeGreaterThan(2)
    expect(bounds.y).toBeGreaterThan(3)
    expect(bounds.z).toBeGreaterThan(1.7)
    model.applyPose(1)
    expect(model.hinge.position.equals(anchor)).toBe(true)
    expect(model.bolts.every(bolt => bolt.position.x < 2)).toBe(true)
    model.applyPose(0)
    expect(Math.abs(model.hinge.rotation.y)).toBe(0)
    expect(model.bolts.every(bolt => bolt.position.x === 2.06)).toBe(true)
    model.dispose()
  })
})
