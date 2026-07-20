<template>
  <div v-if="paper" class="reading-view">
    <header class="reading-header">
      <div class="paper-heading">
        <div>
          <p class="workspace-label">论文阅读工作台</p>
          <h1>{{ paper.title }}</h1>
        </div>
        <div class="paper-meta">
          <span>{{ paper.filename }}</span>
          <span>{{ paper.page_count || '-' }} 页</span>
          <span class="paper-status">{{ paper.status === 'PARSED' ? '已解析' : paper.status === 'PROCESSING' ? '解析中' : '暂不可读' }}</span>
        </div>
      </div>

      <nav v-if="paper.status === 'PARSED'" class="workspace-actions" aria-label="论文功能">
        <button :class="{ active: sourceNavigator === 'sections' }" @click="toggleSourceNavigator('sections')">章节</button>
        <router-link :to="{ name: 'paper-review', params: { id: paper.id } }" class="button-link">批判性阅读</router-link>
        <router-link :to="{ name: 'paper-export', params: { id: paper.id } }" class="button-link">导出报告</router-link>
      </nav>
    </header>

    <div v-if="paper.status === 'PROCESSING'" class="not-ready processing-state">论文正在解析，完成后会自动进入阅读工作台。</div>
    <div v-else-if="paper.status !== 'PARSED'" class="not-ready error-state">论文暂时无法阅读{{ paper.error_message ? `：${paper.error_message}` : '' }}</div>
    <div v-else class="reading-layout">
      <section class="paper-panel">
        <div class="document-toolbar">
          <button aria-label="上一页" :disabled="currentPage <= 1" @click="selectPage(currentPage - 1)">上一页</button>
          <label class="page-control">
            <span>第</span>
            <input
              aria-label="页码"
              class="page-input"
              type="number"
              :value="currentPage"
              min="1"
              :max="paper.page_count || 1"
              @change="selectPage(Number(($event.target as HTMLInputElement).value))"
            />
            <span>/ {{ paper.page_count || 1 }} 页</span>
          </label>
          <button aria-label="下一页" :disabled="currentPage >= (paper.page_count || 1)" @click="selectPage(currentPage + 1)">下一页</button>
        </div>

        <div v-if="sourceNavigator === 'sections'" class="source-navigator">
          <div class="source-navigator-title">原文章节</div>
          <p v-if="!outline.length" class="empty-msg">原论文未提供章节目录</p>
          <div v-else class="source-options">
            <button
              v-for="(item, index) in outline"
              :key="`${item.page_number}-${item.level}-${item.title}`"
              :class="{ active: selectedOutlineIndex === index }"
              :style="{ paddingLeft: `${0.65 + Math.max(0, item.level - 1) * 0.8}rem` }"
              @click="selectOutlineAndClose(item, index)"
            >
              <span>{{ item.title }}</span>
              <small>p.{{ item.page_number }}</small>
            </button>
          </div>
        </div>

        <div ref="pdfStageRef" class="pdf-stage" @mousedown="dismissPdfSelection">
          <div v-if="pageImageLoading" class="pdf-state">正在加载第 {{ currentPage }} 页...</div>
          <div v-else-if="pageImageError" class="pdf-state error-msg">
            <p>{{ pageImageError }}</p>
            <button class="retry-btn" @click="loadOriginalPage(paper.id, currentPage)">重新加载</button>
          </div>
          <div
            v-else-if="pageImageUrl"
            class="pdf-page-surface"
            :style="pageSurfaceStyle"
          >
            <img
              class="paper-page-image"
              :src="pageImageUrl"
              :alt="`${paper.title} 第 ${currentPage} 页`"
              draggable="false"
            />
            <svg
              v-if="pageTextLayer"
              ref="pdfTextLayerRef"
              class="pdf-text-layer"
              :viewBox="`0 0 ${pageTextLayer.width} ${pageTextLayer.height}`"
              preserveAspectRatio="none"
              aria-label="可选择的论文正文"
              @mouseup.stop="onPdfTextSelection"
            >
              <rect
                v-for="(rect, index) in visibleHighlightRects"
                :key="`${rect.highlightId}-${index}`"
                :x="rect.x"
                :y="rect.y"
                :width="rect.width"
                :height="rect.height"
                :class="`pdf-highlight pdf-highlight-${rect.color.toLowerCase()}`"
              />
              <text
                v-for="word in pageTextLayer.words"
                :key="`${word.char_start}-${word.char_end}-${word.x0}-${word.y0}`"
                class="pdf-text-word"
                :data-start="word.char_start"
                :data-end="word.char_end"
                :x="word.x0"
                :y="word.y1 - Math.max(0.5, (word.y1 - word.y0) * 0.12)"
                :font-size="Math.max(1, (word.y1 - word.y0) * 0.88)"
                :textLength="Math.max(0.1, word.x1 - word.x0)"
                lengthAdjust="spacingAndGlyphs"
              >{{ word.text }}</text>
            </svg>
          </div>

          <div
            v-if="pdfSelection && !selectionNoteOpen"
            class="selection-toolbar"
            :style="selectionToolbarStyle"
            @mousedown.stop
          >
            <button :disabled="recordActionBusy" @click="applyPdfHighlight">高光</button>
            <button :disabled="recordActionBusy || submitting" @click="explainPdfSelection">解释</button>
            <button :disabled="recordActionBusy" @click="openPdfSelectionNote">添加笔记</button>
            <button aria-label="关闭选区工具" @click="clearPdfSelection">×</button>
          </div>

          <div
            v-if="pdfSelection && selectionNoteOpen"
            class="selection-note-editor"
            :style="selectionToolbarStyle"
            @mousedown.stop
          >
            <strong>为选中文字添加笔记</strong>
            <p>{{ pdfSelection.text }}</p>
            <textarea v-model="selectionNoteContent" rows="3" maxlength="20000" placeholder="写下你的理解..."></textarea>
            <div>
              <button @click="closePdfSelectionNote">取消</button>
              <button class="submit-btn" :disabled="!selectionNoteContent.trim() || recordActionBusy" @click="savePdfSelectionNote">保存笔记</button>
            </div>
          </div>
          <div v-if="selectionActionNotice" class="pdf-action-notice">{{ selectionActionNotice }}</div>
        </div>

        <div v-if="contentError" class="error-msg compact-message">{{ contentError }}</div>
        <div v-if="progressError" class="progress-warning compact-message">{{ progressError }} <button @click="retryReadingProgress">重试记录进度</button></div>
      </section>

      <aside class="learning-panel" :class="{ 'qa-panel-active': panelTab === 'qa' }">
        <div class="panel-topbar">
          <div class="panel-tabs">
            <button :class="{ active: panelTab === 'learning' }" @click="panelTab = 'learning'">学习解释</button>
            <button :class="{ active: panelTab === 'qa' }" @click="panelTab = 'qa'">论文问答</button>
            <button :class="{ active: panelTab === 'records' }" @click="panelTab = 'records'">学习记录</button>
          </div>
          <router-link v-if="panelTab !== 'learning'" :to="{ name: 'papers' }" class="button-link panel-exit">退出</router-link>
        </div>

        <template v-if="panelTab === 'learning'">
        <h3>学习助手</h3>

        <p class="current-page-hint">当前处理第 {{ currentPage }} 页</p>

        <div class="mode-selector" aria-label="学习方式">
          <button v-for="mode in modes" :key="mode.value" :class="{ active: selectedMode === mode.value }" @click="selectedMode = mode.value">
            {{ mode.label }}
          </button>
        </div>

        <button class="submit-btn" :disabled="!canSubmit || submitting" @click="submitLearning">
          {{ submitting ? '请求中...' : '生成学习解释' }}
        </button>
        <button v-if="activeExplanation" type="button" class="learning-exit" @click="exitLearningExplanation">退出</button>
        <div v-if="assistantError" class="error-msg assistant-error">{{ assistantError }}</div>

        <div v-if="activeExplanation" class="result-area">
          <div v-if="isProcessing(activeExplanation.status)" class="loading-msg">生成中...</div>
          <div v-else-if="activeExplanation.status === 'FAILED'" class="error-msg">
            <p>{{ activeExplanation.error_message || '学习解释生成失败，请稍后重试' }}</p>
            <button class="retry-btn" @click="retryExplanation">重新生成</button>
          </div>
          <div v-else-if="activeExplanation.status === 'SUCCEEDED'" class="result-content">
            <template v-if="activeExplanation.mode === 'SUMMARY'">
              <div class="result-mode-heading summary-heading">
                <span>总结</span>
                <small>提炼本页主旨，不复述原文</small>
              </div>
              <h4>本页概括</h4>
              <p class="answer-text">{{ activeExplanation.answer }}</p>
              <template v-if="activeExplanation.key_points?.length">
                <h4>核心要点</h4>
                <ul class="key-points">
                  <li v-for="(point, index) in activeExplanation.key_points" :key="index">{{ point }}</li>
                </ul>
              </template>
            </template>

            <template v-else-if="activeExplanation.mode === 'EXPLAIN'">
              <div class="result-mode-heading explain-heading">
                <span>选中文字解释</span>
                <small>拆解原理，并用例子帮助理解</small>
              </div>
              <blockquote v-if="activeExplanation.selection_text" class="selection-excerpt">{{ activeExplanation.selection_text }}</blockquote>
              <h4>原理讲解与示例</h4>
              <p class="answer-text explain-answer">{{ activeExplanation.answer }}</p>
              <template v-if="activeExplanation.key_points?.length">
                <h4>理解要点</h4>
                <ul class="key-points explain-points">
                  <li v-for="(point, index) in activeExplanation.key_points" :key="index">{{ point }}</li>
                </ul>
              </template>
              <template v-if="activeExplanation.terms?.length">
                <h4>概念拆解</h4>
                <dl class="terms-list">
                  <div v-for="term in activeExplanation.terms" :key="term.term" class="term-card">
                    <dt>{{ term.term }}</dt>
                    <dd>{{ term.explanation }}</dd>
                  </div>
                </dl>
              </template>
            </template>

            <template v-else>
              <div class="result-mode-heading translation-heading">
                <span>完整翻译</span>
                <small>逐段翻译本页全部正文并保留层次</small>
              </div>
              <div class="translation-content">
                <template v-for="(block, index) in translationBlocks" :key="index">
                  <component :is="`h${block.level}`" v-if="block.kind === 'heading'">{{ block.text }}</component>
                  <p v-else-if="block.kind === 'paragraph'">{{ block.text }}</p>
                  <div v-else class="translation-list-item">{{ block.text }}</div>
                </template>
              </div>
            </template>
          </div>
        </div>

        <section ref="learningHistorySection" class="history-section">
          <h4>解释历史</h4>
          <div v-if="historyLoading" class="loading-msg">加载历史中...</div>
          <div v-else-if="historyError" class="error-msg">
            {{ historyError }}
            <button class="retry-btn" @click="loadHistory">重试</button>
          </div>
          <ul v-else-if="historyItems.length" class="history-list">
            <li
              v-for="item in historyItems"
              :key="item.id"
              :class="{ active: activeExplanation?.id === item.id }"
              @mouseenter="previewExplanationSource(item)"
              @mouseleave="clearSourcePreview"
              @click="openHistoryExplanation(item)"
            >
              <span>{{ modeLabel(item.mode) }} · {{ historyLocation(item) }}</span>
              <span class="hist-status" :class="`status-${item.status.toLowerCase()}`">{{ statusLabel(item.status) }}</span>
              <time>{{ formatTime(item.created_at) }}</time>
              <button class="delete-btn history-delete" :disabled="historyActionBusy || isProcessing(item.status)" @click.stop="removeExplanation(item.id)">删除</button>
            </li>
          </ul>
          <p v-else class="empty-msg">暂无记录</p>
        </section>
        </template>

        <template v-if="panelTab === 'qa'">
        <div class="qa-chat-shell">
          <header class="qa-chat-header">
            <div>
              <h3>论文问答</h3>
              <small>围绕当前论文连续提问</small>
            </div>
            <div class="qa-session-actions">
              <select :value="activeQAConvId || ''" :disabled="qaConvLoading || qaSubmitting" aria-label="历史对话" @change="onQAConversationChange">
                <option value="">新的对话</option>
                <option v-for="conv in qaConversations" :key="conv.id" :value="conv.id">{{ conversationLabel(conv) }}</option>
              </select>
              <button :disabled="qaSubmitting || qaHasActiveTurn" @click="startNewQAConversation">新对话</button>
              <button v-if="activeQAConvId" class="delete-btn" :disabled="qaSubmitting || qaHasActiveTurn" @click="removeQAConversation(activeQAConvId)">删除</button>
            </div>
          </header>

          <div v-if="qaConvError" class="error-msg qa-banner">
            {{ qaConvError }}
            <button class="retry-btn" @click="loadQAConversations(qaConvPage)">重试</button>
          </div>
          <div v-if="activeQAConvId && qaTurnsError" class="error-msg qa-banner">
            {{ qaTurnsError }}
            <button class="retry-btn" @click="loadQATurns(activeQAConvId)">重试</button>
          </div>

          <div ref="qaMessagesRef" class="qa-messages">
            <div v-if="qaTurnsLoading" class="loading-msg qa-center-state">正在加载对话...</div>
            <div v-else-if="!qaTurns.length" class="qa-welcome">
              <div class="qa-avatar assistant-avatar">AI</div>
              <div class="qa-bubble assistant-bubble">
                你好，我会结合这篇论文回答你的问题。你可以询问概念、方法、实验结论，或让某一段内容更容易理解。
              </div>
            </div>
            <template v-for="turn in qaTurns" :key="turn.id">
              <div class="qa-row user-row">
                <div class="qa-bubble user-bubble">{{ turn.question }}</div>
                <div class="qa-avatar user-avatar">我</div>
              </div>
              <div class="qa-row assistant-row">
                <div class="qa-avatar assistant-avatar">AI</div>
                <div class="qa-bubble assistant-bubble">
                  <div v-if="turn.status === 'PENDING' || turn.status === 'RUNNING'" class="typing-indicator" aria-label="正在生成">
                    <span></span><span></span><span></span>
                  </div>
                  <div v-else-if="turn.status === 'FAILED'" class="error-msg">
                    {{ turn.error_message || '回答生成失败，请稍后重试' }}
                    <button class="retry-btn" :disabled="qaSubmitting || qaHasActiveTurn" @click="retryQATurn(turn)">重新提问</button>
                  </div>
                  <p v-else>{{ turn.answer }}</p>
                </div>
              </div>
            </template>
          </div>

          <div class="qa-input-area">
            <div v-if="qaTurnError" class="error-msg">{{ qaTurnError }}</div>
            <div class="qa-composer">
              <select v-model="qaOutputLang" :disabled="qaSubmitting || qaHasActiveTurn">
                <option value="zh">中文</option>
                <option value="en">English</option>
              </select>
              <textarea
                v-model="qaQuestion"
                placeholder="给论文助手发送消息..."
                rows="2"
                maxlength="2000"
                :disabled="qaSubmitting || qaHasActiveTurn"
                @keydown.enter.exact.prevent="submitQATurn"
                @keydown.shift.enter.stop
              ></textarea>
              <button class="qa-send-button" aria-label="发送问题" :disabled="!qaQuestion.trim() || qaSubmitting || qaHasActiveTurn" @click="submitQATurn">
                {{ qaSubmitting ? '…' : '↑' }}
              </button>
            </div>
            <small class="qa-input-tip">Enter 发送，Shift + Enter 换行</small>
          </div>
        </div>
        </template>

        <template v-if="panelTab === 'records'">
        <h3>学习记录</h3>

        <div class="records-sub-tabs">
          <button :class="{ active: recordsSubTab === 'highlights' }" @click="recordsSubTab = 'highlights'">高亮</button>
          <button :class="{ active: recordsSubTab === 'notes' }" @click="recordsSubTab = 'notes'">笔记</button>
        </div>

        <template v-if="recordsSubTab === 'highlights'">
          <div v-if="recordsLoading" class="loading-msg">加载中...</div>
          <div v-else-if="recordsError" class="error-msg">{{ recordsError }} <button @click="loadActiveRecords">重试</button></div>
          <ul v-else-if="highlights.length" class="record-list">
            <li v-for="hl in highlights" :key="hl.id" class="record-item">
              <button class="record-locator" @click="locateSavedHighlight(hl)"><mark class="hl-color-yellow">{{ hl.quoted_text }}</mark></button>
              <span class="record-meta">p.{{ hl.page_number }}</span>
              <button class="delete-btn" :disabled="recordActionBusy" @click="removeHighlight(hl.id)">删除</button>
            </li>
          </ul>
          <p v-else class="empty-msg">暂无高亮</p>
          <div v-if="highlightTotal > 20" class="record-pagination">
            <button :disabled="highlightPage <= 1" @click="goRecordPage(highlightPage - 1)">上一页</button>
            <span>{{ highlightPage }} / {{ Math.ceil(highlightTotal / 20) }}</span>
            <button :disabled="highlightPage >= Math.ceil(highlightTotal / 20)" @click="goRecordPage(highlightPage + 1)">下一页</button>
          </div>
        </template>

        <template v-if="recordsSubTab === 'notes'">
          <div v-if="showNoteForm" class="note-form">
            <strong>编辑笔记</strong>
            <textarea v-model="noteContent" rows="4" maxlength="20000" placeholder="输入笔记内容..."></textarea>
            <div class="note-form-actions">
              <button class="submit-btn" :disabled="recordActionBusy" @click="submitNote">保存修改</button>
              <button @click="cancelNoteForm">取消</button>
            </div>
          </div>
          <div v-if="recordsLoading" class="loading-msg">加载中...</div>
          <div v-else-if="recordsError" class="error-msg">{{ recordsError }} <button @click="loadActiveRecords">重试</button></div>
          <ul v-else-if="notes.length" class="record-list">
            <li
              v-for="n in notes"
              :key="n.id"
              class="record-item"
              @mouseenter="previewNoteSource(n)"
              @mouseleave="clearSourcePreview"
            >
              <span class="note-anchor">{{ n.anchor_type }}</span>
              <p class="note-content">{{ n.content }}</p>
              <span class="record-meta">{{ formatTime(n.updated_at) }}</span>
              <button :disabled="recordActionBusy" @click="startEditNote(n)">编辑</button>
              <button class="delete-btn" :disabled="recordActionBusy" @click="removeNote(n.id)">删除</button>
            </li>
          </ul>
          <p v-else class="empty-msg">暂无笔记</p>
          <div v-if="noteTotal > 20" class="record-pagination">
            <button :disabled="notePage <= 1" @click="goRecordPage(notePage - 1)">上一页</button>
            <span>{{ notePage }} / {{ Math.ceil(noteTotal / 20) }}</span>
            <button :disabled="notePage >= Math.ceil(noteTotal / 20)" @click="goRecordPage(notePage + 1)">下一页</button>
          </div>
        </template>

        </template>
      </aside>
    </div>
  </div>
  <div v-else-if="loadError" class="error-msg page-error">
    <p>{{ loadError }}</p>
    <button class="retry-btn" @click="loadPaper(String(route.params.id || ''))">重试</button>
  </div>
  <div v-else class="loading-msg page-loading">加载论文中...</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  createHighlight,
  createLearningExplanation,
  createNote,
  createQAConversation,
  createQATurn,
  deleteHighlight,
  deleteLearningExplanation,
  deleteNote,
  deleteQAConversation,
  getLearningExplanation,
  getQAConversation,
  getQATurn,
  getPage,
  getPaper,
  getPaperOutline,
  getPaperPageImage,
  getPaperPageTextLayer,
  listHighlights,
  listLearningExplanations,
  listNotes,
  listQAConversations,
  patchNote,
  patchReadingProgress,
  type HighlightResponse,
  type NoteResponse,

  type LearningExplanationListItem,
  type LearningExplanationResponse,
  type LearningMode,
  type LearningStatus,
  type PageDetail,
  type PaperDetail,
  type PaperOutlineItem,
  type PageTextLayerResponse,
  type QAConversationListItem,
  type QATurnStatus,
  type QATurnResponse,
} from '../api'
import { SAFE_POLLING_ERROR, usePolling } from '../composables/usePolling'
import { createUuid4 } from '../utils/uuid'

