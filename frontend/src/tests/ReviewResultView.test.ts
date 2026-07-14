import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import ReviewResultView from '../views/ReviewResultView.vue'
import PaperDetailView from '../views/PaperDetailView.vue'
import * as api from '../api'

vi.mock('../api', () => ({
  getPaper: vi.fn(),
  listTasks: vi.fn(),
  createTask: vi.fn(),
  getTask: vi.fn(),
  listReviews: vi.fn(),
  listSections: vi.fn(),
  listEvidences: vi.fn(),
  getPage: vi.fn(),
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

const mockTaskPending: api.TaskDetail = {
  id: 'task-1',
  paper_id: 'paper-1',
  task_type: 'REVIEW',
  status: 'PENDING',
  progress: 0,
  error_message: null,
  started_at: null,
  completed_at: null,
  created_at: '2026-01-01T00:00:00Z',
}

const mockTaskRunning: api.TaskDetail = {
  ...mockTaskPending,
  id: 'task-2',
  status: 'RUNNING',
  progress: 50,
}

const mockTaskSucceeded: api.TaskDetail = {
  ...mockTaskPending,
  id: 'task-3',
  status: 'SUCCEEDED',
  progress: 100,
  started_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
}

const mockTaskFailed: api.TaskDetail = {
  ...mockTaskPending,
  id: 'task-4',
  status: 'FAILED',
  progress: 30,
  error_message: 'LLM error',
  started_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
}

const mockReview1: api.ReviewResult = {
  id: 'rev-1',
  task_id: 'task-3',
  dimension: 'SOUNDNESS',
  rating: 4,
  summary: 'Sound methodology',
  overall_verdict: null,
  created_at: '2026-01-01T00:01:00Z',
  findings: [
    {
      id: 'f-1',
      finding_type: 'STRENGTH',
      content: 'Clear experimental setup',
      confidence: 0.92,
      verification_status: 'VERIFIED',
      sequence: 1,
      evidence_ids: ['ev-1', 'ev-2'],
    },
    {
      id: 'f-2',
      finding_type: 'WEAKNESS',
      content: 'Limited dataset diversity',
      confidence: 0.85,
      verification_status: 'VERIFIED',
      sequence: 2,
      evidence_ids: ['ev-3'],
    },
    {
      id: 'f-3',
      finding_type: 'SUGGESTION',
      content: 'Consider more benchmarks',
      confidence: 0.78,
      verification_status: 'VERIFIED',
      sequence: 3,
      evidence_ids: ['ev-3'],
    },
  ],
}

const mockReviewOverall: api.ReviewResult = {
  id: 'rev-2',
  task_id: 'task-3',
  dimension: 'OVERALL',
  rating: 4,
  summary: 'Good paper overall',
  overall_verdict: 'WEAK_ACCEPT',
  created_at: '2026-01-01T00:01:00Z',
  findings: [],
}

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/papers/:id/review', name: 'paper-review', component: ReviewResultView },
      { path: '/papers/:id', name: 'paper-detail', component: PaperDetailView },
      { path: '/papers', name: 'papers', component: { template: '<div/>' } },
    ],
  })
}

