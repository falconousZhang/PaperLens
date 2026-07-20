import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import PaperReadingView from '../views/PaperReadingView.vue'
import * as api from '../api'

vi.mock('../api', () => ({
  createHighlight: vi.fn(),
  createLearningExplanation: vi.fn(),
  createNote: vi.fn(),
  createQAConversation: vi.fn(),
  createQATurn: vi.fn(),
  deleteHighlight: vi.fn(),
  deleteLearningExplanation: vi.fn(),
  deleteNote: vi.fn(),
  deleteQAConversation: vi.fn(),
  getLearningExplanation: vi.fn(),
  getPage: vi.fn(),
  getPaper: vi.fn(),
  getPaperOutline: vi.fn(),
  getPaperPageImage: vi.fn(),
  getPaperPageTextLayer: vi.fn(),
  getQAConversation: vi.fn(),
  getQATurn: vi.fn(),
  listHighlights: vi.fn(),
  listLearningExplanations: vi.fn(),
  listNotes: vi.fn(),
  listQAConversations: vi.fn(),
  patchNote: vi.fn(),
  patchReadingProgress: vi.fn(),
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

const page = {
  id: 'page-1',
  page_number: 1,
  text_content: 'Hello world',
  normalized_text_content: 'Hello world',
  width: 100,
  height: 140,
}

const explanation = {
  id: 'explanation-1',
  paper_id: 'paper-1',
  mode: 'SUMMARY' as const,
  scope_type: 'PAGE' as const,
  output_language: 'zh' as const,
  section_id: null,
  page_number: 1,
  evidence_id: null,
  selection_text: null,
  selection_start: null,
  selection_end: null,
  status: 'SUCCEEDED' as const,
  duplicate: false,
  answer: '本页讨论一个核心方法。',
  key_points: ['核心方法'],
  terms: [],
  error_message: null,
  citations: [],
  created_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
}

const conversation = {
  id: 'conversation-1',
  paper_id: 'paper-1',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  turn_count: 1,
  last_question_preview: '这个方法解决什么问题？',
  last_status: 'SUCCEEDED' as const,
}

const turn = {
  id: 'turn-1',
  conversation_id: 'conversation-1',
  sequence: 1,
  question: '这个方法解决什么问题？',
  output_language: 'zh' as const,
  status: 'SUCCEEDED' as const,
  duplicate: false,
  answer: '它解决了论文中描述的核心问题。',
  grounded: true,
  error_message: null,
  citations: [],
  created_at: '2026-01-01T00:00:00Z',
  completed_at: '2026-01-01T00:01:00Z',
}

async function mountView(): Promise<VueWrapper> {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/papers', name: 'papers', component: { template: '<div />' } },
      { path: '/papers/:id/read', component: PaperReadingView },
      { path: '/papers/:id/review', name: 'paper-review', component: { template: '<div />' } },
      { path: '/papers/:id/export', name: 'paper-export', component: { template: '<div />' } },
    ],
  })
  await router.push('/papers/paper-1/read')
  await router.isReady()
  const wrapper = mount(PaperReadingView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('PaperReadingView', () => {
  const wrappers: VueWrapper[] = []

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getPaper).mockResolvedValue(paper)
    vi.mocked(api.getPaperOutline).mockResolvedValue([{ title: 'Introduction', level: 1, page_number: 1 }])
    vi.mocked(api.getPage).mockResolvedValue(page)
    vi.mocked(api.getPaperPageImage).mockResolvedValue(new Blob(['png'], { type: 'image/png' }))
    vi.mocked(api.getPaperPageTextLayer).mockResolvedValue({
      page_number: 1,
      width: 100,
      height: 140,
      words: [
        { text: 'Hello', x0: 10, y0: 10, x1: 30, y1: 20, char_start: 0, char_end: 5 },
        { text: 'world', x0: 32, y0: 10, x1: 54, y1: 20, char_start: 6, char_end: 11 },
      ],
    })
    vi.mocked(api.listLearningExplanations).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    vi.mocked(api.createLearningExplanation).mockResolvedValue(explanation)
    vi.mocked(api.patchReadingProgress).mockResolvedValue({
      paper_id: 'paper-1', reading_status: 'READING', last_page: 1, furthest_page: 1,
      progress_percent: 50, last_read_at: null, updated_at: '2026-01-01T00:00:00Z',
    })
    vi.mocked(api.listHighlights).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 })
    vi.mocked(api.listNotes).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    vi.mocked(api.listQAConversations).mockResolvedValue({ items: [conversation], total: 1, page: 1, page_size: 20 })
    vi.mocked(api.createQAConversation).mockResolvedValue({ ...conversation, turns: null, total: 0, page: 1, page_size: 20 })
    vi.mocked(api.createQATurn).mockResolvedValue(turn)
    vi.mocked(api.getQAConversation).mockResolvedValue({ ...conversation, turns: [turn], total: 1, page: 1, page_size: 20 })
    vi.mocked(api.createHighlight).mockResolvedValue({
      id: 'highlight-1', paper_id: 'paper-1', page_number: 1, char_start: 0, char_end: 11,
      quoted_text: 'Hello world', color: 'YELLOW', created_at: '', updated_at: '', duplicate: false,
    })
    vi.mocked(api.createNote).mockResolvedValue({
      id: 'note-1', paper_id: 'paper-1', anchor_type: 'HIGHLIGHT', page_number: null,
      highlight_id: 'highlight-1', content: '我的理解', created_at: '', updated_at: '',
    })
    vi.stubGlobal('crypto', { randomUUID: vi.fn(() => '11111111-1111-4111-8111-111111111111') })
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:page')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
  })

  afterEach(() => {
    wrappers.splice(0).forEach(wrapper => wrapper.unmount())
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('removes evidence controls and generates learning content for the current page', async () => {
    const wrapper = await mountView()
    wrappers.push(wrapper)
    expect(wrapper.find('.workspace-actions').text()).not.toContain('证据')
    expect(wrapper.find('.scope-selector').exists()).toBe(false)
    expect(wrapper.find('.lang-selector').exists()).toBe(false)
    expect(wrapper.findAll('.mode-selector button')).toHaveLength(2)
    expect(wrapper.text()).toContain('当前处理第 1 页')
    expect(api.listLearningExplanations).toHaveBeenCalledWith('paper-1', 1, 100)
    expect(wrapper.find('.panel-exit').exists()).toBe(false)
    expect(wrapper.find('.learning-exit').exists()).toBe(false)

    await wrapper.find('.learning-panel .submit-btn').trigger('click')
    await flushPromises()
    expect(api.createLearningExplanation).toHaveBeenCalledWith('paper-1', {
      mode: 'SUMMARY', scope_type: 'PAGE', output_language: 'zh', page_number: 1,
    })
    expect(wrapper.text()).toContain('本页概括')
    expect(wrapper.text()).not.toContain('原文引用')
    expect(wrapper.find('.learning-exit').element.tagName).toBe('BUTTON')
    expect(wrapper.find('.learning-exit').text()).toBe('退出')

    await wrapper.find('.learning-exit').trigger('click')
    await flushPromises()
    expect(wrapper.find('.result-area').exists()).toBe(false)
    expect(wrapper.find('.history-section').exists()).toBe(true)
    expect(wrapper.find('.learning-exit').exists()).toBe(false)
    expect((wrapper.find('.page-input').element as HTMLInputElement).value).toBe('1')
    expect(wrapper.find('.reading-view').exists()).toBe(true)
  })

  it('explains selected PDF text and keeps translation as a page action', async () => {
    vi.mocked(api.listLearningExplanations).mockResolvedValue({
      items: [{
        id: 'selection-explanation', paper_id: 'paper-1', mode: 'EXPLAIN', scope_type: 'PAGE',
        output_language: 'zh', section_id: null, page_number: 1, evidence_id: null,
        selection_start: 0, selection_end: 11, status: 'SUCCEEDED', error_message: null,
        created_at: '2026-01-01T00:00:00Z', completed_at: '2026-01-01T00:01:00Z',
      }],
      total: 1, page: 1, page_size: 20,
    })
    vi.mocked(api.createLearningExplanation)
      .mockResolvedValueOnce({
        ...explanation,
        mode: 'EXPLAIN',
        selection_text: 'Hello world',
        selection_start: 0,
        selection_end: 11,
        answer: '原理说明，并给出生活中的例子。',
        terms: [{ term: '核心概念', explanation: '通俗定义' }],
      })
      .mockResolvedValueOnce({ ...explanation, mode: 'TRANSLATE', answer: '# 论文标题\n\n完整正文翻译。', key_points: [], terms: [] })
    const wrapper = await mountView()
    wrappers.push(wrapper)

    await wrapper.find('.history-list li').trigger('mouseenter')
    expect(wrapper.findAll('.pdf-highlight-blue')).toHaveLength(2)
    await wrapper.find('.history-list li').trigger('mouseleave')
    expect(wrapper.find('.pdf-highlight-blue').exists()).toBe(false)

    const words = wrapper.findAll('.pdf-text-word')
    const range = document.createRange()
    range.setStart(words[0]!.element.firstChild!, 0)
    range.setEnd(words[1]!.element.firstChild!, 5)
    Object.defineProperty(range, 'getBoundingClientRect', {
      value: () => ({ left: 10, top: 10, right: 60, bottom: 20, width: 50, height: 10 }),
    })
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)
    await wrapper.find('.pdf-text-layer').trigger('mouseup')
    await wrapper.findAll('.selection-toolbar button')[1]!.trigger('click')
    await flushPromises()
    expect(api.createLearningExplanation).toHaveBeenCalledWith('paper-1', {
      mode: 'EXPLAIN', scope_type: 'PAGE', output_language: 'zh', page_number: 1,
      selection_text: 'Hello world',
      selection_start: 0,
      selection_end: 11,
    })
    expect(wrapper.text()).toContain('选中文字解释')
    expect(wrapper.text()).toContain('原理讲解与示例')
    expect(wrapper.text()).toContain('概念拆解')
    expect(wrapper.findAll('.pdf-highlight-blue')).toHaveLength(2)

    await wrapper.findAll('.mode-selector button')[1]!.trigger('click')
    await wrapper.find('.learning-panel .submit-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.translation-content h2').text()).toBe('论文标题')
    expect(wrapper.find('.translation-content').text()).toContain('完整正文翻译。')
    expect(wrapper.find('.pdf-highlight-blue').exists()).toBe(false)
  })

  it('sorts all explanations by page and opens the selected record on its page', async () => {
    vi.mocked(api.listLearningExplanations).mockResolvedValue({
      items: [
        {
          id: 'page-2-explanation', paper_id: 'paper-1', mode: 'SUMMARY', scope_type: 'PAGE',
          output_language: 'zh', section_id: null, page_number: 2, evidence_id: null,
          selection_start: null, selection_end: null, status: 'SUCCEEDED', error_message: null,
          created_at: '2026-01-02T00:00:00Z', completed_at: '2026-01-02T00:01:00Z',
        },
        {
          id: 'page-1-explanation', paper_id: 'paper-1', mode: 'SUMMARY', scope_type: 'PAGE',
          output_language: 'zh', section_id: null, page_number: 1, evidence_id: null,
          selection_start: null, selection_end: null, status: 'SUCCEEDED', error_message: null,
          created_at: '2026-01-01T00:00:00Z', completed_at: '2026-01-01T00:01:00Z',
        },
      ],
      total: 2, page: 1, page_size: 100,
    })
    vi.mocked(api.getPage).mockImplementation(async (_paperId, pageNumber) => ({
      ...page,
      id: `page-${pageNumber}`,
      page_number: pageNumber,
    }))
    vi.mocked(api.getLearningExplanation).mockResolvedValue({
      ...explanation,
      id: 'page-2-explanation',
      page_number: 2,
    })
    const wrapper = await mountView()
    wrappers.push(wrapper)

    const items = wrapper.findAll('.history-list li')
    expect(items).toHaveLength(2)
    expect(items[0]!.text()).toContain('第 1 页')
    expect(items[1]!.text()).toContain('第 2 页')
    expect(wrapper.find('.history-pagination').exists()).toBe(false)

    await items[1]!.trigger('click')
    await flushPromises()
    expect(api.getPage).toHaveBeenCalledWith('paper-1', 2)
    expect((wrapper.find('.page-input').element as HTMLInputElement).value).toBe('2')
    expect(wrapper.find('.result-area').text()).toContain('本页概括')
  })

  it('uses message bubbles and submits the first turn without secure-context randomUUID', async () => {
    vi.stubGlobal('crypto', {
      getRandomValues: vi.fn((bytes: Uint8Array) => {
        bytes.set(Array.from({ length: 16 }, (_, index) => index))
        return bytes
      }),
    })
    const wrapper = await mountView()
    wrappers.push(wrapper)
    await wrapper.findAll('.panel-tabs button')[1]!.trigger('click')
    await flushPromises()
    expect(wrapper.find('.qa-chat-shell').exists()).toBe(true)
    expect(api.createQAConversation).not.toHaveBeenCalled()

    await wrapper.find('.qa-composer textarea').setValue('这个方法解决什么问题？')
    await wrapper.find('.qa-send-button').trigger('click')
    await flushPromises()
    expect(api.createQAConversation).toHaveBeenCalledWith('paper-1', {})
    expect(api.createQATurn).toHaveBeenCalledWith(
      'conversation-1',
      expect.objectContaining({
        current_page: 1,
        client_request_id: '00010203-0405-4607-8809-0a0b0c0d0e0f',
      }),
    )
    expect(wrapper.find('.user-bubble').text()).toContain('这个方法解决什么问题？')
    expect(wrapper.find('.assistant-bubble').text()).toContain('它解决了论文中描述的核心问题。')
  })

  it('loads every conversation page into one scrollable message history', async () => {
    const secondTurn = {
      ...turn,
      id: 'turn-2',
      sequence: 2,
      question: 'Second question',
      answer: 'Second answer',
    }
    vi.mocked(api.getQAConversation)
      .mockResolvedValueOnce({ ...conversation, turns: [turn], total: 2, page: 1, page_size: 100 })
      .mockResolvedValueOnce({ ...conversation, turns: [secondTurn], total: 2, page: 2, page_size: 100 })

    const wrapper = await mountView()
    wrappers.push(wrapper)
    await wrapper.findAll('.panel-tabs button')[1]!.trigger('click')
    await wrapper.find('.qa-session-actions select').setValue('conversation-1')
    await flushPromises()

    expect(api.getQAConversation).toHaveBeenNthCalledWith(1, 'conversation-1', 1, 100)
    expect(api.getQAConversation).toHaveBeenNthCalledWith(2, 'conversation-1', 2, 100)
    expect(wrapper.find('.qa-messages').text()).toContain('Second answer')
    expect(wrapper.find('.qa-turn-pagination').exists()).toBe(false)
  })

  it('maps a PDF text selection to the page text and saves a highlight', async () => {
    const wrapper = await mountView()
    wrappers.push(wrapper)
    const words = wrapper.findAll('.pdf-text-word')
    const range = document.createRange()
    range.setStart(words[0]!.element.firstChild!, 0)
    range.setEnd(words[1]!.element.firstChild!, 5)
    Object.defineProperty(range, 'getBoundingClientRect', {
      value: () => ({ left: 10, top: 10, right: 60, bottom: 20, width: 50, height: 10 }),
    })
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await wrapper.find('.pdf-text-layer').trigger('mouseup')
    await wrapper.find('.selection-toolbar button').trigger('click')
    await flushPromises()
    expect(api.createHighlight).toHaveBeenCalledWith('paper-1', {
      page_number: 1, char_start: 0, char_end: 11, color: 'YELLOW',
    })
  })

  it('shows note anchors in green only while hovering the note record', async () => {
    vi.mocked(api.listHighlights).mockResolvedValue({
      items: [{
        id: 'note-highlight', paper_id: 'paper-1', page_number: 1, char_start: 0, char_end: 11,
        quoted_text: 'Hello world', color: 'GREEN', created_at: '', updated_at: '', duplicate: false,
      }],
      total: 1, page: 1, page_size: 100,
    })
    vi.mocked(api.listNotes).mockResolvedValue({
      items: [{
        id: 'note-1', paper_id: 'paper-1', anchor_type: 'HIGHLIGHT', page_number: null,
        highlight_id: 'note-highlight', content: '我的理解', created_at: '', updated_at: '',
      }],
      total: 1, page: 1, page_size: 20,
    })
    const wrapper = await mountView()
    wrappers.push(wrapper)
    expect(wrapper.find('.pdf-highlight-green').exists()).toBe(false)

    await wrapper.findAll('.panel-tabs button')[2]!.trigger('click')
    await wrapper.findAll('.records-sub-tabs button')[1]!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).not.toContain('书签')
    expect(wrapper.text()).not.toContain('新建高亮')
    expect(wrapper.text()).not.toContain('新建笔记')
    expect(api.listNotes).toHaveBeenCalledWith('paper-1', { page: 1, page_size: 100 })
    expect(api.listHighlights).toHaveBeenCalledWith('paper-1', {
      page_number: 1, page: 1, page_size: 100,
    })

    await wrapper.find('.record-item').trigger('mouseenter')
    expect(wrapper.findAll('.pdf-highlight-green')).toHaveLength(2)
    await wrapper.find('.record-item').trigger('mouseleave')
    expect(wrapper.find('.pdf-highlight-green').exists()).toBe(false)

    await wrapper.find('.document-toolbar button[aria-label="下一页"]').trigger('click')
    await flushPromises()
    expect(api.listHighlights).toHaveBeenCalledWith('paper-1', {
      page_number: 2, page: 1, page_size: 100,
    })
    expect(wrapper.find('.record-item').exists()).toBe(false)
  })
})
