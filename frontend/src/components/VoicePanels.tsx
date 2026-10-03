import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, ApiError, audioForm } from '../lib/api'
import type { SafeState, VerifyResult, VoicePassword } from '../types'
import { RecorderButton } from './RecorderButton'
import { SafeVault } from './SafeVault'

function describeError(error: unknown): string {
  if (error instanceof ApiError && typeof error.detail === 'object' && error.detail && 'message' in error.detail) return String(error.detail.message)
  return error instanceof Error ? error.message : 'Có lỗi xảy ra. Hãy thử lại.'
}

type Props = { token: string; passwords: VoicePassword[]; refresh: () => Promise<void> | void }

export function SafePanel({ token, passwords, refresh, onEnroll }: Props & { onEnroll: () => void }) {
  const active = passwords.filter(item => item.is_active && !item.requires_reenrollment)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [state, setState] = useState<SafeState>('locked')
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [message, setMessage] = useState('Bấm thu, đọc đúng câu bên dưới rồi gửi để mở két.')
  const timers = useRef<number[]>([])
  useEffect(() => () => timers.current.forEach(window.clearTimeout), [])
  useEffect(() => {
    if (!active.some(item => item.id === selectedId)) setSelectedId(active[0]?.id ?? null)
  }, [passwords, selectedId])
  const selected = active.find(item => item.id === selectedId)

  async function verify(blob: Blob): Promise<boolean> {
    if (!selectedId) return false
    timers.current.forEach(window.clearTimeout)
    timers.current = []
    setState('processing')
    setMessage('Đang so khớp âm thanh bằng MFCC + DTW…')
    try {
      const response = await api<VerifyResult>(`/voice-passwords/${selectedId}/verify`, { method: 'POST', body: audioForm(blob) }, token)
      setResult(response)
      setMessage(response.message || (response.granted ? 'Két đang mở.' : 'Hãy đọc lại đúng câu đã đăng ký.'))
      if (response.granted) {
        setState('granted')
        timers.current.push(window.setTimeout(() => setState('unlocked'), 500))
        timers.current.push(window.setTimeout(() => { setState('locked'); setMessage('Két đã tự khóa. Bạn có thể thử lại.') }, response.auto_lock_seconds * 1000))
      } else {
        setState('denied')
        timers.current.push(window.setTimeout(() => setState('locked'), 2200))
      }
      await refresh()
      return true
    } catch (error) {
      setState('locked')
      setMessage(describeError(error))
      return false
    }
  }

  return <div className="safe-layout">
    <SafeVault state={state} name={selected?.name} />
    <section className="control-card">
      <p className="step-label">VOICE PASSWORD · MFCC + DTW</p>
      <h2>Mở két bằng câu mật khẩu</h2>
      <p className="muted" role="status">{message}</p>
      {selected ? <>
        <label>Mật khẩu đã đăng ký<select value={selectedId ?? ''} disabled={state !== 'locked'} onChange={event => { setSelectedId(Number(event.target.value)); setResult(null) }}>
          {active.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select></label>
        <div className="phrase-box"><span>ĐỌC NGUYÊN CÂU NÀY</span><strong>“{selected.phrase}”</strong></div>
        <RecorderButton key={selected.id} disabled={state !== 'locked'} maxSeconds={6} minSeconds={1}
          label="Thu để mở két" submitLabel="Mở két bằng bản ghi này" onRecorded={verify}
          onStart={() => { setState('listening'); setResult(null); setMessage('Đang nghe. Đọc câu mật khẩu rồi bấm Dừng thu.') }}
          onCaptured={() => { setState('locked'); setMessage('Bạn có thể nghe lại, sau đó bấm mở két.') }} />
        {result && <div className="score-grid">
          <div><span>Điểm DTW ↓</span><strong>{result.dtw_score?.toFixed(3) ?? '—'}</strong></div>
          <div><span>Ngưỡng DTW</span><strong>{result.dtw_threshold?.toFixed(3) ?? '—'}</strong></div>
          <div><span>Độ giống giọng ↑</span><strong>{result.speaker_score?.toFixed(3) ?? '—'}</strong></div>
          <div><span>Ngưỡng giọng</span><strong>{result.speaker_threshold?.toFixed(3) ?? '—'}</strong></div>
          <div><span>Thời gian</span><strong>{result.processing_ms.toFixed(0)} ms</strong></div>
        </div>}
        <p className="recorder-help">Điểm DTW càng thấp càng giống mẫu. Hãy đọc cùng câu, giữ micro và nhịp nói giống lúc đăng ký.</p>
        <p className="voice-security-note" role="note">Két kiểm tra câu nói bằng MFCC + DTW và kiểm tra thêm đặc trưng người nói. Giọng AI được nhái sát hoặc bản ghi phát lại vẫn có thể vượt qua. Đây là mô phỏng, chưa phải khóa sinh trắc học chống giả giọng.</p>
      </> : <div className="simple-empty"><p>Chỉ cần chọn một câu ngắn và đọc 3 lần để bắt đầu.</p><button className="primary" onClick={onEnroll}>Đăng ký câu mật khẩu</button></div>}
      {passwords.some(item => item.requires_reenrollment) && <p className="recorder-help">Mẫu cũ chưa lưu đặc trưng người nói. Để chặn giọng khác tốt hơn, hãy tạo bộ 3 mẫu mới cùng câu.</p>}
    </section>
  </div>
}

export function EnrollPanel({ token, passwords, refresh, onReady }: Props & { onReady: () => void }) {
  const [name, setName] = useState('Két cá nhân')
  const [phrase, setPhrase] = useState('Mở két an toàn')
  const [current, setCurrent] = useState<VoicePassword | null>(null)
  const [sampleCount, setSampleCount] = useState(0)
  const [complete, setComplete] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function create(event: FormEvent) {
    event.preventDefault()
    setError(''); setBusy(true)
    try {
      const item = await api<VoicePassword>('/voice-passwords', { method: 'POST', body: JSON.stringify({ name, phrase }) }, token)
      setCurrent(item); setSampleCount(0); setComplete(false); setMessage('Đọc cùng một câu 3 lần. Mẫu thứ ba lưu xong là có thể mở két.')
      await refresh()
    } catch (cause) { setError(describeError(cause)) } finally { setBusy(false) }
  }

  async function upload(blob: Blob): Promise<boolean> {
    if (!current) return false
    setError(''); setBusy(true); setMessage('Đang kiểm tra và lưu mẫu…')
    try {
      const response = await api<{ sample_count: number; is_active: boolean; duration_seconds: number; speaker_threshold: number | null }>(`/voice-passwords/${current.id}/enroll`, { method: 'POST', body: audioForm(blob) }, token)
      setSampleCount(response.sample_count); setComplete(response.is_active)
      setMessage(response.is_active ? 'Đã sẵn sàng! Ba mẫu đã lưu MFCC và đặc trưng người nói; cả hai ngưỡng đã được tính.' : `Đã lưu mẫu ${response.sample_count}/3. Hãy đọc lại cùng câu lần tiếp theo.`)
      await refresh()
      return true
    } catch (cause) { setError(describeError(cause)); setMessage(''); return false }
    finally { setBusy(false) }
  }

  function resume(item: VoicePassword) {
    setCurrent(item); setSampleCount(item.template_count); setComplete(item.is_active); setError(''); setMessage('Tiếp tục thu cùng câu đã đăng ký.')
  }

  async function remove(item: VoicePassword) {
    if (!window.confirm(`Xóa “${item.name}” và các mẫu đã lưu?`)) return
    try {
      await api(`/voice-passwords/${item.id}`, { method: 'DELETE' }, token)
      if (current?.id === item.id) { setCurrent(null); setSampleCount(0); setComplete(false) }
      await refresh()
    } catch (cause) { setError(describeError(cause)) }
  }

  return <div className="two-column">
    <section className="panel">
      <p className="step-label">ĐĂNG KÝ NHANH · 3 LẦN ĐỌC</p><h2>Một câu, đọc ba lần</h2>
      {!current ? <form onSubmit={create}>
        <label>Tên gợi nhớ<input value={name} onChange={event => setName(event.target.value)} required maxLength={100} /></label>
        <label>Câu mật khẩu<input value={phrase} onChange={event => setPhrase(event.target.value)} required minLength={2} maxLength={255} /></label>
        <p className="muted">Chọn câu ngắn dễ đọc, ví dụ “Mở két an toàn”. Khi mở két, đọc lại nguyên câu đó.</p>
        <button className="primary" disabled={busy}>{busy ? 'Đang tạo…' : 'Bắt đầu thu 3 mẫu'}</button>
      </form> : <div className="enrollment-active">
        <div className="phrase-box"><span>{complete ? 'CÂU MẬT KHẨU ĐÃ SẴN SÀNG' : `LẦN ${Math.min(sampleCount + 1, 3)} / 3 · ĐỌC NGUYÊN CÂU`}</span><strong>“{current.phrase}”</strong></div>
        <div className="sample-dots">{[1,2,3].map(index => <i key={index} className={index <= sampleCount ? 'done' : ''}>{index}</i>)}</div>
        {complete ? <button className="primary" onClick={onReady}>Thử mở két ngay</button> : <>
          <p className="center muted">Nói tự nhiên khoảng 1–3 giây, không cần kéo dài. Đọc xong bấm Dừng thu.</p>
          <RecorderButton key={current.id} disabled={busy} onRecorded={upload} maxSeconds={6} minSeconds={1}
            label={`Thu lần ${sampleCount + 1}/3`} submitLabel={`Lưu mẫu ${sampleCount + 1}`} />
        </>}
        <button className="text-button" disabled={busy} onClick={() => { setCurrent(null); setMessage(''); setComplete(false) }}>Quay lại danh sách</button>
      </div>}
      {message && <p className="success-box" role="status">{message}</p>}
      {error && <p className="error-box" role="alert">{error}</p>}
    </section>
    <section className="panel">
      <p className="step-label">MẪU ÂM THANH</p><h2>Mật khẩu đã lưu</h2>
      <div className="password-list">{passwords.map(item => <article key={item.id}>
        <div><strong>{item.name}</strong><span>“{item.phrase}”</span></div>
        <div className="template-meta"><b>{item.requires_reenrollment ? 'Bản cũ' : `${item.template_count}/3`}</b><em className={item.is_active ? 'active' : ''}>{item.requires_reenrollment ? 'Cần thu lại 3 lần để lưu người nói' : item.is_active ? 'Sẵn sàng' : 'Chưa đủ mẫu'}</em></div>
        {!item.requires_reenrollment && !item.is_active && <button className="resume-link" disabled={busy} onClick={() => resume(item)}>Tiếp tục</button>}
        {item.requires_reenrollment && <button className="resume-link" disabled={busy} onClick={() => { setName(item.name); setPhrase(item.phrase); setCurrent(null); setComplete(false); setMessage('Đã điền lại tên và câu. Bấm bắt đầu để thu bộ mẫu mới.') }}>Đăng ký đơn giản</button>}
        <button className="danger-link" disabled={busy} onClick={() => remove(item)}>Xóa</button>
      </article>)}{!passwords.length && <div className="empty-state">Chưa có câu mật khẩu. Tạo câu đầu tiên ở bên trái.</div>}</div>
      <p className="recorder-help">Dùng cùng microphone, tránh tiếng nhạc nền và nói ở khoảng cách ổn định. Hệ thống lưu cả MFCC của câu và đặc trưng giọng từ ba lần đọc.</p>
    </section>
  </div>
}