const route = useRoute()
const paper = ref<PaperDetail | null>(null)
const {
  startPolling: startLearningSharedPolling,
  stopPolling: stopLearningSharedPolling,
} = usePolling()
const {
  startPolling: startQASharedPolling,
  stopPolling: stopQASharedPolling,
} = usePolling()
const {
  startPolling: startPaperSharedPolling,
  stopPolling: stopPaperSharedPolling,
} = usePolling()
const outline = ref<PaperOutlineItem[]>([])
const selectedOutlineIndex = ref<number | null>(null)
const pageData = ref<PageDetail | null>(null)
const loadError = ref('')
const contentError = ref('')
const contentLoading = ref(false)
const progressError = ref('')
const assistantError = ref('')
const historyError = ref('')
const sourceNavigator = ref<'sections' | null>(null)
const pageImageUrl = ref('')
const pageImageLoading = ref(false)
const pageImageError = ref('')
const pageTextLayer = ref<PageTextLayerResponse | null>(null)
const pageHighlights = ref<HighlightResponse[]>([])

const currentPage = ref(1)
const selectedMode = ref<LearningMode>('SUMMARY')
const submitting = ref(false)

const activeExplanation = ref<LearningExplanationResponse | null>(null)
const historyItems = ref<LearningExplanationListItem[]>([])
const historyLoading = ref(false)
const historyActionBusy = ref(false)
const learningHistorySection = ref<HTMLElement | null>(null)


