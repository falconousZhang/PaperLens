<template>
  <div v-if="paper" class="reading-view">
    <header class="reading-header">
      <router-link :to="{ name: 'paper-detail', params: { id: paper.id } }" class="back-link">&larr; 返回详情</router-link>
      <h2>{{ paper.title }}</h2>
    </header>

    <div v-if="paper.status !== 'PARSED'" class="not-ready">论文尚未解析完成，暂时不能开始阅读。</div>
    <div v-else class="reading-layout">
      <aside class="sidebar">
        <h3>章节目录</h3>
        <p v-if="!sections.length" class="empty-msg">暂无章节</p>
        <ul v-else class="section-list">
          <li
            v-for="section in sections"
            :key="section.id"
            :class="{ active: scopeType === 'SECTION' && selectedSectionId === section.id }"
            :style="{ paddingLeft: `${0.5 + Math.min(Math.max(section.level, 1), 6) * 0.5}rem` }"
            @click="selectSection(section)"
          >
            <span>{{ section.title || section.section_type }}</span>
            <span class="section-pages">{{ pageRange(section) }}</span>
          </li>
        </ul>

        <h3>页面</h3>
        <div class="page-nav">
          <button aria-label="上一页" :disabled="currentPage <= 1" @click="selectPage(currentPage - 1)">&lt;</button>
          <input
            aria-label="页码"
            class="page-input"
            type="number"
            :value="currentPage"
            min="1"
            :max="paper.page_count || 1"
            @change="selectPage(Number(($event.target as HTMLInputElement).value))"
          />
          <span>/ {{ paper.page_count || 1 }}</span>
          <button aria-label="下一页" :disabled="currentPage >= (paper.page_count || 1)" @click="selectPage(currentPage + 1)">&gt;</button>
        </div>

        <h3>证据</h3>
        <p v-if="!evidences.length" class="empty-msg">暂无证据</p>
        <ul v-else class="evidence-list">
          <li
            v-for="evidence in evidences"
            :key="evidence.id"
            :class="{ active: scopeType === 'EVIDENCE' && selectedEvidenceId === evidence.id }"
            @click="selectEvidence(evidence)"
          >
            <span class="ev-type">{{ evidence.evidence_type }}</span>
            <span class="ev-page">p.{{ evidence.page_number }}</span>
            <span class="ev-text">{{ excerpt(evidence.quoted_text) }}</span>
          </li>
        </ul>
      </aside>

      <main class="content-panel">
        <div v-if="contentError" class="error-msg">{{ contentError }}</div>
        <div v-else-if="contentLoading" class="loading-msg">加载正文中...</div>
        <div v-else-if="currentContent" ref="contentRef" class="content-text">
          <template v-if="highlightInfo">
            <span>{{ highlightInfo.before }}</span><mark ref="highlightRef" class="highlight">{{ highlightInfo.highlight }}</mark><span>{{ highlightInfo.after }}</span>
          </template>
          <template v-else>{{ currentContent }}</template>
        </div>
        <div v-else class="empty-msg">当前范围没有可显示的正文</div>
        <div v-if="highlightNotice" class="highlight-notice">{{ highlightNotice }}</div>
        <div v-if="progressError" class="progress-warning">{{ progressError }} <button @click="retryReadingProgress">重试记录进度</button></div>
      </main>

      <aside class="learning-panel">
        <div class="panel-tabs">
          <button :class="{ active: panelTab === 'learning' }" @click="panelTab = 'learning'">学习解释</button>
          <button :class="{ active: panelTab === 'qa' }" @click="panelTab = 'qa'">论文问答</button>
          <button :class="{ active: panelTab === 'records' }" @click="panelTab = 'records'">学习记录</button>
        </div>

        <template v-if="panelTab === 'learning'">
        <h3>学习助手</h3>

        <div class="scope-selector" aria-label="学习范围">
          <button :class="{ active: scopeType === 'SECTION' }" :disabled="!selectedSectionId" @click="activateSectionScope">当前章节</button>
          <button :class="{ active: scopeType === 'PAGE' }" @click="selectPage(currentPage)">当前页面</button>
          <button :class="{ active: scopeType === 'EVIDENCE' }" :disabled="!selectedEvidenceId" @click="activateEvidenceScope">已选证据</button>
        </div>

        <div class="mode-selector" aria-label="学习方式">
          <button v-for="mode in modes" :key="mode.value" :class="{ active: selectedMode === mode.value }" @click="selectedMode = mode.value">
            {{ mode.label }}
          </button>
        </div>

        <div class="lang-selector" aria-label="输出语言">
          <button :class="{ active: outputLang === 'zh' }" @click="outputLang = 'zh'">中文</button>
          <button :class="{ active: outputLang === 'en' }" @click="outputLang = 'en'">English</button>
        </div>

        <button class="submit-btn" :disabled="!canSubmit || submitting" @click="submitLearning">
          {{ submitting ? '请求中...' : '生成学习解释' }}
        </button>
        <div v-if="assistantError" class="error-msg assistant-error">{{ assistantError }}</div>

        <div v-if="activeExplanation" class="result-area">
          <div v-if="isProcessing(activeExplanation.status)" class="loading-msg">生成中...</div>
          <div v-else-if="activeExplanation.status === 'FAILED'" class="error-msg">
            <p>{{ activeExplanation.error_message || '学习解释生成失败，请稍后重试' }}</p>
            <button class="retry-btn" @click="retryExplanation">重新生成</button>
          </div>
          <div v-else-if="activeExplanation.status === 'SUCCEEDED'" class="result-content">
            <h4>回答</h4>
            <p class="answer-text">{{ activeExplanation.answer }}</p>

            <h4>要点</h4>
            <ul class="key-points">
              <li v-for="(point, index) in activeExplanation.key_points || []" :key="index">{{ point }}</li>
            </ul>

            <h4>术语</h4>
            <dl class="terms-list">
              <div v-for="term in activeExplanation.terms || []" :key="term.term" class="term-card">
                <dt>{{ term.term }}</dt>
                <dd>{{ term.explanation }}</dd>
              </div>
            </dl>

            <h4>原文引用</h4>
            <div class="citations-list">
              <button
                v-for="citation in activeExplanation.citations || []"
                :key="citation.evidence_id"
                class="citation-link"
                @click="goToCitation(citation)"
              >
                [{{ citation.sequence }}] 第 {{ citation.page_number }} 页
              </button>
            </div>
          </div>
        </div>

        <section class="history-section">
          <h4>解释历史</h4>
          <div v-if="historyLoading" class="loading-msg">加载历史中...</div>
          <div v-else-if="historyError" class="error-msg">
            {{ historyError }}
            <button class="retry-btn" @click="loadHistory(historyPage)">重试</button>
          </div>
          <ul v-else-if="historyItems.length" class="history-list">
            <li
              v-for="item in historyItems"
              :key="item.id"
              :class="{ active: activeExplanation?.id === item.id }"
              @click="loadExplanation(item.id)"
            >
              <span>{{ modeLabel(item.mode) }} · {{ scopeLabel(item.scope_type) }}</span>
              <span class="hist-status" :class="`status-${item.status.toLowerCase()}`">{{ statusLabel(item.status) }}</span>
              <time>{{ formatTime(item.created_at) }}</time>
            </li>
          </ul>
          <p v-else class="empty-msg">暂无记录</p>
          <div class="history-pagination">
            <button :disabled="historyPage <= 1 || historyLoading" @click="loadHistory(historyPage - 1)">上一页</button>
            <span>{{ historyPage }} / {{ historyTotalPages }}</span>
            <button :disabled="historyPage >= historyTotalPages || historyLoading" @click="loadHistory(historyPage + 1)">下一页</button>
          </div>
        </section>
        </template>

        <template v-if="panelTab === 'qa'">
        <h3>论文问答</h3>

        <div class="qa-conversations">
          <button class="submit-btn" @click="createNewQAConversation" :disabled="qaCreatingConv">新建会话</button>
          <div v-if="qaConvLoading" class="loading-msg">加载会话中...</div>
          <div v-else-if="qaConvError" class="error-msg">
            {{ qaConvError }}
            <button class="retry-btn" @click="loadQAConversations(qaConvPage)">重试</button>
          </div>
          <ul v-else-if="qaConversations.length" class="conv-list">
            <li
              v-for="conv in qaConversations"
              :key="conv.id"
              :class="{ active: activeQAConvId === conv.id }"
              @click="selectQAConversation(conv.id)"
            >
              <span>{{ conversationLabel(conv) }}</span>
              <small>{{ conv.turn_count }} 轮 · {{ conv.last_status ? statusLabel(conv.last_status) : '未提问' }}</small>
              <time>{{ formatTime(conv.updated_at) }}</time>
            </li>
          </ul>
          <p v-else class="empty-msg">暂无会话</p>
          <div class="history-pagination">
            <button :disabled="qaConvPage <= 1 || qaConvLoading" @click="loadQAConversations(qaConvPage - 1)">上一页</button>
            <span>{{ qaConvPage }} / {{ qaConvTotalPages }}</span>
            <button :disabled="qaConvPage >= qaConvTotalPages || qaConvLoading" @click="loadQAConversations(qaConvPage + 1)">下一页</button>
          </div>
        </div>

        <div v-if="activeQAConvId" class="qa-turns-area">
          <div v-if="qaTurnsLoading" class="loading-msg">加载对话中...</div>
          <div v-else-if="qaTurnsError" class="error-msg">
            {{ qaTurnsError }}
            <button class="retry-btn" @click="loadQATurns(activeQAConvId, qaTurnPage)">重试</button>
          </div>
          <div v-else class="qa-messages">
            <div v-for="turn in qaTurns" :key="turn.id" class="qa-message">
              <div class="qa-question">
                <strong>Q:</strong> {{ turn.question }}
              </div>
              <div v-if="turn.status === 'PENDING' || turn.status === 'RUNNING'" class="loading-msg">生成中...</div>
              <div v-else-if="turn.status === 'FAILED'" class="error-msg">
                {{ turn.error_message || '论文问答生成失败，请稍后重试' }}
                <button class="retry-btn" :disabled="qaSubmitting || qaHasActiveTurn" @click="retryQATurn(turn)">重新提问</button>
              </div>
              <div v-else-if="turn.status === 'SUCCEEDED'" class="qa-answer">
                <p :class="{ 'not-grounded': turn.grounded === false }">
                  <strong>A:</strong> {{ turn.answer }}
                  <span v-if="turn.grounded === false" class="grounded-badge not-grounded-badge">当前论文证据不足</span>
                  <span v-else class="grounded-badge grounded-badge">有论文依据</span>
                </p>
                <div v-if="turn.citations?.length" class="citations-list">
                  <button
                    v-for="citation in turn.citations"
                    :key="citation.evidence_id"
                    class="citation-link"
                    @click="goToQACitation(citation)"
                  >
                    [{{ citation.sequence }}] 第 {{ citation.page_number }} 页
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div class="history-pagination qa-turn-pagination">
            <button :disabled="qaTurnPage <= 1 || qaTurnsLoading" @click="loadQATurns(activeQAConvId, qaTurnPage - 1)">上一页</button>
            <span>{{ qaTurnPage }} / {{ qaTurnTotalPages }}</span>
            <button :disabled="qaTurnPage >= qaTurnTotalPages || qaTurnsLoading" @click="loadQATurns(activeQAConvId, qaTurnPage + 1)">下一页</button>
          </div>

          <div class="qa-input-area">
            <div v-if="qaTurnError" class="error-msg">{{ qaTurnError }}</div>
            <textarea
              v-model="qaQuestion"
              placeholder="输入关于本论文的问题..."
              rows="3"
              maxlength="2000"
              :disabled="qaSubmitting || qaHasActiveTurn"
              @keydown.ctrl.enter="submitQATurn"
              @keydown.meta.enter="submitQATurn"
            ></textarea>
            <div class="qa-input-actions">
              <select v-model="qaOutputLang" :disabled="qaSubmitting || qaHasActiveTurn">
                <option value="zh">中文</option>
                <option value="en">English</option>
              </select>
              <button class="submit-btn" :disabled="!qaQuestion.trim() || qaSubmitting || qaHasActiveTurn" @click="submitQATurn">
                {{ qaSubmitting ? '请求中...' : '提问' }}
              </button>
            </div>
          </div>
        </div>
        </template>

        <template v-if="panelTab === 'records'">
        <h3>学习记录</h3>

        <div class="records-sub-tabs">
          <button :class="{ active: recordsSubTab === 'highlights' }" @click="recordsSubTab = 'highlights'">高亮</button>
          <button :class="{ active: recordsSubTab === 'bookmarks' }" @click="recordsSubTab = 'bookmarks'">书签</button>
          <button :class="{ active: recordsSubTab === 'notes' }" @click="recordsSubTab = 'notes'">笔记</button>
          <button :class="{ active: recordsSubTab === 'cards' }" @click="recordsSubTab = 'cards'">知识卡</button>
        </div>

        <template v-if="recordsSubTab === 'highlights'">
          <div class="record-actions">
            <button class="submit-btn" :disabled="scopeType !== 'PAGE' || !currentContent || recordActionBusy" @click="startHighlightSelection">新建高亮</button>
          </div>
          <p v-if="scopeType !== 'PAGE'" class="empty-msg">切换到“当前页面”后才能创建高亮。</p>
          <div v-if="hlSelectionActive" class="hl-selection-hint">请在正文中选择文本，然后点击"确认高亮"</div>
          <div v-if="hlSelectionActive && hlSelectionRange" class="hl-confirm-bar">
            <span class="hl-preview">{{ hlSelectionRange.text }}</span>
            <select v-model="hlColor">
              <option value="YELLOW">黄色</option>
              <option value="GREEN">绿色</option>
              <option value="BLUE">蓝色</option>
              <option value="PINK">粉色</option>
            </select>
            <button class="submit-btn" :disabled="recordActionBusy" @click="confirmHighlight">确认高亮</button>
            <button @click="cancelHighlightSelection">取消</button>
          </div>
          <div v-if="recordsLoading" class="loading-msg">加载中...</div>
          <div v-else-if="recordsError" class="error-msg">{{ recordsError }} <button @click="loadActiveRecords">重试</button></div>
          <ul v-else-if="highlights.length" class="record-list">
            <li v-for="hl in highlights" :key="hl.id" class="record-item">
              <button class="record-locator" @click="locateSavedHighlight(hl)"><mark :class="'hl-color-' + hl.color.toLowerCase()">{{ hl.quoted_text }}</mark></button>
              <span class="record-meta">p.{{ hl.page_number }} · {{ hl.color }}</span>
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

        <template v-if="recordsSubTab === 'bookmarks'">
          <div class="record-actions">
            <input v-model="bookmarkLabel" maxlength="100" placeholder="书签标签（可选）" />
            <button class="submit-btn" :disabled="recordActionBusy || scopeType !== 'PAGE'" @click="addBookmark">收藏当前页</button>
          </div>
          <div v-if="recordsLoading" class="loading-msg">加载中...</div>
          <div v-else-if="recordsError" class="error-msg">{{ recordsError }} <button @click="loadActiveRecords">重试</button></div>
          <ul v-else-if="bookmarks.length" class="record-list">
            <li v-for="bm in bookmarks" :key="bm.id" class="record-item">
              <span>第 {{ bm.page_number }} 页</span>
              <span v-if="bm.label" class="record-meta">{{ bm.label }}</span>
              <button class="delete-btn" :disabled="recordActionBusy" @click="removeBookmark(bm.id)">删除</button>
            </li>
          </ul>
          <p v-else class="empty-msg">暂无书签</p>
          <div v-if="bookmarkTotal > 20" class="record-pagination">
            <button :disabled="bookmarkPage <= 1" @click="goRecordPage(bookmarkPage - 1)">上一页</button>
            <span>{{ bookmarkPage }} / {{ Math.ceil(bookmarkTotal / 20) }}</span>
            <button :disabled="bookmarkPage >= Math.ceil(bookmarkTotal / 20)" @click="goRecordPage(bookmarkPage + 1)">下一页</button>
          </div>
        </template>

        <template v-if="recordsSubTab === 'notes'">
          <div class="record-actions">
            <button class="submit-btn" :disabled="recordActionBusy" @click="startCreateNote">新建笔记</button>
          </div>
          <div v-if="showNoteForm" class="note-form">
            <select v-model="noteAnchorType" :disabled="Boolean(editingNoteId)">
              <option value="PAPER">论文级</option>
              <option value="PAGE">页面级</option>
              <option value="HIGHLIGHT">高亮级</option>
            </select>
            <select v-if="noteAnchorType === 'HIGHLIGHT'" v-model="noteHighlightId" :disabled="Boolean(editingNoteId)">
              <option value="">选择高亮</option>
              <option v-for="hl in sourceHighlights" :key="hl.id" :value="hl.id">{{ hl.quoted_text.slice(0, 30) }}</option>
            </select>
            <textarea v-model="noteContent" rows="4" maxlength="20000" placeholder="输入笔记内容..."></textarea>
            <div class="note-form-actions">
              <button class="submit-btn" :disabled="recordActionBusy" @click="submitNote">{{ editingNoteId ? '保存修改' : '保存' }}</button>
              <button @click="cancelNoteForm">取消</button>
            </div>
          </div>
          <div v-if="recordsLoading" class="loading-msg">加载中...</div>
          <div v-else-if="recordsError" class="error-msg">{{ recordsError }} <button @click="loadActiveRecords">重试</button></div>
          <ul v-else-if="notes.length" class="record-list">
            <li v-for="n in notes" :key="n.id" class="record-item">
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

        <template v-if="recordsSubTab === 'cards'">
          <div class="record-actions">
            <button class="submit-btn" :disabled="recordActionBusy" @click="startCreateCard">新建知识卡</button>
          </div>
          <div v-if="showCardForm" class="card-form">
            <select v-model="cardSourceType" :disabled="Boolean(editingCardId)">
              <option value="">无来源</option>
              <option value="note">来自笔记</option>
              <option value="highlight">来自高亮</option>
            </select>
            <select v-if="cardSourceType === 'note'" v-model="cardSourceNoteId" :disabled="Boolean(editingCardId)">
              <option value="">选择笔记</option>
              <option v-for="n in sourceNotes" :key="n.id" :value="n.id">{{ n.content.slice(0, 30) }}</option>
            </select>
            <select v-if="cardSourceType === 'highlight'" v-model="cardSourceHighlightId" :disabled="Boolean(editingCardId)">
              <option value="">选择高亮</option>
              <option v-for="hl in sourceHighlights" :key="hl.id" :value="hl.id">{{ hl.quoted_text.slice(0, 30) }}</option>
            </select>
            <input v-model="cardFront" placeholder="正面（问题）" maxlength="2000" />
            <textarea v-model="cardBack" rows="3" maxlength="10000" placeholder="背面（答案）"></textarea>
            <div class="note-form-actions">
              <button class="submit-btn" :disabled="recordActionBusy" @click="submitCard">{{ editingCardId ? '保存修改' : '保存' }}</button>
              <button @click="cancelCardForm">取消</button>
            </div>
          </div>
          <div v-if="recordsLoading" class="loading-msg">加载中...</div>
          <div v-else-if="recordsError" class="error-msg">{{ recordsError }} <button @click="loadActiveRecords">重试</button></div>
          <ul v-else-if="cards.length" class="record-list">
            <li v-for="c in cards" :key="c.id" class="record-item card-item">
              <div class="card-front"><strong>Q:</strong> {{ c.front }}</div>
              <div class="card-back"><strong>A:</strong> {{ c.back }}</div>
              <div class="card-meta">
                <span :class="'mastery-' + c.mastery_status.toLowerCase()">{{ masteryLabel(c.mastery_status) }}</span>
                <span v-if="c.archived" class="archived-badge">已归档</span>
              </div>
              <div class="card-actions">
                <select :value="c.mastery_status" @change="updateCardMastery(c.id, ($event.target as HTMLSelectElement).value)">
                  <option value="NEW">新</option>
                  <option value="LEARNING">学习中</option>
                  <option value="MASTERED">已掌握</option>
                </select>
                <button :disabled="recordActionBusy" @click="startEditCard(c)">编辑</button>
                <button :disabled="recordActionBusy" @click="toggleCardArchive(c)">{{ c.archived ? '取消归档' : '归档' }}</button>
                <button class="delete-btn" :disabled="recordActionBusy" @click="removeCard(c.id)">删除</button>
              </div>
            </li>
          </ul>
          <p v-else class="empty-msg">暂无知识卡</p>
          <div v-if="cardTotal > 20" class="record-pagination">
            <button :disabled="cardPage <= 1" @click="goRecordPage(cardPage - 1)">上一页</button>
            <span>{{ cardPage }} / {{ Math.ceil(cardTotal / 20) }}</span>
            <button :disabled="cardPage >= Math.ceil(cardTotal / 20)" @click="goRecordPage(cardPage + 1)">下一页</button>
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
  createBookmark,
  createHighlight,
  createKnowledgeCard,
  createLearningExplanation,
  createNote,
  createQAConversation,
  createQATurn,
  deleteBookmark,
  deleteHighlight,
  deleteKnowledgeCard,
  deleteNote,
  getLearningExplanation,
  getQAConversation,
  getQATurn,
  getPage,
  getPaper,
  listBookmarks,
  listEvidences,
  listHighlights,
  listKnowledgeCards,
  listLearningExplanations,
  listNotes,
  listQAConversations,
  listSections,
  patchKnowledgeCard,
  patchNote,
  patchReadingProgress,
  type AnchorType,
  type BookmarkResponse,
  type HighlightColor,
  type HighlightResponse,
  type KnowledgeCardResponse,
  type MasteryStatus,
  type NoteResponse,

  type EvidenceItem,
  type LearningCitationItem,
  type LearningExplanationListItem,
  type LearningExplanationResponse,
  type LearningMode,
  type LearningScopeType,
  type LearningStatus,
  type PageDetail,
  type PaperDetail,
  type QACitationItem,
  type QAConversationListItem,
  type QATurnStatus,
  type QATurnResponse,
  type SectionItem,
} from '../api'
import { resolveTextSelection } from '../utils/textSelection'

