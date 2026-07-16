import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ReportExportView from '../views/ReportExportView.vue'
import * as api from '../api'

vi.mock('../api', () => ({
  getPaper: vi.fn(),
  createExport: vi.fn(),
  listExports: vi.fn(),
  downloadExportBlob: vi.fn(),
}))

const mockPaper = {
  id: 'paper-1',
  title: 'Test Paper',
  filename: 'test.pdf',
  file_size: 1024,
  page_count: 10,
  status: 'PARSED',
  error_message: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockExportReady = {
  id: 'export-1',
  paper_id: 'paper-1',
  report_type: 'MARKDOWN' as const,
  language: 'zh' as const,
  include_metrics: true,
  include_experiment_analysis: true,
  status: 'READY' as const,
  file_size: 1234,
  error_message: null,
  created_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
}

const mockExportPending = {
  ...mockExportReady,
  id: 'export-2',
  status: 'PENDING' as const,
  file_size: null,
  completed_at: null,
}

const mockExportFailed = {
  ...mockExportReady,
  id: 'export-3',
  report_type: 'PDF' as const,
  status: 'FAILED' as const,
  error_message: '报告生成失败，请稍后重试',
  file_size: null,
  completed_at: null,
}

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/papers/:id/export', name: 'paper-export', component: ReportExportView },
      { path: '/papers/:id', name: 'paper-detail', component: { template: '<div/>' } },
      { path: '/papers', name: 'papers', component: { template: '<div/>' } },
    ],
  })
}