const qaConversations = ref<QAConversationListItem[]>([])
const qaConvTotal = ref(0)
const qaConvPage = ref(1)
const qaConvLoading = ref(false)
const activeQAConvId = ref<string | null>(null)
const qaTurns = ref<QATurnResponse[]>([])
const qaTurnTotal = ref(0)
const qaTurnsLoading = ref(false)
const qaTurnsError = ref('')
const qaQuestion = ref('')
const qaOutputLang = ref<'zh' | 'en'>('zh')
const qaSubmitting = ref(false)
const qaCreatingConv = ref(false)
const qaConvError = ref('')
const qaTurnError = ref('')

const panelTab = ref<'learning' | 'qa' | 'records'>('learning')
const recordsSubTab = ref<'highlights' | 'notes'>('highlights')
const recordsLoading = ref(false)
const recordsError = ref('')
const highlights = ref<HighlightResponse[]>([])
const notes = ref<NoteResponse[]>([])
const sourceHighlights = ref<HighlightResponse[]>([])
const highlightTotal = ref(0)
const noteTotal = ref(0)
const highlightPage = ref(1)
const notePage = ref(1)
const recordActionBusy = ref(false)
const showNoteForm = ref(false)
const editingNoteId = ref<string | null>(null)
const noteContent = ref('')
let qaPaperGeneration = 0
let qaConversationGeneration = 0
let qaTurnGeneration = 0
let qaActionGeneration = 0
let recordPaperGeneration = 0
let highlightGeneration = 0
let noteGeneration = 0
let recordActionGeneration = 0
let progressGeneration = 0
const pdfStageRef = ref<HTMLElement | null>(null)
const pdfTextLayerRef = ref<SVGSVGElement | null>(null)
const qaMessagesRef = ref<HTMLElement | null>(null)
const pdfSelection = ref<{ start: number; end: number; text: string; x: number; y: number } | null>(null)
const sourcePreview = ref<{ start: number; end: number; color: 'BLUE' | 'GREEN'; id: string } | null>(null)
const selectionNoteOpen = ref(false)
const selectionNoteContent = ref('')
const selectionActionNotice = ref('')
let selectionNoticeTimer: number | null = null
let paperGeneration = 0
let contentGeneration = 0
let assistantGeneration = 0
let historyGeneration = 0
let pageImageGeneration = 0
let pageAnnotationGeneration = 0

interface SourceSelection {
  start: number
  end: number
  text: string
}

const modes = [
  { value: 'SUMMARY' as LearningMode, label: '总结' },
  { value: 'TRANSLATE' as LearningMode, label: '翻译' },
]

interface TranslationBlock {
  kind: 'heading' | 'paragraph' | 'list'
  level: number
  text: string
}

const canSubmit = computed(() => currentPage.value >= 1 && Boolean(pageData.value))

const currentContent = computed(() => pageData.value?.normalized_text_content || pageData.value?.text_content || null)

const pageSurfaceStyle = computed(() => {
  const width = pageTextLayer.value?.width || pageData.value?.width
  const height = pageTextLayer.value?.height || pageData.value?.height
  return width && height ? { aspectRatio: `${width} / ${height}` } : {}
})

const selectionToolbarStyle = computed(() => ({
  left: `${pdfSelection.value?.x || 0}px`,
  top: `${pdfSelection.value?.y || 0}px`,
}))

const activeExplanationSource = computed(() => {
  const explanation = activeExplanation.value
  if (
    panelTab.value !== 'learning'
    || explanation?.mode !== 'EXPLAIN'
    || explanation.page_number !== currentPage.value
    || explanation.selection_start === null
    || explanation.selection_end === null
    || explanation.selection_end <= explanation.selection_start
  ) return null
  return {
    id: `active-explanation-${explanation.id}`,
    start: explanation.selection_start,
    end: explanation.selection_end,
    color: 'BLUE' as const,
  }
})

const visibleHighlightRects = computed(() => {
  const words = pageTextLayer.value?.words || []
  const explanationRange = sourcePreview.value || activeExplanationSource.value
  const ranges = [
    ...pageHighlights.value
      .filter(highlight => highlight.color === 'YELLOW')
      .map(highlight => ({
        id: highlight.id,
        start: highlight.char_start,
        end: highlight.char_end,
        color: 'YELLOW' as const,
      })),
    ...(explanationRange ? [explanationRange] : []),
  ]
  return ranges.flatMap(range => words
    .filter(word => word.char_end > range.start && word.char_start < range.end)
    .map(word => ({
      highlightId: range.id,
      color: range.color,
      x: word.x0,
      y: word.y0,
      width: Math.max(0.5, word.x1 - word.x0),
      height: Math.max(0.5, word.y1 - word.y0),
    })))
})