const route = useRoute()

const paper = ref<PaperDetail | null>(null)
const sections = ref<SectionItem[]>([])
const evidences = ref<EvidenceItem[]>([])
const pageData = ref<PageDetail | null>(null)
const loadError = ref('')
const contentError = ref('')
const contentLoading = ref(false)
const progressError = ref('')
const assistantError = ref('')
const historyError = ref('')

const scopeType = ref<LearningScopeType>('SECTION')
const selectedSectionId = ref<string | null>(null)
const currentPage = ref(1)
const selectedEvidenceId = ref<string | null>(null)
const citationTarget = ref<LearningCitationItem | null>(null)
const selectedMode = ref<LearningMode>('SUMMARY')
const outputLang = ref<'zh' | 'en'>('zh')
const submitting = ref(false)

const activeExplanation = ref<LearningExplanationResponse | null>(null)
const historyItems = ref<LearningExplanationListItem[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyLoading = ref(false)


const qaConversations = ref<QAConversationListItem[]>([])
const qaConvTotal = ref(0)
const qaConvPage = ref(1)
const qaConvLoading = ref(false)
const activeQAConvId = ref<string | null>(null)
const qaTurns = ref<QATurnResponse[]>([])
const qaTurnTotal = ref(0)
const qaTurnPage = ref(1)
const qaTurnsLoading = ref(false)
const qaTurnsError = ref('')
const qaQuestion = ref('')
const qaOutputLang = ref<'zh' | 'en'>('zh')
const qaSubmitting = ref(false)
const qaCreatingConv = ref(false)
const qaConvError = ref('')
const qaTurnError = ref('')

const panelTab = ref<'learning' | 'qa' | 'records'>('learning')
const recordsSubTab = ref<'highlights' | 'bookmarks' | 'notes' | 'cards'>('highlights')
const recordsLoading = ref(false)
const recordsError = ref('')
const highlights = ref<HighlightResponse[]>([])
const bookmarks = ref<BookmarkResponse[]>([])
const notes = ref<NoteResponse[]>([])
const cards = ref<KnowledgeCardResponse[]>([])
const sourceHighlights = ref<HighlightResponse[]>([])
const sourceNotes = ref<NoteResponse[]>([])
const highlightTotal = ref(0)
const bookmarkTotal = ref(0)
const noteTotal = ref(0)
const cardTotal = ref(0)
const highlightPage = ref(1)
const bookmarkPage = ref(1)
const notePage = ref(1)
const cardPage = ref(1)
const recordActionBusy = ref(false)
const hlSelectionActive = ref(false)
const hlSelectionRange = ref<{ start: number; end: number; text: string } | null>(null)
const hlColor = ref<HighlightColor>('YELLOW')
const bookmarkLabel = ref('')
const showNoteForm = ref(false)
const editingNoteId = ref<string | null>(null)
const noteAnchorType = ref<AnchorType>('PAPER')
const noteHighlightId = ref('')
const noteContent = ref('')
const showCardForm = ref(false)
const editingCardId = ref<string | null>(null)
const cardSourceType = ref<'' | 'note' | 'highlight'>('')
const cardSourceNoteId = ref('')
const cardSourceHighlightId = ref('')
const cardFront = ref('')
const cardBack = ref('')
let qaPollTimer: ReturnType<typeof setTimeout> | null = null
let qaPaperGeneration = 0
let qaConversationGeneration = 0
let qaTurnGeneration = 0
let qaActionGeneration = 0
let qaPollGeneration = 0
let recordPaperGeneration = 0
let highlightGeneration = 0
let bookmarkGeneration = 0
let noteGeneration = 0
let cardGeneration = 0
let recordActionGeneration = 0
let progressGeneration = 0
const savedHighlightTarget = ref<HighlightResponse | null>(null)

const contentRef = ref<HTMLElement | null>(null)
const highlightRef = ref<HTMLElement | null>(null)
let pollTimer: ReturnType<typeof setTimeout> | null = null
let paperGeneration = 0
let contentGeneration = 0
let assistantGeneration = 0
let historyGeneration = 0
let pollGeneration = 0

const modes = [
  { value: 'SUMMARY' as LearningMode, label: '总结' },
  { value: 'EXPLAIN' as LearningMode, label: '通俗解释' },
  { value: 'TRANSLATE' as LearningMode, label: '翻译' },
]

const canSubmit = computed(() => {
  if (scopeType.value === 'SECTION') return Boolean(selectedSectionId.value)
  if (scopeType.value === 'PAGE') return currentPage.value >= 1
  return Boolean(selectedEvidenceId.value)
})

const currentContent = computed(() => {
  if (scopeType.value === 'SECTION') {
    return sections.value.find(item => item.id === selectedSectionId.value)?.text_content || null
  }
  return pageData.value?.normalized_text_content || pageData.value?.text_content || null
})

const selectedHighlight = computed(() => {
  if (scopeType.value === 'PAGE' && savedHighlightTarget.value) return savedHighlightTarget.value
  if (scopeType.value !== 'EVIDENCE' || !selectedEvidenceId.value) return null
  if (citationTarget.value?.evidence_id === selectedEvidenceId.value) return citationTarget.value
  return evidences.value.find(item => item.id === selectedEvidenceId.value) || null
})

const highlightInfo = computed(() => {
  const target = selectedHighlight.value
  const text = currentContent.value
  if (!target || !text || target.char_start === null || target.char_end === null) return null
  if (target.char_start < 0 || target.char_end > text.length || target.char_start >= target.char_end) return null
  const highlighted = text.slice(target.char_start, target.char_end)
  if (highlighted !== target.quoted_text) return null
  return {
    before: text.slice(0, target.char_start),
    highlight: highlighted,
    after: text.slice(target.char_end),
  }
})

const highlightNotice = computed(() => {
  if (!selectedHighlight.value || contentLoading.value) return ''
  return highlightInfo.value ? '' : '原文位置已变化，无法可靠高亮；已切换到引用所在页面。'
})

const historyTotalPages = computed(() => Math.max(1, Math.ceil(historyTotal.value / 20)))
const qaConvTotalPages = computed(() => Math.max(1, Math.ceil(qaConvTotal.value / 20)))
const qaTurnTotalPages = computed(() => Math.max(1, Math.ceil(qaTurnTotal.value / 20)))
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
  if (status === undefined) return '网络连接失败，请稍后重试。'
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

function selectSection(section: SectionItem): void {
  clearAssistant()
  scopeType.value = 'SECTION'
  selectedSectionId.value = section.id
  selectedEvidenceId.value = null
  citationTarget.value = null
  savedHighlightTarget.value = null
  if (section.start_page) currentPage.value = section.start_page
}

function activateSectionScope(): void {
  const section = sections.value.find(item => item.id === selectedSectionId.value) || sections.value[0]
  if (section) selectSection(section)
}

async function selectPage(pageNumber: number): Promise<void> {
  if (!Number.isInteger(pageNumber) || pageNumber < 1 || pageNumber > (paper.value?.page_count || 1)) return
  clearAssistant()
  scopeType.value = 'PAGE'
  currentPage.value = pageNumber
  selectedEvidenceId.value = null
  citationTarget.value = null
  savedHighlightTarget.value = null
  await loadPageContent(pageNumber)
}

async function selectEvidence(evidence: EvidenceItem): Promise<void> {
  clearAssistant()
  scopeType.value = 'EVIDENCE'
  selectedEvidenceId.value = evidence.id
  selectedSectionId.value = evidence.section_id
  citationTarget.value = {
    evidence_id: evidence.id,
    sequence: 1,
    page_number: evidence.page_number,
    evidence_type: evidence.evidence_type,
    quoted_text: evidence.quoted_text,
    char_start: evidence.char_start,
    char_end: evidence.char_end,
  }
  savedHighlightTarget.value = null
  currentPage.value = evidence.page_number
  await loadPageContent(evidence.page_number)
  await scrollToHighlight()
}

function activateEvidenceScope(): void {
  const evidence = evidences.value.find(item => item.id === selectedEvidenceId.value)
  if (evidence) void selectEvidence(evidence)
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

function buildRequestBody() {
  const body: {
    mode: LearningMode
    scope_type: LearningScopeType
    output_language: 'zh' | 'en'
    section_id?: string
    page_number?: number
    evidence_id?: string
  } = {
    mode: selectedMode.value,
    scope_type: scopeType.value,
    output_language: outputLang.value,
  }
  if (scopeType.value === 'SECTION' && selectedSectionId.value) body.section_id = selectedSectionId.value
  if (scopeType.value === 'PAGE') body.page_number = currentPage.value
  if (scopeType.value === 'EVIDENCE' && selectedEvidenceId.value) body.evidence_id = selectedEvidenceId.value
  return body
}

async function submitLearning(): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || !canSubmit.value || submitting.value) return
  stopPolling()
  const generation = ++assistantGeneration
  submitting.value = true
  assistantError.value = ''
  try {
    const response = await createLearningExplanation(paperId, buildRequestBody())
    if (generation !== assistantGeneration || paper.value?.id !== paperId) return
    activeExplanation.value = response
    if (isProcessing(response.status)) startPolling(response.id, generation, paperId)
    await loadHistory(1)
  } catch (error) {
    if (generation === assistantGeneration) {
      assistantError.value = safeRequestError(error, '创建学习解释失败，请稍后重试。')
    }
  } finally {
    if (generation === assistantGeneration) submitting.value = false
  }
}

