import { FormEvent, useCallback, useEffect, useState } from 'react'
import { EnrollPanel, SafePanel } from './components/VoicePanels'
import { api, ApiError } from './lib/api'
import type { AlgorithmSettings, Attempt, Stats, VoicePassword } from './types'

type Tab = 'safe' | 'enroll' | 'history' | 'dashboard' | 'settings'

const reasonLabels: Record<string, string> = {
  matched: 'Giọng nói khớp với mật khẩu đã đăng ký',
  score_above_threshold: 'Mẫu giọng không đủ tương đồng',
  speaker_mismatch: 'Câu nói khớp nhưng người nói chưa đạt ngưỡng',
  model_unavailable: 'Thiếu mô hình nhận dạng người nói hoặc mẫu đã lưu',
  too_quiet: 'Âm thanh quá nhỏ hoặc không có giọng nói',
  too_short: 'Bản ghi quá ngắn',
  too_long: 'Bản ghi quá dài',
  clipping: 'Âm thanh bị vỡ tiếng',
  no_speech: 'Không phát hiện đủ giọng nói',
  invalid_audio: 'Tệp âm thanh không hợp lệ',
  locked_out: 'Đã vượt quá số lần thử cho phép',
  processing_error: 'Không thể xử lý bản thu; két vẫn khóa',
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (typeof error.detail === 'object' && error.detail && 'message' in error.detail) return String(error.detail.message)
    if (typeof error.detail === 'string') return error.detail
  }
  return error instanceof Error ? error.message : 'Có lỗi xảy ra'
}

function Login({ onAuthenticated }: { onAuthenticated: (token: string, username: string) => void }) {
  const [registering, setRegistering] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await api<{ access_token: string; username: string }>(`/auth/${registering ? 'register' : 'login'}`, {
        method: 'POST', body: JSON.stringify({ username, password }),
      })
      onAuthenticated(result.access_token, result.username)
    } catch (cause) { setError(errorMessage(cause)) } finally { setBusy(false) }
  }

  return (
    <main className="login-shell">
      <section className="login-hero">
        <div className="brand-mark">V</div>
        <p className="eyebrow">VOICE PASSWORD · MFCC + DTW</p>
        <h1>VOICE<span>VAULT</span></h1>
        <p className="hero-copy">Chọn một câu mật khẩu, đọc ba lần để đăng ký, rồi đọc lại chính câu đó để mở két.</p>
        <div className="signal" aria-hidden="true">{[12,26,42,20,55,36,70,44,58,28,46,18].map((height, index) => <i key={index} style={{ height }} />)}</div>
      </section>
      <section className="login-panel">
        <div>
          <p className="step-label">TRUY CẬP HỆ THỐNG</p>
          <h2>{registering ? 'Tạo tài khoản demo' : 'Chào mừng trở lại'}</h2>
          <p className="muted">Dữ liệu được lưu cục bộ trên máy của bạn.</p>
        </div>
        <form onSubmit={submit}>
          <label>Tên đăng nhập<input value={username} onChange={event => setUsername(event.target.value)} minLength={3} required autoFocus /></label>
          <label>Mật khẩu<input type="password" value={password} onChange={event => setPassword(event.target.value)} minLength={8} required /></label>
          {error && <p className="error-box">{error}</p>}
          <button className="primary" disabled={busy}>{busy ? 'Đang xử lý…' : registering ? 'Tạo tài khoản' : 'Đăng nhập'}</button>
        </form>
        <button className="text-button" onClick={() => { setRegistering(value => !value); setError('') }}>
          {registering ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký'}
        </button>
      </section>
    </main>
  )
}

function HistoryPanel({ token, reloadKey }: { token: string; reloadKey: number }) {
  const [attempts, setAttempts] = useState<Attempt[]>([])
  useEffect(() => { api<Attempt[]>('/auth-attempts?limit=100', {}, token).then(setAttempts).catch(() => setAttempts([])) }, [token, reloadKey])
  return <section className="panel full"><p className="step-label">AUDIT LOG</p><h2>Lịch sử xác thực</h2><div className="table-wrap"><table><thead><tr><th>Thời gian</th><th>Câu mật khẩu</th><th>Kết quả</th><th>Điểm DTW / Ngưỡng</th><th>Độ giống người nói</th><th>Xử lý</th><th>Lý do</th></tr></thead><tbody>{attempts.map(item => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString('vi-VN')}</td><td>{item.voice_password_name}</td><td><span className={`badge ${item.granted ? 'ok' : 'no'}`}>{item.granted ? 'Granted' : 'Denied'}</span></td><td>{item.dtw_score?.toFixed(3) ?? '—'} / {item.dtw_threshold?.toFixed(3) ?? '—'}</td><td>{item.speaker_score?.toFixed(3) ?? '—'}</td><td>{item.processing_ms.toFixed(0)} ms</td><td>{reasonLabels[item.reason] || item.reason}</td></tr>)}</tbody></table>{!attempts.length && <div className="empty-state">Chưa có lượt xác thực.</div>}</div></section>
}

