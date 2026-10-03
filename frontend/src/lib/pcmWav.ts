/** Encode mono microphone samples as a standard, seekable PCM WAV file. */
export function encodePcmWav(chunks: Float32Array[], sampleRate: number): Blob {
  if (!Number.isFinite(sampleRate) || sampleRate <= 0) throw new Error('Sample rate không hợp lệ')
  const sampleCount = chunks.reduce((total, chunk) => total + chunk.length, 0)
  if (!sampleCount) throw new Error('Không có dữ liệu âm thanh trong bản ghi')

  const buffer = new ArrayBuffer(44 + sampleCount * 2)
  const view = new DataView(buffer)
  const writeText = (offset: number, value: string) => {
    for (let index = 0; index < value.length; index++) view.setUint8(offset + index, value.charCodeAt(index))
  }
  writeText(0, 'RIFF')
  view.setUint32(4, 36 + sampleCount * 2, true)
  writeText(8, 'WAVE')
  writeText(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeText(36, 'data')
  view.setUint32(40, sampleCount * 2, true)

  let offset = 44
  for (const chunk of chunks) {
    for (const value of chunk) {
      const clipped = Math.max(-1, Math.min(1, value))
      view.setInt16(offset, clipped < 0 ? Math.round(clipped * 32768) : Math.round(clipped * 32767), true)
      offset += 2
    }
  }
  return new Blob([buffer], { type: 'audio/wav' })
}
