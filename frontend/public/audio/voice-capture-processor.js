class VoiceCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.chunks = []
    this.sampleCount = 0
    this.capturing = true
    this.port.onmessage = (event) => {
      if (event.data === 'stop') {
        this.capturing = false
        this.flush()
        this.port.postMessage({ done: true })
      }
    }
  }

  flush() {
    if (!this.sampleCount) return
    const samples = new Float32Array(this.sampleCount)
    let offset = 0
    for (const chunk of this.chunks) {
      samples.set(chunk, offset)
      offset += chunk.length
    }
    this.port.postMessage({ samples }, [samples.buffer])
    this.chunks = []
    this.sampleCount = 0
  }

  process(inputs) {
    const input = inputs[0]
    if (this.capturing && input?.length && input[0]?.length) {
      const samples = new Float32Array(input[0])
      this.chunks.push(samples)
      this.sampleCount += samples.length
      if (this.sampleCount >= 4096) this.flush()
    }
    return true
  }
}

registerProcessor('voice-capture', VoiceCaptureProcessor)
