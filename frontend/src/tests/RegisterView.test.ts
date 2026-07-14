import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import RegisterView from '../views/RegisterView.vue'
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
  email: 'new@example.com',
  display_name: 'New User',
  role: 'USER',
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z',
}

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/register', name: 'register', component: RegisterView },
      { path: '/', name: 'home', component: { template: '<div>Home</div>' } },
      { path: '/papers', name: 'papers', component: { template: '<div>Papers</div>' } },
    ],
  })
}

describe('RegisterView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('renders register form', () => {
    const router = createTestRouter()
    const wrapper = mount(RegisterView, { global: { plugins: [router] } })
    expect(wrapper.find('h1').text()).toBe('注册')
    expect(wrapper.findAll('input')).toHaveLength(4)
  })

  it('shows error when passwords do not match', async () => {
    const router = createTestRouter()
    const wrapper = mount(RegisterView, { global: { plugins: [router] } })

    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('test@example.com')
    await inputs[1]!.setValue('Test')
    await inputs[2]!.setValue('StrongPass123!@#')
    await inputs[3]!.setValue('DifferentPass456!@#')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.error').text()).toContain('不一致')
  })

  it('shows error when password too short', async () => {
    const router = createTestRouter()
    const wrapper = mount(RegisterView, { global: { plugins: [router] } })

    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('test@example.com')
    await inputs[1]!.setValue('Test')
    await inputs[2]!.setValue('short')
    await inputs[3]!.setValue('short')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.error').text()).toContain('15')
  })

  it('calls register on valid input', async () => {
    vi.mocked(api.register).mockResolvedValue({
      access_token: 'at-1',
      token_type: 'bearer',
      expires_in: 900,
      user: mockUser,
    })

    const router = createTestRouter()
    const wrapper = mount(RegisterView, { global: { plugins: [router] } })

    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('new@example.com')
    await inputs[1]!.setValue('New User')
    await inputs[2]!.setValue('StrongPass123!@#')
    await inputs[3]!.setValue('StrongPass123!@#')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(api.register).toHaveBeenCalledWith('new@example.com', 'StrongPass123!@#', 'New User')
    expect(router.currentRoute.value.fullPath).toBe('/papers')
    expect(localStorage.length).toBe(0)
  })
})