function startPolling(explanationId: string, assistantToken = assistantGeneration, paperId = paper.value?.id || ''): void {
  stopPolling()
  const pollToken = pollGeneration
  const schedule = () => {
    pollTimer = setTimeout(async () => {
      if (pollToken !== pollGeneration || assistantToken !== assistantGeneration || paper.value?.id !== paperId) return
      try {
        const response = await getLearningExplanation(explanationId)
        if (pollToken !== pollGeneration || assistantToken !== assistantGeneration || paper.value?.id !== paperId) return
        activeExplanation.value = response
        if (isProcessing(response.status)) schedule()
        else stopPolling()
      } catch (error) {
        if (pollToken === pollGeneration) assistantError.value = safeRequestError(error, '暂时无法获取生成进度，请重试。')
        stopPolling()
      }
    }, 3000)
  }
  schedule()
}

function stopPolling(): void {
  pollGeneration++
  if (pollTimer !== null) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

async function loadExplanation(explanationId: string): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  stopPolling()
  const generation = ++assistantGeneration
  assistantError.value = ''
  try {
    const response = await getLearningExplanation(explanationId)
    if (generation !== assistantGeneration || paper.value?.id !== paperId || response.paper_id !== paperId) return
    activeExplanation.value = response
    if (isProcessing(response.status)) startPolling(explanationId, generation, paperId)
  } catch (error) {
    if (generation === assistantGeneration) assistantError.value = safeRequestError(error, '加载解释失败，请重试。')
  }
}