const translationBlocks = computed<TranslationBlock[]>(() => {
  const answer = activeExplanation.value?.answer || ''
  const blocks: TranslationBlock[] = []
  for (const line of answer.split(/\r?\n/)) {
    const text = line.trim()
    if (!text) continue
    const heading = text.match(/^(#{1,6})\s+(.+)$/)
    if (heading) blocks.push({ kind: 'heading', level: Math.min(6, (heading[1] || '#').length + 1), text: heading[2] || '' })
    else if (/^[-*•]\s+/.test(text)) blocks.push({ kind: 'list', level: 0, text: text.replace(/^[-*•]\s+/, '• ') })
    else blocks.push({ kind: 'paragraph', level: 0, text })
  }
  return blocks
})

const qaHasActiveTurn = computed(() => {
  if (qaTurns.value.some(turn => turn.status === 'PENDING' || turn.status === 'RUNNING')) return true
  const activeConversation = qaConversations.value.find(item => item.id === activeQAConvId.value)
  return activeConversation?.last_status === 'PENDING' || activeConversation?.last_status === 'RUNNING'
})

function safeRequestError(error: unknown, fallback: string): string {
  const status = (error as { response?: { status?: number } })?.response?.status
  if (status === 401) return '登录状态已失效，请重新登录。'
  if (status === 404) return '资源不存在或无权访问。'
  if (status === 409) return '当前内容暂不适合生成，请缩小阅读范围后重试。'
  if (status === 422) return '学习范围或参数无效，请重新选择。'
  if (status === undefined) {
    return (error as { request?: unknown })?.request
      ? '网络连接失败，请稍后重试。'
      : fallback
  }
  return fallback
}

function isProcessing(status: LearningStatus): boolean {
  return status === 'PENDING' || status === 'RUNNING'
}

function clearAssistant(): void {
  assistantGeneration++
  stopPolling()
  activeExplanation.value = null
  assistantError.value = ''
}

function exitLearningExplanation(): void {
  clearAssistant()
  clearSourcePreview()
  void nextTick(() => {
    learningHistorySection.value?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
  })
}

function clearSourcePreview(): void {
  sourcePreview.value = null
}

function previewExplanationSource(item: LearningExplanationListItem): void {
  if (
    item.mode !== 'EXPLAIN'
    || item.page_number !== currentPage.value
    || item.selection_start === null
    || item.selection_end === null
    || item.selection_end <= item.selection_start
  ) {
    clearSourcePreview()
    return
  }
  sourcePreview.value = {
    id: `explanation-${item.id}`,
    start: item.selection_start,
    end: item.selection_end,
    color: 'BLUE',
  }
}

function previewNoteSource(note: NoteResponse): void {
  const highlight = note.highlight_id
    ? pageHighlights.value.find(item => item.id === note.highlight_id)
      || sourceHighlights.value.find(item => item.id === note.highlight_id)
    : null
  if (!highlight || highlight.page_number !== currentPage.value) {
    clearSourcePreview()
    return
  }
  sourcePreview.value = {
    id: `note-${note.id}`,
    start: highlight.char_start,
    end: highlight.char_end,
    color: 'GREEN',
  }
}

function toggleSourceNavigator(target: 'sections'): void {
  sourceNavigator.value = sourceNavigator.value === target ? null : target
}

async function selectOutlineAndClose(item: PaperOutlineItem, index: number): Promise<void> {
  selectedOutlineIndex.value = index
  sourceNavigator.value = null
  await selectPage(item.page_number)
}

async function selectPage(pageNumber: number): Promise<boolean> {
  if (!Number.isInteger(pageNumber) || pageNumber < 1 || pageNumber > (paper.value?.page_count || 1)) return false
  clearAssistant()
  currentPage.value = pageNumber
  clearSourcePreview()
  clearPdfSelection()
  if (panelTab.value === 'records') {
    highlights.value = []
    notes.value = []
    sourceHighlights.value = []
    highlightTotal.value = 0
    noteTotal.value = 0
    highlightPage.value = 1
    notePage.value = 1
  }
  const loaded = await loadPageContent(pageNumber)
  if (loaded && panelTab.value === 'records') loadActiveRecords()
  return loaded
}

async function loadPageContent(pageNumber: number): Promise<boolean> {
  const paperId = paper.value?.id
  if (!paperId) return false
  const generation = ++contentGeneration
  contentLoading.value = true
  contentError.value = ''
  try {
    const data = await getPage(paperId, pageNumber)
    if (generation !== contentGeneration || paper.value?.id !== paperId || currentPage.value !== pageNumber) return false
    pageData.value = data
    contentLoading.value = false
    await reportReadingProgress(pageNumber)
    if (generation !== contentGeneration || paper.value?.id !== paperId || currentPage.value !== pageNumber) return false
    return true
  } catch (error) {
    if (generation === contentGeneration && paper.value?.id === paperId) {
      pageData.value = null
      contentError.value = safeRequestError(error, '加载页面失败，请重试。')
    }
    return false
  } finally {
    if (generation === contentGeneration) contentLoading.value = false
  }
}

function buildRequestBody(mode: LearningMode, selection?: SourceSelection) {
  return {
    mode,
    scope_type: 'PAGE' as const,
    output_language: 'zh' as const,
    page_number: currentPage.value,
    ...(selection ? {
      selection_text: selection.text,
      selection_start: selection.start,
      selection_end: selection.end,
    } : {}),
  }
}

async function requestLearning(mode: LearningMode, selection?: SourceSelection): Promise<boolean> {
  const paperId = paper.value?.id
  const requestedPage = currentPage.value
  if (!paperId || !canSubmit.value || submitting.value) return false
  stopPolling()
  const generation = ++assistantGeneration
  submitting.value = true
  assistantError.value = ''
  try {
    const response = await createLearningExplanation(paperId, buildRequestBody(mode, selection))
    if (
      generation !== assistantGeneration
      || paper.value?.id !== paperId
      || currentPage.value !== requestedPage
    ) return false
    activeExplanation.value = response
    if (isProcessing(response.status)) startPolling(response.id, generation, paperId, requestedPage)
    await loadHistory()
    return true
  } catch (error) {
    if (generation === assistantGeneration) {
      assistantError.value = safeRequestError(error, '创建学习解释失败，请稍后重试。')
    }
    return false
  } finally {
    if (generation === assistantGeneration) submitting.value = false
  }
}

async function submitLearning(): Promise<void> {
  await requestLearning(selectedMode.value)
}

function startPolling(
  explanationId: string,
  assistantToken = assistantGeneration,
  paperId = paper.value?.id || '',
  pageNumber = currentPage.value,
): void {
  startLearningSharedPolling(
    () => getLearningExplanation(explanationId),
    response => {
      if (
        assistantToken !== assistantGeneration
        || paper.value?.id !== paperId
        || currentPage.value !== pageNumber
      ) return
      activeExplanation.value = response
      if (!isProcessing(response.status)) void loadHistory()
    },
    response => !isProcessing(response.status),
    () => {
      if (
        assistantToken === assistantGeneration
        && paper.value?.id === paperId
        && currentPage.value === pageNumber
      ) {
        assistantError.value = SAFE_POLLING_ERROR
      }
    },
  )
}

function stopPolling(): void {
  stopLearningSharedPolling()
}

async function openHistoryExplanation(item: LearningExplanationListItem): Promise<void> {
  if (item.page_number && item.page_number !== currentPage.value) {
    const loaded = await selectPage(item.page_number)
    if (!loaded) return
  }
  await loadExplanation(item.id)
}

async function loadExplanation(explanationId: string): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  stopPolling()
  const generation = ++assistantGeneration
  assistantError.value = ''
  try {
    const response = await getLearningExplanation(explanationId)
    if (
      generation !== assistantGeneration
      || paper.value?.id !== paperId
      || response.paper_id !== paperId
      || response.page_number !== currentPage.value
    ) return
    activeExplanation.value = response
    if (isProcessing(response.status)) startPolling(explanationId, generation, paperId, currentPage.value)
  } catch (error) {
    if (generation === assistantGeneration) assistantError.value = safeRequestError(error, '加载解释失败，请重试。')
  }
}

async function retryExplanation(): Promise<void> {
  const explanation = activeExplanation.value
  if (!explanation) return
  if (
    explanation.mode === 'EXPLAIN'
    && (
      !explanation.selection_text
      || explanation.selection_start === null
      || explanation.selection_end === null
    )
  ) {
    assistantError.value = '原有整页通俗解释不能重新生成，请在左侧选中文字后点击“解释”。'
    return
  }
  if (explanation.page_number && explanation.page_number !== currentPage.value) {
    await selectPage(explanation.page_number)
  }
  await requestLearning(
    explanation.mode,
    explanation.selection_text
      && explanation.selection_start !== null
      && explanation.selection_end !== null
      ? {
          text: explanation.selection_text,
          start: explanation.selection_start,
          end: explanation.selection_end,
        }
      : undefined,
  )
}

async function loadHistory(): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  const generation = ++historyGeneration
  historyLoading.value = true
  historyError.value = ''
  try {
    const items: LearningExplanationListItem[] = []
    let apiPage = 1
    let total = 0
    do {
      const response = await listLearningExplanations(paperId, apiPage, 100)
      if (generation !== historyGeneration || paper.value?.id !== paperId) return
      items.push(...response.items)
      total = response.total
      apiPage += 1
      if (!response.items.length) break
    } while (items.length < total)
    historyItems.value = items.sort((left, right) => {
      const pageDifference = (left.page_number ?? Number.MAX_SAFE_INTEGER) - (right.page_number ?? Number.MAX_SAFE_INTEGER)
      if (pageDifference !== 0) return pageDifference
      return Date.parse(right.created_at) - Date.parse(left.created_at)
    })
  } catch (error) {
    if (generation === historyGeneration) historyError.value = safeRequestError(error, '加载解释历史失败，请重试。')
  } finally {
    if (generation === historyGeneration) historyLoading.value = false
  }
}

async function removeExplanation(explanationId: string): Promise<void> {
  if (!window.confirm('确认删除这条论文解释吗？删除后无法恢复。')) return
  historyActionBusy.value = true
  historyError.value = ''
  try {
    await deleteLearningExplanation(explanationId)
    if (activeExplanation.value?.id === explanationId) clearAssistant()
    await loadHistory()
  } catch (error) {
    historyError.value = safeRequestError(error, '删除论文解释失败，请重试。')
  } finally {
    historyActionBusy.value = false
  }
}

async function loadQAConversations(pageNumber = 1): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || pageNumber < 1) return
  const paperToken = qaPaperGeneration
  const requestToken = ++qaConversationGeneration
  qaConvLoading.value = true
  qaConvError.value = ''
  try {
    const response = await listQAConversations(paperId, pageNumber, 20)
    if (
      paperToken !== qaPaperGeneration
      || requestToken !== qaConversationGeneration
      || paper.value?.id !== paperId
    ) return
    qaConversations.value = response.items
    qaConvTotal.value = response.total
    qaConvPage.value = response.page
  } catch (error) {
    if (paperToken === qaPaperGeneration && requestToken === qaConversationGeneration) {
      qaConvError.value = safeRequestError(error, '加载问答会话失败，请重试。')
    }
  } finally {
    if (requestToken === qaConversationGeneration) qaConvLoading.value = false
  }
}

function startNewQAConversation(): void {
  if (qaSubmitting.value) return
  stopQAPolling()
  activeQAConvId.value = null
  qaTurns.value = []
  qaTurnTotal.value = 0
  qaTurnsError.value = ''
  qaTurnError.value = ''
  qaQuestion.value = ''
}

async function removeQAConversation(conversationId: string): Promise<void> {
  if (!window.confirm('确认删除这段论文问答吗？删除后无法恢复。')) return
  qaConvError.value = ''
  try {
    await deleteQAConversation(conversationId)
    if (activeQAConvId.value === conversationId) startNewQAConversation()
    const targetPage = qaConversations.value.length === 1 && qaConvPage.value > 1
      ? qaConvPage.value - 1
      : qaConvPage.value
    await loadQAConversations(targetPage)
  } catch (error) {
    qaConvError.value = safeRequestError(error, '删除问答会话失败，请重试。')
  }
}

async function selectQAConversation(conversationId: string): Promise<void> {
  if (activeQAConvId.value === conversationId && qaTurns.value.length) return
  activeQAConvId.value = conversationId
  qaTurnError.value = ''
  await loadQATurns(conversationId)
}

function onQAConversationChange(event: Event): void {
  const conversationId = (event.target as HTMLSelectElement).value
  if (conversationId) void selectQAConversation(conversationId)
  else startNewQAConversation()
}

async function scrollQAEnd(): Promise<void> {
  await nextTick()
  if (qaMessagesRef.value) qaMessagesRef.value.scrollTop = qaMessagesRef.value.scrollHeight
}

async function loadQATurns(conversationId: string | null): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || !conversationId) return
  stopQAPolling()
  const paperToken = qaPaperGeneration
  const requestToken = ++qaTurnGeneration
  qaTurnsLoading.value = true
  qaTurnsError.value = ''
  try {
    const pageSize = 100
    let pageNumber = 1
    let response = await getQAConversation(conversationId, pageNumber, pageSize)
    const allTurns = [...(response.turns || [])]
    while (allTurns.length < response.total) {
      pageNumber += 1
      const nextResponse = await getQAConversation(conversationId, pageNumber, pageSize)
      if (nextResponse.paper_id !== response.paper_id) throw new Error('Conversation paper changed')
      const nextTurns = nextResponse.turns || []
      if (!nextTurns.length) throw new Error('Conversation history is incomplete')
      allTurns.push(...nextTurns)
      response = nextResponse
    }
    if (
      paperToken !== qaPaperGeneration
      || requestToken !== qaTurnGeneration
      || activeQAConvId.value !== conversationId
      || response.paper_id !== paperId
    ) return
    qaTurns.value = allTurns
    qaTurnTotal.value = response.total
    const processing = qaTurns.value.find(
      turn => turn.status === 'PENDING' || turn.status === 'RUNNING',
    )
    if (processing) startQAPolling(processing.id, conversationId, paperToken)
    await scrollQAEnd()
  } catch (error) {
    if (paperToken === qaPaperGeneration && requestToken === qaTurnGeneration) {
      qaTurnsError.value = safeRequestError(error, '加载问答历史失败，请重试。')
    }
  } finally {
    if (requestToken === qaTurnGeneration) qaTurnsLoading.value = false
  }
}

