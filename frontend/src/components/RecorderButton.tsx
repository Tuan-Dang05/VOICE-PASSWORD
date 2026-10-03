import { useEffect, useState } from 'react'
import { useRecorder } from '../hooks/useRecorder'

interface Props {
  disabled?: boolean
  onRecorded: (blob: Blob) => Promise<boolean | void>
  onStart?: () => void
  onCaptured?: () => void
  label?: string
  submitLabel?: string
  maxSeconds?: number
  minSeconds?: number
}

export function RecorderButton({ disabled, onRecorded, onStart, onCaptured, label = 'Bắt đầu nói', submitLabel = 'Dùng bản ghi này', maxSeconds = 8, minSeconds = 1 }: Props) {
  const recorder = useRecorder(maxSeconds)
  const [busy, setBusy] = useState(false)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState('')
  const [recordedSeconds, setRecordedSeconds] = useState(0)

  function clearPreview() {
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    setAudioUrl('')
    setRecordedBlob(null)
  }

  useEffect(() => () => { if (audioUrl) URL.revokeObjectURL(audioUrl) }, [audioUrl])

  async function start() {
    clearPreview()
    try { await recorder.start(); onStart?.() } catch { /* hook exposes user-friendly error */ }
  }

  async function stop() {
    try {
      const { blob, durationSeconds } = await recorder.stop()
      setRecordedSeconds(durationSeconds)
      setRecordedBlob(blob)
      setAudioUrl(URL.createObjectURL(blob))
      onCaptured?.()
    } catch { /* hook exposes user-friendly error */ }
  }

  async function submit() {
    if (!recordedBlob || recordedSeconds < minSeconds) return
    setBusy(true)
    try { if (await onRecorded(recordedBlob) !== false) clearPreview() } finally { setBusy(false) }
  }

  useEffect(() => {
    if (recorder.recording && recorder.seconds >= maxSeconds && !busy) void stop()
  // stop is intentionally driven only by recorder state
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recorder.recording, recorder.seconds, busy, maxSeconds])

  return (
    <div className="recorder">
      <div className={`frequency-visualizer ${recorder.recording ? 'active' : recordedBlob ? 'captured' : ''}`} aria-label="Mức tần số âm thanh">
        <div className="frequency-meta"><span>{recorder.recording ? 'ĐANG THU TÍN HIỆU' : recordedBlob ? 'BẢN GHI SẴN SÀNG' : 'VOICE FREQUENCY'}</span><b>{recorder.recording ? `${recorder.seconds}s / ${recorder.maxSeconds}s` : `${recorder.sampleRate ? Math.round(recorder.sampleRate / 1000) : 16} kHz · WAV`}</b></div>
        <div className="frequency-bars" aria-hidden="true">
          {recorder.levels.map((level, index) => <i key={index} style={{ height: `${recordedBlob && !recorder.recording ? 18 + Math.sin(index * 1.35) * 10 + (index % 4) * 4 : level}%` }} />)}
        </div>
      </div>
      {recorder.recording ? (
        <button className="record-button recording" onClick={stop} type="button">
          <span className="record-dot" /> Dừng thu · {recorder.seconds}s
        </button>
      ) : recordedBlob && audioUrl ? (
        <div className="recording-preview">
          <audio key={audioUrl} controls preload="auto" src={audioUrl}>Trình duyệt không hỗ trợ phát audio.</audio>
          <div className="preview-actions">
            <button className="secondary" onClick={start} disabled={busy} type="button">Thu lại</button>
            <button className="primary" onClick={submit} disabled={busy || recordedSeconds < minSeconds} type="button">{busy ? 'Đang gửi…' : submitLabel}</button>
          </div>
        </div>
      ) : (
        <button className="record-button" onClick={start} disabled={disabled || busy} type="button">
          <span className="mic-icon">●</span> {label}
        </button>
      )}
      <small>Thu từ {minSeconds}–{maxSeconds} giây. Bạn có thể nghe lại hoặc thu lại trước khi gửi.</small>
      {recordedBlob && recordedSeconds < minSeconds && <p className="inline-error">Bản ghi quá ngắn; hãy thu lại ít nhất {minSeconds} giây.</p>}
      {recorder.error && <p className="inline-error">{recorder.error}</p>}
    </div>
  )
}
