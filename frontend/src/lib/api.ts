const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    const message = typeof detail === 'string' ? detail : (detail as { message?: string })?.message || 'Có lỗi xảy ra'
    super(message)
    this.status = status
    this.detail = detail
  }
}

export async function api<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    let payload: { detail?: unknown } = {}
    try { payload = await response.json() } catch { /* response without JSON */ }
    throw new ApiError(response.status, payload.detail ?? `HTTP ${response.status}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function audioForm(blob: Blob): FormData {
  const form = new FormData()
  const extension = blob.type.includes('ogg') ? 'ogg' : blob.type.includes('wav') ? 'wav' : 'webm'
  form.append('file', blob, `recording.${extension}`)
  return form
}