async function retryExplanation(): Promise<void> {
  const explanation = activeExplanation.value
  if (!explanation) return
  selectedMode.value = explanation.mode
  outputLang.value = explanation.output_language
  scopeType.value = explanation.scope_type
  selectedSectionId.value = explanation.section_id
  selectedEvidenceId.value = explanation.evidence_id
  if (explanation.evidence_id) {
    const evidence = evidences.value.find(item => item.id === explanation.evidence_id)
    if (evidence) {
      citationTarget.value = {
        evidence_id: evidence.id,
        sequence: 1,
        page_number: evidence.page_number,
        evidence_type: evidence.evidence_type,
        quoted_text: evidence.quoted_text,
        char_start: evidence.char_start,
        char_end: evidence.char_end,
      }
      savedHighlightTarget.value = null
      currentPage.value = evidence.page_number
      await loadPageContent(evidence.page_number)
    }
  }
  if (explanation.page_number) {
    currentPage.value = explanation.page_number
    await loadPageContent(explanation.page_number)
  }
  await submitLearning()
}

async function loadHistory(pageNumber: number): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || pageNumber < 1) return
  const generation = ++historyGeneration
  historyLoading.value = true
  historyError.value = ''
  try {
    const response = await listLearningExplanations(paperId, pageNumber, 20)
    if (generation !== historyGeneration || paper.value?.id !== paperId) return
    historyItems.value = response.items
    historyTotal.value = response.total
    historyPage.value = response.page
  } catch (error) {
    if (generation === historyGeneration) historyError.value = safeRequestError(error, '加载解释历史失败，请重试。')
  } finally {
    if (generation === historyGeneration) historyLoading.value = false
  }
}

