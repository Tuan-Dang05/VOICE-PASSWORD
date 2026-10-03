import { useEffect, useRef, useState } from 'react'
import { encodePcmWav } from '../lib/pcmWav'

export interface CapturedRecording {
  blob: Blob
  durationSeconds: number
}

export function useRecorder(maxSeconds = 5) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [sampleRate, setSampleRate] = useState(0)
  const [error, setError] = useState('')
  const [levels, setLevels] = useState<number[]>(() => Array.from({ length: 24 }, (_, index) => 18 + Math.sin(index * 0.85) * 8))
  const streamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const captureRef = useRef<AudioWorkletNode | null>(null)
  const chunksRef = useRef<Float32Array[]>([])
  const framesRef = useRef(0)
  const animationRef = useRef<number | null>(null)
  const stopPromiseRef = useRef<Promise<CapturedRecording> | null>(null)

  function releaseAudio() {
    if (animationRef.current !== null) cancelAnimationFrame(animationRef.current)
    animationRef.current = null
    captureRef.current?.disconnect()
    captureRef.current = null
    streamRef.current?.getTracks().forEach(track => track.stop())
    streamRef.current = null
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') void audioContextRef.current.close()
    audioContextRef.current = null
  }

  useEffect(() => () => releaseAudio(), [])

  useEffect(() => {
    if (!recording) return
    const timer = window.setInterval(() => setSeconds(value => value + 1), 1000)
    return () => window.clearInterval(timer)
  }, [recording])

  async function start() {
    setError('')
    if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext || !window.AudioWorkletNode) {
      setError('Trình duyệt không hỗ trợ thu WAV. Hãy dùng Chrome hoặc Edge mới trên localhost.')
      throw new Error('unsupported_recorder')
    }
    releaseAudio()
    chunksRef.current = []
    framesRef.current = 0
    stopPromiseRef.current = null
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
      streamRef.current = stream
      const context = new AudioContext()
      audioContextRef.current = context
      await context.audioWorklet.addModule(`${import.meta.env.BASE_URL}audio/voice-capture-processor.js`)
      const source = context.createMediaStreamSource(stream)
      const analyser = context.createAnalyser()
      analyser.fftSize = 64
      analyser.smoothingTimeConstant = 0.78
      source.connect(analyser)
      const capture = new AudioWorkletNode(context, 'voice-capture', { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1] })
      captureRef.current = capture
      capture.port.onmessage = (event: MessageEvent<{ samples?: Float32Array }>) => {
        if (event.data.samples) {
          chunksRef.current.push(event.data.samples)
          framesRef.current += event.data.samples.length
        }
      }
      analyser.connect(capture)
      const mute = context.createGain()
      mute.gain.value = 0
      capture.connect(mute).connect(context.destination)
      await context.resume()
      const frequencyData = new Uint8Array(analyser.frequencyBinCount)
      const draw = () => {
        analyser.getByteFrequencyData(frequencyData)
        setLevels(Array.from({ length: 24 }, (_, index) => {
          const sourceIndex = Math.min(frequencyData.length - 1, Math.floor(index * frequencyData.length / 24))
          return Math.max(8, Math.round((frequencyData[sourceIndex] / 255) * 88))
        }))
        animationRef.current = requestAnimationFrame(draw)
      }
      draw()
      setSampleRate(context.sampleRate)
      setSeconds(0)
      setRecording(true)
    } catch (cause) {
      releaseAudio()
      setError('Không thể thu âm. Hãy kiểm tra quyền microphone rồi thử lại.')
      throw cause
    }
  }

  function stop(): Promise<CapturedRecording> {
    if (stopPromiseRef.current) return stopPromiseRef.current
    const capture = captureRef.current
    const context = audioContextRef.current
    if (!capture || !context) return Promise.reject(new Error('Chưa bắt đầu thu âm'))
    stopPromiseRef.current = new Promise<CapturedRecording>((resolve, reject) => {
      let finished = false
      const finish = () => {
        if (finished) return
        finished = true
        window.clearTimeout(timeout)
        try {
          const durationSeconds = framesRef.current / context.sampleRate
          const blob = encodePcmWav(chunksRef.current, context.sampleRate)
          resolve({ blob, durationSeconds })
        } catch (cause) {
          setError('Bản ghi không có âm thanh. Hãy thu lại.')
          reject(cause)
        } finally {
          releaseAudio()
          setRecording(false)
        }
      }
      capture.port.onmessage = (event: MessageEvent<{ samples?: Float32Array; done?: boolean }>) => {
        if (event.data.samples) {
          chunksRef.current.push(event.data.samples)
          framesRef.current += event.data.samples.length
        }
        if (event.data.done) finish()
      }
      const timeout = window.setTimeout(finish, 1500)
      capture.port.postMessage('stop')
    })
    return stopPromiseRef.current
  }

  return { recording, seconds, maxSeconds, sampleRate, levels, error, start, stop }
}
