import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'


vi.mock('../api', () => ({
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  logoutAll: vi.fn(),
  refreshToken: vi.fn(),
  setAccessToken: vi.fn(),
  updateMe: vi.fn(),
  changePassword: vi.fn(),
  forgotPassword: vi.fn(),
  resetPassword: vi.fn(),
}))

const mockUser = {
  id: 'user-1',
  email: 'test@example.com',
  display_name: 'Test User',
  role: 'USER',
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z',
}

function tokenResponse(token = 'access-1', user = mockUser) {
  return {
    access_token: token,
    token_type: 'bearer',
    expires_in: 900,
    user,
  }
}

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('keeps access credentials in memory only after login', async () => {
    vi.mocked(api.login).mockResolvedValue(tokenResponse())
    const auth = useAuthStore()

    await auth.login('test@example.com', 'password')

    expect(auth.isAuthenticated).toBe(true)
    expect(auth.accessToken).toBe('access-1')
    expect(auth.user).toEqual(mockUser)
    expect(api.setAccessToken).toHaveBeenCalledWith('access-1')
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })

  it('uses the safe public user returned by registration', async () => {
    vi.mocked(api.register).mockResolvedValue(tokenResponse('access-2'))
    const auth = useAuthStore()

    await auth.register('test@example.com', 'StrongPass123!@#', 'Test')

    expect(auth.accessToken).toBe('access-2')
    expect(auth.user?.status).toBe('ACTIVE')
    expect(localStorage.length).toBe(0)
  })

  it('bootstraps once by rotating the HttpOnly refresh cookie', async () => {
    vi.mocked(api.refreshToken).mockResolvedValue(tokenResponse('bootstrap-access'))
    const auth = useAuthStore()

    await Promise.all([auth.bootstrap(), auth.bootstrap(), auth.bootstrap()])

    expect(api.refreshToken).toHaveBeenCalledTimes(1)
    expect(auth.bootstrapped).toBe(true)
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.accessToken).toBe('bootstrap-access')
  })

  it('finishes bootstrap anonymously when the cookie is unavailable', async () => {
    vi.mocked(api.refreshToken).mockRejectedValue(new Error('unauthorized'))
    const auth = useAuthStore()

    await auth.bootstrap()

    expect(auth.bootstrapped).toBe(true)
    expect(auth.isAuthenticated).toBe(false)
    expect(api.setAccessToken).toHaveBeenCalledWith(null)
  })

  it('clears memory even when logout fails', async () => {
    vi.mocked(api.login).mockResolvedValue(tokenResponse())
    vi.mocked(api.logout).mockRejectedValue(new Error('network'))
    const auth = useAuthStore()
    await auth.login('test@example.com', 'password')

    await expect(auth.logout()).resolves.toBeUndefined()

    expect(auth.isAuthenticated).toBe(false)
    expect(auth.user).toBeNull()
    expect(api.setAccessToken).toHaveBeenLastCalledWith(null)
  })

  it('clears memory after logout-all and password change', async () => {
    vi.mocked(api.login).mockResolvedValue(tokenResponse())
    vi.mocked(api.logoutAll).mockResolvedValue(undefined)
    vi.mocked(api.changePassword).mockResolvedValue({ message: 'ok' })
    const auth = useAuthStore()

    await auth.login('test@example.com', 'password')
    await auth.logoutAll()
    expect(auth.isAuthenticated).toBe(false)

    await auth.login('test@example.com', 'password')
    await auth.changePassword('old password value', 'new password value')
    expect(auth.isAuthenticated).toBe(false)
  })

  it('keeps the current session when password change is rejected', async () => {
    vi.mocked(api.login).mockResolvedValue(tokenResponse())
    vi.mocked(api.changePassword).mockRejectedValue(new Error('wrong password'))
    const auth = useAuthStore()
    await auth.login('test@example.com', 'password')

    await expect(auth.changePassword('wrong', 'new password value')).rejects.toThrow('wrong password')

    expect(auth.isAuthenticated).toBe(true)
    expect(auth.accessToken).toBe('access-1')
  })

  it('derives admin status from the current database-backed user response', async () => {
    vi.mocked(api.login).mockResolvedValue(tokenResponse('admin-access', {
      ...mockUser,
      role: 'ADMIN',
    }))
    const auth = useAuthStore()
    await auth.login('admin@example.com', 'password')
    expect(auth.isAdmin).toBe(true)
  })
})