async function goToCitation(citation: LearningCitationItem): Promise<void> {
  scopeType.value = 'EVIDENCE'
  savedHighlightTarget.value = null
  selectedEvidenceId.value = citation.evidence_id
  selectedSectionId.value = evidences.value.find(item => item.id === citation.evidence_id)?.section_id || null
  citationTarget.value = citation
  currentPage.value = citation.page_number
  const loaded = await loadPageContent(citation.page_number)
  if (loaded) await scrollToHighlight()
}

async function scrollToHighlight(): Promise<void> {
  await nextTick()
  highlightRef.value?.scrollIntoView({ block: 'center', behavior: 'smooth' })
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

async function createNewQAConversation(): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || qaCreatingConv.value) return
  const paperToken = qaPaperGeneration
  const actionToken = ++qaActionGeneration
  qaCreatingConv.value = true
  qaConvError.value = ''
  try {
    const conversation = await createQAConversation(paperId, {})
    if (
      paperToken !== qaPaperGeneration
      || actionToken !== qaActionGeneration
      || paper.value?.id !== paperId
      || conversation.paper_id !== paperId
    ) return
    await loadQAConversations(1)
    if (paperToken !== qaPaperGeneration || actionToken !== qaActionGeneration) return
    activeQAConvId.value = conversation.id
    qaTurns.value = []
    qaTurnTotal.value = 0
    qaTurnPage.value = 1
    qaTurnsError.value = ''
  } catch (error) {
    if (paperToken === qaPaperGeneration && actionToken === qaActionGeneration) {
      qaConvError.value = safeRequestError(error, '创建会话失败，请重试。')
    }
  } finally {
    if (actionToken === qaActionGeneration) qaCreatingConv.value = false
  }
}

async function selectQAConversation(conversationId: string): Promise<void> {
  if (activeQAConvId.value === conversationId && qaTurns.value.length) return
  activeQAConvId.value = conversationId
  qaTurnError.value = ''
  await loadQATurns(conversationId, 1)
}

async function loadQATurns(conversationId: string | null, pageNumber = 1): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || !conversationId || pageNumber < 1) return
  stopQAPolling()
  const paperToken = qaPaperGeneration
  const requestToken = ++qaTurnGeneration
  qaTurnsLoading.value = true
  qaTurnsError.value = ''
  try {
    const response = await getQAConversation(conversationId, pageNumber, 20)
    if (
      paperToken !== qaPaperGeneration
      || requestToken !== qaTurnGeneration
      || activeQAConvId.value !== conversationId
      || response.paper_id !== paperId
    ) return
    qaTurns.value = response.turns || []
    qaTurnTotal.value = response.total
    qaTurnPage.value = response.page
    const processing = qaTurns.value.find(
      turn => turn.status === 'PENDING' || turn.status === 'RUNNING',
    )
    if (processing) startQAPolling(processing.id, conversationId, paperToken)
  } catch (error) {
    if (paperToken === qaPaperGeneration && requestToken === qaTurnGeneration) {
      qaTurnsError.value = safeRequestError(error, '加载问答历史失败，请重试。')
    }
  } finally {
    if (requestToken === qaTurnGeneration) qaTurnsLoading.value = false
  }
}

async function submitQATurn(): Promise<void> {
  const conversationId = activeQAConvId.value
  const paperId = paper.value?.id
  const question = qaQuestion.value.trim()
  if (
    !conversationId
    || !paperId
    || !question
    || qaSubmitting.value
    || qaHasActiveTurn.value
  ) return
  const paperToken = qaPaperGeneration
  const actionToken = ++qaActionGeneration
  qaSubmitting.value = true
  qaTurnError.value = ''
  try {
    const turn = await createQATurn(conversationId, {
      question,
      output_language: qaOutputLang.value,
      client_request_id: crypto.randomUUID(),
    })
    if (
      paperToken !== qaPaperGeneration
      || actionToken !== qaActionGeneration
      || activeQAConvId.value !== conversationId
      || paper.value?.id !== paperId
    ) return
    qaQuestion.value = ''
    const targetPage = Math.max(1, Math.ceil((qaTurnTotal.value + (turn.duplicate ? 0 : 1)) / 20))
    await loadQATurns(conversationId, targetPage)
    if (paperToken === qaPaperGeneration && actionToken === qaActionGeneration) {
      await loadQAConversations(qaConvPage.value)
    }
  } catch (error) {
    if (paperToken === qaPaperGeneration && actionToken === qaActionGeneration) {
      const status = (error as { response?: { status?: number } })?.response?.status
      qaTurnError.value = status === 409
        ? '当前会话仍有问题正在生成，请等待完成后再提问。'
        : safeRequestError(error, '提问失败，请重试。')
    }
  } finally {
    if (actionToken === qaActionGeneration) qaSubmitting.value = false
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
  stopQAPolling()
  const pollToken = qaPollGeneration
  const schedule = () => {
    qaPollTimer = setTimeout(async () => {
      if (
        pollToken !== qaPollGeneration
        || paperToken !== qaPaperGeneration
        || activeQAConvId.value !== conversationId
        || panelTab.value !== 'qa'
      ) return
      try {
        const updated = await getQATurn(turnId)
        if (
          pollToken !== qaPollGeneration
          || paperToken !== qaPaperGeneration
          || activeQAConvId.value !== conversationId
        ) return
        const index = qaTurns.value.findIndex(turn => turn.id === turnId)
        if (index >= 0) qaTurns.value[index] = updated
        if (updated.status === 'PENDING' || updated.status === 'RUNNING') {
          schedule()
        } else {
          stopQAPolling()
          void loadQAConversations(qaConvPage.value)
        }
      } catch (error) {
        if (pollToken === qaPollGeneration) {
          qaTurnError.value = safeRequestError(error, '暂时无法获取问答进度，请重试。')
        }
        stopQAPolling()
      }
    }, 3000)
  }
  schedule()
}

function stopQAPolling(): void {
  qaPollGeneration++
  if (qaPollTimer !== null) {
    clearTimeout(qaPollTimer)
    qaPollTimer = null
  }
}

async function goToQACitation(citation: QACitationItem): Promise<void> {
  scopeType.value = 'EVIDENCE'
  savedHighlightTarget.value = null
  selectedEvidenceId.value = citation.evidence_id
  selectedSectionId.value = evidences.value.find(item => item.id === citation.evidence_id)?.section_id || null
  citationTarget.value = citation
  currentPage.value = citation.page_number
  const loaded = await loadPageContent(citation.page_number)
  if (loaded) await scrollToHighlight()
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
  qaTurnPage.value = 1
  qaTurnsLoading.value = false
  qaTurnsError.value = ''
  qaQuestion.value = ''
  qaTurnError.value = ''
  qaSubmitting.value = false
  qaCreatingConv.value = false
}

function masteryLabel(status: MasteryStatus): string {
  return { NEW: '新', LEARNING: '学习中', MASTERED: '已掌握' }[status] || status
}

function recordRequestError(reason: unknown, fallback: string): string {
  return (reason as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message || fallback
}

function invalidateRecordLists(): void {
  highlightGeneration++
  bookmarkGeneration++
  noteGeneration++
  cardGeneration++
  recordsLoading.value = false
}

async function loadHighlightsPage(pageNumber = highlightPage.value): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  const paperToken = recordPaperGeneration
  const requestToken = ++highlightGeneration
  recordsLoading.value = true
  recordsError.value = ''
  try {
    const response = await listHighlights(paperId, { page: pageNumber, page_size: 20 })
    if (paperToken !== recordPaperGeneration || requestToken !== highlightGeneration || recordsSubTab.value !== 'highlights') return
    highlights.value = response.items
    highlightTotal.value = response.total
    highlightPage.value = response.page
  } catch (reason) {
    if (paperToken === recordPaperGeneration && requestToken === highlightGeneration) recordsError.value = recordRequestError(reason, '加载高亮失败')
  } finally {
    if (paperToken === recordPaperGeneration && requestToken === highlightGeneration) recordsLoading.value = false
  }
}

async function loadBookmarksPage(pageNumber = bookmarkPage.value): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  const paperToken = recordPaperGeneration
  const requestToken = ++bookmarkGeneration
  recordsLoading.value = true
  recordsError.value = ''
  try {
    const response = await listBookmarks(paperId, { page: pageNumber, page_size: 20 })
    if (paperToken !== recordPaperGeneration || requestToken !== bookmarkGeneration || recordsSubTab.value !== 'bookmarks') return
    bookmarks.value = response.items
    bookmarkTotal.value = response.total
    bookmarkPage.value = response.page
  } catch (reason) {
    if (paperToken === recordPaperGeneration && requestToken === bookmarkGeneration) recordsError.value = recordRequestError(reason, '加载书签失败')
  } finally {
    if (paperToken === recordPaperGeneration && requestToken === bookmarkGeneration) recordsLoading.value = false
  }
}