async function submitQATurn(): Promise<void> {
  let conversationId = activeQAConvId.value
  const paperId = paper.value?.id
  const question = qaQuestion.value.trim()
  if (
    !paperId
    || !question
    || qaSubmitting.value
    || qaHasActiveTurn.value
  ) return
  const paperToken = qaPaperGeneration
  const actionToken = ++qaActionGeneration
  qaSubmitting.value = true
  qaTurnError.value = ''
  let createdConversationId: string | null = null
  try {
    if (!conversationId) {
      qaCreatingConv.value = true
      const conversation = await createQAConversation(paperId, {})
      if (
        paperToken !== qaPaperGeneration
        || actionToken !== qaActionGeneration
        || paper.value?.id !== paperId
        || conversation.paper_id !== paperId
      ) return
      conversationId = conversation.id
      createdConversationId = conversation.id
      activeQAConvId.value = conversation.id
      qaTurnTotal.value = 0
    }
    await createQATurn(conversationId, {
      question,
      output_language: qaOutputLang.value,
      client_request_id: createUuid4(),
      current_page: currentPage.value,
    })
    if (
      paperToken !== qaPaperGeneration
      || actionToken !== qaActionGeneration
      || activeQAConvId.value !== conversationId
      || paper.value?.id !== paperId
    ) return
    qaQuestion.value = ''
    await loadQATurns(conversationId)
    if (paperToken === qaPaperGeneration && actionToken === qaActionGeneration) {
      await loadQAConversations(createdConversationId ? 1 : qaConvPage.value)
    }
  } catch (error) {
    if (paperToken === qaPaperGeneration && actionToken === qaActionGeneration) {
      const status = (error as { response?: { status?: number } })?.response?.status
      qaTurnError.value = status === 409
        ? '当前会话仍有问题正在生成，请等待完成后再提问。'
        : safeRequestError(error, '提问失败，请重试。')
    }
    if (createdConversationId) {
      try {
        await deleteQAConversation(createdConversationId)
        if (activeQAConvId.value === createdConversationId) activeQAConvId.value = null
      } catch {}
    }
  } finally {
    if (actionToken === qaActionGeneration) {
      qaSubmitting.value = false
      qaCreatingConv.value = false
    }
  }
}

async function retryQATurn(turn: QATurnResponse): Promise<void> {
  if (turn.status !== 'FAILED' || qaSubmitting.value || qaHasActiveTurn.value) return
  qaQuestion.value = turn.question
  qaOutputLang.value = turn.output_language
  await submitQATurn()
}

function startQAPolling(
  turnId: string,
  conversationId: string,
  paperToken = qaPaperGeneration,
): void {
  startQASharedPolling(
    () => getQATurn(turnId),
    updated => {
      if (
        paperToken !== qaPaperGeneration
        || activeQAConvId.value !== conversationId
        || panelTab.value !== 'qa'
      ) return
      const index = qaTurns.value.findIndex(turn => turn.id === turnId)
      if (index >= 0) qaTurns.value[index] = updated
      void scrollQAEnd()
      if (updated.status !== 'PENDING' && updated.status !== 'RUNNING') {
        void loadQAConversations(qaConvPage.value)
      }
    },
    updated => updated.status !== 'PENDING' && updated.status !== 'RUNNING',
    () => {
      if (paperToken === qaPaperGeneration && activeQAConvId.value === conversationId) {
        qaTurnError.value = SAFE_POLLING_ERROR
      }
    },
  )
}

function stopQAPolling(): void {
  stopQASharedPolling()
}

function resetQAState(): void {
  qaPaperGeneration++
  qaConversationGeneration++
  qaTurnGeneration++
  qaActionGeneration++
  stopQAPolling()
  qaConversations.value = []
  qaConvTotal.value = 0
  qaConvPage.value = 1
  qaConvLoading.value = false
  qaConvError.value = ''
  activeQAConvId.value = null
  qaTurns.value = []
  qaTurnTotal.value = 0
  qaTurnsLoading.value = false
  qaTurnsError.value = ''
  qaQuestion.value = ''
  qaTurnError.value = ''
  qaSubmitting.value = false
  qaCreatingConv.value = false
}

function recordRequestError(reason: unknown, fallback: string): string {
  return (reason as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || fallback
}

function invalidateRecordLists(): void {
  highlightGeneration++
  noteGeneration++
  recordsLoading.value = false
}

async function loadHighlightsPage(pageNumber = highlightPage.value): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  const requestedPaperPage = currentPage.value
  const paperToken = recordPaperGeneration
  const requestToken = ++highlightGeneration
  recordsLoading.value = true
  recordsError.value = ''
  try {
    const response = await listHighlights(paperId, {
      page_number: requestedPaperPage,
      page: 1,
      page_size: 100,
    })
    if (
      paperToken !== recordPaperGeneration
      || requestToken !== highlightGeneration
      || recordsSubTab.value !== 'highlights'
      || currentPage.value !== requestedPaperPage
    ) return
    const yellowHighlights = response.items.filter(item => item.color === 'YELLOW')
    const start = (pageNumber - 1) * 20
    highlights.value = yellowHighlights.slice(start, start + 20)
    highlightTotal.value = yellowHighlights.length
    highlightPage.value = pageNumber
  } catch (reason) {
    if (paperToken === recordPaperGeneration && requestToken === highlightGeneration) recordsError.value = recordRequestError(reason, '加载高亮失败')
  } finally {
    if (paperToken === recordPaperGeneration && requestToken === highlightGeneration) recordsLoading.value = false
  }
}

async function loadNotesPage(pageNumber = notePage.value): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  const requestedPaperPage = currentPage.value
  const paperToken = recordPaperGeneration
  const requestToken = ++noteGeneration
  recordsLoading.value = true
    recordsError.value = ''
  try {
    const [response, highlightResponse] = await Promise.all([
      listNotes(paperId, { page: 1, page_size: 100 }),
      listHighlights(paperId, {
        page_number: requestedPaperPage,
        page: 1,
        page_size: 100,
      }),
    ])
    if (
      paperToken !== recordPaperGeneration
      || requestToken !== noteGeneration
      || recordsSubTab.value !== 'notes'
      || currentPage.value !== requestedPaperPage
    ) return
    const currentHighlights = highlightResponse.items.filter(item => item.page_number === requestedPaperPage)
    const currentHighlightIds = new Set(currentHighlights.map(item => item.id))
    const currentNotes = response.items.filter(note => (
      note.page_number === requestedPaperPage
      || Boolean(note.highlight_id && currentHighlightIds.has(note.highlight_id))
    ))
    const start = (pageNumber - 1) * 20
    notes.value = currentNotes.slice(start, start + 20)
    sourceHighlights.value = currentHighlights
    noteTotal.value = currentNotes.length
    notePage.value = pageNumber
  } catch (reason) {
    if (paperToken === recordPaperGeneration && requestToken === noteGeneration) recordsError.value = recordRequestError(reason, '加载笔记失败')
  } finally {
    if (paperToken === recordPaperGeneration && requestToken === noteGeneration) recordsLoading.value = false
  }
}

function loadActiveRecords(): void {
  if (recordsSubTab.value === 'highlights') void loadHighlightsPage()
  if (recordsSubTab.value === 'notes') void loadNotesPage()
}

function goRecordPage(pageNumber: number): void {
  if (pageNumber < 1) return
  if (recordsSubTab.value === 'highlights') void loadHighlightsPage(pageNumber)
  if (recordsSubTab.value === 'notes') void loadNotesPage(pageNumber)
}

async function removeHighlight(id: string): Promise<void> {
  if (!window.confirm('确认删除这条高亮吗？')) return
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  try {
    await deleteHighlight(id)
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    await loadHighlightsPage(highlightPage.value)
    if (paper.value?.id) await loadPageAnnotations(paper.value.id, currentPage.value)
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '删除高亮失败')
  } finally {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordActionBusy.value = false
  }
}

async function locateSavedHighlight(highlight: HighlightResponse): Promise<void> {
  await selectPage(highlight.page_number)
}

function startEditNote(note: NoteResponse): void {
  editingNoteId.value = note.id
  noteContent.value = note.content
  showNoteForm.value = true
}

function cancelNoteForm(): void {
  showNoteForm.value = false
  editingNoteId.value = null
  noteContent.value = ''
}

async function submitNote(): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || !editingNoteId.value || !noteContent.value.trim()) return
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  try {
    await patchNote(editingNoteId.value, noteContent.value.trim())
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    cancelNoteForm()
    await loadNotesPage(notePage.value)
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '保存笔记失败')
  } finally {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordActionBusy.value = false
  }
}

async function removeNote(id: string): Promise<void> {
  if (!window.confirm('确认删除这条笔记吗？')) return
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  try {
    await deleteNote(id)
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    await loadNotesPage(notePage.value)
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '删除笔记失败')
  } finally {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordActionBusy.value = false
  }
}

async function reportReadingProgress(pageNumber: number): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || paper.value?.status !== 'PARSED') return
  const requestToken = ++progressGeneration
  progressError.value = ''
  try {
    await patchReadingProgress(paperId, pageNumber)
  } catch {
    if (requestToken === progressGeneration && paper.value?.id === paperId && currentPage.value === pageNumber) {
      progressError.value = '阅读进度暂未保存，不影响继续阅读。'
    }
  }
}

function retryReadingProgress(): void {
  void reportReadingProgress(currentPage.value)
}

function resetRecordState(): void {
  recordPaperGeneration++
  recordActionGeneration++
  progressGeneration++
  invalidateRecordLists()
  recordActionBusy.value = false
  recordsError.value = ''
  progressError.value = ''
  highlights.value = []
  notes.value = []
  sourceHighlights.value = []
  highlightTotal.value = 0
  noteTotal.value = 0
  highlightPage.value = 1
  notePage.value = 1
  clearSourcePreview()
  pageHighlights.value = []
  pageAnnotationGeneration++
  clearPdfSelection()
  cancelNoteForm()
}

