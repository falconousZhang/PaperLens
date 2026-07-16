import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import PaperReadingView from '../views/PaperReadingView.vue'
import * as api from '../api'

vi.mock('../api', () => ({
  getPaper: vi.fn(),
  listSections: vi.fn(),
  listEvidences: vi.fn(),
  getPage: vi.fn(),
  createLearningExplanation: vi.fn(),
  getLearningExplanation: vi.fn(),
  listLearningExplanations: vi.fn(),
  createQAConversation: vi.fn(),
  listQAConversations: vi.fn(),
  getQAConversation: vi.fn(),
  createQATurn: vi.fn(),
  getQATurn: vi.fn(),
  patchReadingProgress: vi.fn(),
  createHighlight: vi.fn(),
  listHighlights: vi.fn(),
  deleteHighlight: vi.fn(),
  createBookmark: vi.fn(),
  listBookmarks: vi.fn(),
  deleteBookmark: vi.fn(),
  createNote: vi.fn(),
  listNotes: vi.fn(),
  patchNote: vi.fn(),
  deleteNote: vi.fn(),
  createKnowledgeCard: vi.fn(),
  listKnowledgeCards: vi.fn(),
  patchKnowledgeCard: vi.fn(),
  deleteKnowledgeCard: vi.fn(),
}))

const paper = {
  id: 'paper-1',
  title: 'Learning Paper',
  filename: 'paper.pdf',
  file_size: 100,
  page_count: 2,
  status: 'PARSED',
  error_message: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const section = {
  id: 'section-1',
  section_type: 'INTRODUCTION',
  title: 'Introduction',
  level: 1,
  sequence: 1,
  start_page: 1,
  end_page: 1,
  text_content: 'Section learning text',
}

const evidence = {
  id: 'evidence-1',
  quoted_text: 'Citation evidence',
  page_number: 1,
  bbox_x0: null,
  bbox_y0: null,
  bbox_x1: null,
  bbox_y1: null,
  char_start: 7,
  char_end: 24,
  evidence_type: 'TEXT',
  section_id: 'section-1',
  chunk_id: null,
}

const page = {
  id: 'page-1',
  page_number: 1,
  text_content: 'Before Citation evidence After',
  normalized_text_content: 'Before Citation evidence After',
  width: null,
  height: null,
}

const succeeded = {
  id: 'explanation-1',
  paper_id: 'paper-1',
  mode: 'SUMMARY' as const,
  scope_type: 'SECTION' as const,
  output_language: 'zh' as const,
  section_id: 'section-1',
  page_number: null,
  evidence_id: null,
  status: 'SUCCEEDED' as const,
  duplicate: false,
  answer: '<script>plain text only</script>',
  key_points: ['Grounded point'],
  terms: [{ term: 'Term', explanation: 'Plain explanation' }],
  error_message: null,
  citations: [{
    evidence_id: 'evidence-1',
    sequence: 1,
    page_number: 1,
    evidence_type: 'TEXT',
    quoted_text: 'Citation evidence',
    char_start: 7,
    char_end: 24,
  }],
  created_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
}

const pending = {
  ...succeeded,
  status: 'PENDING' as const,
  answer: null,
  key_points: null,
  terms: null,
  citations: null,
  completed_at: null,
}

const failed = {
  ...pending,
  status: 'FAILED' as const,
  error_message: '学习解释生成失败，请稍后重试',
  completed_at: '2026-01-01T00:01:00Z',
}

const qaConversation = {
  id: 'conversation-1',
  paper_id: 'paper-1',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  turn_count: 1,
  last_question_preview: 'What accuracy is reported?',
  last_status: 'SUCCEEDED' as const,
}

const qaSucceeded = {
  id: 'qa-turn-1',
  conversation_id: 'conversation-1',
  sequence: 1,
  question: 'What accuracy is reported?',
  output_language: 'en' as const,
  status: 'SUCCEEDED' as const,
  duplicate: false,
  answer: '<script>95% as plain text</script>',
  grounded: true,
  error_message: null,
  citations: [{
    evidence_id: 'evidence-1',
    sequence: 1,
    page_number: 1,
    evidence_type: 'TEXT',
    quoted_text: 'Citation evidence',
    char_start: 7,
    char_end: 24,
  }],
  created_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
}

const qaPending = {
  ...qaSucceeded,
  status: 'PENDING' as const,
  answer: null,
  grounded: null,
  citations: null,
  completed_at: null,
}

const qaFailed = {
  ...qaPending,
  status: 'FAILED' as const,
  error_message: '论文问答生成失败，请稍后重试',
  completed_at: '2026-01-01T00:01:00Z',
}

const qaConversationDetail = {
  id: 'conversation-1',
  paper_id: 'paper-1',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:01:00Z',
  turns: [qaSucceeded],
  total: 1,
  page: 1,
  page_size: 20,
}

function testRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/papers/:id/read', name: 'paper-read', component: PaperReadingView },
      { path: '/papers/:id', name: 'paper-detail', component: { template: '<div />' } },
    ],
  })
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(innerResolve => { resolve = innerResolve })
  return { promise, resolve }
}