async function loadNotesPage(pageNumber = notePage.value): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  const paperToken = recordPaperGeneration
  const requestToken = ++noteGeneration
  recordsLoading.value = true
  recordsError.value = ''
  try {
    const response = await listNotes(paperId, { page: pageNumber, page_size: 20 })
    if (paperToken !== recordPaperGeneration || requestToken !== noteGeneration || recordsSubTab.value !== 'notes') return
    notes.value = response.items
    noteTotal.value = response.total
    notePage.value = response.page
  } catch (reason) {
    if (paperToken === recordPaperGeneration && requestToken === noteGeneration) recordsError.value = recordRequestError(reason, '加载笔记失败')
  } finally {
    if (paperToken === recordPaperGeneration && requestToken === noteGeneration) recordsLoading.value = false
  }
}

async function loadCardsPage(pageNumber = cardPage.value): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  const paperToken = recordPaperGeneration
  const requestToken = ++cardGeneration
  recordsLoading.value = true
  recordsError.value = ''
  try {
    const response = await listKnowledgeCards(paperId, { page: pageNumber, page_size: 20 })
    if (paperToken !== recordPaperGeneration || requestToken !== cardGeneration || recordsSubTab.value !== 'cards') return
    cards.value = response.items
    cardTotal.value = response.total
    cardPage.value = response.page
  } catch (reason) {
    if (paperToken === recordPaperGeneration && requestToken === cardGeneration) recordsError.value = recordRequestError(reason, '加载知识卡失败')
  } finally {
    if (paperToken === recordPaperGeneration && requestToken === cardGeneration) recordsLoading.value = false
  }
}

function loadActiveRecords(): void {
  if (recordsSubTab.value === 'highlights') void loadHighlightsPage()
  if (recordsSubTab.value === 'bookmarks') void loadBookmarksPage()
  if (recordsSubTab.value === 'notes') void loadNotesPage()
  if (recordsSubTab.value === 'cards') void loadCardsPage()
}

function goRecordPage(pageNumber: number): void {
  if (pageNumber < 1) return
  if (recordsSubTab.value === 'highlights') void loadHighlightsPage(pageNumber)
  if (recordsSubTab.value === 'bookmarks') void loadBookmarksPage(pageNumber)
  if (recordsSubTab.value === 'notes') void loadNotesPage(pageNumber)
  if (recordsSubTab.value === 'cards') void loadCardsPage(pageNumber)
}

async function loadSourceOptions(): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  try {
    const [highlightResponse, noteResponse] = await Promise.all([
      listHighlights(paperId, { page: 1, page_size: 100 }),
      listNotes(paperId, { page: 1, page_size: 100 }),
    ])
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    sourceHighlights.value = highlightResponse.items
    sourceNotes.value = noteResponse.items
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '加载来源选项失败')
  }
}

function startHighlightSelection(): void {
  if (scopeType.value !== 'PAGE' || !contentRef.value) {
    recordsError.value = '请先切换到当前页面再创建高亮'
    return
  }
  hlSelectionActive.value = true
  hlSelectionRange.value = null
  document.addEventListener('mouseup', onTextSelection)
}

function cancelHighlightSelection(): void {
  hlSelectionActive.value = false
  hlSelectionRange.value = null
  document.removeEventListener('mouseup', onTextSelection)
}

function onTextSelection(): void {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount !== 1 || sel.isCollapsed || !contentRef.value || scopeType.value !== 'PAGE') return
  const range = sel.getRangeAt(0)
  const resolved = resolveTextSelection(contentRef.value, range, 5000)
  if (!resolved) {
    hlSelectionRange.value = null
    recordsError.value = '请选择当前正文内不超过 5000 字的有效文本'
    return
  }
  recordsError.value = ''
  hlSelectionRange.value = resolved
}

async function confirmHighlight(): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || !hlSelectionRange.value || scopeType.value !== 'PAGE') return
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  recordsError.value = ''
  try {
    await createHighlight(paperId, {
      page_number: currentPage.value,
      char_start: hlSelectionRange.value.start,
      char_end: hlSelectionRange.value.end,
      color: hlColor.value,
    })
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    cancelHighlightSelection()
    await loadHighlightsPage(1)
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '创建高亮失败')
  } finally {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordActionBusy.value = false
  }
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
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '删除高亮失败')
  } finally {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordActionBusy.value = false
  }
}

async function locateSavedHighlight(highlight: HighlightResponse): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId) return
  scopeType.value = 'PAGE'
  currentPage.value = highlight.page_number
  selectedEvidenceId.value = null
  citationTarget.value = null
  savedHighlightTarget.value = null
  const loaded = await loadPageContent(highlight.page_number)
  if (loaded && paper.value?.id === paperId) {
    savedHighlightTarget.value = highlight
    await scrollToHighlight()
  }
}

async function addBookmark(): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || scopeType.value !== 'PAGE') return
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  try {
    await createBookmark(paperId, { page_number: currentPage.value, label: bookmarkLabel.value.trim() || null })
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    bookmarkLabel.value = ''
    await loadBookmarksPage(1)
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '创建书签失败')
  } finally {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordActionBusy.value = false
  }
}

async function removeBookmark(id: string): Promise<void> {
  if (!window.confirm('确认删除这个书签吗？')) return
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  try {
    await deleteBookmark(id)
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    await loadBookmarksPage(bookmarkPage.value)
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '删除书签失败')
  } finally {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordActionBusy.value = false
  }
}

function startCreateNote(): void {
  editingNoteId.value = null
  noteAnchorType.value = 'PAPER'
  noteHighlightId.value = ''
  noteContent.value = ''
  showNoteForm.value = true
  void loadSourceOptions()
}

function startEditNote(note: NoteResponse): void {
  editingNoteId.value = note.id
  noteAnchorType.value = note.anchor_type
  noteHighlightId.value = note.highlight_id || ''
  noteContent.value = note.content
  showNoteForm.value = true
}

function cancelNoteForm(): void {
  showNoteForm.value = false
  editingNoteId.value = null
  noteContent.value = ''
  noteHighlightId.value = ''
}

