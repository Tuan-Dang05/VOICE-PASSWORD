import { describe, expect, it } from 'vitest'
import { encodePcmWav } from './pcmWav'

describe('WAV recording', () => {
  it('writes a complete one-second mono PCM file with readable duration metadata', async () => {
    const rate = 16000
    const samples = new Float32Array(rate)
    samples[0] = 0.5
    samples[rate - 1] = -0.5
    const blob = encodePcmWav([samples.subarray(0, 4000), samples.subarray(4000)], rate)
    const data = new DataView(await blob.arrayBuffer())
    const tag = (offset: number) => String.fromCharCode(...new Uint8Array(data.buffer, offset, 4))
    expect(blob.type).toBe('audio/wav')
    expect(blob.size).toBe(44 + rate * 2)
    expect(tag(0)).toBe('RIFF')
    expect(tag(8)).toBe('WAVE')
    expect(tag(36)).toBe('data')
    expect(data.getUint32(24, true)).toBe(rate)
    expect(data.getUint16(22, true)).toBe(1)
    expect(data.getUint16(34, true)).toBe(16)
    expect(data.getUint32(40, true) / (rate * 2)).toBe(1)
    expect(data.getInt16(44, true)).toBe(16384)
    expect(data.getInt16(blob.size - 2, true)).toBe(-16384)
  })

  it('rejects an empty capture rather than presenting a 0:00 preview', () => {
    expect(() => encodePcmWav([], 48000)).toThrow('Không có dữ liệu âm thanh')
  })
})