function DashboardPanel({ token, reloadKey }: { token: string; reloadKey: number }) {
  const [stats, setStats] = useState<Stats | null>(null)
  useEffect(() => { api<Stats>('/stats', {}, token).then(setStats).catch(() => setStats(null)) }, [token, reloadKey])
  const cards = stats ? [
    ['Tổng lượt thử', stats.total_attempts.toString(), 'Tất cả yêu cầu đã ghi log'],
    ['Tỷ lệ thành công', `${(stats.success_rate * 100).toFixed(1)}%`, `${stats.granted} granted · ${stats.denied} denied`],
    ['Độ trễ trung bình', `${stats.average_processing_ms.toFixed(0)} ms`, `P95 ${stats.p95_processing_ms.toFixed(0)} ms`],
    ['FAR / FRR', stats.far == null ? 'Chưa gắn nhãn' : `${(stats.far * 100).toFixed(1)} / ${((stats.frr ?? 0) * 100).toFixed(1)}%`, 'Chỉ tính mẫu evaluation có ground truth'],
  ] : []
  return <><div className="dashboard-head"><div><p className="step-label">SYSTEM METRICS</p><h2>Dashboard đánh giá</h2></div><span className="live"><i /> LIVE</span></div><div className="metric-grid">{cards.map(([label,value,note]) => <article key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>)}</div><section className="panel full"><h3>Cách đọc kết quả</h3><p className="muted">DTW càng thấp càng giống câu đăng ký; độ giống người nói càng cao càng khớp. Két chỉ mở khi cả hai đạt ngưỡng. FAR/FRR cần đo trên tập test có người nói và giọng AI khác.</p></section></>
}

function SettingsPanel({ token }: { token: string }) {
  const [settings, setSettings] = useState<AlgorithmSettings | null>(null)
  const [message, setMessage] = useState('')
  useEffect(() => { api<AlgorithmSettings>('/settings', {}, token).then(setSettings) }, [token])
  if (!settings) return <div className="empty-state">Đang tải cấu hình…</div>
  const current = settings
  async function save(event: FormEvent) {
    event.preventDefault()
    const updated = await api<AlgorithmSettings>('/settings', { method: 'PUT', body: JSON.stringify({ auto_lock_seconds: current.auto_lock_seconds, max_failed_attempts: current.max_failed_attempts, lockout_seconds: current.lockout_seconds, min_rms: current.min_rms }) }, token)
    setSettings(updated); setMessage('Đã lưu cấu hình.')
  }
  const field = (key: keyof AlgorithmSettings, label: string, step = '1') => <label>{label}<input type="number" step={step} value={current[key]} onChange={event => setSettings({ ...current, [key]: Number(event.target.value) })} /></label>
  return <section className="panel settings-panel"><p className="step-label">ALGORITHM CONFIG</p><h2>Cấu hình hệ thống</h2><form onSubmit={save}><div className="settings-grid">{field('auto_lock_seconds','Tự khóa sau (giây)')}{field('max_failed_attempts','Số lần sai tối đa')}{field('lockout_seconds','Thời gian khóa tạm (giây)')}{field('min_rms','RMS tối thiểu','0.001')}</div><p className="muted">Ngưỡng DTW được hệ thống tính riêng cho từng câu từ ba lần đọc.</p><div className="readonly-config"><span>Sample rate <b>{current.sample_rate} Hz</b></span><span>MFCC <b>{current.n_mfcc} hệ số</b></span><span>Mẫu/câu <b>3 lần</b></span><span>So khớp <b>MFCC + DTW</b></span></div><button className="primary">Lưu cấu hình</button>{message && <p className="success-box">{message}</p>}</form></section>
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('voice_token') || '')
  const [username, setUsername] = useState(() => localStorage.getItem('voice_user') || '')
  const [tab, setTab] = useState<Tab>('safe')
  const [passwords, setPasswords] = useState<VoicePassword[]>([])
  const [reloadKey, setReloadKey] = useState(0)

  const refresh = useCallback(async () => {
    if (!token) return
    try { setPasswords(await api<VoicePassword[]>('/voice-passwords', {}, token)); setReloadKey(value => value + 1) }
    catch (error) { if (error instanceof ApiError && error.status === 401) logout() }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])
  useEffect(() => { refresh() }, [refresh])

  function authenticated(nextToken: string, nextUsername: string) { localStorage.setItem('voice_token', nextToken); localStorage.setItem('voice_user', nextUsername); setToken(nextToken); setUsername(nextUsername) }
  function logout() { localStorage.removeItem('voice_token'); localStorage.removeItem('voice_user'); setToken(''); setUsername(''); setPasswords([]) }
  if (!token) return <Login onAuthenticated={authenticated} />

  const nav: [Tab,string][] = [['safe','Két sắt'],['enroll','Đăng ký giọng'],['history','Lịch sử'],['dashboard','Thống kê'],['settings','Cấu hình']]
  return (
    <div className="app-shell">
      <header><div className="mini-brand"><b>V</b><span>VOICE<strong>VAULT</strong></span></div><nav>{nav.map(([id,label]) => <button key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{label}</button>)}</nav><div className="user-menu"><span>{username}</span><button onClick={logout}>Đăng xuất</button></div></header>
      <main className="workspace">
        {tab === 'safe' && <SafePanel token={token} passwords={passwords} refresh={refresh} onEnroll={() => setTab('enroll')} />}
        {tab === 'enroll' && <EnrollPanel token={token} passwords={passwords} refresh={refresh} onReady={() => setTab('safe')} />}
        {tab === 'history' && <HistoryPanel token={token} reloadKey={reloadKey} />}
        {tab === 'dashboard' && <DashboardPanel token={token} reloadKey={reloadKey} />}
        {tab === 'settings' && <SettingsPanel token={token} />}
      </main>
      <footer><span>Voice Password · MFCC + DTW</span><span>LOCAL DEMO · REPLAY ATTACK NOT MITIGATED</span></footer>
    </div>
  )
}
