<template>
  <div class="paper-detail" v-if="paper">
    <h2>{{ paper.title }}</h2>
    <div class="meta">
      <span>文件: {{ paper.filename }}</span>
      <span>大小: {{ (paper.file_size / 1024 / 1024).toFixed(1) }} MB</span>
      <span>页数: {{ paper.page_count ?? '-' }}</span>
      <span :class="'status-' + paper.status.toLowerCase()">{{ statusLabel(paper.status) }}</span>
    </div>

    <div v-if="paper.status === 'FAILED'" class="failed-notice">
      <p>论文解析失败{{ paper.error_message ? '：' + paper.error_message : '' }}，请重新上传或检查文件是否为有效的文本型 PDF。</p>
      <router-link to="/upload">重新上传</router-link>
    </div>

    <div v-if="paper.status === 'PROCESSING'" class="processing-notice">
      <p v-if="!pollError">论文正在解析中，请稍候...</p>
      <p v-else class="poll-error-text">轮询状态失败：{{ pollError }}</p>
      <button v-if="pollError" @click="retryPoll" class="retry-btn">重试</button>
    </div>

    <div v-if="paper.status === 'PARSED'" class="tabs">
      <button :class="{ active: tab === 'sections' }" @click="tab = 'sections'">章节</button>
      <button :class="{ active: tab === 'pages' }" @click="openPages">页面</button>
      <button :class="{ active: tab === 'evidences' }" @click="tab = 'evidences'">证据</button>
    </div>

    <div v-if="paper.status === 'PARSED' && tab === 'sections'" class="section-list">
      <div v-for="s in sections" :key="s.id" class="section-item">
        <h4>{{ s.title || s.section_type }}</h4>
        <p class="section-meta">{{ s.section_type }} | 页 {{ s.start_page }}-{{ s.end_page }}</p>
        <pre class="section-text">{{ (s.text_content || '').slice(0, 500) }}{{ (s.text_content || '').length > 500 ? '...' : '' }}</pre>
      </div>
      <p v-if="sections.length === 0">暂无章节数据</p>
    </div>

    <div v-if="paper.status === 'PARSED' && tab === 'pages'" class="page-view">
      <div class="page-nav">
        <button :disabled="currentPage <= 1" @click="prevPage">上一页</button>
        <span>第 {{ currentPage }} / {{ paper.page_count || 1 }} 页</span>
        <button :disabled="currentPage >= (paper.page_count || 1)" @click="nextPage">下一页</button>
        <input type="number" v-model.number="pageJump" min="1" :max="paper.page_count || 1" @keyup.enter="jumpToPage" placeholder="跳转" class="page-jump-input" />
        <button @click="jumpToPage">跳转</button>
      </div>
      <div v-if="pageError" class="error-msg">
        <p>{{ pageError }}</p>
        <button @click="loadPage(currentPage)" class="retry-btn">重试</button>
      </div>
      <div v-else-if="pageData" class="page-content" ref="pageContentRef">
        <div v-if="evidenceDegraded" class="degraded-notice">
          该证据暂不支持精确高亮
        </div>
        <template v-if="highlightRange">
          <span>{{ highlightRange.before }}</span>
          <mark class="highlight">{{ highlightRange.highlight }}</mark>
          <span>{{ highlightRange.after }}</span>
        </template>
        <template v-else>
          <span>{{ pageData.normalized_text_content || pageData.text_content || '' }}</span>
        </template>
      </div>
      <div v-else class="loading-msg">加载中...</div>
    </div>

    <div v-if="paper.status === 'PARSED' && tab === 'evidences'" class="evidence-list">
      <div v-for="e in evidences" :key="e.id" class="evidence-item" @click="goToEvidence(e)">
        <p class="evidence-meta">页 {{ e.page_number }} | {{ e.evidence_type }}</p>
        <p class="evidence-text">{{ e.quoted_text.slice(0, 300) }}{{ e.quoted_text.length > 300 ? '...' : '' }}</p>
      </div>
      <p v-if="evidences.length === 0">暂无证据数据</p>
    </div>

    <router-link to="/papers" class="back-link">返回列表</router-link>
  </div>
  <div v-else-if="loadError" class="error-msg">
    <p>{{ loadError }}</p>
    <button @click="load" class="retry-btn">重试</button>
  </div>
  <div v-else class="loading-msg">加载中...</div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { getPaper, getPage, listSections, listEvidences, type PaperDetail, type SectionItem, type EvidenceItem, type PageDetail } from '../api'