function pdfWordAt(node: Node): SVGTextElement | null {
  const element = node instanceof Element ? node : node.parentElement
  const word = element?.closest('.pdf-text-word')
  return word?.tagName.toLowerCase() === 'text' ? word as SVGTextElement : null
}

function pdfSelectionOffset(node: Node, offset: number): number | null {
  const word = pdfWordAt(node)
  if (!word || !pdfTextLayerRef.value?.contains(word)) return null
  const start = Number(word.dataset.start)
  const end = Number(word.dataset.end)
  if (!Number.isInteger(start) || !Number.isInteger(end) || end <= start) return null
  return start + Math.min(Math.max(0, offset), end - start)
}

function onPdfTextSelection(): void {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount !== 1 || selection.isCollapsed || !pdfStageRef.value) return
  const range = selection.getRangeAt(0)
  const startOffset = pdfSelectionOffset(range.startContainer, range.startOffset)
  const endOffset = pdfSelectionOffset(range.endContainer, range.endOffset)
  const content = currentContent.value
  if (startOffset === null || endOffset === null || !content) return
  let start = Math.min(startOffset, endOffset)
  let end = Math.max(startOffset, endOffset)
  while (start < end && /\s/.test(content.charAt(start))) start++
  while (end > start && /\s/.test(content.charAt(end - 1))) end--
  if (end <= start || end - start > 5000) return
  const rect = range.getBoundingClientRect()
  const stageRect = pdfStageRef.value.getBoundingClientRect()
  pdfSelection.value = {
    start,
    end,
    text: content.slice(start, end),
    x: rect.left - stageRect.left + pdfStageRef.value.scrollLeft + rect.width / 2,
    y: rect.top - stageRect.top + pdfStageRef.value.scrollTop - 8,
  }
  selectionNoteOpen.value = false
  selectionNoteContent.value = ''
}

function dismissPdfSelection(event: MouseEvent): void {
  if (event.button === 0 && pdfSelection.value) clearPdfSelection()
}

function clearPdfSelection(): void {
  pdfSelection.value = null
  selectionNoteOpen.value = false
  selectionNoteContent.value = ''
  window.getSelection()?.removeAllRanges()
}

function openPdfSelectionNote(): void {
  selectionNoteOpen.value = true
  selectionNoteContent.value = ''
}

function closePdfSelectionNote(): void {
  selectionNoteOpen.value = false
  selectionNoteContent.value = ''
}

function showSelectionNotice(message: string): void {
  selectionActionNotice.value = message
  if (selectionNoticeTimer !== null) window.clearTimeout(selectionNoticeTimer)
  selectionNoticeTimer = window.setTimeout(() => {
    selectionActionNotice.value = ''
    selectionNoticeTimer = null
  }, 2200)
}

async function loadPageAnnotations(paperId: string, pageNumber: number): Promise<void> {
  const generation = ++pageAnnotationGeneration
  try {
    const response = await listHighlights(paperId, { page_number: pageNumber, page: 1, page_size: 100 })
    if (
      generation === pageAnnotationGeneration
      && paper.value?.id === paperId
      && currentPage.value === pageNumber
    ) pageHighlights.value = response.items
  } catch {
    if (generation === pageAnnotationGeneration) pageHighlights.value = []
  }
}

async function explainPdfSelection(): Promise<void> {
  const selection = pdfSelection.value
  if (!selection || submitting.value) return
  panelTab.value = 'learning'
  const accepted = await requestLearning('EXPLAIN', selection)
  if (accepted) {
    clearPdfSelection()
    showSelectionNotice('已提交选中文字解释')
  }
}

async function applyPdfHighlight(): Promise<void> {
  const paperId = paper.value?.id
  const selection = pdfSelection.value
  const pageNumber = currentPage.value
  if (!paperId || !selection || recordActionBusy.value) return
  recordActionBusy.value = true
  try {
    await createHighlight(paperId, {
      page_number: pageNumber,
      char_start: selection.start,
      char_end: selection.end,
      color: 'YELLOW',
    })
    clearPdfSelection()
    await loadPageAnnotations(paperId, pageNumber)
    if (panelTab.value === 'records' && recordsSubTab.value === 'highlights') await loadHighlightsPage(1)
    showSelectionNotice('高光已保存')
  } catch (reason) {
    recordsError.value = recordRequestError(reason, '保存高光失败')
    showSelectionNotice(recordsError.value)
  } finally {
    recordActionBusy.value = false
  }
}

async function savePdfSelectionNote(): Promise<void> {
  const paperId = paper.value?.id
  const selection = pdfSelection.value
  const content = selectionNoteContent.value.trim()
  const pageNumber = currentPage.value
  if (!paperId || !selection || !content || recordActionBusy.value) return
  recordActionBusy.value = true
  try {
    const highlight = await createHighlight(paperId, {
      page_number: pageNumber,
      char_start: selection.start,
      char_end: selection.end,
      color: 'GREEN',
    })
    await createNote(paperId, {
      anchor_type: 'HIGHLIGHT',
      highlight_id: highlight.id,
      content,
    })
    clearPdfSelection()
    await loadPageAnnotations(paperId, pageNumber)
    if (panelTab.value === 'records' && recordsSubTab.value === 'notes') await loadNotesPage(1)
    showSelectionNotice('笔记已保存，并关联到所选原文')
  } catch (reason) {
    recordsError.value = recordRequestError(reason, '保存笔记失败')
    showSelectionNotice(recordsError.value)
  } finally {
    recordActionBusy.value = false
  }
}

function releaseOriginalPage(): void {
  if (pageImageUrl.value && typeof URL.revokeObjectURL === 'function') {
    URL.revokeObjectURL(pageImageUrl.value)
  }
  pageImageUrl.value = ''
}

async function loadOriginalPage(paperId: string, pageNumber: number): Promise<void> {
  const generation = ++pageImageGeneration
  pageImageLoading.value = true
  pageImageError.value = ''
  pageTextLayer.value = null
  pageHighlights.value = []
  clearPdfSelection()
  releaseOriginalPage()
  try {
    const [imageResult, textLayerResult] = await Promise.allSettled([
      getPaperPageImage(paperId, pageNumber),
      getPaperPageTextLayer(paperId, pageNumber),
    ])
    if (imageResult.status === 'rejected') throw imageResult.reason
    if (
      generation !== pageImageGeneration
      || paper.value?.id !== paperId
      || currentPage.value !== pageNumber
    ) return
    if (typeof URL.createObjectURL !== 'function') {
      pageImageError.value = '当前浏览器不支持显示论文页面，请更换浏览器后重试。'
      return
    }
    pageImageUrl.value = URL.createObjectURL(imageResult.value)
    pageTextLayer.value = textLayerResult.status === 'fulfilled' ? textLayerResult.value : null
    void loadPageAnnotations(paperId, pageNumber)
  } catch (error) {
    if (generation === pageImageGeneration) pageImageError.value = safeRequestError(error, '加载论文页面失败，请重试。')
  } finally {
    if (generation === pageImageGeneration) pageImageLoading.value = false
  }
}

async function initializeParsedPaper(paperId: string, generation: number): Promise<void> {
  const pageBeforeSelection = currentPage.value
  const loadedOutline = await getPaperOutline(paperId)
  if (generation !== paperGeneration || paper.value?.id !== paperId) return
  outline.value = loadedOutline
  await loadPageContent(currentPage.value)
  if (generation === paperGeneration && paper.value?.id === paperId) await loadHistory()
  if (
    generation === paperGeneration
    && paper.value?.id === paperId
    && currentPage.value === pageBeforeSelection
  ) {
    await loadOriginalPage(paperId, currentPage.value)
  }
}

function startPaperStatusPolling(paperId: string, generation: number): void {
  startPaperSharedPolling(
    () => getPaper(paperId),
    async updatedPaper => {
      if (generation !== paperGeneration || String(route.params.id || '') !== paperId) return
      paper.value = updatedPaper
      if (updatedPaper.status === 'PARSED') await initializeParsedPaper(paperId, generation)
    },
    updatedPaper => updatedPaper.status !== 'PROCESSING',
    () => {
      if (generation === paperGeneration) loadError.value = '解析状态刷新失败，请刷新页面重试。'
    },
  )
}

async function loadPaper(paperId: string): Promise<void> {
  const generation = ++paperGeneration
  contentGeneration++
  assistantGeneration++
  historyGeneration++
  pageImageGeneration++
  pageAnnotationGeneration++
  stopPolling()
  stopPaperSharedPolling()
  resetQAState()
  resetRecordState()
  releaseOriginalPage()
  paper.value = null
  outline.value = []
  selectedOutlineIndex.value = null
  pageData.value = null
  activeExplanation.value = null
  historyItems.value = []
  loadError.value = ''
  contentError.value = ''
  assistantError.value = ''
  historyError.value = ''
  pageImageError.value = ''
  pageImageLoading.value = false
  pageTextLayer.value = null
  pageHighlights.value = []
  sourceNavigator.value = null
  if (!paperId) {
    loadError.value = '论文标识无效。'
    return
  }
  try {
    const loadedPaper = await getPaper(paperId)
    if (generation !== paperGeneration || String(route.params.id || '') !== paperId) return
    currentPage.value = 1
    paper.value = loadedPaper
    if (loadedPaper.status === 'PROCESSING') {
      startPaperStatusPolling(paperId, generation)
      return
    }
    if (loadedPaper.status === 'PARSED') await initializeParsedPaper(paperId, generation)
  } catch (error) {
    if (generation === paperGeneration) loadError.value = safeRequestError(error, '加载论文阅读工作台失败，请重试。')
  }
}

function modeLabel(mode: LearningMode): string {
  if (mode === 'EXPLAIN') return '选中文字解释'
  return modes.find(item => item.value === mode)?.label || mode
}

function historyLocation(item: LearningExplanationListItem): string {
  return item.page_number ? `第 ${item.page_number} 页` : '历史解释'
}

function statusLabel(status: LearningStatus | QATurnStatus): string {
  return { PENDING: '等待中', RUNNING: '生成中', SUCCEEDED: '已完成', FAILED: '失败' }[status]
}

function conversationLabel(conversation: QAConversationListItem): string {
  return conversation.last_question_preview || '新会话'
}

function formatTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '时间未知' : date.toLocaleString('zh-CN')
}

