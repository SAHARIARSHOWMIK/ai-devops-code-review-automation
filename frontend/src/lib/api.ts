const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export type ApiError = { detail?: string }

export function token(): string | null {
  return localStorage.getItem('access_token')
}

export function setSession(accessToken: string, user: unknown) {
  localStorage.setItem('access_token', accessToken)
  localStorage.setItem('current_user', JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('current_user')
}

export function currentUser<T = Record<string, unknown>>(): T | null {
  const value = localStorage.getItem('current_user')
  return value ? JSON.parse(value) as T : null
}

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && options.body) headers.set('Content-Type', 'application/json')
  if (token()) headers.set('Authorization', `Bearer ${token()}`)
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (response.status === 401) {
    clearSession()
    if (!location.pathname.includes('/login')) location.href = '/login'
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as ApiError
    throw new Error(error.detail || `Request failed (${response.status})`)
  }
  return response.json()
}

export const get = <T = any>(path: string) => api<T>(path)
export const post = <T = any>(path: string, body?: unknown) => api<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
export const put = <T = any>(path: string, body: unknown) => api<T>(path, { method: 'PUT', body: JSON.stringify(body) })
