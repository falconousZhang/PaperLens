import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import PaperDetailView from '../views/PaperDetailView.vue'
import * as api from '../api'

vi.mock('../api', () => ({
  getPaper: vi.fn(),
  getPage: vi.fn(),
  listSections: vi.fn(),
  listEvidences: vi.fn(),
}))

const mockPaper = {
  id: 'test-uuid-1',
  title: 'Test Paper',
  filename: 'test.pdf',
  file_size: 1024,
  page_count: 2,
  status: 'PARSED',
  error_message: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockSections = [
  { id: 'sec-1', section_type: 'ABSTRACT', title: 'Abstract', level: 1, sequence: 1, start_page: 1, end_page: 1, text_content: 'Abstract text' },
]

const mockEvidences = [
  { id: 'ev-1', quoted_text: 'This is highlighted evidence text', page_number: 1, bbox_x0: 72, bbox_y0: 72, bbox_x1: 200, bbox_y1: 100, char_start: 6, char_end: 39, evidence_type: 'TEXT', section_id: 'sec-1', chunk_id: 'chunk-1' },
  { id: 'ev-2', quoted_text: 'Evidence on page two', page_number: 2, bbox_x0: 72, bbox_y0: 72, bbox_x1: 200, bbox_y1: 100, char_start: 0, char_end: 20, evidence_type: 'TEXT', section_id: null, chunk_id: null },
  { id: 'ev-3', quoted_text: 'No char range evidence', page_number: 2, bbox_x0: 72, bbox_y0: 72, bbox_x1: 200, bbox_y1: 100, char_start: null, char_end: null, evidence_type: 'TEXT', section_id: null, chunk_id: null },
]

const mockPage1 = {
  id: 'page-1',
  page_number: 1,
  text_content: 'Hello This is highlighted evidence text world',
  normalized_text_content: 'Hello This is highlighted evidence text world',
  width: 612,
  height: 792,
}

const mockPage2 = {
  id: 'page-2',
  page_number: 2,
  text_content: 'Evidence on page two more text here',
  normalized_text_content: 'Evidence on page two more text here',
  width: 612,
  height: 792,
}

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/papers/:id', component: PaperDetailView },
      { path: '/papers', component: { template: '<div/>' } },
    ],
  })
}