async function submitNote(): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || !noteContent.value.trim()) return
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  try {
    if (editingNoteId.value) {
      await patchNote(editingNoteId.value, noteContent.value.trim())
    } else {
      await createNote(paperId, {
        anchor_type: noteAnchorType.value,
        page_number: noteAnchorType.value === 'PAGE' ? currentPage.value : null,
        highlight_id: noteAnchorType.value === 'HIGHLIGHT' && noteHighlightId.value ? noteHighlightId.value : null,
        content: noteContent.value.trim(),
      })
    }
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

function startCreateCard(): void {
  editingCardId.value = null
  cardSourceType.value = ''
  cardSourceNoteId.value = ''
  cardSourceHighlightId.value = ''
  cardFront.value = ''
  cardBack.value = ''
  showCardForm.value = true
  void loadSourceOptions()
}

function startEditCard(card: KnowledgeCardResponse): void {
  editingCardId.value = card.id
  cardSourceType.value = card.source_note_id ? 'note' : card.source_highlight_id ? 'highlight' : ''
  cardSourceNoteId.value = card.source_note_id || ''
  cardSourceHighlightId.value = card.source_highlight_id || ''
  cardFront.value = card.front
  cardBack.value = card.back
  showCardForm.value = true
}

function cancelCardForm(): void {
  showCardForm.value = false
  editingCardId.value = null
  cardSourceType.value = ''
  cardSourceNoteId.value = ''
  cardSourceHighlightId.value = ''
  cardFront.value = ''
  cardBack.value = ''
}

async function submitCard(): Promise<void> {
  const paperId = paper.value?.id
  if (!paperId || !cardFront.value.trim() || !cardBack.value.trim()) return
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  try {
    if (editingCardId.value) {
      await patchKnowledgeCard(editingCardId.value, { front: cardFront.value.trim(), back: cardBack.value.trim() })
    } else {
      await createKnowledgeCard(paperId, {
        source_note_id: cardSourceType.value === 'note' && cardSourceNoteId.value ? cardSourceNoteId.value : null,
        source_highlight_id: cardSourceType.value === 'highlight' && cardSourceHighlightId.value ? cardSourceHighlightId.value : null,
        front: cardFront.value.trim(),
        back: cardBack.value.trim(),
      })
    }
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    cancelCardForm()
    await loadCardsPage(cardPage.value)
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '保存知识卡失败')
  } finally {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordActionBusy.value = false
  }
}

async function removeCard(id: string): Promise<void> {
  if (!window.confirm('确认删除这张知识卡吗？')) return
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  try {
    await deleteKnowledgeCard(id)
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    await loadCardsPage(cardPage.value)
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '删除知识卡失败')
  } finally {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordActionBusy.value = false
  }
}

async function updateCardMastery(cardId: string, status: string): Promise<void> {
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  try {
    const updated = await patchKnowledgeCard(cardId, { mastery_status: status as MasteryStatus })
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    const idx = cards.value.findIndex(c => c.id === cardId)
    if (idx >= 0) cards.value[idx] = updated
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '更新掌握状态失败')
  } finally {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordActionBusy.value = false
  }
}

