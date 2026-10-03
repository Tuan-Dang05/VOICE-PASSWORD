import { Box3, MathUtils, PerspectiveCamera, Vector3 } from 'three'

// Fit every corner of the animated model, including the open door, at any orbit angle.
export function fitVaultCamera(camera: PerspectiveCamera, target: Vector3, bounds: Box3) {
  camera.updateMatrixWorld()
  const right = new Vector3().setFromMatrixColumn(camera.matrixWorld, 0)
  const up = new Vector3().setFromMatrixColumn(camera.matrixWorld, 1)
  const back = new Vector3().setFromMatrixColumn(camera.matrixWorld, 2)
  const tanY = Math.tan(MathUtils.degToRad(camera.fov / 2)) / camera.zoom
  const tanX = tanY * camera.aspect
  let distance = 0
  for (const x of [bounds.min.x, bounds.max.x]) {
    for (const y of [bounds.min.y, bounds.max.y]) {
      for (const z of [bounds.min.z, bounds.max.z]) {
        const point = new Vector3(x, y, z).sub(target)
        distance = Math.max(distance,
          Math.abs(point.dot(right)) / (tanX * 0.86) + point.dot(back),
          Math.abs(point.dot(up)) / (tanY * 0.86) + point.dot(back))
      }
    }
  }
  camera.position.copy(target).addScaledVector(back, distance)
  camera.updateMatrixWorld()
}