describe('PaperReadingView', () => {
  let router: ReturnType<typeof testRouter>
  const wrappers: Array<ReturnType<typeof mount>> = []

  async function mountView() {
    const wrapper = mount(PaperReadingView, { global: { plugins: [router] } })
    wrappers.push(wrapper)
    await flushPromises()
    return wrapper
  }

  async function openQA(wrapper: Awaited<ReturnType<typeof mountView>>) {
    await wrapper.findAll('.panel-tabs button')[1]!.trigger('click')
    await flushPromises()
  }

  beforeEach(async () => {
    vi.clearAllMocks()
    router = testRouter()
    await router.push('/papers/paper-1/read')
    await router.isReady()
    vi.mocked(api.getPaper).mockResolvedValue(paper as any)
    vi.mocked(api.listSections).mockResolvedValue([section] as any)
    vi.mocked(api.listEvidences).mockResolvedValue([evidence] as any)
    vi.mocked(api.getPage).mockResolvedValue(page as any)
    vi.mocked(api.createLearningExplanation).mockResolvedValue(succeeded as any)
    vi.mocked(api.getLearningExplanation).mockResolvedValue(succeeded as any)
    vi.mocked(api.listLearningExplanations).mockResolvedValue({
      items: [], total: 0, page: 1, page_size: 20,
    })
    vi.mocked(api.patchReadingProgress).mockResolvedValue({
      paper_id: paper.id, reading_status: 'READING', last_page: 1, furthest_page: 1,
      progress_percent: 50, last_read_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
    })
    vi.mocked(api.listHighlights).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    vi.mocked(api.listBookmarks).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    vi.mocked(api.listNotes).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    vi.mocked(api.listKnowledgeCards).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    vi.mocked(api.listQAConversations).mockResolvedValue({
      items: [qaConversation], total: 1, page: 1, page_size: 20,
    } as any)
    vi.mocked(api.createQAConversation).mockResolvedValue({
      ...qaConversationDetail, turns: null, total: 0,
    } as any)
    vi.mocked(api.getQAConversation).mockResolvedValue(qaConversationDetail as any)
    vi.mocked(api.createQATurn).mockResolvedValue(qaPending as any)
    vi.mocked(api.getQATurn).mockResolvedValue(qaSucceeded as any)
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => '11111111-1111-4111-8111-111111111111') })
    vi.stubGlobal('scrollTo', vi.fn())
    Element.prototype.scrollIntoView = vi.fn()
  })

  afterEach(() => {
    wrappers.splice(0).forEach(wrapper => wrapper.unmount())
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('loads the protected three-column reading workspace without fetching a page initially', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('.sidebar').exists()).toBe(true)
    expect(wrapper.find('.content-panel').text()).toContain('Section learning text')
    expect(wrapper.find('.learning-panel').exists()).toBe(true)
    expect(api.getPage).not.toHaveBeenCalled()
    expect(api.listLearningExplanations).toHaveBeenCalledWith('paper-1', 1, 20)
  })

  it('submits only identifiers and renders model output as text', async () => {
    const wrapper = await mountView()
    await wrapper.find('.submit-btn').trigger('click')
    await flushPromises()
    expect(api.createLearningExplanation).toHaveBeenCalledWith('paper-1', {
      mode: 'SUMMARY',
      scope_type: 'SECTION',
      output_language: 'zh',
      section_id: 'section-1',
    })
    const serialized = JSON.stringify(vi.mocked(api.createLearningExplanation).mock.calls[0]?.[1])
    expect(serialized).not.toContain('Section learning text')
    expect(wrapper.find('.answer-text').text()).toBe('<script>plain text only</script>')
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('.term-card').text()).toContain('Plain explanation')
  })

  it('polls every three seconds until a terminal result', async () => {
    vi.useFakeTimers()
    vi.mocked(api.createLearningExplanation).mockResolvedValue(pending as any)
    vi.mocked(api.getLearningExplanation).mockResolvedValue(succeeded as any)
    const wrapper = await mountView()
    await wrapper.find('.submit-btn').trigger('click')
    await flushPromises()
    expect(api.getLearningExplanation).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(3000)
    await flushPromises()
    expect(api.getLearningExplanation).toHaveBeenCalledWith('explanation-1')
    expect(wrapper.find('.answer-text').exists()).toBe(true)
  })

  it('offers a retry after a fixed failure', async () => {
    vi.mocked(api.createLearningExplanation)
      .mockResolvedValueOnce(failed as any)
      .mockResolvedValueOnce(succeeded as any)
    const wrapper = await mountView()
    await wrapper.find('.submit-btn').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('学习解释生成失败，请稍后重试')
    await wrapper.find('.result-area .retry-btn').trigger('click')
    await flushPromises()
    expect(api.createLearningExplanation).toHaveBeenCalledTimes(2)
  })

  it('uses real previous and next history pagination parameters', async () => {
    vi.mocked(api.listLearningExplanations)
      .mockResolvedValueOnce({ items: [succeeded as any], total: 25, page: 1, page_size: 20 })
      .mockResolvedValueOnce({ items: [], total: 25, page: 2, page_size: 20 })
    const wrapper = await mountView()
    const buttons = wrapper.findAll('.history-pagination button')
    await buttons[1]!.trigger('click')
    await flushPromises()
    expect(api.listLearningExplanations).toHaveBeenLastCalledWith('paper-1', 2, 20)
    expect(wrapper.find('.history-pagination').text()).toContain('2 / 2')
  })

  it('switches to a citation page, highlights exact text, and keeps the explanation visible', async () => {
    const wrapper = await mountView()
    await wrapper.find('.submit-btn').trigger('click')
    await flushPromises()
    await wrapper.find('.citation-link').trigger('click')
    await flushPromises()
    expect(api.getPage).toHaveBeenCalledWith('paper-1', 1)
    expect(wrapper.find('mark').text()).toBe('Citation evidence')
    expect(wrapper.find('.answer-text').exists()).toBe(true)
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled()
  })

  it('shows a deterministic fallback when citation offsets no longer match', async () => {
    vi.mocked(api.createLearningExplanation).mockResolvedValue({
      ...succeeded,
      citations: [{ ...succeeded.citations[0], char_start: 0, char_end: 4 }],
    } as any)
    const wrapper = await mountView()
    await wrapper.find('.submit-btn').trigger('click')
    await flushPromises()
    await wrapper.find('.citation-link').trigger('click')
    await flushPromises()
    expect(wrapper.find('mark').exists()).toBe(false)
    expect(wrapper.find('.highlight-notice').text()).toContain('无法可靠高亮')
  })

  it('does not let an old paper request overwrite a new route', async () => {
    const oldSections = deferred<any[]>()
    vi.mocked(api.getPaper).mockImplementation(async id => ({ ...paper, id, title: id } as any))
    vi.mocked(api.listSections).mockImplementation(async id => {
      if (id === 'paper-1') return oldSections.promise
      return [{ ...section, id: 'section-2', text_content: 'New paper text' }] as any
    })
    const wrapper = mount(PaperReadingView, { global: { plugins: [router] } })
    wrappers.push(wrapper)
    await flushPromises()
    await router.push('/papers/paper-2/read')
    await flushPromises()
    oldSections.resolve([{ ...section, text_content: 'Old paper text' }])
    await flushPromises()
    expect(wrapper.text()).toContain('New paper text')
    expect(wrapper.text()).not.toContain('Old paper text')
  })

  it('clears polling timers on unmount', async () => {
    vi.useFakeTimers()
    vi.mocked(api.createLearningExplanation).mockResolvedValue(pending as any)
    const wrapper = await mountView()
    await wrapper.find('.submit-btn').trigger('click')
    await flushPromises()
    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(3000)
    expect(api.getLearningExplanation).not.toHaveBeenCalled()
  })

  it('maps server errors to safe user-facing text', async () => {
    vi.mocked(api.createLearningExplanation).mockRejectedValue({
      response: { status: 500, data: { error: { message: 'secret raw exception' } } },
    })
    const wrapper = await mountView()
    await wrapper.find('.submit-btn').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('创建学习解释失败，请稍后重试。')
    expect(wrapper.text()).not.toContain('secret raw exception')
  })

  it('loads QA only after the tab is opened and never creates a session automatically', async () => {
    const wrapper = await mountView()
    expect(api.listQAConversations).not.toHaveBeenCalled()
    expect(api.createQAConversation).not.toHaveBeenCalled()
    await openQA(wrapper)
    expect(api.listQAConversations).toHaveBeenCalledWith('paper-1', 1, 20)
    expect(wrapper.find('.conv-list').text()).toContain('What accuracy is reported?')
    expect(api.createQAConversation).not.toHaveBeenCalled()
    expect(api.createQATurn).not.toHaveBeenCalled()
  })

  it('creates an empty conversation and submits only the question contract', async () => {
    const wrapper = await mountView()
    await openQA(wrapper)
    await wrapper.find('.qa-conversations > .submit-btn').trigger('click')
    await flushPromises()
    expect(api.createQAConversation).toHaveBeenCalledWith('paper-1', {})

    await wrapper.find('.qa-input-area textarea').setValue('What accuracy is reported?')
    await wrapper.find('.qa-input-actions .submit-btn').trigger('click')
    await flushPromises()
    expect(api.createQATurn).toHaveBeenCalledWith('conversation-1', {
      question: 'What accuracy is reported?',
      output_language: 'zh',
      client_request_id: '11111111-1111-4111-8111-111111111111',
    })
    const serialized = JSON.stringify(vi.mocked(api.createQATurn).mock.calls[0]?.[1])
    expect(serialized).not.toContain('Citation evidence')
    expect(serialized).not.toContain('Section learning text')
  })

  it('uses real conversation and turn pagination parameters', async () => {
    vi.mocked(api.listQAConversations)
      .mockResolvedValueOnce({ items: [qaConversation], total: 25, page: 1, page_size: 20 } as any)
      .mockResolvedValueOnce({ items: [], total: 25, page: 2, page_size: 20 } as any)
    vi.mocked(api.getQAConversation)
      .mockResolvedValueOnce({ ...qaConversationDetail, total: 21 } as any)
      .mockResolvedValueOnce({ ...qaConversationDetail, turns: [], total: 21, page: 2 } as any)
    const wrapper = await mountView()
    await openQA(wrapper)
    await wrapper.findAll('.qa-conversations .history-pagination button')[1]!.trigger('click')
    await flushPromises()
    expect(api.listQAConversations).toHaveBeenLastCalledWith('paper-1', 2, 20)

    vi.mocked(api.listQAConversations).mockResolvedValue({
      items: [qaConversation], total: 1, page: 1, page_size: 20,
    } as any)
    await wrapper.findAll('.panel-tabs button')[0]!.trigger('click')
    await openQA(wrapper)
    await wrapper.find('.conv-list li').trigger('click')
    await flushPromises()
    await wrapper.findAll('.qa-turn-pagination button')[1]!.trigger('click')
    await flushPromises()
    expect(api.getQAConversation).toHaveBeenLastCalledWith('conversation-1', 2, 20)
  })

  it('polls QA serially and renders an evidence-insufficient result as plain text', async () => {
    vi.useFakeTimers()
    vi.mocked(api.getQAConversation).mockResolvedValue({
      ...qaConversationDetail,
      turns: [qaPending],
    } as any)
    vi.mocked(api.getQATurn).mockResolvedValue({
      ...qaSucceeded,
      answer: '<script>仅根据当前论文无法确认，论文证据不足。</script>',
      grounded: false,
      citations: [],
    } as any)
    const wrapper = await mountView()
    await openQA(wrapper)
    await wrapper.find('.conv-list li').trigger('click')
    await flushPromises()
    expect(api.getQATurn).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(3000)
    await flushPromises()
    expect(api.getQATurn).toHaveBeenCalledWith('qa-turn-1')
    expect(wrapper.text()).toContain('当前论文证据不足')
    expect(wrapper.text()).toContain('<script>仅根据当前论文无法确认')
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('.qa-answer .citation-link').exists()).toBe(false)
  })

  it('retries a failed question with a newly generated request id', async () => {
    const randomUUID = vi.fn()
      .mockReturnValueOnce('11111111-1111-4111-8111-111111111111')
      .mockReturnValueOnce('22222222-2222-4222-8222-222222222222')
    vi.stubGlobal('crypto', { randomUUID })
    vi.mocked(api.getQAConversation).mockResolvedValue({
      ...qaConversationDetail,
      turns: [qaFailed],
    } as any)
    const wrapper = await mountView()
    await openQA(wrapper)
    await wrapper.find('.conv-list li').trigger('click')
    await flushPromises()
    await wrapper.find('.qa-message .retry-btn').trigger('click')
    await flushPromises()
    expect(api.createQATurn).toHaveBeenCalledWith('conversation-1', {
      question: qaFailed.question,
      output_language: qaFailed.output_language,
      client_request_id: '11111111-1111-4111-8111-111111111111',
    })
  })

  it('ignores a stale conversation response after switching sessions', async () => {
    const oldConversation = deferred<any>()
    const secondConversation = { ...qaConversation, id: 'conversation-2', last_question_preview: 'Second question' }
    vi.mocked(api.listQAConversations).mockResolvedValue({
      items: [qaConversation, secondConversation], total: 2, page: 1, page_size: 20,
    } as any)
    vi.mocked(api.getQAConversation).mockImplementation(async id => {
      if (id === 'conversation-1') return oldConversation.promise
      return {
        ...qaConversationDetail,
        id: 'conversation-2',
        turns: [{ ...qaSucceeded, id: 'turn-2', conversation_id: 'conversation-2', question: 'Second question' }],
      } as any
    })
    const wrapper = await mountView()
    await openQA(wrapper)
    const conversations = wrapper.findAll('.conv-list li')
    await conversations[0]!.trigger('click')
    await conversations[1]!.trigger('click')
    await flushPromises()
    oldConversation.resolve(qaConversationDetail)
    await flushPromises()
    expect(wrapper.find('.qa-messages').text()).toContain('Second question')
    expect(wrapper.find('.qa-messages').text()).not.toContain('What accuracy is reported?')
  })

  it('loads only the active learning-record list lazily and paginates it', async () => {
    vi.mocked(api.listHighlights)
      .mockResolvedValueOnce({ items: [], total: 21, page: 1, page_size: 20 })
      .mockResolvedValueOnce({ items: [], total: 21, page: 2, page_size: 20 })
    const wrapper = await mountView()
    expect(api.listHighlights).not.toHaveBeenCalled()
    await wrapper.findAll('.panel-tabs button')[2]!.trigger('click')
    await flushPromises()
    expect(api.listHighlights).toHaveBeenCalledWith('paper-1', { page: 1, page_size: 20 })
    expect(api.listBookmarks).not.toHaveBeenCalled()
    await wrapper.findAll('.record-pagination button')[1]!.trigger('click')
    await flushPromises()
    expect(api.listHighlights).toHaveBeenLastCalledWith('paper-1', { page: 2, page_size: 20 })
  })

  it('records progress only after a real page load and exposes only server-supported enums', async () => {
    const wrapper = await mountView()
    expect(api.patchReadingProgress).not.toHaveBeenCalled()
    await wrapper.findAll('.scope-selector button')[1]!.trigger('click')
    await flushPromises()
    expect(api.getPage).toHaveBeenCalledWith('paper-1', 1)
    expect(api.patchReadingProgress).toHaveBeenCalledWith('paper-1', 1)
    await wrapper.findAll('.panel-tabs button')[2]!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).not.toContain('紫色')
    await wrapper.findAll('.records-sub-tabs button')[3]!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).not.toContain('复习中')
  })

  it('uses the bookmark duplicate contract without optimistic state changes', async () => {
    vi.mocked(api.createBookmark).mockResolvedValue({
      id: '11111111-1111-4111-8111-111111111112',
      paper_id: 'paper-1', page_number: 1, label: null,
      created_at: '2026-01-01T00:00:00Z', duplicate: true,
    })
    const wrapper = await mountView()
    await wrapper.findAll('.scope-selector button')[1]!.trigger('click')
    await flushPromises()
    await wrapper.findAll('.panel-tabs button')[2]!.trigger('click')
    await wrapper.findAll('.records-sub-tabs button')[1]!.trigger('click')
    await flushPromises()
    await wrapper.find('.record-actions .submit-btn').trigger('click')
    await flushPromises()
    expect(api.createBookmark).toHaveBeenCalledWith('paper-1', { page_number: 1, label: null })
    expect(api.listBookmarks).toHaveBeenLastCalledWith('paper-1', { page: 1, page_size: 20 })
  })
})
