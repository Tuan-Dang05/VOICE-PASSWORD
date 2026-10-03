import { lazy, Suspense, useEffect, useState } from 'react'
import type { SafeState } from '../types'
import './SafeVault.css'

const VaultScene = lazy(() => import('./VaultScene'))

const labels: Record<SafeState, { title: string; description: string }> = {
  locked: { title: 'LOCKED', description: 'Két đang khóa' },
  listening: { title: 'LISTENING', description: 'Đang lắng nghe' },
  processing: { title: 'PROCESSING', description: 'Đang xác thực' },
  granted: { title: 'ACCESS GRANTED', description: 'Xác thực thành công' },
  denied: { title: 'ACCESS DENIED', description: 'Truy cập bị từ chối' },
  unlocked: { title: 'UNLOCKED', description: 'Két đã mở' },
}

export function SafeVault({ state, name }: { state: SafeState; name?: string }) {
  const [preview, setPreview] = useState(false)
  const [backView, setBackView] = useState(false)
  const status = labels[state]
  useEffect(() => {
    if (!preview) return
    const timer = window.setTimeout(() => setPreview(false), 5300)
    return () => window.clearTimeout(timer)
  }, [preview])
  useEffect(() => { setPreview(false); if (state !== 'locked') setBackView(false) }, [state])
  return (
    <section className={`vault-showcase vault-${state}`} aria-label="Két sắt mô phỏng">
      <div className="vault-heading"><span>KÉT TUẤN ĐẶNG</span><span>PERSONAL SAFE / 01</span></div>
      <Suspense fallback={<div className="vault-loading">Đang dựng mô hình 3D…</div>}>
        <VaultScene state={state} name={name} preview={preview && state === 'locked'} backView={backView} />
      </Suspense>
      <div className="vault-view-hint">Kéo để xoay 360°</div>
      <div className="vault-status" role="status" aria-live="polite"><i /><strong>{status.title}</strong><span>{status.description}</span></div>
      <p className="vault-caption">{preview ? 'Đang xem thử chuyển động · Trạng thái xác thực vẫn là khóa.' : state === 'unlocked' ? 'Két sẽ tự đóng cửa và khóa lại theo thời gian đã cấu hình.' : 'Tay xoay, chốt khóa và cửa chuyển động khi xác thực thành công.'}</p>
      <div className="vault-view-actions">
      <button type="button" className="vault-preview-button" disabled={preview || state !== 'locked'} onClick={() => { setBackView(false); setPreview(true) }}>
        <span aria-hidden="true">▷</span> {preview ? 'Đang xem thử…' : 'Xem thử mở két'}
      </button>
      </div>
    </section>
  )
}