async function toggleCardArchive(card: KnowledgeCardResponse): Promise<void> {
  const paperToken = recordPaperGeneration
  const actionToken = ++recordActionGeneration
  recordActionBusy.value = true
  try {
    const updated = await patchKnowledgeCard(card.id, { archived: !card.archived })
    if (paperToken !== recordPaperGeneration || actionToken !== recordActionGeneration) return
    const idx = cards.value.findIndex(c => c.id === card.id)
    if (idx >= 0) cards.value[idx] = updated
  } catch (reason) {
    if (paperToken === recordPaperGeneration && actionToken === recordActionGeneration) recordsError.value = recordRequestError(reason, '更新归档状态失败')
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
  bookmarks.value = []
  notes.value = []
  cards.value = []
  sourceHighlights.value = []
  sourceNotes.value = []
  highlightTotal.value = 0
  bookmarkTotal.value = 0
  noteTotal.value = 0
  cardTotal.value = 0
  highlightPage.value = 1
  bookmarkPage.value = 1
  notePage.value = 1
  cardPage.value = 1
  savedHighlightTarget.value = null
  cancelHighlightSelection()
  cancelNoteForm()
  cancelCardForm()
}

async function loadPaper(paperId: string): Promise<void> {
  const generation = ++paperGeneration
  contentGeneration++
  assistantGeneration++
  historyGeneration++
  stopPolling()
  resetQAState()
  resetRecordState()
  paper.value = null
  sections.value = []
  evidences.value = []
  pageData.value = null
  activeExplanation.value = null
  loadError.value = ''
  contentError.value = ''
  assistantError.value = ''
  historyError.value = ''
  if (!paperId) {
    loadError.value = '论文标识无效。'
    return
  }
  try {
    const loadedPaper = await getPaper(paperId)
    if (generation !== paperGeneration || String(route.params.id || '') !== paperId) return
    paper.value = loadedPaper
    currentPage.value = 1
    if (loadedPaper.status !== 'PARSED') return

    const [loadedSections, loadedEvidences] = await Promise.all([
      listSections(paperId),
      listEvidences(paperId),
    ])
    if (generation !== paperGeneration || paper.value?.id !== paperId) return
    sections.value = loadedSections
    evidences.value = loadedEvidences
    const first = loadedSections[0]
    if (first) {
      scopeType.value = 'SECTION'
      selectedSectionId.value = first.id
      currentPage.value = first.start_page || 1
    } else {
      scopeType.value = 'PAGE'
      await loadPageContent(1)
    }
    await loadHistory(1)
  } catch (error) {
    if (generation === paperGeneration) loadError.value = safeRequestError(error, '加载论文阅读工作台失败，请重试。')
  }
}

function excerpt(text: string): string {
  return text.length > 80 ? `${text.slice(0, 80)}…` : text
}

function pageRange(section: SectionItem): string {
  if (section.start_page === null) return ''
  return section.end_page && section.end_page !== section.start_page
    ? `p.${section.start_page}–${section.end_page}`
    : `p.${section.start_page}`
}

function modeLabel(mode: LearningMode): string {
  return modes.find(item => item.value === mode)?.label || mode
}

function scopeLabel(scope: LearningScopeType): string {
  return { SECTION: '章节', PAGE: '页面', EVIDENCE: '证据' }[scope]
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

watch(panelTab, tab => {
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
    if (activeQAConvId.value) void loadQATurns(activeQAConvId.value, qaTurnPage.value)
  }
  if (tab === 'records' && paper.value?.status === 'PARSED') {
    loadActiveRecords()
  } else {
    invalidateRecordLists()
    recordActionGeneration++
    recordActionBusy.value = false
    cancelHighlightSelection()
  }
})

watch(recordsSubTab, () => {
  invalidateRecordLists()
  recordActionGeneration++
  recordActionBusy.value = false
  recordsError.value = ''
  cancelHighlightSelection()
  cancelNoteForm()
  cancelCardForm()
  if (panelTab.value === 'records' && paper.value?.status === 'PARSED') loadActiveRecords()
})

onUnmounted(() => {
  paperGeneration++
  contentGeneration++
  assistantGeneration++
  historyGeneration++
  stopPolling()
  resetQAState()
  resetRecordState()
})
</script>

<style scoped>
.reading-view { min-height: 100vh; display: flex; flex-direction: column; color: #25243a; background: #f7f7fb; }
.reading-header { min-height: 3.5rem; padding: 0.75rem 1.25rem; border-bottom: 1px solid #dedee8; display: flex; align-items: center; gap: 1rem; background: #fff; }
.reading-header h2 { min-width: 0; margin: 0; font-size: 1.1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.back-link { color: #33315b; text-decoration: none; white-space: nowrap; }
.reading-layout { display: grid; grid-template-columns: 15rem minmax(20rem, 1fr) 22rem; min-height: calc(100vh - 3.5rem); }
.sidebar, .learning-panel { padding: 1rem; overflow-y: auto; background: #fff; }
.sidebar { border-right: 1px solid #dedee8; }
.learning-panel { border-left: 1px solid #dedee8; }
.sidebar h3, .learning-panel h3 { margin: 0.8rem 0 0.5rem; font-size: 0.9rem; }
.sidebar h3:first-child { margin-top: 0; }
.section-list, .evidence-list, .history-list { margin: 0; padding: 0; list-style: none; }
.section-list li, .evidence-list li { margin-bottom: 0.2rem; padding: 0.45rem 0.5rem; border-radius: 0.35rem; cursor: pointer; font-size: 0.84rem; }
.section-list li:hover, .evidence-list li:hover, .history-list li:hover { background: #f0f0fa; }
.section-list li.active, .evidence-list li.active, .history-list li.active { background: #e7e6fb; color: #23214d; }
.section-pages, .ev-page { margin-left: 0.4rem; color: #77758d; font-size: 0.75rem; }
.ev-type { padding: 0.1rem 0.3rem; border-radius: 0.2rem; background: #ececf3; font-size: 0.7rem; }
.ev-text { display: block; margin-top: 0.25rem; color: #57566a; line-height: 1.35; }
.page-nav { display: flex; align-items: center; gap: 0.4rem; }
.page-input { width: 3.4rem; padding: 0.25rem; text-align: center; }
.content-panel { position: relative; padding: 2rem clamp(1.25rem, 4vw, 4rem); overflow-y: auto; background: #fcfcff; }
.content-text { max-width: 54rem; margin: 0 auto; white-space: pre-wrap; font-family: Georgia, 'Times New Roman', serif; font-size: 1rem; line-height: 1.85; }
.highlight { background: #fff08a; color: inherit; }
.highlight-notice { max-width: 54rem; margin: 1rem auto; padding: 0.6rem; border-radius: 0.4rem; background: #fff8df; color: #7a5a00; }
.progress-warning { max-width: 54rem; margin: 1rem auto; padding: 0.6rem; border-radius: 0.4rem; background: #fff4e5; color: #8a4b08; }
.scope-selector, .mode-selector, .lang-selector { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.3rem; margin-bottom: 0.7rem; }
.lang-selector { grid-template-columns: repeat(2, 1fr); }
button { padding: 0.4rem 0.55rem; border: 1px solid #d8d7e2; border-radius: 0.35rem; background: #fff; cursor: pointer; }
button.active, .submit-btn { border-color: #25234f; background: #25234f; color: #fff; }
button:disabled { cursor: not-allowed; opacity: 0.45; }
.submit-btn { width: 100%; padding: 0.65rem; }
.result-area, .history-section { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #dedee8; }
.result-content h4, .history-section h4 { margin: 0.85rem 0 0.4rem; }
.answer-text { white-space: pre-wrap; line-height: 1.55; }
.key-points { padding-left: 1.25rem; }
.terms-list { display: grid; gap: 0.5rem; margin: 0; }
.term-card { padding: 0.55rem; border-radius: 0.4rem; background: #f0f0f7; }
.term-card dt { font-weight: 700; }
.term-card dd { margin: 0.25rem 0 0; color: #57566a; }
.citations-list { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.citation-link { color: #34318a; text-decoration: underline; }
.history-list li { display: grid; grid-template-columns: 1fr auto; gap: 0.25rem 0.5rem; padding: 0.5rem; border-radius: 0.35rem; cursor: pointer; font-size: 0.8rem; }
.history-list time { grid-column: 1 / -1; color: #77758d; }
.status-succeeded { color: #257335; }
.status-failed { color: #b32626; }
.status-pending, .status-running { color: #a66000; }
.history-pagination { display: flex; align-items: center; justify-content: space-between; margin-top: 0.6rem; }
.error-msg { color: #a51f1f; }
.assistant-error, .not-ready, .page-error, .page-loading { padding: 1rem; }
.loading-msg, .empty-msg { color: #77758d; }
.retry-btn { color: #9f2424; border-color: #c95b5b; }
.panel-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 0.3rem; margin-bottom: 0.7rem; }
.conv-list { margin: 0; padding: 0; list-style: none; }
.conv-list li { padding: 0.45rem 0.5rem; border-radius: 0.35rem; cursor: pointer; font-size: 0.84rem; margin-bottom: 0.2rem; }
.conv-list li:hover { background: #f0f0fa; }
.conv-list li.active { background: #e7e6fb; color: #23214d; }
.conv-list time { display: block; color: #77758d; font-size: 0.75rem; }
.conv-list small { display: block; color: #77758d; font-size: 0.72rem; }
.qa-messages { max-height: 24rem; overflow-y: auto; margin-bottom: 0.7rem; }
.qa-message { margin-bottom: 0.7rem; padding: 0.5rem; border-radius: 0.4rem; background: #f7f7fb; }
.qa-question { font-size: 0.85rem; }
.qa-answer { font-size: 0.85rem; }
.qa-answer p { margin: 0; white-space: pre-wrap; line-height: 1.5; }
.not-grounded { border-left: 3px solid #d4a017; padding-left: 0.5rem; }
.grounded-badge { display: inline-block; padding: 0.1rem 0.4rem; border-radius: 0.2rem; font-size: 0.7rem; margin-left: 0.3rem; }
.grounded-badge { background: #e6f4ea; color: #1e7e34; }
.not-grounded-badge { background: #fff3cd; color: #856404; }
.qa-input-area textarea { width: 100%; padding: 0.5rem; border: 1px solid #d8d7e2; border-radius: 0.35rem; resize: vertical; font-family: inherit; font-size: 0.85rem; }
.qa-input-actions { display: flex; gap: 0.4rem; margin-top: 0.4rem; align-items: center; }
.qa-input-actions select { padding: 0.35rem; border: 1px solid #d8d7e2; border-radius: 0.35rem; }
.qa-input-actions .submit-btn { flex: 1; }
.qa-turn-pagination { margin-bottom: 0.7rem; }
.panel-tabs { grid-template-columns: 1fr 1fr 1fr; }
.records-sub-tabs { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.3rem; margin-bottom: 0.7rem; }
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
.hl-confirm-bar { padding: 0.5rem; background: #f0f0f7; border-radius: 0.35rem; margin-bottom: 0.5rem; }
.hl-preview { display: block; font-size: 0.84rem; margin-bottom: 0.3rem; max-height: 3rem; overflow: hidden; }
.hl-confirm-bar select { padding: 0.25rem; border: 1px solid #d8d7e2; border-radius: 0.25rem; margin-right: 0.3rem; }
.note-form, .card-form { padding: 0.5rem; background: #f7f7fb; border-radius: 0.35rem; margin-bottom: 0.5rem; }
.note-form select, .card-form select, .note-form input, .card-form input { width: 100%; padding: 0.35rem; border: 1px solid #d8d7e2; border-radius: 0.25rem; margin-bottom: 0.3rem; font-size: 0.84rem; box-sizing: border-box; }
.note-form textarea, .card-form textarea { width: 100%; padding: 0.35rem; border: 1px solid #d8d7e2; border-radius: 0.25rem; resize: vertical; font-family: inherit; font-size: 0.84rem; margin-bottom: 0.3rem; box-sizing: border-box; }
.note-form-actions { display: flex; gap: 0.3rem; }
.note-anchor { display: inline-block; padding: 0.1rem 0.3rem; border-radius: 0.2rem; background: #ececf3; font-size: 0.7rem; margin-right: 0.3rem; }
.note-content { margin: 0.3rem 0; white-space: pre-wrap; line-height: 1.4; }
.card-item .card-front { font-weight: 600; }
.card-item .card-back { color: #57566a; margin: 0.2rem 0; }
.card-meta { margin: 0.2rem 0; }
.mastery-new { color: #888; }
.mastery-learning { color: #f57c00; }
.mastery-mastered { color: #2e7d32; }
.archived-badge { display: inline-block; padding: 0.1rem 0.3rem; border-radius: 0.2rem; background: #e0e0e0; font-size: 0.7rem; margin-left: 0.3rem; }
.card-actions { display: flex; gap: 0.3rem; align-items: center; margin-top: 0.3rem; }
.card-actions select { padding: 0.2rem; border: 1px solid #d8d7e2; border-radius: 0.25rem; font-size: 0.75rem; }
.card-actions button { padding: 0.15rem 0.4rem; border: 1px solid #d8d7e2; border-radius: 0.25rem; background: #fff; cursor: pointer; font-size: 0.75rem; }
@media (max-width: 960px) {
  .reading-layout { grid-template-columns: 1fr; }
  .sidebar, .learning-panel { border: 0; border-bottom: 1px solid #dedee8; overflow: visible; }
  .content-panel { min-height: 55vh; order: 2; }
  .learning-panel { order: 3; }
}
</style>
