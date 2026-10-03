import * as THREE from 'three'

// Locally served banknote image and high-contrast plaques for the 3D scene.
export function createVaultTextures(anisotropy: number) {
  const textures: THREE.Texture[] = []
  let disposed = false
  function draw(width: number, height: number, paint: (ctx: CanvasRenderingContext2D) => void) {
    const canvas = document.createElement('canvas')
    canvas.width = width; canvas.height = height
    const ctx = canvas.getContext('2d')!
    paint(ctx)
    const texture = new THREE.CanvasTexture(canvas)
    texture.colorSpace = THREE.SRGBColorSpace
    texture.anisotropy = anisotropy
    textures.push(texture)
    return texture
  }
  const banknote = new THREE.TextureLoader().load(`${import.meta.env.BASE_URL}textures/usd-100-front.png`, texture => {
    if (disposed) texture.dispose()
  })
  banknote.colorSpace = THREE.SRGBColorSpace
  banknote.anisotropy = anisotropy
  textures.push(banknote)
  const moneyLabel = draw(512, 128, ctx => {
    ctx.fillStyle = '#ede2bb'; ctx.fillRect(0, 0, 512, 128)
    ctx.fillStyle = '#5b4827'; ctx.font = 'bold 65px Time new Roman'; ctx.textAlign = 'center'; ctx.fillText('$10,000', 256, 87)
  })
  const brand = draw(2048, 1152, ctx => {
    ctx.fillStyle = '#102a22'; ctx.fillRect(0, 0, 2048, 1152)
    ctx.strokeStyle = '#efd38f'; ctx.lineWidth = 8; ctx.strokeRect(30, 30, 1988, 1092)
    ctx.fillStyle = '#ffe4a1'; ctx.textAlign = 'center'
    ctx.font = 'bold 184px Time new Roman'; ctx.fillText('Két Sắt Tuấn Đặng', 1024, 385)
    ctx.fillStyle = '#ffffff'; ctx.font = 'bold 110px Time new Roman'
    ctx.fillText('An toàn - Uy tín', 1024, 630)
    ctx.fillText('Đặt lên hàng đầu', 1024, 803)
    ctx.strokeStyle = '#efd38f'; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(700, 973); ctx.lineTo(1348, 973); ctx.stroke()
  })
  brand.generateMipmaps = false
  brand.minFilter = THREE.LinearFilter
  return { banknote, moneyLabel, brand, dispose: () => { disposed = true; textures.forEach(texture => texture.dispose()) } }
}