watch(
  () => String(route.params.id || ''),
  paperId => void loadPaper(paperId),
  { immediate: true },
)

watch(currentPage, pageNumber => {
  if (paper.value?.status === 'PARSED') void loadOriginalPage(paper.value.id, pageNumber)
})

watch(panelTab, tab => {
  clearSourcePreview()
  stopQAPolling()
  qaConversationGeneration++
  qaTurnGeneration++
  qaActionGeneration++
  qaConvLoading.value = false
  qaTurnsLoading.value = false
  qaSubmitting.value = false
  qaCreatingConv.value = false
  if (tab === 'qa' && paper.value?.status === 'PARSED') {
    void loadQAConversations(qaConvPage.value)
    if (activeQAConvId.value) void loadQATurns(activeQAConvId.value)
  }
  if (tab === 'records' && paper.value?.status === 'PARSED') {
    loadActiveRecords()
  } else {
    invalidateRecordLists()
    recordActionGeneration++
    recordActionBusy.value = false
  }
})

watch(recordsSubTab, () => {
  clearSourcePreview()
  invalidateRecordLists()
  recordActionGeneration++
  recordActionBusy.value = false
  recordsError.value = ''
  cancelNoteForm()
  if (panelTab.value === 'records' && paper.value?.status === 'PARSED') loadActiveRecords()
})

onUnmounted(() => {
  paperGeneration++
  contentGeneration++
  assistantGeneration++
  historyGeneration++
  stopPolling()
  stopPaperSharedPolling()
  pageImageGeneration++
  pageAnnotationGeneration++
  if (selectionNoticeTimer !== null) window.clearTimeout(selectionNoticeTimer)
  releaseOriginalPage()
  resetQAState()
  resetRecordState()
})
</script>

