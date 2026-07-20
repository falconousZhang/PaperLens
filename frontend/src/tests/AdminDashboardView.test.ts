import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import AdminDashboardView from '../views/AdminDashboardView.vue'
import { useAuthStore } from '../stores/auth'
import * as api from '../api'

vi.mock('../api', async () => {
  const actual = await vi.importActual<typeof import('../api')>('../api')
  return {
    ...actual,
    getAdminDashboard: vi.fn(),
    listAdminUsers: vi.fn(),
    getAdminUser: vi.fn(),
    patchAdminUser: vi.fn(),
    listAdminPapers: vi.fn(),
    listAdminTasks: vi.fn(),
    listAdminExports: vi.fn(),
    listAuditLogs: vi.fn(),
  }
})

const emptyList = { items: [], total: 0, page: 1, page_size: 20 }
const adminUser = {
  id: '10000000-0000-4000-8000-000000000001',
  email: 'admin@example.com',
  display_name: 'Admin',
  role: 'ADMIN',
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z',
}
const listedUser = {
  ...adminUser,
  id: '10000000-0000-4000-8000-000000000002',
  email: 'user@example.com',
  display_name: 'User',
  role: 'USER',
  failed_login_count: 0,
  locked_until: null,
  updated_at: '2026-01-01T00:00:00Z',
  active_session_count: 0,
  paper_count: 1,
  task_count: 2,
  export_count: 3,
}

async function renderView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.user = adminUser
  auth.accessToken = 'memory-token'
  auth.bootstrapped = true
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/admin', component: AdminDashboardView },
      { path: '/login', component: { template: '<div>login</div>' } },
    ],
  })
  await router.push('/admin')
  await router.isReady()
  const wrapper = mount(AdminDashboardView, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return { wrapper, router, auth }
}

describe('AdminDashboardView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getAdminDashboard).mockResolvedValue({
      users_by_role: { ADMIN: 1, USER: 1 },
      users_by_status: { ACTIVE: 2 },
      papers_by_status: {},
      tasks_by_type: {},
      tasks_by_status: {},
      exports_by_type: {},
      exports_by_status: {},
    })
    vi.mocked(api.listAdminUsers).mockResolvedValue(emptyList)
    vi.mocked(api.listAdminPapers).mockResolvedValue(emptyList)
    vi.mocked(api.listAdminTasks).mockResolvedValue(emptyList)
    vi.mocked(api.listAdminExports).mockResolvedValue(emptyList)
    vi.mocked(api.listAuditLogs).mockResolvedValue(emptyList)
  })

  it('finishes loading after switching to the users tab', async () => {
    vi.mocked(api.listAdminUsers).mockResolvedValue({ ...emptyList, items: [listedUser], total: 1 })
    const { wrapper } = await renderView()

    await wrapper.get('.admin-tabs').findAll('button')[1]!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('user@example.com')
    expect(wrapper.text()).not.toContain('加载中...')
    expect(api.listAdminUsers).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  })

  it('keeps paper, task and export pagination and filters independent', async () => {
    const { wrapper } = await renderView()
    await wrapper.get('.admin-tabs').findAll('button')[2]!.trigger('click')
    await flushPromises()

    const paperFilters = wrapper.findAll('.filters')[0]!
    await paperFilters.get('select').setValue('PARSED')
    await paperFilters.findAll('input')[0]!.setValue('10000000-0000-4000-8000-000000000002')
    await paperFilters.findAll('button')[0]!.trigger('click')
    await flushPromises()
    expect(api.listAdminPapers).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 20,
      status: 'PARSED',
      user_id: '10000000-0000-4000-8000-000000000002',
    })

    await wrapper.get('.content-tabs').findAll('button')[1]!.trigger('click')
    await flushPromises()
    expect(api.listAdminTasks).toHaveBeenLastCalledWith({ page: 1, page_size: 20 })
  })

  it('requires a trimmed reason and uses fixed conflict text', async () => {
    vi.mocked(api.listAdminUsers).mockResolvedValue({ ...emptyList, items: [listedUser], total: 1 })
    vi.mocked(api.patchAdminUser).mockRejectedValue({ response: { status: 409, data: { error: { message: 'secret database detail' } } } })
    const { wrapper } = await renderView()
    await wrapper.get('.admin-tabs').findAll('button')[1]!.trigger('click')
    await flushPromises()

    const actionButtons = wrapper.find('tbody').findAll('button')
    await actionButtons[1]!.trigger('click')
    const submit = wrapper.find('.modal-actions').findAll('button')[1]!
    await wrapper.get('textarea').setValue('          ')
    expect(submit.attributes('disabled')).toBeDefined()
    await wrapper.get('textarea').setValue('valid admin operation reason')
    await submit.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('操作冲突，请刷新后重试')
    expect(wrapper.text()).not.toContain('secret database detail')
  })
})