describe('ReportExportView', () => {
  let router: ReturnType<typeof createTestRouter>
  let wrappers: Array<ReturnType<typeof mount>>

  function mountView() {
    const wrapper = mount(ReportExportView, { global: { plugins: [router] } })
    wrappers.push(wrapper)
    return wrapper
  }

  beforeEach(async () => {
    vi.clearAllMocks()
    wrappers = []
    router = createTestRouter()
    router.push('/papers/paper-1/export')
    await router.isReady()
    vi.mocked(api.getPaper).mockResolvedValue(mockPaper as any)
    vi.mocked(api.listExports).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    vi.mocked(api.createExport).mockResolvedValue(mockExportReady as any)
  })

  afterEach(() => {
    wrappers.forEach(wrapper => wrapper.unmount())
    vi.useRealTimers()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('loads paper and shows export form for PARSED paper', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(api.getPaper).toHaveBeenCalledWith('paper-1')
    expect(wrapper.find('.export-form').exists()).toBe(true)
    expect(wrapper.text()).toContain('创建导出报告')
  })

  it('shows not-ready notice for non-PARSED paper', async () => {
    vi.mocked(api.getPaper).mockResolvedValue({ ...mockPaper, status: 'PROCESSING' } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.not-ready-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('论文尚未解析完成')
  })

  it('shows three format options', async () => {
    const wrapper = mountView()
    await flushPromises()
    const options = wrapper.findAll('select#report-type option')
    const values = options.map(o => (o.element as HTMLOptionElement).value)
    expect(values).toContain('MARKDOWN')
    expect(values).toContain('PDF')
    expect(values).toContain('DOCX')
  })

  it('submits MARKDOWN export and reloads history', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()
    expect(api.createExport).toHaveBeenCalledWith('paper-1', expect.objectContaining({
      report_type: 'MARKDOWN',
      language: 'zh',
    }))
    expect(api.listExports).toHaveBeenCalled()
  })

  it('submits PDF export', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('select#report-type').setValue('PDF')
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()
    expect(api.createExport).toHaveBeenCalledWith('paper-1', expect.objectContaining({
      report_type: 'PDF',
    }))
  })

  it('submits DOCX export', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('select#report-type').setValue('DOCX')
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()
    expect(api.createExport).toHaveBeenCalledWith('paper-1', expect.objectContaining({
      report_type: 'DOCX',
    }))
  })

  it('shows 409 error message for review not ready', async () => {
    vi.mocked(api.createExport).mockRejectedValue({
      response: { status: 409 },
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()
    expect(wrapper.find('.error-text').text()).toBe('审阅结果尚未就绪，请先完成论文审阅')
  })

  it('shows 413 error message for report too large', async () => {
    vi.mocked(api.createExport).mockRejectedValue({
      response: { status: 413 },
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()
    expect(wrapper.find('.error-text').text()).toBe('报告超过大小上限')
  })

  it('shows export history with items', async () => {
    vi.mocked(api.listExports).mockResolvedValue({
      items: [mockExportReady, mockExportPending, mockExportFailed],
      total: 3,
      page: 1,
      page_size: 20,
    })
    const wrapper = mountView()
    await flushPromises()
    const rows = wrapper.findAll('.export-table tbody tr')
    expect(rows.length).toBe(3)
    expect(wrapper.text()).toContain('已完成')
    expect(wrapper.text()).toContain('等待生成')
    expect(wrapper.text()).toContain('生成失败')
  })

  it('shows empty history message', async () => {
    vi.mocked(api.listExports).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('暂无导出记录')
  })

  it('downloads READY report via blob', async () => {
    const blob = new Blob(['# Report'], { type: 'text/markdown' })
    const createObjectURL = vi.fn(() => 'blob:report')
    const revokeObjectURL = vi.fn()
    const NativeURL = globalThis.URL
    vi.stubGlobal('URL', Object.assign(class extends NativeURL {}, { createObjectURL, revokeObjectURL }))
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.mocked(api.downloadExportBlob).mockResolvedValue(blob)
    vi.mocked(api.listExports).mockResolvedValue({
      items: [mockExportReady],
      total: 1,
      page: 1,
      page_size: 20,
    })
    const wrapper = mountView()
    await flushPromises()

    const downloadBtn = wrapper.find('.btn-small')
    expect(downloadBtn.exists()).toBe(true)
    expect(downloadBtn.text()).toBe('下载')
    await downloadBtn.trigger('click')
    await flushPromises()
    expect(api.downloadExportBlob).toHaveBeenCalledWith('export-1')
    expect(createObjectURL).toHaveBeenCalledWith(blob)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:report')
  })

  it('shows a safe download error', async () => {
    vi.mocked(api.downloadExportBlob).mockRejectedValue(new Error('private storage path'))
    vi.mocked(api.listExports).mockResolvedValue({
      items: [mockExportReady],
      total: 1,
      page: 1,
      page_size: 20,
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.btn-small').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('下载失败，请稍后重试')
    expect(wrapper.text()).not.toContain('private storage path')
  })

  it('paginates export history with bounded API parameters', async () => {
    vi.mocked(api.listExports)
      .mockResolvedValueOnce({ items: [mockExportReady], total: 21, page: 1, page_size: 20 })
      .mockResolvedValueOnce({ items: [mockExportFailed], total: 21, page: 2, page_size: 20 })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('第 1 / 2 页，共 21 条')
    const paginationButtons = wrapper.findAll('.pagination button')
    expect(paginationButtons).toHaveLength(2)
    await paginationButtons[1]!.trigger('click')
    await flushPromises()
    expect(api.listExports).toHaveBeenLastCalledWith('paper-1', 2, 20)
    expect(wrapper.text()).toContain('第 2 / 2 页，共 21 条')
  })

  it('ignores stale page responses', async () => {
    vi.mocked(api.listExports).mockResolvedValueOnce({
      items: [mockExportReady], total: 21, page: 1, page_size: 20,
    })
    const wrapper = mountView()
    await flushPromises()

    let resolvePage2!: (value: any) => void
    let resolvePage1!: (value: any) => void
    const page2Response = new Promise(resolve => { resolvePage2 = resolve })
    const page1Response = new Promise(resolve => { resolvePage1 = resolve })
    vi.mocked(api.listExports)
      .mockImplementationOnce(() => page2Response as any)
      .mockImplementationOnce(() => page1Response as any)

    const paginationButtons = wrapper.findAll('.pagination button')
    expect(paginationButtons).toHaveLength(2)
    await paginationButtons[1]!.trigger('click')
    await paginationButtons[0]!.trigger('click')
    resolvePage1({ items: [{ ...mockExportReady, id: 'current-page' }], total: 21, page: 1, page_size: 20 })
    await flushPromises()
    resolvePage2({ items: [{ ...mockExportReady, id: 'stale-page' }], total: 21, page: 2, page_size: 20 })
    await flushPromises()

    expect(wrapper.text()).toContain('第 1 / 2 页，共 21 条')
    expect(wrapper.findAll('.export-table tbody tr')).toHaveLength(1)
    expect(api.listExports).toHaveBeenLastCalledWith('paper-1', 1, 20)
  })

  it('shows export history loading errors and retries', async () => {
    vi.mocked(api.listExports)
      .mockRejectedValueOnce(new Error('internal detail'))
      .mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 20 })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('导出历史加载失败')
    expect(wrapper.text()).not.toContain('internal detail')
    const retry = wrapper.find('.export-history .error-text .btn')
    await retry.trigger('click')
    await flushPromises()
    expect(api.listExports).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).not.toContain('导出历史加载失败')
  })

  it('retries FAILED export', async () => {
    vi.mocked(api.listExports).mockResolvedValue({
      items: [mockExportFailed],
      total: 1,
      page: 1,
      page_size: 20,
    })
    const wrapper = mountView()
    await flushPromises()

    const retryBtn = wrapper.find('.btn-small')
    expect(retryBtn.exists()).toBe(true)
    expect(retryBtn.text()).toBe('重试')
    await retryBtn.trigger('click')
    await flushPromises()
    expect(api.createExport).toHaveBeenCalledWith('paper-1', expect.objectContaining({
      report_type: 'PDF',
    }))
  })

  it('stops polling on unmount', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listExports).mockResolvedValue({
      items: [mockExportPending],
      total: 1,
      page: 1,
      page_size: 20,
    })
    const wrapper = mountView()
    await flushPromises()

    const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout')
    const callsBefore = vi.mocked(api.listExports).mock.calls.length
    wrapper.unmount()
    expect(clearTimeoutSpy).toHaveBeenCalled()

    vi.advanceTimersByTime(10000)
    expect(vi.mocked(api.listExports).mock.calls.length).toBe(callsBefore)
  })

  it('201 upsert: duplicate=false on new export', async () => {
    vi.mocked(api.createExport).mockResolvedValue({
      ...mockExportReady,
      duplicate: false,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()
    expect(api.createExport).toHaveBeenCalled()
  })

  it('200 upsert: duplicate=true on existing export', async () => {
    vi.mocked(api.createExport).mockResolvedValue({
      ...mockExportReady,
      duplicate: true,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()
    expect(api.createExport).toHaveBeenCalled()
  })
})
