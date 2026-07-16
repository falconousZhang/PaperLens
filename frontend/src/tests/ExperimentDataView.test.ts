import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import ExperimentDataView from '../views/ExperimentDataView.vue'
import PaperDetailView from '../views/PaperDetailView.vue'
import * as api from '../api'


vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    getPaper: vi.fn(),
    listTasks: vi.fn(),
    getTask: vi.fn(),
    listExperimentFiles: vi.fn(),
    getExperimentFile: vi.fn(),
    uploadExperimentFile: vi.fn(),
    createExperimentAnalysis: vi.fn(),
    getExperimentResult: vi.fn(),
    createComparisons: vi.fn(),
  }
})

const mockPaper = {
  id: 'paper-1',
  title: 'Experiment Test Paper',
  filename: 'test.pdf',
  file_size: 2048,
  page_count: 10,
  status: 'PARSED',
  error_message: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockPaperProcessing = { ...mockPaper, status: 'PROCESSING' }

const mockMetricTaskSucceeded: api.TaskDetail = {
  id: 'mt-1',
  paper_id: 'paper-1',
  task_type: 'METRIC_EXTRACTION',
  status: 'SUCCEEDED',
  progress: 100,
  error_message: null,
  started_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
  created_at: '2026-01-01T00:00:00Z',
}

const mockExperimentFile: api.ExperimentFileListItem = {
  id: 'ef-1',
  paper_id: 'paper-1',
  filename: 'results.csv',
  file_type: 'CSV',
  file_size: 5242880,
  row_count: 100,
  column_count: 5,
  created_at: '2026-01-01T00:00:00Z',
}

const mockExperimentFileDetail: api.ExperimentFileMetadata = {
  ...mockExperimentFile,
  columns_info: {
    version: 1,
    encoding: 'utf-8',
    delimiter: ',',
    sheet_name: null,
    columns: [
      { name: 'accuracy', dtype: 'float', nullable: false, null_count: 0 },
      { name: 'note', dtype: 'string', nullable: true, null_count: 2 },
    ],
  },
}

const mockExperimentResult: api.ExperimentResultResponse = {
  id: 'er-1',
  file_id: 'ef-1',
  task_id: 'at-1',
  summary_stats: {
    version: 1,
    row_count: 100,
    column_count: 3,
    columns: [
      { name: 'accuracy', dtype: 'float', count: 100, null_count: 0, stats: { mean: 0.856, stddev: 0.05, min: 0.7, max: 0.95, median: 0.86 } },
      { name: 'loss', dtype: 'float', count: 98, null_count: 2, stats: { mean: 0.234, stddev: 0.01, min: 0.1, max: 0.5, median: 0.22 } },
      { name: 'name', dtype: 'string', count: 100, null_count: 0, stats: null },
    ],
  },
  metric_comparisons: null,
  created_at: '2026-01-01T00:01:00Z',
}

const mockComparisonItem: api.ComparisonItem = {
  metric_record_id: 'mr-1',
  metric_task_id: 'mt-1',
  metric_name: 'accuracy',
  checkpoint_type: 'MEAN',
  column_name: 'accuracy',
  statistic: 'MEAN',
  paper_value: 0.856,
  experiment_value: 0.85,
  diff: -0.006,
  absolute_diff: 0.006,
  relative_diff: 0.007,
  allowed_diff: 0.01,
  status: 'MATCH',
  reason: null,
}

const mockMismatchItem: api.ComparisonItem = {
  metric_record_id: 'mr-2',
  metric_task_id: 'mt-1',
  metric_name: 'loss',
  checkpoint_type: 'MAX',
  column_name: 'loss',
  statistic: 'MAX',
  paper_value: 0.5,
  experiment_value: 0.8,
  diff: 0.3,
  absolute_diff: 0.3,
  relative_diff: 0.6,
  allowed_diff: 0.05,
  status: 'MISMATCH',
  reason: null,
}

const mockUnverifiableItem: api.ComparisonItem = {
  metric_record_id: 'mr-3',
  metric_task_id: 'mt-1',
  metric_name: 'f1',
  checkpoint_type: 'BEST',
  column_name: null,
  statistic: null,
  paper_value: 0.9,
  experiment_value: null,
  diff: null,
  absolute_diff: null,
  relative_diff: null,
  allowed_diff: null,
  status: 'UNVERIFIABLE',
  reason: 'NO_EXPERIMENT_COLUMN',
}

const mockAnalysisTaskResponse: api.ExperimentAnalysisTaskResponse = {
  id: 'at-1',
  paper_id: 'paper-1',
  task_type: 'EXPERIMENT_ANALYSIS',
  status: 'PENDING',
  progress: 0,
  experiment_file_id: 'ef-1',
  created_at: '2026-01-01T00:00:00Z',
  duplicate: false,
}

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/papers/:id/experiment', name: 'paper-experiment', component: ExperimentDataView },
      { path: '/papers/:id', name: 'paper-detail', component: PaperDetailView },
      { path: '/papers/:id/metrics', name: 'paper-metrics', component: { template: '<div/>' } },
      { path: '/papers', name: 'papers', component: { template: '<div/>' } },
    ],
  })
}

