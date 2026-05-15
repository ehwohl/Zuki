export function initGrainTexture() {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 256
  const ctx = canvas.getContext('2d')!
  const img = ctx.createImageData(256, 256)
  for (let i = 0; i < img.data.length; i += 4) {
    const v = (Math.random() * 255) | 0
    img.data[i] = v
    img.data[i + 1] = v
    img.data[i + 2] = v
    img.data[i + 3] = 18
  }
  ctx.putImageData(img, 0, 0)
  document.documentElement.style.setProperty('--noise-url', `url(${canvas.toDataURL()})`)
}