describe('PaperDetailView', () => {
  let router: ReturnType<typeof createTestRouter>

  beforeEach(async () => {
    router = createTestRouter()
    router.push('/papers/test-uuid-1')
    await router.isReady()
    vi.mocked(api.getPaper).mockResolvedValue(mockPaper as any)
    vi.mocked(api.listSections).mockResolvedValue(mockSections as any)
    vi.mocked(api.listEvidences).mockResolvedValue(mockEvidences as any)
    vi.mocked(api.getPage).mockImplementation(async (_paperId: string, pageNum: number) => {
      if (pageNum === 1) return mockPage1 as any
      if (pageNum === 2) return mockPage2 as any
      throw { response: { status: 404, data: { error: { message: '页面不存在' } } } }
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('loads paper, sections and evidences on mount', async () => {
    mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()
    expect(api.getPaper).toHaveBeenCalledWith('test-uuid-1')
    expect(api.listSections).toHaveBeenCalledWith('test-uuid-1')
    expect(api.listEvidences).toHaveBeenCalledWith('test-uuid-1')
  })

  it('clicking page-2 evidence loads page 2 and highlights', async () => {
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    const tabs = wrapper.findAll('.tabs button')
    const evidencesTab = tabs.find(b => b.text() === '证据')
    expect(evidencesTab).toBeTruthy()
    await evidencesTab!.trigger('click')
    await flushPromises()

    const evItems = wrapper.findAll('.evidence-item')
    expect(evItems.length).toBeGreaterThanOrEqual(2)

    const page2Ev = evItems[1]!
    await page2Ev.trigger('click')
    await flushPromises()

    expect(api.getPage).toHaveBeenCalledWith('test-uuid-1', 2)
    expect(wrapper.find('.highlight').exists()).toBe(true)
    expect(wrapper.find('.highlight').text()).toBe('Evidence on page two')
  })

  it('shows FAILED status with error_message', async () => {
    vi.mocked(api.getPaper).mockResolvedValue({ ...mockPaper, status: 'FAILED', error_message: 'OCR not supported' } as any)
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()
    expect(wrapper.find('.failed-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('OCR not supported')
  })

  it('stops polling on unmount and does not call API after', async () => {
    vi.useFakeTimers()
    vi.mocked(api.getPaper).mockResolvedValue({ ...mockPaper, status: 'PROCESSING' } as any)
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
    const callCountBefore = vi.mocked(api.getPaper).mock.calls.length
    wrapper.unmount()
    expect(clearIntervalSpy).toHaveBeenCalled()

    vi.advanceTimersByTime(10000)
    expect(vi.mocked(api.getPaper).mock.calls.length).toBe(callCountBefore)
  })

  it('null char range: degraded notice shown, no mark', async () => {
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    const tabs = wrapper.findAll('.tabs button')
    const evidencesTab = tabs.find(b => b.text() === '证据')
    await evidencesTab!.trigger('click')
    await flushPromises()

    const evItems = wrapper.findAll('.evidence-item')
    const nullRangeEv = evItems[2]!
    await nullRangeEv.trigger('click')
    await flushPromises()

    expect(wrapper.find('.degraded-notice').exists()).toBe(true)
    expect(wrapper.find('.highlight').exists()).toBe(false)
  })

  it('highlight mismatch: degraded notice shown, no mark', async () => {
    const mismatchEv = { id: 'ev-mis', quoted_text: 'WRONG TEXT', page_number: 1, bbox_x0: 72, bbox_y0: 72, bbox_x1: 200, bbox_y1: 100, char_start: 6, char_end: 16, evidence_type: 'TEXT', section_id: null, chunk_id: null }
    vi.mocked(api.listEvidences).mockResolvedValue([mismatchEv] as any)
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    const tabs = wrapper.findAll('.tabs button')
    const evidencesTab = tabs.find(b => b.text() === '证据')
    await evidencesTab!.trigger('click')
    await flushPromises()

    const evItem = wrapper.find('.evidence-item')
    await evItem.trigger('click')
    await flushPromises()

    expect(wrapper.find('.degraded-notice').exists()).toBe(true)
    expect(wrapper.find('.highlight').exists()).toBe(false)
  })

  it('out-of-bounds char range: degraded notice shown, no mark', async () => {
    const oobEv = { id: 'ev-oob', quoted_text: 'Hello', page_number: 1, bbox_x0: 72, bbox_y0: 72, bbox_x1: 200, bbox_y1: 100, char_start: 999, char_end: 1004, evidence_type: 'TEXT', section_id: null, chunk_id: null }
    vi.mocked(api.listEvidences).mockResolvedValue([oobEv] as any)
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    const tabs = wrapper.findAll('.tabs button')
    const evidencesTab = tabs.find(b => b.text() === '证据')
    await evidencesTab!.trigger('click')
    await flushPromises()

    const evItem = wrapper.find('.evidence-item')
    await evItem.trigger('click')
    await flushPromises()

    expect(wrapper.find('.degraded-notice').exists()).toBe(true)
    expect(wrapper.find('.highlight').exists()).toBe(false)
  })

  it('page API failure: click retry restores page', async () => {
    let callCount = 0
    vi.mocked(api.getPage).mockImplementation(async (_pid: string, pn: number) => {
      callCount++
      if (pn === 1 && callCount === 1) {
        throw { response: { status: 500, data: { error: { message: '服务器错误' } } } }
      }
      if (pn === 1) return mockPage1 as any
      if (pn === 2) return mockPage2 as any
      throw { response: { status: 404, data: { error: { message: '页面不存在' } } } }
    })
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    const tabs = wrapper.findAll('.tabs button')
    const pagesTab = tabs.find(b => b.text() === '页面')
    await pagesTab!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.error-msg').exists()).toBe(true)
    expect(wrapper.text()).toContain('服务器错误')

    const retryBtn = wrapper.find('.error-msg .retry-btn')
    expect(retryBtn.exists()).toBe(true)
    await retryBtn.trigger('click')
    await flushPromises()

    expect(wrapper.find('.error-msg').exists()).toBe(false)
    expect(wrapper.find('.page-content').exists()).toBe(true)
  })

  it('initial load failure: click retry loads paper', async () => {
    let callCount = 0
    vi.mocked(api.getPaper).mockImplementation(async () => {
      callCount++
      if (callCount === 1) throw { response: { status: 500, data: { error: { message: '加载失败' } } } }
      return mockPaper as any
    })
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('.error-msg').exists()).toBe(true)
    expect(wrapper.text()).toContain('加载失败')

    const retryBtn = wrapper.find('.error-msg .retry-btn')
    await retryBtn.trigger('click')
    await flushPromises()

    expect(wrapper.find('.paper-detail').exists()).toBe(true)
    expect(wrapper.find('.tabs').exists()).toBe(true)
  })

  it('PROCESSING to PARSED: polls then loads sections and evidences, timer stops', async () => {
    vi.useFakeTimers()
    let callCount = 0
    vi.mocked(api.getPaper).mockImplementation(async () => {
      callCount++
      if (callCount <= 1) return { ...mockPaper, status: 'PROCESSING' } as any
      return mockPaper as any
    })
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    vi.advanceTimersByTime(4000)
    await flushPromises()

    expect(vi.mocked(api.listSections)).toHaveBeenCalledWith('test-uuid-1')
    expect(vi.mocked(api.listEvidences)).toHaveBeenCalledWith('test-uuid-1')

    const callsBefore = vi.mocked(api.getPaper).mock.calls.length
    vi.advanceTimersByTime(10000)
    await flushPromises()
    expect(vi.mocked(api.getPaper).mock.calls.length).toBe(callsBefore)
    wrapper.unmount()
  })

  it('XSS: raw special characters displayed safely', async () => {
    const xssPage = {
      id: 'page-xss',
      page_number: 1,
      text_content: '<script>alert(1)</script> and <b>bold</b> & stuff < > "quotes"',
      normalized_text_content: '<script>alert(1)</script> and <b>bold</b> & stuff < > "quotes"',
      width: 612,
      height: 792,
    }
    vi.mocked(api.getPage).mockResolvedValue(xssPage as any)
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    const tabs = wrapper.findAll('.tabs button')
    const pagesTab = tabs.find(b => b.text() === '页面')
    await pagesTab!.trigger('click')
    await flushPromises()

    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.text()).toContain('<script>alert(1)</script>')
    expect(wrapper.text()).toContain('<b>bold</b>')
    expect(wrapper.text()).toContain('& stuff')
    expect(wrapper.text()).toContain('<')
    expect(wrapper.text()).toContain('>')
    expect(wrapper.text()).not.toContain('&lt;script&gt;')
    expect(wrapper.text()).not.toContain('&amp; stuff')
  })

  it('stale page response does not overwrite current page', async () => {
    let resolvePage1: (v: any) => void
    const page1Deferred = new Promise(r => { resolvePage1 = r })

    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    const tabs = wrapper.findAll('.tabs button')
    const evidencesTab = tabs.find(b => b.text() === '证据')
    await evidencesTab!.trigger('click')
    await flushPromises()

    vi.mocked(api.getPage).mockImplementation(async (_pid: string, pn: number) => {
      if (pn === 1) return page1Deferred
      if (pn === 2) return mockPage2 as any
      throw { response: { status: 404, data: { error: { message: '页面不存在' } } } }
    })

    const evItems = wrapper.findAll('.evidence-item')
    const page2Ev = evItems[1]!
    await page2Ev.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Evidence on page two')

    resolvePage1!(mockPage1)
    await flushPromises()

    expect(wrapper.text()).toContain('Evidence on page two')
  })

  it('same-page evidence navigation calls getPage exactly once', async () => {
    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    const tabs = wrapper.findAll('.tabs button')
    const evidencesTab = tabs.find(b => b.text() === '证据')
    await evidencesTab!.trigger('click')
    await flushPromises()

    const evItems = wrapper.findAll('.evidence-item')
    const page1Ev = evItems[0]!
    vi.mocked(api.getPage).mockClear()
    await page1Ev.trigger('click')
    await flushPromises()

    const page1Calls = vi.mocked(api.getPage).mock.calls.filter(c => c[1] === 1).length
    expect(page1Calls).toBeLessThanOrEqual(1)
  })

  it('polling failure stops timer; retry creates at most one timer', async () => {
    vi.useFakeTimers()
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
    let callCount = 0
    vi.mocked(api.getPaper).mockImplementation(async () => {
      callCount++
      if (callCount === 1) return { ...mockPaper, status: 'PROCESSING' } as any
      if (callCount === 2) throw { response: { status: 500, data: { error: { message: '轮询失败' } } } }
      return mockPaper as any
    })

    const wrapper = mount(PaperDetailView, { global: { plugins: [router] } })
    await flushPromises()

    vi.advanceTimersByTime(4000)
    await flushPromises()

    expect(wrapper.find('.poll-error-text').exists()).toBe(true)

    const retryBtn = wrapper.find('.processing-notice .retry-btn')
    await retryBtn.trigger('click')
    await flushPromises()

    expect(clearIntervalSpy).toHaveBeenCalled()

    vi.advanceTimersByTime(4000)
    await flushPromises()

    const getPaperCalls = vi.mocked(api.getPaper).mock.calls.length
    vi.advanceTimersByTime(10000)
    await flushPromises()
    const getPaperCallsAfter = vi.mocked(api.getPaper).mock.calls.length
    expect(getPaperCallsAfter).toBe(getPaperCalls)

    wrapper.unmount()
  })
})
