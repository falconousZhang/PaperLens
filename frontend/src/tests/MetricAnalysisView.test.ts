import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import MetricAnalysisView from '../views/MetricAnalysisView.vue'
import PaperDetailView from '../views/PaperDetailView.vue'
import * as api from '../api'

vi.mock('../api', () => ({
  getPaper: vi.fn(),
  listTasks: vi.fn(),
  createMetricExtractionTask: vi.fn(),
  getTask: vi.fn(),
  listMetrics: vi.fn(),
}))

const mockPaper = {
  id: 'paper-1',
  title: 'Metric Test Paper',
  filename: 'test.pdf',
  file_size: 1024,
  page_count: 10,
  status: 'PARSED',
  error_message: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockPaperProcessing = { ...mockPaper, status: 'PROCESSING' }
const mockPaperFailed = { ...mockPaper, status: 'FAILED' }

const mockMetricTaskPending: api.TaskDetail = {
  id: 'mt-1',
  paper_id: 'paper-1',
  task_type: 'METRIC_EXTRACTION',
  status: 'PENDING',
  progress: 0,
  error_message: null,
  started_at: null,
  completed_at: null,
  created_at: '2026-01-01T00:00:00Z',
}

const mockMetricTaskRunning: api.TaskDetail = {
  ...mockMetricTaskPending,
  id: 'mt-2',
  status: 'RUNNING',
  progress: 50,
}

const mockMetricTaskSucceeded: api.TaskDetail = {
  ...mockMetricTaskPending,
  id: 'mt-3',
  status: 'SUCCEEDED',
  progress: 100,
  started_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
}

const mockMetricTaskFailed: api.TaskDetail = {
  ...mockMetricTaskPending,
  id: 'mt-4',
  status: 'FAILED',
  progress: 30,
  error_message: 'Extraction failed',
  started_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
}

const mockReviewTask: api.TaskDetail = {
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

const mockMetric1: api.MetricRecord = {
  id: 'mr-1',
  paper_id: 'paper-1',
  task_id: 'mt-3',
  model_name: 'BERT-base',
  dataset_name: 'SQuAD',
  metric_name: 'accuracy',
  metric_value: 0.8856,
  checkpoint_type: 'BEST',
  checkpoint_source: null,
  evidence_id: 'ev-1',
  table_id: null,
  row_index: null,
  raw_text: 'accuracy: 88.56%',
  created_at: '2026-01-01T00:01:00Z',
}

const mockMetric2: api.MetricRecord = {
  id: 'mr-2',
  paper_id: 'paper-1',
  task_id: 'mt-3',
  model_name: 'BERT-large',
  dataset_name: 'GLUE',
  metric_name: 'loss',
  metric_value: 0.234,
  checkpoint_type: 'FINAL',
  checkpoint_source: null,
  evidence_id: null,
  table_id: 'tbl-1',
  row_index: 3,
  raw_text: 'loss: 0.234',
  created_at: '2026-01-01T00:01:00Z',
}

const mockMetric3: api.MetricRecord = {
  id: 'mr-3',
  paper_id: 'paper-1',
  task_id: 'mt-3',
  model_name: 'RoBERTa',
  dataset_name: 'SQuAD',
  metric_name: 'f1',
  metric_value: 0.912,
  checkpoint_type: 'UNKNOWN',
  checkpoint_source: null,
  evidence_id: null,
  table_id: null,
  row_index: null,
  raw_text: 'f1: 0.912',
  created_at: '2026-01-01T00:01:00Z',
}

const emptyMetricResponse: api.MetricListResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
}

const metricResponse: api.MetricListResponse = {
  items: [mockMetric1, mockMetric2, mockMetric3],
  total: 3,
  page: 1,
  page_size: 20,
}

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/papers/:id/metrics', name: 'paper-metrics', component: MetricAnalysisView },
      { path: '/papers/:id', name: 'paper-detail', component: PaperDetailView },
      { path: '/papers/:id/read', name: 'paper-read', component: { template: '<div/>' } },
      { path: '/papers', name: 'papers', component: { template: '<div/>' } },
    ],
  })
}

