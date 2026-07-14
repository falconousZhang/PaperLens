import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import api, {
  authRefreshClient,
  getAccessToken,
  setAccessToken,
  setAuthFailureHandler,
} from '../api'


const originalApiAdapter = api.defaults.adapter
const originalRefreshAdapter = authRefreshClient.defaults.adapter
const user = {
  id: 'user-1',
  email: 'test@example.com',
  display_name: 'Test User',
  role: 'USER',
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z',
}

function rejectWithStatus(config: InternalAxiosRequestConfig, status: number): never {
  const response = {
    data: { error: { code: 'INVALID_TOKEN', message: 'invalid', details: null } },
    status,
    statusText: 'Unauthorized',
    headers: {},
    config,
  }
  throw new AxiosError('unauthorized', 'ERR_BAD_REQUEST', config, undefined, response)
}

describe('API authentication interceptor', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setAccessToken(null)
    setAuthFailureHandler(null)
  })

  afterEach(() => {
    api.defaults.adapter = originalApiAdapter
    authRefreshClient.defaults.adapter = originalRefreshAdapter
    setAccessToken(null)
    setAuthFailureHandler(null)
  })

  it('uses one refresh for concurrent 401 responses and replays each request once', async () => {
    let refreshCalls = 0
    const apiAttempts = new Map<string, number>()
    authRefreshClient.defaults.adapter = async (config) => {
      refreshCalls += 1
      await Promise.resolve()
      return {
        data: {
          access_token: 'new-access',
          token_type: 'bearer',
          expires_in: 900,
          user,
        },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }
    }
    api.defaults.adapter = async (config) => {
      const url = config.url ?? ''
      apiAttempts.set(url, (apiAttempts.get(url) ?? 0) + 1)
      if (config.headers.Authorization !== 'Bearer new-access') {
        return rejectWithStatus(config, 401)
      }
      return {
        data: { ok: url },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }
    }
    setAccessToken('expired-access')

    const [papers, tasks] = await Promise.all([
      api.get('/papers'),
      api.get('/tasks/one'),
    ])

    expect(refreshCalls).toBe(1)
    expect(apiAttempts.get('/papers')).toBe(2)
    expect(apiAttempts.get('/tasks/one')).toBe(2)
    expect(papers.data.ok).toBe('/papers')
    expect(tasks.data.ok).toBe('/tasks/one')
    expect(getAccessToken()).toBe('new-access')
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })

  it('never retries a replayed request more than once', async () => {
    let apiCalls = 0
    const authFailure = vi.fn()
    setAuthFailureHandler(authFailure)
    authRefreshClient.defaults.adapter = async (config) => ({
      data: {
        access_token: 'still-invalid',
        token_type: 'bearer',
        expires_in: 900,
        user,
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
    api.defaults.adapter = async (config) => {
      apiCalls += 1
      return rejectWithStatus(config, 401)
    }
    setAccessToken('expired-access')

    await expect(api.get('/papers')).rejects.toBeInstanceOf(AxiosError)

    expect(apiCalls).toBe(2)
    expect(authFailure).toHaveBeenCalledTimes(1)
    expect(getAccessToken()).toBeNull()
  })

  it('does not recursively refresh when the refresh endpoint rejects', async () => {
    let refreshCalls = 0
    let apiCalls = 0
    authRefreshClient.defaults.adapter = async (config) => {
      refreshCalls += 1
      return rejectWithStatus(config, 401)
    }
    api.defaults.adapter = async (config) => {
      apiCalls += 1
      return rejectWithStatus(config, 401)
    }
    setAccessToken('expired-access')

    await expect(api.get('/papers')).rejects.toBeInstanceOf(AxiosError)

    expect(apiCalls).toBe(1)
    expect(refreshCalls).toBe(1)
  })
})
