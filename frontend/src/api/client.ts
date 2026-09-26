// HTTP client: in-memory access token, automatic refresh on 401, and one refresh at a time.
//
// The access token lives only in this module (never localStorage), so injected scripts can't
// read it from storage. The refresh token is an httpOnly cookie the browser sends to
// /api/v1/auth only. Refresh tokens are single use: two refreshes racing with the same cookie
// look like theft and end the session, so every refresh goes through one shared promise, and
// across tabs through a Web Lock.

import { toApiError } from './errors'
import type { TokenResponse } from './types'

const BASE = '/api/v1'
const SESSION_HINT = 'nebula:has-session' // "a refresh cookie probably exists"; not a secret

type Query = Record<string, string | number | undefined>
type Options = { method?: string; body?: unknown; query?: Query; signal?: AbortSignal }

let accessToken: string | null = null
let refreshing: Promise<string | null> | null = null
const listeners = new Set<(signedIn: boolean) => void>()

export function onSessionChange(listener: (signedIn: boolean) => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function hasSessionHint(): boolean {
  try {
    return localStorage.getItem(SESSION_HINT) === '1'
  } catch {
    return false
  }
}

export function setSession(token: string | null): void {
  const changed = (accessToken === null) !== (token === null)
  accessToken = token
  try {
    if (token) localStorage.setItem(SESSION_HINT, '1')
    else localStorage.removeItem(SESSION_HINT)
  } catch {
    // Storage may be disabled (private mode); the hint is only an optimisation.
  }
  if (changed) listeners.forEach((listener) => listener(token !== null))
}

function url(path: string, query?: Query): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== '') params.set(key, String(value))
  }
  const search = params.toString()
  return `${BASE}${path}${search ? `?${search}` : ''}`
}

async function send(path: string, options: Options, token: string | null): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(url(path, options.query), {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    credentials: 'same-origin',
    signal: options.signal,
  })
}

async function refreshOnce(): Promise<string | null> {
  const response = await send('/auth/refresh', { method: 'POST' }, null)
  if (!response.ok) return null
  const { access_token } = (await response.json()) as TokenResponse
  return access_token
}

/** Get a new access token from the refresh cookie. Concurrent callers share one request. */
export function refresh(): Promise<string | null> {
  refreshing ??= (async () => {
    try {
      const run = () => refreshOnce()
      const token = navigator.locks
        ? await navigator.locks.request('nebula-refresh', run)
        : await run()
      setSession(token)
      return token
    } catch {
      setSession(null)
      return null
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}

/** Call the API. Throws ApiError for non-2xx responses; returns undefined for 204. */
export async function request<T>(path: string, options: Options = {}): Promise<T> {
  const token = accessToken
  let response = await send(path, options, token)

  // Expired access token: refresh once, then retry the original request once.
  if (response.status === 401 && token && !path.startsWith('/auth/')) {
    const fresh = await refresh()
    if (fresh) response = await send(path, options, fresh)
  }

  if (!response.ok) throw await toApiError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