describe('ExperimentDataView', () => {
  let router: Router
  let wrappers: Array<ReturnType<typeof mount>>

  function mountView() {
    const wrapper = mount(ExperimentDataView, { global: { plugins: [router] } })
    wrappers.push(wrapper)
    return wrapper
  }

  beforeEach(async () => {
    vi.clearAllMocks()
    wrappers = []
    router = createTestRouter()
    await router.push('/papers/paper-1/experiment')
    await router.isReady()
    vi.mocked(api.getPaper).mockResolvedValue(mockPaper as any)
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listExperimentFiles).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 } as any)
    vi.mocked(api.getExperimentFile).mockResolvedValue(mockExperimentFileDetail)
    vi.mocked(api.uploadExperimentFile).mockResolvedValue({ ...mockExperimentFileDetail, duplicate: false } as any)
    vi.mocked(api.createExperimentAnalysis).mockResolvedValue(mockAnalysisTaskResponse as any)
    vi.mocked(api.getTask).mockResolvedValue({ ...mockAnalysisTaskResponse, status: 'SUCCEEDED', progress: 100 } as any)
    vi.mocked(api.getExperimentResult).mockRejectedValue({ response: { status: 404 } })
    vi.mocked(api.createComparisons).mockResolvedValue({} as any)
  })

  afterEach(() => {
    wrappers.forEach(w => w.unmount())
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('loads paper and tasks on mount', async () => {
    mountView()
    await flushPromises()
    expect(api.getPaper).toHaveBeenCalledWith('paper-1')
    expect(api.listTasks).toHaveBeenCalledWith('paper-1')
  })

  it('shows not-ready notice for non-PARSED paper', async () => {
    vi.mocked(api.getPaper).mockResolvedValue(mockPaperProcessing as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.not-ready-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('论文正在解析中')
  })

  it('shows empty files state when no experiment files', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.empty-files').exists()).toBe(true)
    expect(wrapper.text()).toContain('暂无实验数据文件')
  })

  it('displays file list with correct columns', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.files-table').exists()).toBe(true)
    const row = wrapper.find('.files-table tbody tr')
    expect(row.text()).toContain('results.csv')
    expect(row.text()).toContain('CSV')
    expect(row.text()).toContain('5.0 MB')
    expect(row.text()).toContain('100')
    expect(row.text()).toContain('5')
  })

  it('selecting a file triggers result load', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    expect(api.getExperimentResult).toHaveBeenCalledWith('ef-1')
    expect(api.getExperimentFile).toHaveBeenCalledWith('ef-1')
  })

  it('renders trusted column metadata from the file detail endpoint', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile], total: 1, page: 1, page_size: 20,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    const rows = wrapper.findAll('.columns-table tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('accuracy')
    expect(rows[1]!.text()).toContain('note')
    expect(rows[1]!.text()).toContain('是')
  })

  it('rejects a mismatched file-detail response', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile], total: 1, page: 1, page_size: 20,
    } as any)
    vi.mocked(api.getExperimentFile).mockResolvedValue({
      ...mockExperimentFileDetail, paper_id: 'paper-other',
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('文件详情上下文异常')
    expect(wrapper.find('.columns-table').exists()).toBe(false)
  })

  it('paginates the experiment file list and clears selection', async () => {
    const secondFile = { ...mockExperimentFile, id: 'ef-21', filename: 'page2.csv' }
    vi.mocked(api.listExperimentFiles).mockImplementation(async (_paperId, page = 1) => ({
      items: page === 2 ? [secondFile] : [mockExperimentFile],
      total: 21,
      page,
      page_size: 20,
    }))
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    await wrapper.find('.pagination button:last-child').trigger('click')
    await flushPromises()
    expect(api.listExperimentFiles).toHaveBeenLastCalledWith('paper-1', 2, 20)
    expect(wrapper.text()).toContain('page2.csv')
    expect(wrapper.find('.analysis-section').exists()).toBe(false)
  })

  it('shows "not analyzed" when result is 404', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockRejectedValue({ response: { status: 404 } })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    expect(wrapper.find('.no-result').exists()).toBe(true)
    expect(wrapper.text()).toContain('尚未分析')
  })

  it('shows existing result immediately on file select', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    expect(wrapper.find('.stats-table').exists()).toBe(true)
  })

  it('upload success refreshes file list', async () => {
    vi.mocked(api.uploadExperimentFile).mockResolvedValue({
      id: 'ef-2',
      paper_id: 'paper-1',
      filename: 'new.csv',
      file_type: 'CSV',
      file_size: 1024,
      row_count: 10,
      column_count: 3,
      columns_info: { version: 1, encoding: 'utf-8', delimiter: ',', sheet_name: null, columns: [{ name: 'a', dtype: 'float', nullable: false, null_count: 0 }] },
      created_at: '2026-01-01T00:00:00Z',
      duplicate: false,
    } as any)
    vi.mocked(api.getExperimentFile).mockResolvedValue({
      ...mockExperimentFileDetail,
      id: 'ef-2',
      filename: 'new.csv',
    })
    const wrapper = mountView()
    await flushPromises()
    const fileInput = wrapper.find('.file-input')
    const file = new File(['data'], 'test.csv', { type: 'text/csv' })
    Object.defineProperty(fileInput.element, 'files', { value: [file], writable: false })
    await fileInput.trigger('change')
    await flushPromises()
    await wrapper.find('.primary-btn').trigger('click')
    await flushPromises()
    expect(api.uploadExperimentFile).toHaveBeenCalledWith('paper-1', expect.any(File))
    expect(api.listExperimentFiles).toHaveBeenCalledTimes(2)
    expect(api.getExperimentFile).toHaveBeenCalledWith('ef-2')
    expect(api.getExperimentResult).toHaveBeenCalledWith('ef-2')
  })

  it('upload duplicate (200) also refreshes file list', async () => {
    vi.mocked(api.uploadExperimentFile).mockResolvedValue({
      id: 'ef-1',
      paper_id: 'paper-1',
      filename: 'dup.csv',
      file_type: 'CSV',
      file_size: 1024,
      row_count: 10,
      column_count: 3,
      columns_info: { version: 1, encoding: 'utf-8', delimiter: ',', sheet_name: null, columns: [{ name: 'a', dtype: 'float', nullable: false, null_count: 0 }] },
      created_at: '2026-01-01T00:00:00Z',
      duplicate: true,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    const fileInput = wrapper.find('.file-input')
    const file = new File(['data'], 'dup.csv', { type: 'text/csv' })
    Object.defineProperty(fileInput.element, 'files', { value: [file], writable: false })
    await fileInput.trigger('change')
    await flushPromises()
    await wrapper.find('.primary-btn').trigger('click')
    await flushPromises()
    expect(api.listExperimentFiles).toHaveBeenCalledTimes(2)
  })

  it('upload double-click lock prevents duplicate uploads', async () => {
    let resolveUpload!: () => void
    const uploadPromise = new Promise<api.ExperimentFileUploadResponse>(resolve => {
      resolveUpload = () => resolve({} as any)
    })
    vi.mocked(api.uploadExperimentFile).mockReturnValue(uploadPromise as any)
    const wrapper = mountView()
    await flushPromises()
    const fileInput = wrapper.find('.file-input')
    const file = new File(['data'], 'test.csv', { type: 'text/csv' })
    Object.defineProperty(fileInput.element, 'files', { value: [file], writable: false })
    await fileInput.trigger('change')
    await flushPromises()
    const btn = wrapper.find('.primary-btn')
    await btn.trigger('click')
    await btn.trigger('click')
    await flushPromises()
    expect(api.uploadExperimentFile).toHaveBeenCalledTimes(1)
    resolveUpload!()
    await flushPromises()
  })

  it('upload validation error is mapped without exposing server details', async () => {
    vi.mocked(api.uploadExperimentFile).mockRejectedValue({
      response: { status: 422, data: { error: { message: '文件格式不支持' } } },
    })
    const wrapper = mountView()
    await flushPromises()
    const fileInput = wrapper.find('.file-input')
    const file = new File(['data'], 'test.csv', { type: 'text/csv' })
    Object.defineProperty(fileInput.element, 'files', { value: [file], writable: false })
    await fileInput.trigger('change')
    await flushPromises()
    await wrapper.find('.primary-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.upload-error').exists()).toBe(true)
    expect(wrapper.text()).toContain('提交内容无效')
    expect(wrapper.text()).not.toContain('文件格式不支持')
  })

  it('blocks unsupported, empty, and oversized files before upload', async () => {
    const cases = [
      { file: new File(['data'], 'notes.txt'), message: '文件格式不支持' },
      { file: new File([], 'empty.csv'), message: '实验文件不能为空' },
      { file: new File(['data'], 'large.xlsx'), size: 20 * 1024 * 1024 + 1, message: '不能超过 20MB' },
    ]
    for (const testCase of cases) {
      const wrapper = mountView()
      await flushPromises()
      const fileInput = wrapper.find('.file-input')
      if (testCase.size) Object.defineProperty(testCase.file, 'size', { value: testCase.size })
      Object.defineProperty(fileInput.element, 'files', { value: [testCase.file], configurable: true })
      await fileInput.trigger('change')
      await flushPromises()
      expect(wrapper.text()).toContain(testCase.message)
      expect(api.uploadExperimentFile).not.toHaveBeenCalled()
      wrapper.unmount()
    }
  })

  it('create analysis 201 starts polling', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    await wrapper.find('.analysis-section .primary-btn').trigger('click')
    await flushPromises()
    expect(api.createExperimentAnalysis).toHaveBeenCalledWith('ef-1')
    expect(wrapper.find('.task-progress').exists()).toBe(true)
  })

  it('create analysis 200 (duplicate) also enters task state machine', async () => {
    vi.mocked(api.createExperimentAnalysis).mockResolvedValue({
      ...mockAnalysisTaskResponse,
      duplicate: true,
    } as any)
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    await wrapper.find('.analysis-section .primary-btn').trigger('click')
    await flushPromises()
    expect(api.createExperimentAnalysis).toHaveBeenCalledWith('ef-1')
    expect(wrapper.find('.task-progress').exists()).toBe(true)
  })

  it('polling: PENDING -> SUCCEEDED stops timer, loads result', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    let pollCount = 0
    vi.mocked(api.getTask).mockImplementation(async () => {
      pollCount++
      if (pollCount <= 1) return { ...mockAnalysisTaskResponse, status: 'RUNNING', progress: 50 } as any
      return { ...mockAnalysisTaskResponse, status: 'SUCCEEDED', progress: 100 } as any
    })
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    await wrapper.find('.analysis-section .primary-btn').trigger('click')
    await flushPromises()
    vi.advanceTimersByTime(4000)
    await flushPromises()
    vi.advanceTimersByTime(4000)
    await flushPromises()
    expect(wrapper.find('.stats-table').exists()).toBe(true)
    const callsBefore = vi.mocked(api.getTask).mock.calls.length
    vi.advanceTimersByTime(10000)
    await flushPromises()
    expect(vi.mocked(api.getTask).mock.calls.length).toBe(callsBefore)
  })

  it('ignores an in-flight polling response after switching files', async () => {
    vi.useFakeTimers()
    const secondFile = { ...mockExperimentFile, id: 'ef-2', filename: 'other.csv' }
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile, secondFile], total: 2, page: 1, page_size: 20,
    } as any)
    let resolveTask!: (task: api.TaskDetail) => void
    vi.mocked(api.getTask).mockReturnValue(new Promise(resolve => { resolveTask = resolve }))
    const wrapper = mountView()
    await flushPromises()
    const rows = wrapper.findAll('.file-row')
    await rows[0]!.trigger('click')
    await flushPromises()
    await wrapper.find('.analysis-section .primary-btn').trigger('click')
    await flushPromises()
    vi.advanceTimersByTime(4000)
    await Promise.resolve()
    await rows[1]!.trigger('click')
    await flushPromises()
    const resultCallsBefore = vi.mocked(api.getExperimentResult).mock.calls.length
    resolveTask!({ ...mockAnalysisTaskResponse, status: 'SUCCEEDED', progress: 100 } as any)
    await flushPromises()
    expect(api.getExperimentResult).toHaveBeenCalledTimes(resultCallsBefore)
    expect(wrapper.find('.stats-table').exists()).toBe(false)
  })

  it('polling network failure stops timer and shows error', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getTask).mockRejectedValue({
      response: { status: 500, data: { error: { message: 'Network error' } } },
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    await wrapper.find('.analysis-section .primary-btn').trigger('click')
    await flushPromises()
    vi.advanceTimersByTime(4000)
    await flushPromises()
    expect(wrapper.find('.poll-error').exists()).toBe(true)
    expect(wrapper.text()).toContain('暂时无法获取分析进度')
    expect(wrapper.text()).not.toContain('Network error')
  })

  it('analysis FAILED shows error and retry button', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getTask).mockResolvedValue({
      ...mockAnalysisTaskResponse,
      status: 'FAILED',
      progress: 30,
      error_message: 'Analysis crashed',
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    await wrapper.find('.analysis-section .primary-btn').trigger('click')
    await flushPromises()
    vi.advanceTimersByTime(4000)
    await flushPromises()
    expect(wrapper.find('.failed-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('实验分析失败，请稍后重试')
    expect(wrapper.text()).not.toContain('Analysis crashed')
  })

  it('stats table displays columns in backend order, null stats as em dash', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    const rows = wrapper.findAll('.stats-table tbody tr')
    expect(rows.length).toBe(3)
    expect(rows[0]!.text()).toContain('accuracy')
    expect(rows[0]!.text()).toContain('0.856')
    expect(rows[1]!.text()).toContain('loss')
    expect(rows[1]!.text()).toContain('0.234')
    expect(rows[2]!.text()).toContain('name')
    const nameRowCells = rows[2]!.findAll('td')
    expect(nameRowCells[4]!.text()).toBe('\u2014')
    expect(nameRowCells[5]!.text()).toBe('\u2014')
    expect(nameRowCells[6]!.text()).toBe('\u2014')
    expect(nameRowCells[7]!.text()).toBe('\u2014')
    expect(nameRowCells[8]!.text()).toBe('\u2014')
  })

  it('metric task selector only shows SUCCEEDED METRIC_EXTRACTION tasks', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult as any)
    const failedMetricTask: api.TaskDetail = {
      ...mockMetricTaskSucceeded,
      id: 'mt-failed',
      status: 'FAILED',
    }
    const reviewTask: api.TaskDetail = {
      id: 'rt-1',
      paper_id: 'paper-1',
      task_type: 'REVIEW',
      status: 'SUCCEEDED',
      progress: 100,
      error_message: null,
      started_at: null,
      completed_at: null,
      created_at: '2026-01-01T00:00:00Z',
    }
    vi.mocked(api.listTasks).mockResolvedValue({
      items: [mockMetricTaskSucceeded, failedMetricTask, reviewTask],
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    const options = wrapper.findAll('#metric-task-select option')
    expect(options.length).toBe(1)
    expect(options[0]!.attributes('value')).toBe('mt-1')
  })

  it('selects the newest successful metric task even when the API response is unsorted', async () => {
    const newerTask: api.TaskDetail = {
      ...mockMetricTaskSucceeded,
      id: 'mt-new',
      created_at: '2026-02-01T00:00:00Z',
    }
    vi.mocked(api.listTasks).mockResolvedValue({
      items: [mockMetricTaskSucceeded, newerTask],
    } as any)
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile], total: 1, page: 1, page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    expect((wrapper.find('#metric-task-select').element as HTMLSelectElement).value).toBe('mt-new')
  })

  it('no metrics notice when no SUCCEEDED metric tasks', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult as any)
    vi.mocked(api.listTasks).mockResolvedValue({ items: [] } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    expect(wrapper.find('.no-metrics-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('没有成功的指标提取任务')
    expect(wrapper.find('a[href="/papers/paper-1/metrics"]').exists()).toBe(true)
  })

  it('restores an existing comparison even when its source task is absent from the task list', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [] } as any)
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile], total: 1, page: 1, page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue({
      ...mockExperimentResult,
      metric_comparisons: [mockComparisonItem],
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    expect(wrapper.find('.comparison-table').exists()).toBe(true)
    expect(wrapper.find('.no-metrics-notice').exists()).toBe(false)
    expect(wrapper.find('#metric-task-select option').text()).toBe('已有交叉验证来源')
  })

  it('comparison: MATCH green, MISMATCH red, UNVERIFIABLE orange', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue({
      ...mockExperimentResult,
      metric_comparisons: [mockComparisonItem, mockMismatchItem, mockUnverifiableItem],
    } as any)
    vi.mocked(api.createComparisons).mockResolvedValue({
      file_id: 'ef-1',
      experiment_result_id: 'er-1',
      metric_task_id: 'mt-1',
      comparisons: [mockComparisonItem, mockMismatchItem, mockUnverifiableItem],
      duplicate: false,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    const rows = wrapper.findAll('.comparison-table tbody tr')
    expect(rows.length).toBe(3)
    expect(rows[0]!.find('.status-match').exists()).toBe(true)
    expect(rows[1]!.find('.status-mismatch').exists()).toBe(true)
    expect(rows[2]!.find('.status-unverifiable').exists()).toBe(true)
    expect(api.createComparisons).not.toHaveBeenCalled()
    expect(wrapper.find('.comparison-locked').exists()).toBe(true)
    expect(wrapper.find('#metric-task-select').attributes('disabled')).toBeDefined()
  })

  it('comparison: five reason labels mapped to Chinese', async () => {
    const reasons: Array<api.ComparisonReason> = [
      'AMBIGUOUS_PAPER_METRIC',
      'NO_EXPERIMENT_COLUMN',
      'AMBIGUOUS_EXPERIMENT_COLUMN',
      'UNSUPPORTED_CHECKPOINT',
      'EMPTY_NORMALIZED_NAME',
    ]
    const items: api.ComparisonItem[] = reasons.map((reason, i) => ({
      metric_record_id: `mr-${i}`,
      metric_task_id: 'mt-1',
      metric_name: `metric-${i}`,
      checkpoint_type: 'BEST' as const,
      column_name: null,
      statistic: null,
      paper_value: 0.5 + i * 0.1,
      experiment_value: null,
      diff: null,
      absolute_diff: null,
      relative_diff: null,
      allowed_diff: null,
      status: 'UNVERIFIABLE' as const,
      reason,
    }))
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue({
      ...mockExperimentResult,
      metric_comparisons: items,
    } as any)
    vi.mocked(api.createComparisons).mockResolvedValue({
      file_id: 'ef-1',
      experiment_result_id: 'er-1',
      metric_task_id: 'mt-1',
      comparisons: items,
      duplicate: false,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('论文指标歧义')
    expect(text).toContain('无对应实验列')
    expect(text).toContain('实验列歧义')
    expect(text).toContain('不支持的检查点')
    expect(text).toContain('标准化名称为空')
  })

  it('comparison 201 returns result, 200 sets duplicate', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult as any)
    vi.mocked(api.createComparisons).mockResolvedValue({
      file_id: 'ef-1',
      experiment_result_id: 'er-1',
      metric_task_id: 'mt-1',
      comparisons: [mockComparisonItem],
      duplicate: true,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    await wrapper.find('.comparison-controls .primary-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.comparison-table').exists()).toBe(true)
  })

  it('rejects a comparison response from a different file context', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile], total: 1, page: 1, page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult)
    vi.mocked(api.createComparisons).mockResolvedValue({
      file_id: 'ef-other',
      experiment_result_id: 'er-1',
      metric_task_id: 'mt-1',
      comparisons: [mockComparisonItem],
      duplicate: false,
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    await wrapper.find('.comparison-controls .primary-btn').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('交叉验证响应上下文异常')
    expect(wrapper.find('.comparison-table').exists()).toBe(false)
  })

  it('comparison 409 shows error message', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult as any)
    vi.mocked(api.createComparisons).mockRejectedValue({
      response: { status: 409, data: { error: { message: 'Conflict' } } },
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    await wrapper.find('.comparison-controls .primary-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.comparison-error').exists()).toBe(true)
  })

  it('zero values stay visible and null comparison values use an em dash', async () => {
    const zeroItem: api.ComparisonItem = {
      ...mockComparisonItem,
      paper_value: 0,
      experiment_value: 0,
      diff: 0,
      absolute_diff: 0,
      relative_diff: null,
      allowed_diff: 0.01,
    }
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue({
      ...mockExperimentResult,
      metric_comparisons: [zeroItem],
    } as any)
    vi.mocked(api.createComparisons).mockResolvedValue({
      file_id: 'ef-1',
      experiment_result_id: 'er-1',
      metric_task_id: 'mt-1',
      comparisons: [zeroItem],
      duplicate: false,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    const row = wrapper.find('.comparison-table tbody tr')
    const cells = row.findAll('td')
    expect(cells[4]!.text()).toBe('0')
    expect(cells[8]!.text()).toBe('—')
  })

  it('unmount cleans up timer', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.createExperimentAnalysis).mockResolvedValue({
      ...mockAnalysisTaskResponse,
      status: 'RUNNING',
      progress: 50,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    await wrapper.find('.analysis-section .primary-btn').trigger('click')
    await flushPromises()
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
    wrapper.unmount()
    expect(clearIntervalSpy).toHaveBeenCalled()
  })

  it('route param change resets state and reloads', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    const wrapper = mountView()
    await flushPromises()
    const fileInput = wrapper.find('.file-input')
    const file = new File(['data'], 'pending.csv', { type: 'text/csv' })
    Object.defineProperty(fileInput.element, 'files', { value: [file], configurable: true })
    await fileInput.trigger('change')
    expect(wrapper.find('.upload-row .primary-btn').exists()).toBe(true)
    const newPaper = { ...mockPaper, id: 'paper-2', title: 'Second Paper' }
    vi.mocked(api.getPaper).mockImplementation(async (id: string) => {
      if (id === 'paper-2') return newPaper as any
      return mockPaper as any
    })
    await router.push('/papers/paper-2/experiment')
    await flushPromises()
    expect(api.getPaper).toHaveBeenCalledWith('paper-2')
    expect(api.listTasks).toHaveBeenCalledWith('paper-2')
    expect(wrapper.find('.upload-row .primary-btn').exists()).toBe(false)
  })

  it('load error shows retry button', async () => {
    vi.mocked(api.getPaper).mockRejectedValue(new Error('Server error'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.error-msg').exists()).toBe(true)
    expect(wrapper.find('.error-msg .retry-btn').exists()).toBe(true)
  })

  it('stale response from previous paper is ignored on route change', async () => {
    let resolveOldPaper!: (paper: typeof mockPaper) => void
    const oldPaperRequest = new Promise<typeof mockPaper>(resolve => {
      resolveOldPaper = resolve
    })
    const newPaper = { ...mockPaper, id: 'paper-2', title: 'Second Paper' }
    vi.mocked(api.getPaper).mockImplementation(async (paperId: string) => {
      if (paperId === 'paper-1') return oldPaperRequest as any
      return newPaper as any
    })
    vi.mocked(api.listTasks).mockImplementation(async () => ({ items: [] }))
    const wrapper = mountView()
    await Promise.resolve()
    await router.push('/papers/paper-2/experiment')
    await flushPromises()
    expect(wrapper.text()).toContain('Second Paper')
    resolveOldPaper!(mockPaper)
    await flushPromises()
    expect(wrapper.text()).toContain('Second Paper')
    expect(wrapper.text()).not.toContain('Experiment Test Paper')
  })

  it('does not use localStorage, sessionStorage, or v-html', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    expect(wrapper.find('[v-html]').exists()).toBe(false)
    expect(wrapper.html()).not.toContain('localStorage')
    expect(wrapper.html()).not.toContain('sessionStorage')
  })

  it('does not display API keys, tokens, or raw error details', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue(mockExperimentResult as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    expect(wrapper.text()).not.toContain('api_key')
    expect(wrapper.text()).not.toContain('token')
    expect(wrapper.text()).not.toContain('Authorization')
  })

  it('comparison table shows all fixed columns', async () => {
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue({
      ...mockExperimentResult,
      metric_comparisons: [mockComparisonItem],
    } as any)
    vi.mocked(api.createComparisons).mockResolvedValue({
      file_id: 'ef-1',
      experiment_result_id: 'er-1',
      metric_task_id: 'mt-1',
      comparisons: [mockComparisonItem],
      duplicate: false,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    const headers = wrapper.findAll('.comparison-table thead th')
    expect(headers.length).toBe(12)
    const headerTexts = headers.map(h => h.text())
    expect(headerTexts).toContain('指标名')
    expect(headerTexts).toContain('Checkpoint')
    expect(headerTexts).toContain('列名')
    expect(headerTexts).toContain('统计量')
    expect(headerTexts).toContain('论文值')
    expect(headerTexts).toContain('实验值')
    expect(headerTexts).toContain('差值（实验值 - 论文值）')
    expect(headerTexts).toContain('绝对差值')
    expect(headerTexts).toContain('相对差值')
    expect(headerTexts).toContain('允许差值')
    expect(headerTexts).toContain('状态')
    expect(headerTexts).toContain('原因')
  })

  it('renders XSS content as inert text without v-html', async () => {
    const xssItem: api.ComparisonItem = {
      ...mockComparisonItem,
      metric_name: '<img src=x onerror=alert(1)>',
      column_name: '<script>alert(1)</script>',
    }
    vi.mocked(api.listExperimentFiles).mockResolvedValue({
      items: [mockExperimentFile],
      total: 1,
      page: 1,
      page_size: 20,
    } as any)
    vi.mocked(api.getExperimentResult).mockResolvedValue({
      ...mockExperimentResult,
      metric_comparisons: [xssItem],
    } as any)
    vi.mocked(api.createComparisons).mockResolvedValue({
      file_id: 'ef-1',
      experiment_result_id: 'er-1',
      metric_task_id: 'mt-1',
      comparisons: [xssItem],
      duplicate: false,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.file-row').trigger('click')
    await flushPromises()
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('<img src=x onerror=alert(1)>')
  })
})
