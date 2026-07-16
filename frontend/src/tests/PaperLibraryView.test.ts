import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import PaperListView from '../views/PaperListView.vue'
import * as api from '../api'


vi.mock('../api', () => ({
  checkHealth: vi.fn(),
  listLibraryPapers: vi.fn(),
  patchLibraryEntry: vi.fn(),
}))

const item = {
  paper_id: '11111111-1111-4111-8111-111111111111',
  title: '<script>plain title</script>',
  filename: 'paper.pdf',
  page_count: 10,
  status: 'PARSED',
  created_at: '2026-01-01T00:00:00Z',
  reading_status: 'TO_READ' as const,
  favorite: false,
  collection_name: null,
  last_page: null,
  furthest_page: null,
  progress_percent: 0,
  last_read_at: null,
  completed_at: null,
  updated_at: '2026-01-01T00:00:00Z',
  highlight_count: 1,
  bookmark_count: 2,
  note_count: 3,
  card_count: 4,
}

function router() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: HomeView },
      { path: '/papers', name: 'papers', component: PaperListView },
      { path: '/papers/:id', name: 'paper-detail', component: { template: '<div />' } },
      { path: '/papers/:id/read', name: 'paper-read', component: { template: '<div />' } },
      { path: '/upload', name: 'upload', component: { template: '<div />' } },
    ],
  })
}

describe('paper learning product wording and library', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.checkHealth).mockResolvedValue({ status: 'healthy', version: '0.1.0' })
    vi.mocked(api.listLibraryPapers).mockResolvedValue({ items: [item], total: 1, page: 1, page_size: 20 })
    vi.mocked(api.patchLibraryEntry).mockResolvedValue({
      paper_id: item.paper_id,
      reading_status: 'READING',
      favorite: false,
      collection_name: null,
      last_page: null,
      furthest_page: null,
      last_read_at: null,
      completed_at: null,
      updated_at: '2026-01-02T00:00:00Z',
    })
  })

  it('shows the personal paper reading learning product wording', async () => {
    const wrapper = mount(HomeView, { global: { plugins: [createPinia(), router()] } })
    await flushPromises()
    expect(wrapper.text()).toContain('AI 驱动的个人论文阅读学习助手')
    expect(wrapper.text()).toContain('论文库')
  })

  it('renders safe library data, all four counts, and the compatible read route', async () => {
    const testRouter = router()
    await testRouter.push('/papers')
    await testRouter.isReady()
    const wrapper = mount(PaperListView, { global: { plugins: [testRouter] } })
    await flushPromises()
    expect(wrapper.text()).toContain('<script>plain title</script>')
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.text()).toContain('高亮 1')
    expect(wrapper.text()).toContain('书签 2')
    expect(wrapper.text()).toContain('笔记 3')
    expect(wrapper.text()).toContain('知识卡 4')
    expect(wrapper.find('.read-link').attributes('href')).toBe(`/papers/${item.paper_id}/read`)
  })

  it('keeps the old status visible and reports a failed update', async () => {
    vi.mocked(api.patchLibraryEntry).mockRejectedValueOnce(new Error('network'))
    const testRouter = router()
    await testRouter.push('/papers')
    await testRouter.isReady()
    const wrapper = mount(PaperListView, { global: { plugins: [testRouter] } })
    await flushPromises()
    await wrapper.findAll('.card-actions button')[0]!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('待读')
    expect(wrapper.find('.action-error').text()).toContain('论文库更新失败')
  })
})