<style scoped>
.reading-view { min-height: calc(100vh - 48px); display: flex; flex-direction: column; color: #25243a; background: #f2f4f8; }
.reading-header { padding: 1rem 1.25rem 0.9rem; border-bottom: 1px solid #dedee8; background: #fff; }
.paper-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; }
.workspace-label { margin: 0 0 0.25rem; color: #7a8093; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.1em; }
.reading-header h1 { min-width: 0; margin: 0; color: #171a33; font-size: 1.35rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.paper-meta { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 0.7rem; color: #686d80; font-size: 0.78rem; }
.paper-status { color: #2e7d32; font-weight: 700; }
.workspace-actions { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.9rem; }
.workspace-actions button { min-height: 34px; padding: 0.45rem 0.9rem; border-radius: 8px; font-size: 0.88rem; font-weight: 600; }
.reading-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(420px, 1fr); gap: 1px; height: calc(100vh - 195px); min-height: 680px; background: #dfe2eb; }
.paper-panel { min-width: 0; display: flex; flex-direction: column; overflow: hidden; background: #eef0f5; }
.learning-panel { min-width: 0; min-height: 0; padding: 1.1rem 1.25rem 2rem; overflow-y: auto; background: #fff; }
.learning-panel.qa-panel-active { display: flex; flex-direction: column; overflow: hidden; }
.learning-panel h3 { margin: 0.8rem 0 0.5rem; font-size: 0.95rem; }
.document-toolbar { display: flex; align-items: center; gap: 0.5rem; padding: 0.65rem 0.85rem; border-bottom: 1px solid #d9dce6; background: #fff; }
.document-toolbar button { min-width: 64px; }
.page-control { display: flex; align-items: center; gap: 0.35rem; color: #64697d; font-size: 0.82rem; }
.page-input { width: 3.6rem; padding: 0.35rem; border: 1px solid #d8d7e2; border-radius: 6px; text-align: center; }
.source-navigator { max-height: 15rem; padding: 0.75rem; border-bottom: 1px solid #d9dce6; overflow-y: auto; background: #fff; }
.source-navigator-title { margin-bottom: 0.55rem; color: #555b70; font-size: 0.78rem; font-weight: 700; }
.source-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.45rem; }
.source-options button { display: flex; min-width: 0; flex-direction: column; align-items: flex-start; gap: 0.2rem; padding: 0.55rem 0.65rem; text-align: left; }
.source-options button span { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-options button small { color: #7a8093; }
.pdf-stage { position: relative; min-height: 0; flex: 1; padding: 0.75rem; overflow: auto; background: #dfe2e8; }
.pdf-page-surface { position: relative; width: min(100%, 960px); height: auto; margin: 0 auto; background: #fff; box-shadow: 0 8px 24px rgba(30, 35, 55, 0.12); }
.paper-page-image { display: block; width: 100%; height: 100%; object-fit: fill; background: #fff; user-select: none; }
.pdf-text-layer { position: absolute; z-index: 2; inset: 0; width: 100%; height: 100%; overflow: visible; user-select: text; }
.pdf-text-word { fill: transparent; color: transparent; cursor: text; pointer-events: all; user-select: text; }
.pdf-text-word::selection { color: transparent; background: rgba(76, 91, 212, 0.35); }
.pdf-highlight { pointer-events: none; opacity: 0.42; }
.pdf-highlight-yellow { fill: #ffe66b; }
.pdf-highlight-green { fill: #75d98b; }
.pdf-highlight-blue { fill: #6eafff; }
.pdf-highlight-pink { fill: #ff8fb3; }
.selection-toolbar, .selection-note-editor { position: absolute; z-index: 8; transform: translate(-50%, -100%); border: 1px solid #2a294d; border-radius: 10px; color: #fff; background: #22213f; box-shadow: 0 8px 24px rgba(23, 26, 51, 0.25); }
.selection-toolbar { display: flex; align-items: center; gap: 0.3rem; padding: 0.35rem; white-space: nowrap; }
.selection-toolbar button, .selection-toolbar select { min-height: 30px; border-color: rgba(255, 255, 255, 0.25); color: #fff; background: #22213f; }
.selection-toolbar select option { color: #22213f; background: #fff; }
.selection-toolbar button:hover { background: #393765; }
.selection-note-editor { width: min(360px, calc(100vw - 2rem)); padding: 0.75rem; }
.selection-note-editor p { max-height: 3.2rem; margin: 0.45rem 0; overflow: hidden; color: #d8d8e8; font-size: 0.78rem; line-height: 1.4; }
.selection-note-editor textarea { box-sizing: border-box; width: 100%; padding: 0.55rem; border: 0; border-radius: 6px; resize: vertical; font: inherit; }
.selection-note-editor > div { display: flex; gap: 0.4rem; margin-top: 0.45rem; }
.selection-note-editor .submit-btn { flex: 1; padding: 0.45rem; }
.pdf-action-notice { position: sticky; z-index: 9; bottom: 1rem; width: max-content; max-width: calc(100% - 2rem); margin: 0 auto; padding: 0.55rem 0.85rem; border-radius: 999px; color: #fff; background: rgba(34, 33, 63, 0.92); box-shadow: 0 6px 18px rgba(23, 26, 51, 0.2); font-size: 0.82rem; }
.pdf-state { display: grid; height: 100%; min-height: 24rem; place-items: center; color: #74798b; background: #fff; border-radius: 8px; }
.compact-message { margin: 0; padding: 0.55rem 0.85rem; border-radius: 0; }
.not-ready { margin: 2rem auto; width: min(720px, calc(100% - 2rem)); padding: 1.25rem; border-radius: 10px; text-align: center; }
.processing-state { color: #7a5600; background: #fff7df; }
.error-state { color: #9f2424; background: #fff0f0; }
.history-list { margin: 0; padding: 0; list-style: none; }
.history-list li:hover { background: #f0f0fa; }
.history-list li.active { background: #e7e6fb; color: #23214d; }
.highlight { background: #fff08a; color: inherit; }
.highlight-notice { padding: 0.6rem; background: #fff8df; color: #7a5a00; }
.progress-warning { padding: 0.6rem; background: #fff4e5; color: #8a4b08; }
.mode-selector { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.3rem; margin-bottom: 0.7rem; }
.current-page-hint { margin: 0 0 0.65rem; color: #71768a; font-size: 0.8rem; }
button { padding: 0.4rem 0.55rem; border: 1px solid #d8d7e2; border-radius: 0.35rem; background: #fff; cursor: pointer; }
button.active, .submit-btn { border-color: #25234f; background: #25234f; color: #fff; }
button:disabled { cursor: not-allowed; opacity: 0.45; }
.submit-btn { width: 100%; padding: 0.65rem; }
.result-area, .history-section { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #dedee8; }
.result-content h4, .history-section h4 { margin: 0.85rem 0 0.4rem; }
.answer-text { white-space: pre-wrap; line-height: 1.55; }
.result-mode-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 0.8rem; margin-bottom: 0.9rem; padding: 0.75rem 0.85rem; border-left: 4px solid; border-radius: 8px; }
.result-mode-heading span { font-size: 1rem; font-weight: 800; }
.result-mode-heading small { color: #686d80; text-align: right; }
.summary-heading { border-color: #4f63c7; background: #eef1ff; }
.explain-heading { border-color: #c87b23; background: #fff5e8; }
.translation-heading { border-color: #25845b; background: #eaf8f1; }
.selection-excerpt { max-height: 8rem; margin: 0 0 0.8rem; padding: 0.7rem 0.8rem; border-left: 3px solid #c87b23; overflow-y: auto; color: #59576a; background: #fffaf2; white-space: pre-wrap; }
.explain-answer { padding: 0.75rem; border-radius: 8px; background: #fffaf2; }
.explain-points li::marker { color: #c87b23; }
.translation-content { padding: 0.9rem 1rem; border: 1px solid #d8e8df; border-radius: 8px; background: #fbfffd; color: #222b27; font-family: Georgia, 'Noto Serif SC', 'Times New Roman', serif; line-height: 1.75; }
.translation-content h2, .translation-content h3, .translation-content h4, .translation-content h5, .translation-content h6 { margin: 1.1rem 0 0.55rem; color: #17271f; line-height: 1.35; }
.translation-content h2:first-child, .translation-content h3:first-child, .translation-content h4:first-child { margin-top: 0; }
.translation-content p { margin: 0 0 0.85rem; white-space: pre-wrap; }
.translation-list-item { margin: 0.3rem 0 0.3rem 1rem; }
.key-points { padding-left: 1.25rem; }
.terms-list { display: grid; gap: 0.5rem; margin: 0; }
.term-card { padding: 0.55rem; border-radius: 0.4rem; background: #f0f0f7; }
.term-card dt { font-weight: 700; }
.term-card dd { margin: 0.25rem 0 0; color: #57566a; }
.history-list li { display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 0.25rem 0.5rem; padding: 0.5rem; border-radius: 0.35rem; cursor: pointer; font-size: 0.8rem; }
.history-list time { grid-column: 1 / 3; color: #77758d; }
.history-delete { grid-column: 3; grid-row: 1 / 3; }
.status-succeeded { color: #257335; }
.status-failed { color: #b32626; }
.status-pending, .status-running { color: #a66000; }
.error-msg { color: #a51f1f; }
.assistant-error, .not-ready, .page-error, .page-loading { padding: 1rem; }
.loading-msg, .empty-msg { color: #77758d; }
.retry-btn { color: #9f2424; border-color: #c95b5b; }
.panel-topbar { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: stretch; gap: 0.4rem; margin-bottom: 0.7rem; }
.panel-tabs { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.3rem; min-width: 0; }
.panel-exit { display: inline-flex; align-items: center; justify-content: center; min-width: 3.4rem; padding: 0.4rem 0.7rem; border: 1px solid #d8d7e2; border-radius: 0.35rem; color: #a51f1f; background: #fff; text-decoration: none; white-space: nowrap; }
.learning-exit { width: 100%; margin-top: 0.45rem; padding: 0.58rem; border-color: #b4232b; color: #fff; background: #c92f37; font-weight: 700; }
.learning-exit:hover { border-color: #921a21; background: #aa222a; }
.qa-messages { max-height: 24rem; overflow-y: auto; margin-bottom: 0.7rem; }
.qa-input-area textarea { width: 100%; padding: 0.5rem; border: 1px solid #d8d7e2; border-radius: 0.35rem; resize: vertical; font-family: inherit; font-size: 0.85rem; }
.qa-input-actions { display: flex; gap: 0.4rem; margin-top: 0.4rem; align-items: center; }
.qa-input-actions select { padding: 0.35rem; border: 1px solid #d8d7e2; border-radius: 0.35rem; }
.qa-input-actions .submit-btn { flex: 1; }
.qa-chat-shell { display: flex; min-height: 0; flex: 1; flex-direction: column; overflow: hidden; border: 1px solid #dedee8; border-radius: 14px; background: #f7f8fb; }
.qa-chat-header { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; padding: 0.75rem 0.9rem; border-bottom: 1px solid #e2e3ea; background: #fff; }
.qa-chat-header h3 { margin: 0; color: #1b1c32; font-size: 1rem; }
.qa-chat-header small { color: #85899a; }
.qa-session-actions { display: flex; align-items: center; gap: 0.35rem; }
.qa-session-actions select { max-width: 190px; padding: 0.4rem; border: 1px solid #d8d7e2; border-radius: 7px; color: #34364b; background: #fff; }
.qa-session-actions .delete-btn { margin: 0; padding: 0.4rem 0.55rem; }
.qa-banner { margin: 0.55rem 0.75rem 0; padding: 0.55rem; border-radius: 7px; background: #fff1f1; }
.qa-chat-shell .qa-messages { width: auto; height: auto; min-height: 0; max-height: none; flex: 1 1 0; margin: 0; padding: 1rem; overflow-y: auto; overscroll-behavior: contain; scroll-behavior: smooth; }
.qa-row, .qa-welcome { display: flex; align-items: flex-start; gap: 0.55rem; margin-bottom: 1rem; }
.qa-row.user-row { justify-content: flex-end; }
.qa-avatar { display: grid; width: 32px; height: 32px; flex: 0 0 32px; place-items: center; border-radius: 50%; font-size: 0.72rem; font-weight: 800; }
.assistant-avatar { color: #fff; background: #292750; }
.user-avatar { color: #315d3f; background: #dff2e5; }
.qa-bubble { max-width: min(78%, 620px); padding: 0.7rem 0.85rem; border-radius: 14px; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 0.88rem; line-height: 1.6; box-shadow: 0 1px 2px rgba(23, 26, 51, 0.06); }
.assistant-bubble { border-top-left-radius: 4px; color: #303246; background: #fff; }
.user-bubble { border-top-right-radius: 4px; color: #fff; background: #34315f; }
.assistant-bubble p { margin: 0; white-space: pre-wrap; }
.qa-center-state { padding: 2rem; text-align: center; }
.typing-indicator { display: flex; align-items: center; gap: 0.25rem; min-height: 20px; }
.typing-indicator span { width: 6px; height: 6px; border-radius: 50%; background: #85899a; animation: typing-bounce 1.1s infinite ease-in-out; }
.typing-indicator span:nth-child(2) { animation-delay: 0.15s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.3s; }
@keyframes typing-bounce { 0%, 60%, 100% { transform: translateY(0); opacity: 0.45; } 30% { transform: translateY(-4px); opacity: 1; } }
.qa-chat-shell .qa-input-area { z-index: 2; flex: 0 0 auto; padding: 0.75rem; border-top: 1px solid #e2e3ea; background: #fff; }
.qa-composer { display: flex; align-items: flex-end; gap: 0.45rem; padding: 0.4rem; border: 1px solid #cfd1dc; border-radius: 16px; background: #fff; box-shadow: 0 2px 10px rgba(23, 26, 51, 0.06); }
.qa-composer:focus-within { border-color: #4a477e; box-shadow: 0 0 0 3px rgba(74, 71, 126, 0.1); }
.qa-composer select { align-self: center; padding: 0.35rem; border: 0; color: #6d7081; background: transparent; }
.qa-composer textarea { box-sizing: border-box; width: auto; min-height: 42px; max-height: 130px; flex: 1; padding: 0.55rem 0.2rem; border: 0; outline: 0; resize: none; font: inherit; line-height: 1.45; }
.qa-send-button { display: grid; width: 36px; height: 36px; flex: 0 0 36px; place-items: center; padding: 0; border: 0; border-radius: 50%; color: #fff; background: #292750; font-size: 1.1rem; font-weight: 800; }
.qa-input-tip { display: block; margin-top: 0.35rem; color: #9295a4; text-align: center; font-size: 0.7rem; }
.records-sub-tabs { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.3rem; margin-bottom: 0.7rem; }
.record-actions { display: flex; gap: .35rem; margin-bottom: 0.5rem; }
.record-actions input { min-width: 0; flex: 1; padding: .4rem; border: 1px solid #d8d7e2; border-radius: .35rem; }
.record-list { margin: 0; padding: 0; list-style: none; }
.record-item { padding: 0.5rem; border-radius: 0.35rem; margin-bottom: 0.3rem; background: #f7f7fb; font-size: 0.84rem; }
.record-meta { display: block; color: #77758d; font-size: 0.75rem; margin-top: 0.2rem; }
.delete-btn { padding: 0.15rem 0.4rem; border: 1px solid #d8d7e2; border-radius: 0.25rem; background: #fff; color: #a51f1f; cursor: pointer; font-size: 0.75rem; margin-top: 0.2rem; }
.hl-color-yellow { background: #fff08a; }
.hl-color-green { background: #b5f5b5; }
.hl-color-blue { background: #b3d4fc; }
.hl-color-pink { background: #ffc0cb; }
.record-locator { max-width: 100%; padding: 0; border: 0; text-align: left; background: transparent; }
.record-pagination { display: flex; align-items: center; justify-content: space-between; margin-top: .6rem; }
.hl-selection-hint { padding: 0.5rem; background: #fff8df; border-radius: 0.35rem; color: #7a5a00; font-size: 0.84rem; margin-bottom: 0.5rem; }
.selection-source { max-height: 14rem; margin-bottom: 0.5rem; padding: 0.75rem; border: 1px solid #d8dbe6; border-radius: 0.4rem; overflow-y: auto; white-space: pre-wrap; color: #30354a; background: #fafbfe; font-family: Georgia, 'Times New Roman', serif; font-size: 0.86rem; line-height: 1.65; user-select: text; }
.hl-confirm-bar { padding: 0.5rem; background: #f0f0f7; border-radius: 0.35rem; margin-bottom: 0.5rem; }
.hl-preview { display: block; font-size: 0.84rem; margin-bottom: 0.3rem; max-height: 3rem; overflow: hidden; }
.hl-confirm-bar select { padding: 0.25rem; border: 1px solid #d8d7e2; border-radius: 0.25rem; margin-right: 0.3rem; }
.note-form { padding: 0.5rem; background: #f7f7fb; border-radius: 0.35rem; margin-bottom: 0.5rem; }
.note-form select, .note-form input { width: 100%; padding: 0.35rem; border: 1px solid #d8d7e2; border-radius: 0.25rem; margin-bottom: 0.3rem; font-size: 0.84rem; box-sizing: border-box; }
.note-form textarea { width: 100%; padding: 0.35rem; border: 1px solid #d8d7e2; border-radius: 0.25rem; resize: vertical; font-family: inherit; font-size: 0.84rem; margin-bottom: 0.3rem; box-sizing: border-box; }
.note-form-actions { display: flex; gap: 0.3rem; }
.note-anchor { display: inline-block; padding: 0.1rem 0.3rem; border-radius: 0.2rem; background: #ececf3; font-size: 0.7rem; margin-right: 0.3rem; }
.note-content { margin: 0.3rem 0; white-space: pre-wrap; line-height: 1.4; }
@media (max-width: 1080px) {
  .reading-layout { grid-template-columns: 1fr; }
  .reading-layout { height: auto; min-height: 0; }
  .paper-panel { height: 72vh; min-height: 620px; }
  .learning-panel { overflow: visible; }
  .learning-panel.qa-panel-active { height: 72vh; min-height: 620px; overflow: hidden; }
}
@media (max-width: 700px) {
  .paper-heading { align-items: flex-start; flex-direction: column; }
  .paper-meta { justify-content: flex-start; }
  .document-toolbar { flex-wrap: wrap; }
  .source-options { grid-template-columns: 1fr; }
  .reading-layout { grid-template-columns: minmax(0, 1fr); }
}
</style>