describe('MetricAnalysisView', () => {
  let router: Router
  let wrappers: Array<ReturnType<typeof mount>>

  function mountView() {
    const wrapper = mount(MetricAnalysisView, { global: { plugins: [router] } })
    wrappers.push(wrapper)
    return wrapper
  }

  beforeEach(async () => {
    vi.clearAllMocks()
    wrappers = []
    router = createTestRouter()
    await router.push('/papers/paper-1/metrics')
    await router.isReady()
    vi.mocked(api.getPaper).mockResolvedValue(mockPaper as any)
    vi.mocked(api.listTasks).mockResolvedValue({ items: [] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(emptyMetricResponse as any)
    vi.mocked(api.createMetricExtractionTask).mockResolvedValue({
      id: 'mt-new',
      paper_id: 'paper-1',
      task_type: 'METRIC_EXTRACTION',
      status: 'PENDING',
      progress: 0,
      created_at: '2026-01-01T00:00:00Z',
    } as any)
    vi.mocked(api.getTask).mockResolvedValue(mockMetricTaskSucceeded as any)
  })

  afterEach(() => {
    wrappers.forEach(w => w.unmount())
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('loads paper and tasks but never queries mixed metrics without a successful task_id', async () => {
    mountView()
    await flushPromises()
    expect(api.getPaper).toHaveBeenCalledWith('paper-1')
    expect(api.listTasks).toHaveBeenCalledWith('paper-1')
    expect(api.listMetrics).not.toHaveBeenCalled()
  })

  it('shows not-ready notice for non-PARSED paper', async () => {
    vi.mocked(api.getPaper).mockResolvedValue(mockPaperProcessing as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.not-ready-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('论文正在解析中')
    expect(api.listMetrics).not.toHaveBeenCalled()
  })

  it('shows not-ready notice for FAILED paper', async () => {
    vi.mocked(api.getPaper).mockResolvedValue(mockPaperFailed as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.not-ready-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('论文解析失败')
  })

  it('shows empty state with extract button when no metric tasks', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('尚未提取指标')
    expect(wrapper.find('.primary-btn').exists()).toBe(true)
  })

  it('only filters METRIC_EXTRACTION tasks, ignores REVIEW tasks', async () => {
    const oldMetricTask: api.TaskDetail = {
      ...mockMetricTaskSucceeded,
      id: 'mt-old',
      created_at: '2025-01-01T00:00:00Z',
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockReviewTask, mockMetricTaskSucceeded, oldMetricTask] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    const taskSelector = wrapper.find('.task-selector')
    expect(taskSelector.exists()).toBe(true)
    const options = taskSelector.findAll('option')
    expect(options.length).toBe(2)
  })

  it('auto-selects latest SUCCEEDED metric task and loads its metrics', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    mountView()
    await flushPromises()
    expect(api.listMetrics).toHaveBeenCalledWith('paper-1', expect.objectContaining({ task_id: 'mt-3' }))
  })

  it('recovers PENDING/RUNNING task and starts polling without creating new task', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskRunning] } as any)
    mountView()
    await flushPromises()
    expect(api.createMetricExtractionTask).not.toHaveBeenCalled()
    vi.advanceTimersByTime(4000)
    await flushPromises()
    expect(api.getTask).toHaveBeenCalledWith('mt-2')
  })

  it('polling: RUNNING -> SUCCEEDED stops timer, refreshes data, loads metrics', async () => {
    vi.useFakeTimers()
    let pollCount = 0
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskRunning] } as any)
    vi.mocked(api.getTask).mockImplementation(async () => {
      pollCount++
      if (pollCount <= 1) return { ...mockMetricTaskRunning, progress: 75 } as any
      return mockMetricTaskSucceeded as any
    })
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.task-progress').exists()).toBe(true)
    vi.advanceTimersByTime(4000)
    await flushPromises()
    expect(api.getTask).toHaveBeenCalledWith('mt-2')
    vi.advanceTimersByTime(4000)
    await flushPromises()
    const callsBefore = vi.mocked(api.getTask).mock.calls.length
    vi.advanceTimersByTime(10000)
    await flushPromises()
    expect(vi.mocked(api.getTask).mock.calls.length).toBe(callsBefore)
  })

  it('FAILED task shows error and allows retry', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskFailed] } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.failed-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('Extraction failed')
    const retryBtn = wrapper.find('.failed-notice .retry-btn')
    expect(retryBtn.exists()).toBe(true)
  })

  it('poll network failure stops timer and shows error, retry does not stack timers', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskRunning] } as any)
    let pollCount = 0
    vi.mocked(api.getTask).mockImplementation(async () => {
      pollCount++
      if (pollCount === 1) throw { response: { status: 500, data: { error: { message: 'Network error' } } } }
      return mockMetricTaskSucceeded as any
    })
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
    const wrapper = mountView()
    await flushPromises()
    vi.advanceTimersByTime(4000)
    await flushPromises()
    expect(clearIntervalSpy).toHaveBeenCalled()
    expect(wrapper.find('.poll-error').exists()).toBe(true)
    expect(wrapper.text()).toContain('Network error')
    await wrapper.find('.poll-error .retry-btn').trigger('click')
    vi.advanceTimersByTime(4000)
    await flushPromises()
    expect(api.getTask).toHaveBeenCalledTimes(2)
  })

  it('create lock prevents double-click from creating two tasks', async () => {
    const wrapper = mountView()
    await flushPromises()
    const btn = wrapper.find('.primary-btn')
    await btn.trigger('click')
    await btn.trigger('click')
    await flushPromises()
    expect(api.createMetricExtractionTask).toHaveBeenCalledTimes(1)
  })

  it('FAILED task preserves previous successful results', async () => {
    const oldTask: api.TaskDetail = {
      ...mockMetricTaskSucceeded,
      id: 'mt-old',
      created_at: '2025-01-01T00:00:00Z',
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskFailed, oldTask] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.failed-notice').exists()).toBe(true)
    expect(wrapper.find('.metrics-table').exists()).toBe(true)
  })

  it('succeeded-without-results shows message in empty state', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(emptyMetricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.result-empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('该次指标提取已完成，但没有可展示的指标结果')
  })

  it('metric table displays model, dataset, metric name, value, checkpoint, source, time', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.metrics-table').exists()).toBe(true)
    const rows = wrapper.findAll('.metrics-table tbody tr')
    expect(rows.length).toBe(3)
    expect(rows[0]!.text()).toContain('BERT-base')
    expect(rows[0]!.text()).toContain('SQuAD')
    expect(rows[0]!.text()).toContain('accuracy')
    expect(rows[0]!.text()).toContain('88.56%')
    expect(rows[0]!.text()).toContain('存储值：0.8856')
    expect(rows[0]!.text()).toContain('最佳')
    expect(rows[0]!.text()).toContain('查看证据')
    expect(rows[1]!.text()).toContain('0.234')
    expect(rows[1]!.text()).toContain('最终')
    expect(rows[1]!.text()).toContain('表格 tbl-1 / 0-based 行 3')
    expect(rows[2]!.text()).toContain('91.20%')
    expect(rows[2]!.text()).toContain('未知')
    expect(rows[2]!.text()).toContain('来源不可用')
  })

  it('percent metrics display as percentage, non-percent as raw number', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    const rows = wrapper.findAll('.metrics-table tbody tr')
    expect(rows[0]!.text()).toContain('88.56%')
    expect(rows[1]!.text()).toContain('0.234')
    expect(rows[2]!.text()).toContain('91.20%')
  })

  it('checkpoint type labels: BEST=最佳, FINAL=最终, MAX=最大, MEAN=均值, LAST=最近, UNKNOWN=未知', async () => {
    const metricsWithAllTypes: api.MetricRecord[] = [
      { ...mockMetric1, checkpoint_type: 'BEST' },
      { ...mockMetric1, id: 'mr-b', checkpoint_type: 'FINAL' },
      { ...mockMetric1, id: 'mr-c', checkpoint_type: 'MAX' },
      { ...mockMetric1, id: 'mr-d', checkpoint_type: 'MEAN' },
      { ...mockMetric1, id: 'mr-e', checkpoint_type: 'LAST' },
      { ...mockMetric1, id: 'mr-f', checkpoint_type: 'UNKNOWN' },
    ]
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue({ items: metricsWithAllTypes, total: 6, page: 1, page_size: 20 } as any)
    const wrapper = mountView()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('最佳')
    expect(text).toContain('最终')
    expect(text).toContain('最大')
    expect(text).toContain('均值')
    expect(text).toContain('最近')
    expect(text).toContain('未知')
  })

  it('checkpoint type CSS classes applied correctly', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.checkpoint-best').exists()).toBe(true)
    expect(wrapper.find('.checkpoint-final').exists()).toBe(true)
    expect(wrapper.find('.checkpoint-unknown').exists()).toBe(true)
  })

  it('source UI creates one Evidence deep link, shows table identity and degrades no source', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    const rows = wrapper.findAll('.metrics-table tbody tr')
    expect(rows[0]!.text()).toContain('查看证据')
    expect(rows[0]!.find('.evidence-link').attributes('href')).toBe('/papers/paper-1/read?evidence=ev-1')
    expect(rows[1]!.text()).toContain('表格 tbl-1 / 0-based 行 3')
    expect(rows[1]!.find('a').exists()).toBe(false)
    expect(rows[2]!.text()).toContain('来源不可用')
  })

  it('filter bar: metric_name and dataset_name exact filter sent to backend', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    const nameInput = wrapper.find('#filter-metric-name')
    await nameInput.setValue('accuracy')
    await nameInput.trigger('change')
    await flushPromises()
    expect(api.listMetrics).toHaveBeenCalledWith('paper-1', expect.objectContaining({ metric_name: 'accuracy' }))
    const datasetInput = wrapper.find('#filter-dataset')
    await datasetInput.setValue('SQuAD')
    await datasetInput.trigger('change')
    await flushPromises()
    expect(api.listMetrics).toHaveBeenCalledWith('paper-1', expect.objectContaining({ dataset_name: 'SQuAD' }))
  })

  it('filter bar: checkpoint_type dropdown sends filter to backend', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    const select = wrapper.find('#filter-checkpoint')
    await select.setValue('BEST')
    await select.trigger('change')
    await flushPromises()
    expect(api.listMetrics).toHaveBeenCalledWith('paper-1', expect.objectContaining({ checkpoint_type: 'BEST' }))
  })

  it('clear filters resets all and reloads', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    const nameInput = wrapper.find('#filter-metric-name')
    await nameInput.setValue('accuracy')
    await nameInput.trigger('change')
    await flushPromises()
    expect(wrapper.find('.clear-btn').exists()).toBe(true)
    await wrapper.find('.clear-btn').trigger('click')
    await flushPromises()
    const calls = vi.mocked(api.listMetrics).mock.calls
    const lastCall = calls[calls.length - 1]!
    expect(lastCall[1]).not.toHaveProperty('metric_name')
  })

  it('pagination: next/prev buttons and page display', async () => {
    const manyMetrics = Array.from({ length: 25 }, (_, i) => ({
      ...mockMetric1,
      id: `mr-${i}`,
      metric_name: `metric_${i}`,
    }))
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue({ items: manyMetrics.slice(0, 20), total: 25, page: 1, page_size: 20 } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('第 1 / 2 页')
    expect(wrapper.text()).toContain('共 25 条')
    const nextBtn = wrapper.findAll('.pagination button')[1]!
    expect(nextBtn.attributes('disabled')).toBeUndefined()
    await nextBtn.trigger('click')
    await flushPromises()
    expect(api.listMetrics).toHaveBeenCalledWith('paper-1', expect.objectContaining({ page: 2 }))
  })

  it('task selector dropdown switches selected task and reloads metrics', async () => {
    const oldTask: api.TaskDetail = {
      ...mockMetricTaskSucceeded,
      id: 'mt-old',
      created_at: '2025-01-01T00:00:00Z',
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded, oldTask] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.task-selector').exists()).toBe(true)
    const select = wrapper.find('#task-select')
    await select.setValue('mt-old')
    await select.trigger('change')
    await flushPromises()
    expect(api.listMetrics).toHaveBeenCalledWith('paper-1', expect.objectContaining({ task_id: 'mt-old' }))
  })

  it('unmount cleans up timer', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskRunning] } as any)
    const wrapper = mountView()
    await flushPromises()
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
    wrapper.unmount()
    expect(clearIntervalSpy).toHaveBeenCalled()
    vi.advanceTimersByTime(10000)
    await flushPromises()
    const callsBefore = vi.mocked(api.getTask).mock.calls.length
    vi.advanceTimersByTime(10000)
    await flushPromises()
    expect(vi.mocked(api.getTask).mock.calls.length).toBe(callsBefore)
  })

  it('route param change resets state and reloads', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    mountView()
    await flushPromises()
    const newPaper = { ...mockPaper, id: 'paper-2', title: 'Second Paper' }
    vi.mocked(api.getPaper).mockImplementation(async (id: string) => {
      if (id === 'paper-2') return newPaper as any
      return mockPaper as any
    })
    await router.push('/papers/paper-2/metrics')
    await flushPromises()
    expect(api.getPaper).toHaveBeenCalledWith('paper-2')
    expect(api.listTasks).toHaveBeenCalledWith('paper-2')
  })

  it('load error shows retry button', async () => {
    vi.mocked(api.getPaper).mockRejectedValue(new Error('Server error'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.error-msg').exists()).toBe(true)
    expect(wrapper.find('.error-msg .retry-btn').exists()).toBe(true)
  })

  it('stale response from previous paper is ignored on route change', async () => {
    let resolveOldPaper: (paper: typeof mockPaper) => void
    const oldPaperRequest = new Promise<typeof mockPaper>(resolve => {
      resolveOldPaper = resolve
    })
    const newPaper = { ...mockPaper, id: 'paper-2', title: 'Second Paper' }
    vi.mocked(api.getPaper).mockImplementation(async (paperId: string) => {
      if (paperId === 'paper-1') return oldPaperRequest as any
      return newPaper as any
    })
    vi.mocked(api.listTasks).mockImplementation(async () => ({ items: [] }))
    vi.mocked(api.listMetrics).mockImplementation(async () => emptyMetricResponse as any)
    const wrapper = mountView()
    await Promise.resolve()
    await router.push('/papers/paper-2/metrics')
    await flushPromises()
    expect(wrapper.text()).toContain('Second Paper')
    resolveOldPaper!(mockPaper)
    await flushPromises()
    expect(wrapper.text()).toContain('Second Paper')
    expect(wrapper.text()).not.toContain('Metric Test Paper')
  })

  it('progress bar clamps out-of-range values to 0-100', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listTasks).mockResolvedValue({
      items: [{ ...mockMetricTaskRunning, progress: 150 }],
    } as any)
    const wrapper = mountView()
    await flushPromises()
    const progress = wrapper.find('[role="progressbar"]')
    expect(progress.attributes('aria-valuenow')).toBe('100')
    expect(progress.attributes('style')).toContain('width: 100%')
    expect(wrapper.find('.progress-text').text()).toBe('100%')
  })

  it('empty filter params are not sent to backend', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    mountView()
    await flushPromises()
    const call = vi.mocked(api.listMetrics).mock.calls[0]!
    const params = call[1] as Record<string, any>
    expect(params).not.toHaveProperty('metric_name')
    expect(params).not.toHaveProperty('dataset_name')
    expect(params).not.toHaveProperty('checkpoint_type')
  })

  it('history selector contains only SUCCEEDED metric tasks', async () => {
    const oldTask: api.TaskDetail = {
      ...mockMetricTaskSucceeded,
      id: 'mt-old',
      created_at: '2025-01-01T00:00:00Z',
    }
    vi.mocked(api.listTasks).mockResolvedValue({
      items: [mockMetricTaskRunning, mockMetricTaskFailed, mockMetricTaskSucceeded, oldTask],
    } as any)
    vi.mocked(api.listMetrics).mockResolvedValue(metricResponse as any)
    const wrapper = mountView()
    await flushPromises()
    const options = wrapper.findAll('#task-select option')
    expect(options.map(option => option.attributes('value'))).toEqual(['mt-3', 'mt-old'])
  })

  it('keeps filters visible when the backend returns zero matches so users can clear them', async () => {
    let calls = 0
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockImplementation(async () => {
      calls += 1
      return calls === 1 ? metricResponse : emptyMetricResponse
    })
    const wrapper = mountView()
    await flushPromises()
    const input = wrapper.find('#filter-metric-name')
    await input.setValue('missing')
    await input.trigger('change')
    await flushPromises()
    expect(wrapper.find('.filter-bar').exists()).toBe(true)
    expect(wrapper.find('.clear-btn').exists()).toBe(true)
    expect(wrapper.find('.result-empty-state').text()).toContain('当前筛选条件下没有匹配指标')
  })

  it('ignores a slow stale filter response after a newer filter has completed', async () => {
    let resolveSlow!: (value: api.MetricListResponse) => void
    const slowResponse = new Promise<api.MetricListResponse>(resolve => {
      resolveSlow = resolve
    })
    const fastMetric = { ...mockMetric2, id: 'mr-fast', metric_name: 'fast' }
    const slowMetric = { ...mockMetric1, id: 'mr-slow', metric_name: 'slow' }
    let calls = 0
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockImplementation(async (_paperId, params) => {
      calls += 1
      if (calls === 1) return metricResponse
      if (params?.metric_name === 'slow') return slowResponse
      return { ...emptyMetricResponse, items: [fastMetric], total: 1 }
    })
    const wrapper = mountView()
    await flushPromises()
    const input = wrapper.find('#filter-metric-name')
    await input.setValue('slow')
    await input.trigger('change')
    await Promise.resolve()
    await input.setValue('fast')
    await input.trigger('change')
    await flushPromises()
    expect(wrapper.find('.metrics-table').text()).toContain('fast')
    resolveSlow({ ...emptyMetricResponse, items: [slowMetric], total: 1 })
    await flushPromises()
    expect(wrapper.find('.metrics-table').text()).toContain('fast')
    expect(wrapper.find('.metrics-table').text()).not.toContain('slow')
  })

  it('recovers from a 409 create race by reloading the active server task', async () => {
    vi.mocked(api.listTasks)
      .mockResolvedValueOnce({ items: [] } as any)
      .mockResolvedValueOnce({ items: [mockMetricTaskRunning] } as any)
    vi.mocked(api.createMetricExtractionTask).mockRejectedValue({ response: { status: 409 } })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.primary-btn').trigger('click')
    await flushPromises()
    expect(api.listTasks).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.task-progress').exists()).toBe(true)
    expect(wrapper.find('.error-msg').exists()).toBe(false)
  })

  it('degrades dual and malformed sources without creating guessed links', async () => {
    const dualSource = {
      ...mockMetric1,
      id: 'mr-dual',
      table_id: 'tbl-unexpected',
      row_index: 0,
    }
    const malformedRow = {
      ...mockMetric2,
      id: 'mr-row',
      row_index: -1,
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue({
      ...emptyMetricResponse,
      items: [dualSource, malformedRow, mockMetric3],
      total: 3,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.findAll('.unavailable-source')).toHaveLength(3)
    expect(wrapper.find('.evidence-link').exists()).toBe(false)
  })

  it('renders model, dataset and raw_text as inert text', async () => {
    const unsafeMetric = {
      ...mockMetric1,
      model_name: '<img src=x onerror=alert(1)>',
      dataset_name: '<b>unsafe</b>',
      raw_text: '<script>window.pwned=true</script>',
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockMetricTaskSucceeded] } as any)
    vi.mocked(api.listMetrics).mockResolvedValue({
      ...emptyMetricResponse,
      items: [unsafeMetric],
      total: 1,
    } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('<script>window.pwned=true</script>')
    expect(wrapper.html()).toContain('&lt;b&gt;unsafe&lt;/b&gt;')
  })
})