const route = useRoute()
const paper = ref<PaperDetail | null>(null)
const sections = ref<SectionItem[]>([])
const evidences = ref<EvidenceItem[]>([])
const pageData = ref<PageDetail | null>(null)
const pageError = ref('')
const loadError = ref('')
const pollError = ref('')
const tab = ref<'sections' | 'pages' | 'evidences'>('sections')
const currentPage = ref(1)
const pageJump = ref<number | null>(null)
const selectedEvidence = ref<EvidenceItem | null>(null)
const pageContentRef = ref<HTMLElement | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null
let pageRequestId = 0

function statusLabel(s: string) {
  const m: Record<string, string> = { UPLOADING: '上传中', PROCESSING: '解析中', PARSED: '已解析', FAILED: '失败' }
  return m[s] || s
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPolling(id: string) {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const p = await getPaper(id)
      paper.value = p
      if (p.status !== 'PROCESSING') {
        stopPolling()
        if (p.status === 'PARSED') {
          sections.value = await listSections(id)
          evidences.value = await listEvidences(id)
        }
      }
    } catch (e: any) {
      stopPolling()
      pollError.value = e?.response?.data?.error?.message || e?.message || '轮询失败'
    }
  }, 3000)
}

const evidenceDegraded = computed(() => {
  if (!selectedEvidence.value) return false
  const ev = selectedEvidence.value
  if (ev.char_start === null || ev.char_end === null) return true
  if (!pageData.value) return true
  const text = pageData.value.normalized_text_content || pageData.value.text_content || ''
  if (ev.char_start < 0 || ev.char_end > text.length || ev.char_start >= ev.char_end) return true
  const sliced = text.slice(ev.char_start, ev.char_end)
  if (sliced !== ev.quoted_text) return true
  return false
})

const highlightRange = computed(() => {
  if (!selectedEvidence.value || !pageData.value) return null
  const ev = selectedEvidence.value
  if (ev.char_start === null || ev.char_end === null) return null
  const text = pageData.value.normalized_text_content || pageData.value.text_content || ''
  const start = ev.char_start
  const end = ev.char_end
  if (start < 0 || end > text.length || start >= end) return null
  const sliced = text.slice(start, end)
  if (sliced !== ev.quoted_text) return null
  return {
    before: text.slice(0, start),
    highlight: sliced,
    after: text.slice(end),
  }
})

async function loadPage(pageNumber: number) {
  if (!paper.value) return
  const requestId = ++pageRequestId
  pageError.value = ''
  pageData.value = null
  try {
    const data = await getPage(paper.value.id, pageNumber)
    if (requestId !== pageRequestId) return
    pageData.value = data
    if (selectedEvidence.value && selectedEvidence.value.page_number === pageNumber) {
      await nextTick()
      scrollToHighlight()
    }
  } catch (e: any) {
    if (requestId !== pageRequestId) return
    pageError.value = e?.response?.data?.error?.message || e?.message || '加载页面失败'
  }
}

