import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import LoginView from '../views/LoginView.vue'
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

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: LoginView },
      { path: '/', name: 'home', component: { template: '<div>Home</div>' } },
      { path: '/papers', name: 'papers', component: { template: '<div>Papers</div>' } },
    ],
  })
}

describe('LoginView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('renders login form', () => {
    const router = createTestRouter()
    const wrapper = mount(LoginView, { global: { plugins: [router] } })
    expect(wrapper.find('h1').text()).toBe('登录')
    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })

  it('shows error on failed login', async () => {
    vi.mocked(api.login).mockRejectedValue({
      response: { data: { error: { message: '邮箱或密码错误' } } },
      message: '邮箱或密码错误',
    })

    const router = createTestRouter()
    const wrapper = mount(LoginView, { global: { plugins: [router] } })

    await wrapper.find('input[type="email"]').setValue('bad@example.com')
    await wrapper.find('input[type="password"]').setValue('wrong')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.error').text()).toContain('邮箱或密码错误')
  })

  it('redirects on successful login', async () => {
    vi.mocked(api.login).mockResolvedValue({
      access_token: 'at-1',
      token_type: 'bearer',
      expires_in: 900,
      user: mockUser,
    })

    const router = createTestRouter()
    router.push('/login')
    await router.isReady()

    const wrapper = mount(LoginView, { global: { plugins: [router] } })

    await wrapper.find('input[type="email"]').setValue('test@example.com')
    await wrapper.find('input[type="password"]').setValue('StrongPass123!@#')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(api.login).toHaveBeenCalledWith('test@example.com', 'StrongPass123!@#')
    expect(router.currentRoute.value.fullPath).toBe('/papers')
    expect(localStorage.length).toBe(0)
  })

  it('rejects an external redirect target after successful login', async () => {
    vi.mocked(api.login).mockResolvedValue({
      access_token: 'at-1',
      token_type: 'bearer',
      expires_in: 900,
      user: mockUser,
    })
    const router = createTestRouter()
    await router.push({ path: '/login', query: { redirect: '//evil.example/path' } })
    await router.isReady()
    const wrapper = mount(LoginView, { global: { plugins: [router] } })

    await wrapper.find('input[type="email"]').setValue('test@example.com')
    await wrapper.find('input[type="password"]').setValue('StrongPass123!@#')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/papers')
  })
})