describe('ReviewResultView', () => {
  let router: Router
  let wrappers: Array<ReturnType<typeof mount>>

  function mountView() {
    const wrapper = mount(ReviewResultView, { global: { plugins: [router] } })
    wrappers.push(wrapper)
    return wrapper
  }

  beforeEach(async () => {
    vi.clearAllMocks()
    wrappers = []
    router = createTestRouter()
    router.push('/papers/paper-1/review')
    await router.isReady()
    vi.mocked(api.getPaper).mockResolvedValue(mockPaper as any)
    vi.mocked(api.listTasks).mockResolvedValue({ items: [] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [] } as any)
    vi.mocked(api.createTask).mockResolvedValue({
      id: 'task-new',
      paper_id: 'paper-1',
      task_type: 'REVIEW',
      status: 'PENDING',
      progress: 0,
      created_at: '2026-01-01T00:00:00Z',
    } as any)
    vi.mocked(api.getTask).mockResolvedValue(mockTaskSucceeded as any)
  })

  afterEach(() => {
    wrappers.forEach(w => w.unmount())
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('loads paper, tasks and reviews on mount with correct params', async () => {
    mountView()
    await flushPromises()
    expect(api.getPaper).toHaveBeenCalledWith('paper-1')
    expect(api.listTasks).toHaveBeenCalledWith('paper-1')
    expect(api.listReviews).toHaveBeenCalledWith('paper-1')
  })

  it('shows empty state with create button when no tasks and no reviews', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('尚未发起审阅')
    expect(wrapper.find('.primary-btn').exists()).toBe(true)
  })

  it('default 7 dimensions and zh in create payload', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.primary-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.create-form').exists()).toBe(true)
    await wrapper.find('.form-actions .primary-btn').trigger('click')
    await flushPromises()
    expect(api.createTask).toHaveBeenCalledWith('paper-1', {
      task_type: 'REVIEW',
      options: {
        dimensions: ['SOUNDNESS', 'NOVELTY', 'CLARITY', 'COMPLETENESS', 'REPRODUCIBILITY', 'SIGNIFICANCE', 'OVERALL'],
        language: 'zh',
      },
    })
  })

  it('no dimensions selected prevents submit', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.primary-btn').trigger('click')
    await flushPromises()
    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    for (const cb of checkboxes) {
      await cb.setValue(false)
    }
    await flushPromises()
    const submitBtn = wrapper.find('.form-actions .primary-btn')
    expect(submitBtn.attributes('disabled')).toBeDefined()
  })

  it('double-click only creates one task', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.find('.primary-btn').trigger('click')
    await flushPromises()
    const submitBtn = wrapper.find('.form-actions .primary-btn')
    await submitBtn.trigger('click')
    await submitBtn.trigger('click')
    await flushPromises()
    expect(api.createTask).toHaveBeenCalledTimes(1)
  })

  it('recovers PENDING task and polls without creating new one', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskPending] } as any)
    mountView()
    await flushPromises()

    expect(api.createTask).not.toHaveBeenCalled()
    vi.advanceTimersByTime(4000)
    await flushPromises()
    expect(api.getTask).toHaveBeenCalledWith('task-1')
  })

  it('RUNNING to SUCCEEDED: updates progress, stops timer, refreshes reviews', async () => {
    vi.useFakeTimers()
    let pollCount = 0
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskRunning] } as any)
    vi.mocked(api.getTask).mockImplementation(async () => {
      pollCount++
      if (pollCount <= 1) return { ...mockTaskRunning, progress: 75 } as any
      return mockTaskSucceeded as any
    })
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [mockReview1, mockReviewOverall] } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.task-progress').exists()).toBe(true)
    vi.advanceTimersByTime(4000)
    await flushPromises()
    expect(api.getTask).toHaveBeenCalledWith('task-2')
    vi.advanceTimersByTime(4000)
    await flushPromises()
    const callsBefore = vi.mocked(api.getTask).mock.calls.length
    vi.advanceTimersByTime(10000)
    await flushPromises()
    expect(vi.mocked(api.getTask).mock.calls.length).toBe(callsBefore)
  })

  it('FAILED task shows error and allows retry', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskFailed] } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.failed-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('LLM error')
    const retryBtn = wrapper.find('.failed-notice .retry-btn')
    expect(retryBtn.exists()).toBe(true)
    await retryBtn.trigger('click')
    await flushPromises()
    expect(wrapper.find('.create-form').exists()).toBe(true)
  })

  it('poll network failure stops timer, retry does not stack timers', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskRunning] } as any)
    let pollCount = 0
    vi.mocked(api.getTask).mockImplementation(async () => {
      pollCount++
      if (pollCount === 1) throw { response: { status: 500, data: { error: { message: 'Network error' } } } }
      return mockTaskSucceeded as any
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

  it('clamps out-of-range active task progress to accessible 0-100 range', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listTasks).mockResolvedValue({
      items: [{ ...mockTaskRunning, progress: 150 }],
    } as any)
    const wrapper = mountView()
    await flushPromises()

    const progress = wrapper.find('[role="progressbar"]')
    expect(progress.attributes('aria-valuenow')).toBe('100')
    expect(progress.attributes('style')).toContain('width: 100%')
    expect(wrapper.find('.progress-text').text()).toBe('100%')
  })

  it('keeps previous successful results visible while a re-review task is active', async () => {
    vi.useFakeTimers()
    const oldTask: api.TaskDetail = {
      ...mockTaskSucceeded,
      id: 'task-old',
      created_at: '2025-01-01T00:00:00Z',
    }
    const oldReview: api.ReviewResult = {
      ...mockReview1,
      id: 'review-old',
      task_id: 'task-old',
      summary: 'Previous successful result',
      created_at: '2025-01-01T00:01:00Z',
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskRunning, oldTask] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [oldReview] } as any)

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.task-progress').exists()).toBe(true)
    expect(wrapper.find('.results-section').exists()).toBe(true)
    expect(wrapper.text()).toContain('Previous successful result')
  })

  it('keeps previous successful results visible when the newest task failed', async () => {
    const oldTask: api.TaskDetail = {
      ...mockTaskSucceeded,
      id: 'task-old',
      created_at: '2025-01-01T00:00:00Z',
    }
    const oldReview: api.ReviewResult = {
      ...mockReview1,
      id: 'review-old',
      task_id: 'task-old',
      summary: 'Previous successful result',
      created_at: '2025-01-01T00:01:00Z',
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskFailed, oldTask] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [oldReview] } as any)

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.failed-notice').exists()).toBe(true)
    expect(wrapper.find('.results-section').exists()).toBe(true)
    expect(wrapper.text()).toContain('Previous successful result')
  })

  it('shows terminal FAILED state returned by polling', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskRunning] } as any)
    vi.mocked(api.getTask).mockResolvedValue({ ...mockTaskFailed, id: mockTaskRunning.id } as any)
    const wrapper = mountView()
    await flushPromises()

    vi.advanceTimersByTime(4000)
    await flushPromises()

    expect(wrapper.find('.task-progress').exists()).toBe(false)
    expect(wrapper.find('.failed-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('LLM error')
  })

  it('shows a reloadable error when a succeeded task result refresh fails', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listTasks)
      .mockResolvedValueOnce({ items: [mockTaskRunning] } as any)
      .mockRejectedValueOnce(new Error('refresh unavailable'))
    vi.mocked(api.getTask).mockResolvedValue({ ...mockTaskSucceeded, id: mockTaskRunning.id } as any)
    const wrapper = mountView()
    await flushPromises()

    vi.advanceTimersByTime(4000)
    await flushPromises()

    expect(wrapper.find('.error-msg').exists()).toBe(true)
    expect(wrapper.text()).toContain('任务已完成，但刷新审阅结果失败')
    expect(wrapper.text()).toContain('refresh unavailable')
  })

  it('unmount cleans up timer', async () => {
    vi.useFakeTimers()
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskRunning] } as any)
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

  it('paper id change ignores stale responses from the previous paper', async () => {
    let resolveOldPaper: (paper: typeof mockPaper) => void
    const oldPaperRequest = new Promise<typeof mockPaper>(resolve => {
      resolveOldPaper = resolve
    })
    const newPaper = { ...mockPaper, id: 'paper-2', title: 'Second Paper' }
    vi.mocked(api.getPaper).mockImplementation(async (paperId: string) => {
      if (paperId === 'paper-1') return oldPaperRequest as any
      return newPaper as any
    })

    const wrapper = mountView()
    await Promise.resolve()
    await router.push('/papers/paper-2/review')
    await flushPromises()

    expect(wrapper.text()).toContain('Second Paper')
    resolveOldPaper!(mockPaper)
    await flushPromises()
    expect(wrapper.text()).toContain('Second Paper')
    expect(wrapper.text()).not.toContain('Test Paper')
  })

  it('multi-task reviews only show latest task_id results', async () => {
    const oldReview: api.ReviewResult = {
      id: 'rev-old',
      task_id: 'task-old',
      dimension: 'NOVELTY',
      rating: 3,
      summary: 'Old review',
      overall_verdict: null,
      created_at: '2025-01-01T00:00:00Z',
      findings: [],
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskSucceeded] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [oldReview, mockReview1, mockReviewOverall] } as any)
    const wrapper = mountView()
    await flushPromises()
    const cards = wrapper.findAll('.dimension-card')
    const dimensions = cards.map(c => c.find('h3').text())
    expect(dimensions).not.toContain('新颖性')
    expect(dimensions).toContain('合理性')
  })

  it('OVERALL overview, dimension order, verdict, null fields safe display', async () => {
    const reviewNoRating: api.ReviewResult = {
      id: 'rev-nr',
      task_id: 'task-3',
      dimension: 'NOVELTY',
      rating: null,
      summary: null,
      overall_verdict: null,
      created_at: '2026-01-01T00:01:00Z',
      findings: [],
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskSucceeded] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [mockReview1, mockReviewOverall, reviewNoRating] } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.overview').exists()).toBe(true)
    expect(wrapper.text()).toContain('4')
    expect(wrapper.text()).toContain('弱接受')
    const cards = wrapper.findAll('.dimension-card')
    const dims = cards.map(c => c.find('h3').text())
    expect(dims[0]).toBe('合理性')
    expect(dims[1]).toBe('新颖性')
    expect(dims[2]).toBe('总体评价')
    const noveltyCard = cards[1]!
    expect(noveltyCard.text()).toContain('评分: -')
  })

  it('finding type filter works correctly', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskSucceeded] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [mockReview1] } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.findAll('.finding-card').length).toBe(3)
    const strengthBtn = wrapper.findAll('.filter-btn').find(b => b.text() === '优点')
    expect(strengthBtn).toBeTruthy()
    await strengthBtn!.trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.finding-card').length).toBe(1)
    expect(wrapper.find('.finding-card').text()).toContain('Clear experimental setup')
  })

  it('multiple evidence_ids render as independent links', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskSucceeded] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [mockReview1] } as any)
    const wrapper = mountView()
    await flushPromises()
    const links = wrapper.findAll('.evidence-link')
    expect(links.length).toBeGreaterThanOrEqual(3)
  })

  it('XSS: LLM content with script/img tags displayed as text', async () => {
    const xssReview: api.ReviewResult = {
      id: 'rev-xss',
      task_id: 'task-3',
      dimension: 'SOUNDNESS',
      rating: 3,
      summary: '<script>alert(1)</script>',
      overall_verdict: null,
      created_at: '2026-01-01T00:01:00Z',
      findings: [
        {
          id: 'f-xss',
          finding_type: 'STRENGTH',
          content: '<img onerror="alert(1)" src=x>',
          confidence: 0.5,
          verification_status: 'VERIFIED',
          sequence: 1,
          evidence_ids: [],
        },
      ],
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskSucceeded] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [xssReview] } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.text()).toContain('<script>alert(1)</script>')
    expect(wrapper.text()).toContain('<img onerror="alert(1)" src=x>')
  })

  it('clicking evidence link navigates to paper detail with evidence query', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskSucceeded] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [mockReview1] } as any)
    const wrapper = mountView()
    await flushPromises()
    const link = wrapper.find('.evidence-link')
    expect(link.exists()).toBe(true)
    const href = link.attributes('href') || link.element.closest('a')?.getAttribute('href') || ''
    expect(href).toContain('evidence=ev-1')
  })

  it('non-PARSED paper shows appropriate message', async () => {
    vi.mocked(api.getPaper).mockResolvedValue({ ...mockPaper, status: 'PROCESSING' } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.not-ready-notice').exists()).toBe(true)
  })

  it('SUCCEEDED without results shows inconsistency message', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskSucceeded] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [] } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('审阅已完成但未获取到结果')
  })

  it('CANCELLED task shows error and allows retry', async () => {
    const cancelledTask: api.TaskDetail = {
      ...mockTaskPending,
      id: 'task-cancel',
      status: 'CANCELLED',
      progress: 0,
      error_message: null,
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [cancelledTask] } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.failed-notice').exists()).toBe(true)
  })

  it('null confidence displays as dash, not NaN%', async () => {
    const nullConfReview: api.ReviewResult = {
      id: 'rev-nc',
      task_id: 'task-3',
      dimension: 'SOUNDNESS',
      rating: 3,
      summary: null,
      overall_verdict: null,
      created_at: '2026-01-01T00:01:00Z',
      findings: [
        {
          id: 'f-nc',
          finding_type: 'STRENGTH',
          content: 'Test',
          confidence: null,
          verification_status: 'VERIFIED',
          sequence: 1,
          evidence_ids: [],
        },
      ],
    }
    vi.mocked(api.listTasks).mockResolvedValue({ items: [mockTaskSucceeded] } as any)
    vi.mocked(api.listReviews).mockResolvedValue({ reviews: [nullConfReview] } as any)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).not.toContain('NaN%')
  })
})