function scrollToHighlight() {
  if (!pageContentRef.value) return
  const mark = pageContentRef.value.querySelector('.highlight')
  if (mark) {
    mark.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function jumpToPage() {
  if (pageJump.value && pageJump.value >= 1 && pageJump.value <= (paper.value?.page_count || 1)) {
    selectedEvidence.value = null
    currentPage.value = pageJump.value
    pageJump.value = null
  }
}

function openPages() {
  tab.value = 'pages'
  if (!pageData.value || pageData.value.page_number !== currentPage.value) {
    loadPage(currentPage.value)
  }
}

function prevPage() {
  selectedEvidence.value = null
  if (currentPage.value > 1) currentPage.value--
}

function nextPage() {
  selectedEvidence.value = null
  if (currentPage.value < (paper.value?.page_count || 1)) currentPage.value++
}

function goToEvidence(e: EvidenceItem) {
  selectedEvidence.value = e
  tab.value = 'pages'
  if (currentPage.value !== e.page_number) {
    currentPage.value = e.page_number
  } else if (pageData.value && pageData.value.page_number === e.page_number) {
    nextTick(() => scrollToHighlight())
  } else {
    loadPage(currentPage.value)
  }
}

watch(currentPage, (newPage) => {
  loadPage(newPage)
})

function retryPoll() {
  pollError.value = ''
  stopPolling()
  load()
}

async function load() {
  const id = route.params.id as string
  loadError.value = ''
  try {
    paper.value = await getPaper(id)
    if (paper.value.status === 'PROCESSING') {
      startPolling(id)
    } else if (paper.value.status === 'PARSED') {
      sections.value = await listSections(id)
      evidences.value = await listEvidences(id)
    }
  } catch (e: any) {
    loadError.value = e?.response?.data?.error?.message || e?.message || '加载论文详情失败'
  }
}

onMounted(load)
onUnmounted(() => {
  stopPolling()
  pageRequestId++
})
</script>

<style scoped>
.paper-detail { max-width: 960px; margin: 2rem auto; padding: 0 1rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
h2 { color: #1a1a2e; }
.meta { display: flex; gap: 1.5rem; flex-wrap: wrap; margin: 1rem 0; color: #666; font-size: 0.9rem; }
.status-processing { color: #f57c00; font-weight: 600; }
.status-parsed { color: #2e7d32; }
.status-failed { color: #c62828; }
.processing-notice, .failed-notice { padding: 1rem; border-radius: 8px; margin: 1rem 0; }
.processing-notice { background: #fff3e0; color: #e65100; }
.failed-notice { background: #ffebee; color: #c62828; }
.poll-error-text { color: #c62828; }
.tabs { display: flex; gap: 0.5rem; margin: 1.5rem 0; }
.tabs button { padding: 0.5rem 1.5rem; border: 1px solid #e0e0e0; border-radius: 6px; background: #fafafa; cursor: pointer; }
.tabs button.active { background: #1a1a2e; color: #fff; border-color: #1a1a2e; }
.section-item, .evidence-item { padding: 1rem; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 0.75rem; }
.section-item h4 { margin: 0 0 0.25rem; color: #1a1a2e; }
.section-meta, .evidence-meta { font-size: 0.8rem; color: #888; margin: 0.25rem 0; }
.section-text { white-space: pre-wrap; font-size: 0.85rem; color: #333; margin: 0.5rem 0 0; max-height: 200px; overflow-y: auto; }
.evidence-item { cursor: pointer; }
.evidence-item:hover { background: #f5f5ff; }
.evidence-text { font-size: 0.85rem; color: #333; margin: 0.25rem 0; }
.page-nav { display: flex; align-items: center; gap: 0.75rem; margin: 1rem 0; }
.page-nav button { padding: 0.4rem 1rem; border: 1px solid #e0e0e0; border-radius: 4px; background: #fafafa; cursor: pointer; }
.page-nav button:disabled { opacity: 0.5; cursor: not-allowed; }
.page-jump-input { width: 60px; padding: 0.3rem; border: 1px solid #e0e0e0; border-radius: 4px; text-align: center; }
.page-content { white-space: pre-wrap; font-size: 0.85rem; color: #333; padding: 1rem; border: 1px solid #e0e0e0; border-radius: 8px; max-height: 600px; overflow-y: auto; line-height: 1.6; }
.highlight { background: #fff176; padding: 0 2px; border-radius: 2px; }
.degraded-notice { background: #fff3e0; color: #e65100; padding: 0.5rem; border-radius: 4px; margin-bottom: 0.5rem; font-size: 0.85rem; }
.error-msg { color: #c62828; padding: 1rem; }
.retry-btn { margin-top: 0.5rem; padding: 0.4rem 1rem; border: 1px solid #c62828; border-radius: 4px; background: #fff; color: #c62828; cursor: pointer; }
.loading-msg { color: #888; padding: 1rem; text-align: center; }
.back-link { display: inline-block; margin-top: 1.5rem; color: #1a1a2e; }
</style>
