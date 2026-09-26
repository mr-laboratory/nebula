// Client tests: bearer token, one refresh per 401 burst, sign-out on failed refresh, problem details.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

type Client = typeof import('./client')
type ErrorsModule = typeof import('./errors')

function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
}

let client: Client
let ApiError: ErrorsModule['ApiError']
let fetchMock: ReturnType<typeof vi.fn>

beforeEach(async () => {
  vi.resetModules() // fresh module state (token, pending refresh) for every test
  localStorage.clear()
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  client = await import('./client')
  ;({ ApiError } = await import('./errors')) // same module instance the client throws from
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const calls = () => fetchMock.mock.calls.map(([url]) => String(url))
function authHeader(index: number): string | undefined {
  const init = fetchMock.mock.calls[index]?.[1] as RequestInit | undefined
  return (init?.headers as Record<string, string> | undefined)?.Authorization
}

describe('request', () => {
  it('sends the access token as a bearer header', async () => {
    client.setSession('token-a')
    fetchMock.mockResolvedValueOnce(json(200, { ok: true }))

    await client.request('/users/me')

    expect(calls()).toEqual(['/api/v1/users/me'])
    expect(authHeader(0)).toBe('Bearer token-a')
  })

  it('builds query strings and skips empty values', async () => {
    fetchMock.mockResolvedValueOnce(json(200, {}))

    await client.request('/posts', {
      query: { tag: 'python', q: '', author: undefined, limit: 12 },
    })

    expect(calls()).toEqual(['/api/v1/posts?tag=python&limit=12'])
  })

  it('refreshes once on 401 and retries with the new token', async () => {
    client.setSession('expired')
    fetchMock
      .mockResolvedValueOnce(json(401, { title: 'Unauthorized', status: 401 }))
      .mockResolvedValueOnce(json(200, { access_token: 'fresh', token_type: 'bearer' }))
      .mockResolvedValueOnce(json(200, { username: 'ada' }))

    const me = await client.request<{ username: string }>('/users/me')

    expect(me.username).toBe('ada')
    expect(calls()).toEqual(['/api/v1/users/me', '/api/v1/auth/refresh', '/api/v1/users/me'])
    expect(authHeader(2)).toBe('Bearer fresh')
  })

  it('shares one refresh between concurrent 401s', async () => {
    client.setSession('expired')
    fetchMock.mockImplementation(async (url: string, init: RequestInit) => {
      if (url.endsWith('/auth/refresh')) return json(200, { access_token: 'fresh' })
      const auth = (init.headers as Record<string, string>).Authorization
      return auth === 'Bearer fresh' ? json(200, {}) : json(401, {})
    })

    await Promise.all([client.request('/a'), client.request('/b'), client.request('/c')])

    expect(calls().filter((url) => url.endsWith('/auth/refresh'))).toHaveLength(1)
  })

  it('signs out when the refresh fails', async () => {
    const listener = vi.fn()
    client.setSession('expired')
    client.onSessionChange(listener)
    fetchMock
      .mockResolvedValueOnce(json(401, {}))
      .mockResolvedValueOnce(json(401, { title: 'Unauthorized' }))

    await expect(client.request('/users/me')).rejects.toMatchObject({ status: 401 })

    expect(listener).toHaveBeenCalledWith(false)
    expect(client.hasSessionHint()).toBe(false)
  })

  it('does not refresh when no token was sent', async () => {
    fetchMock.mockResolvedValueOnce(json(401, {}))

    await expect(client.request('/users/me')).rejects.toBeInstanceOf(ApiError)

    expect(calls()).toEqual(['/api/v1/users/me'])
  })

  it('never refreshes for auth endpoints', async () => {
    client.setSession('token')
    fetchMock.mockResolvedValueOnce(json(401, {}))

    await expect(client.request('/auth/logout', { method: 'POST' })).rejects.toBeInstanceOf(
      ApiError,
    )

    expect(calls()).toEqual(['/api/v1/auth/logout'])
  })

  it('turns problem details into ApiError with field messages and Retry-After', async () => {
    fetchMock.mockResolvedValueOnce(
      json(
        422,
        {
          title: 'Unprocessable Content',
          status: 422,
          detail: 'Invalid input',
          errors: [
            { loc: ['body', 'password'], msg: 'Value error, too short', type: 'value_error' },
          ],
        },
        { 'Retry-After': '7' },
      ),
    )

    const error = await client
      .request('/auth/register', { method: 'POST', body: {} })
      .catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as InstanceType<typeof ApiError>).fieldMessages()).toEqual({
      password: 'too short',
    })
    expect((error as InstanceType<typeof ApiError>).retryAfter).toBe(7)
  })

  it('returns undefined for 204', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await expect(client.request('/comments/1', { method: 'DELETE' })).resolves.toBeUndefined()
  })
})

describe('session hint', () => {
  it('is stored while signed in and removed on sign-out', () => {
    client.setSession('token')
    expect(client.hasSessionHint()).toBe(true)
    client.setSession(null)
    expect(client.hasSessionHint()).toBe(false)
  })
})
