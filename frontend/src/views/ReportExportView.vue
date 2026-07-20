<template>
  <main v-if="paper" class="report-export">
    <header class="page-header">
      <div>
        <p class="eyebrow">论文学习归档</p>
        <h1>导出论文学习报告</h1>
        <p class="paper-name">{{ paper.title }}</p>
        <div class="paper-meta">
          <span>{{ paper.filename }}</span>
          <span>{{ paper.page_count ?? '-' }} 页</span>
        </div>
      </div>
      <router-link :to="{ name: 'paper-read', params: { id: paper.id } }" class="exit-button">退出</router-link>
    </header>

    <section v-if="paper.status !== 'PARSED'" class="not-ready-notice">
      <h2>论文仍在解析</h2>
      <p>解析完成后即可导出学习报告，无需先生成审阅结果。</p>
      <router-link :to="{ name: 'paper-read', params: { id: paper.id } }" class="secondary-button">返回阅读</router-link>
    </section>

    <template v-else>
      <div v-if="loadError" class="error-banner">
        <span>{{ loadError }}</span>
        <button type="button" @click="loadData">重试</button>
      </div>

      <section class="export-grid">
        <div class="panel export-form">
          <div class="panel-heading">
            <span class="step">01</span>
            <div>
              <h2>导出设置</h2>
              <p>选择适合保存或继续编辑的格式</p>
            </div>
          </div>

          <label class="field-label" for="report-type">文件格式</label>
          <select id="report-type" v-model="form.report_type" class="sr-only" tabindex="-1">
            <option value="MARKDOWN">Markdown</option>
            <option value="PDF">PDF</option>
            <option value="DOCX">DOCX</option>
          </select>
          <div class="format-options" role="group" aria-label="文件格式">
            <button
              v-for="option in formatOptions"
              :key="option.value"
              type="button"
              class="format-option"
              :class="{ active: form.report_type === option.value }"
              :aria-pressed="form.report_type === option.value"
              @click="form.report_type = option.value"
            >
              <strong>{{ option.label }}</strong>
              <span>{{ option.description }}</span>
            </button>
          </div>

          <div class="language-row">
            <div>
              <label class="field-label" for="report-lang">报告语言</label>
              <p>控制固定标题和栏目名称</p>
            </div>
            <select id="report-lang" v-model="form.language">
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </div>

          <button type="button" class="btn-primary" :disabled="submitting" @click="submitExport">
            <span>{{ submitting ? '正在创建…' : '生成学习报告' }}</span>
            <span aria-hidden="true">→</span>
          </button>
          <p class="ready-hint">论文已解析即可生成，不要求先完成审阅。</p>
          <p v-if="submitError" class="error-text">{{ submitError }}</p>
        </div>

        <div class="panel content-panel">
          <div class="panel-heading">
            <span class="step">02</span>
            <div>
              <h2>报告内容</h2>
              <p>学习记录是报告主体，分析内容按需附加</p>
            </div>
          </div>

          <h3 class="section-label">固定包含</h3>
          <div class="included-list">
            <div v-for="item in coreSections" :key="item.title" class="included-item">
              <span class="included-icon">✓</span>
              <div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.description }}</p>
              </div>
            </div>
          </div>

          <h3 class="section-label optional-label">扩展内容</h3>
          <div class="option-row option-row--automatic">
            <div>
              <strong>批判性阅读</strong>
              <p>存在成功审阅时自动加入，不存在也可正常导出</p>
            </div>
            <span>自动</span>
          </div>
          <label class="option-row">
            <div>
              <strong>指标数据</strong>
              <p>加入论文中提取的模型、数据集与指标记录</p>
            </div>
            <input v-model="form.include_metrics" type="checkbox" class="toggle-input" />
          </label>
          <label class="option-row">
            <div>
              <strong>实验分析</strong>
              <p>加入已上传实验文件的统计与对照结果</p>
            </div>
            <input v-model="form.include_experiment_analysis" type="checkbox" class="toggle-input" />
          </label>
        </div>
      </section>

      <section class="panel export-history">
        <div class="history-heading">
          <div>
            <p class="eyebrow">历史记录</p>
            <h2>已生成的学习报告</h2>
          </div>
          <span v-if="total > 0" class="history-count">{{ total }} 份</span>
        </div>

        <p v-if="historyError" class="error-text history-error">
          {{ historyError }}
          <button type="button" class="btn" @click="loadExports">重试</button>
        </p>
        <div v-if="loadingHistory" class="empty-state">正在加载导出记录…</div>
        <div v-else-if="exports.length === 0 && !historyError" class="empty-state">
          <strong>还没有学习报告</strong>
          <span>完成上方设置后生成第一份报告。</span>
        </div>
        <div v-else class="history-table-wrap">
          <table class="export-table">
            <thead>
              <tr>
                <th>格式</th>
                <th>包含内容</th>
                <th>状态</th>
                <th>大小</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="exp in exports" :key="exp.id">
                <td><span class="format-badge">{{ exp.report_type }}</span></td>
                <td class="content-summary">{{ exportContentSummary(exp) }}</td>
                <td><span class="status-badge" :class="`status-${exp.status.toLowerCase()}`">{{ statusText(exp.status) }}</span></td>
                <td>{{ exp.file_size != null ? formatSize(exp.file_size) : '—' }}</td>
                <td>{{ formatDate(exp.created_at) }}</td>
                <td>
                  <button
                    v-if="exp.status === 'READY'"
                    type="button"
                    class="table-action btn-small"
                    :disabled="downloadingId === exp.id"
                    @click="downloadExport(exp.id, exp.report_type)"
                  >{{ downloadingId === exp.id ? '下载中…' : '下载' }}</button>
                  <button
                    v-if="exp.status === 'FAILED'"
                    type="button"
                    class="table-action btn-small"
                    @click="retryExport(exp)"
                  >重试</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="downloadError" class="error-text">{{ downloadError }}</p>
        <div v-if="totalPages > 1" class="pagination">
          <button type="button" :disabled="page <= 1 || loadingHistory" @click="changePage(page - 1)">上一页</button>
          <span>第 {{ page }} / {{ totalPages }} 页，共 {{ total }} 条</span>
          <button type="button" :disabled="page >= totalPages || loadingHistory" @click="changePage(page + 1)">下一页</button>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  createExport,
  downloadExportBlob,
  getPaper,
  listExports,
  type ExportListItem,
  type ExportReportResponse,
  type ExportReportType,
  type ExportStatus,
} from '../api'
import { SAFE_POLLING_ERROR, usePolling } from '../composables/usePolling'

const route = useRoute()
const { startPolling: startSharedPolling, stopPolling } = usePolling()
const paperId = computed(() => String(route.params.id))

const formatOptions: Array<{ value: ExportReportType; label: string; description: string }> = [
  { value: 'PDF', label: 'PDF', description: '适合阅读与归档' },
  { value: 'DOCX', label: 'DOCX', description: '适合继续编辑' },
  { value: 'MARKDOWN', label: 'Markdown', description: '适合纯文本保存' },
]
const coreSections = [
  { title: '学习解释', description: '页面总结、翻译和选中文字解释，按页排列' },
  { title: '高亮摘录', description: '保存过的论文原文重点及所在页码' },
  { title: '学习笔记', description: '论文级、页面级和原文锚定笔记' },
]

const paper = ref<Awaited<ReturnType<typeof getPaper>> | null>(null)
const loadError = ref('')
const submitting = ref(false)
const submitError = ref('')
const loadingHistory = ref(false)
const historyError = ref('')
const downloadError = ref('')
const downloadingId = ref<string | null>(null)
const exports = ref<ExportListItem[]>([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
let loadRequestId = 0
let historyRequestId = 0
let downloadRequestId = 0
let destroyed = false

const form = ref({
  report_type: 'PDF' as ExportReportType,
  language: 'zh' as 'zh' | 'en',
  include_metrics: false,
  include_experiment_analysis: false,
})

async function loadData() {
  const requestId = ++loadRequestId
  const requestedPaperId = paperId.value
  loadError.value = ''
  stopPolling()
  try {
    const loadedPaper = await getPaper(requestedPaperId)
    if (destroyed || requestId !== loadRequestId || requestedPaperId !== paperId.value) return
    paper.value = loadedPaper
    await loadExports()
  } catch {
    if (destroyed || requestId !== loadRequestId) return
    loadError.value = '页面加载失败，请稍后重试'
  }
}

async function loadExports() {
  const requestId = ++historyRequestId
  const requestedPaperId = paperId.value
  const requestedPage = page.value
  loadingHistory.value = exports.value.length === 0
  historyError.value = ''
  try {
    const resp = await listExports(requestedPaperId, requestedPage, pageSize)
    if (destroyed || requestId !== historyRequestId || requestedPaperId !== paperId.value || requestedPage !== page.value) return
    exports.value = resp.items
    total.value = resp.total
    if (page.value > totalPages.value) {
      page.value = totalPages.value
      await loadExports()
      return
    }
    if (resp.items.some(item => item.status === 'PENDING' || item.status === 'GENERATING')) startPolling()
    else stopPolling()
  } catch {
    if (destroyed || requestId !== historyRequestId) return
    historyError.value = '导出历史加载失败'
    stopPolling()
  } finally {
    if (!destroyed && requestId === historyRequestId) loadingHistory.value = false
  }
}

function startPolling() {
  const requestedPaperId = paperId.value
  const requestedPage = page.value
  startSharedPolling(
    () => listExports(requestedPaperId, requestedPage, pageSize),
    async resp => {
      if (destroyed || requestedPaperId !== paperId.value || requestedPage !== page.value) return
      exports.value = resp.items
      total.value = resp.total
      if (page.value > totalPages.value) {
        page.value = totalPages.value
        await loadExports()
      }
    },
    resp => !resp.items.some(item => item.status === 'PENDING' || item.status === 'GENERATING'),
    () => {
      if (!destroyed) historyError.value = SAFE_POLLING_ERROR
    },
  )
}

async function submitExport() {
  submitting.value = true
  submitError.value = ''
  try {
    const created = await createExport(paperId.value, { ...form.value })
    page.value = 1
    upsertExport(created)
    await loadExports()
  } catch (error: any) {
    if (error?.response?.status === 409) submitError.value = '当前论文状态暂时无法导出，请稍后重试'
    else if (error?.response?.status === 413) submitError.value = '报告内容过多，请减少可选扩展后重试'
    else submitError.value = '导出失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

function upsertExport(report: ExportReportResponse) {
  const item: ExportListItem = {
    id: report.id,
    paper_id: report.paper_id,
    report_type: report.report_type,
    language: report.language,
    include_metrics: report.include_metrics,
    include_experiment_analysis: report.include_experiment_analysis,
    status: report.status,
    file_size: report.file_size,
    error_message: report.error_message,
    created_at: report.created_at,
    completed_at: report.completed_at,
  }
  exports.value = [item, ...exports.value.filter(existing => existing.id !== item.id)].slice(0, pageSize)
}

async function retryExport(exp: ExportListItem) {
  form.value.report_type = exp.report_type
  form.value.language = exp.language
  form.value.include_metrics = exp.include_metrics
  form.value.include_experiment_analysis = exp.include_experiment_analysis
  await submitExport()
}

async function downloadExport(exportId: string, reportType: ExportReportType) {
  const requestId = ++downloadRequestId
  downloadingId.value = exportId
  downloadError.value = ''
  let url: string | null = null
  let anchor: HTMLAnchorElement | null = null
  try {
    const blob = await downloadExportBlob(exportId)
    if (destroyed || requestId !== downloadRequestId) return
    const ext = { MARKDOWN: '.md', PDF: '.pdf', DOCX: '.docx' }[reportType]
    url = URL.createObjectURL(blob)
    anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `paper_learning_report_${exportId.slice(0, 8)}${ext}`
    document.body.appendChild(anchor)
    anchor.click()
  } catch {
    if (!destroyed && requestId === downloadRequestId) downloadError.value = '下载失败，请稍后重试'
  } finally {
    if (anchor?.parentNode) anchor.parentNode.removeChild(anchor)
    if (url) URL.revokeObjectURL(url)
    if (!destroyed && requestId === downloadRequestId) downloadingId.value = null
  }
}

function statusText(status: ExportStatus) {
  return { PENDING: '等待生成', GENERATING: '生成中', READY: '已完成', FAILED: '生成失败' }[status]
}

function exportContentSummary(exp: ExportListItem) {
  const parts = ['学习内容', '审阅（有则）']
  if (exp.include_metrics) parts.push('指标')
  if (exp.include_experiment_analysis) parts.push('实验')
  return parts.join(' · ')
}

function changePage(nextPage: number) {
  if (nextPage < 1 || nextPage > totalPages.value || nextPage === page.value) return
  page.value = nextPage
  stopPolling()
  void loadExports()
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(value: string) {
  try {
    return new Date(value).toLocaleString('zh-CN')
  } catch {
    return value
  }
}

watch(paperId, () => {
  page.value = 1
  total.value = 0
  exports.value = []
  paper.value = null
  void loadData()
})

onMounted(loadData)
onUnmounted(() => {
  destroyed = true
  loadRequestId++
  historyRequestId++
  downloadRequestId++
  stopPolling()
})
</script>

<style scoped>
.report-export {
  --navy: #25224f;
  --navy-soft: #eeedf8;
  --ink: #16172a;
  --muted: #686c7d;
  --line: #dddfea;
  max-width: 1180px;
  margin: 0 auto;
  padding: 36px 28px 64px;
  color: var(--ink);
}
.page-header,
.history-heading,
.panel-heading,
.language-row,
.option-row,
.pagination {
  display: flex;
  align-items: center;
}
.page-header {
  justify-content: space-between;
  gap: 28px;
  padding-bottom: 26px;
  border-bottom: 1px solid var(--line);
}
.eyebrow {
  margin: 0 0 7px;
  color: #65618c;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .14em;
}
.page-header h1 {
  margin: 0;
  font-size: clamp(28px, 3vw, 40px);
  letter-spacing: -.035em;
}
.paper-name {
  margin: 13px 0 6px;
  font-size: 17px;
  font-weight: 650;
}
.paper-meta {
  display: flex;
  gap: 15px;
  color: var(--muted);
  font-size: 13px;
}
.paper-meta span + span::before {
  content: '·';
  margin-right: 15px;
}
.exit-button,
.secondary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 18px;
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--navy);
  background: #fff;
  font-weight: 650;
  text-decoration: none;
}
.export-grid {
  display: grid;
  grid-template-columns: minmax(0, .95fr) minmax(0, 1.05fr);
  gap: 20px;
  margin-top: 24px;
}
.panel {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 10px 30px rgba(24, 26, 48, .045);
}
.export-form,
.content-panel {
  padding: 24px;
}
.panel-heading {
  gap: 12px;
  margin-bottom: 22px;
}
.panel-heading h2,
.history-heading h2 {
  margin: 0;
  font-size: 20px;
}
.panel-heading p,
.language-row p,
.included-item p,
.option-row p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}
.step {
  display: inline-grid;
  width: 38px;
  height: 38px;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 9px;
  color: #fff;
  background: var(--navy);
  font-size: 12px;
  font-weight: 700;
}
.field-label,
.section-label {
  display: block;
  margin: 0 0 9px;
  font-size: 13px;
  font-weight: 700;
}
.format-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.format-option {
  min-height: 78px;
  padding: 13px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  text-align: left;
}
.format-option strong,
.format-option span {
  display: block;
}
.format-option span {
  margin-top: 5px;
  color: var(--muted);
  font-size: 11px;
}
.format-option.active {
  border-color: var(--navy);
  background: var(--navy-soft);
  box-shadow: inset 0 0 0 1px var(--navy);
}
.language-row {
  justify-content: space-between;
  gap: 18px;
  margin: 22px 0;
  padding-top: 19px;
  border-top: 1px solid var(--line);
}
.language-row .field-label {
  margin-bottom: 0;
}
.language-row select {
  min-width: 128px;
  height: 38px;
  padding: 0 11px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
.btn-primary {
  display: flex;
  width: 100%;
  min-height: 46px;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  border: 0;
  border-radius: 9px;
  color: #fff;
  background: var(--navy);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: .55;
  cursor: wait;
}
.ready-hint {
  margin: 11px 0 0;
  color: #737789;
  font-size: 12px;
  text-align: center;
}
.included-list {
  display: grid;
  gap: 9px;
}
.included-item {
  display: flex;
  gap: 11px;
  padding: 12px 13px;
  border-radius: 9px;
  background: #f7f8fb;
}
.included-icon {
  display: inline-grid;
  width: 22px;
  height: 22px;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 50%;
  color: #fff;
  background: #3d7b5b;
  font-size: 12px;
}
.optional-label {
  margin-top: 20px;
}
.option-row {
  justify-content: space-between;
  gap: 18px;
  min-height: 54px;
  padding: 10px 2px;
  border-top: 1px solid #ececf2;
  cursor: pointer;
}
.option-row--automatic {
  cursor: default;
}
.option-row--automatic > span {
  padding: 4px 9px;
  border-radius: 999px;
  color: #5b587b;
  background: var(--navy-soft);
  font-size: 11px;
  font-weight: 700;
}
.toggle-input {
  width: 38px;
  height: 21px;
  accent-color: var(--navy);
  cursor: pointer;
}
.export-history {
  margin-top: 20px;
  padding: 24px;
}
.history-heading {
  justify-content: space-between;
  margin-bottom: 18px;
}
.history-count,
.format-badge,
.status-badge {
  display: inline-flex;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}
.history-count {
  padding: 6px 10px;
  color: #5b587b;
  background: var(--navy-soft);
}
.history-table-wrap {
  overflow-x: auto;
}
.export-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.export-table th,
.export-table td {
  padding: 13px 10px;
  border-bottom: 1px solid #ececf2;
  text-align: left;
  white-space: nowrap;
}
.export-table th {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .04em;
}
.content-summary {
  color: #565a6c;
}
.format-badge {
  padding: 4px 8px;
  color: var(--navy);
  background: var(--navy-soft);
}
.status-badge {
  padding: 4px 8px;
}
.status-ready { color: #23633f; background: #e5f3eb; }
.status-failed { color: #a23a42; background: #fdebed; }
.status-pending,
.status-generating { color: #7b5c16; background: #fbf2d8; }
.table-action,
.pagination button,
.history-error button,
.error-banner button {
  border: 1px solid var(--line);
  border-radius: 7px;
  color: var(--navy);
  background: #fff;
  cursor: pointer;
}
.table-action {
  padding: 6px 11px;
  font-weight: 650;
}
.empty-state {
  display: grid;
  min-height: 120px;
  place-content: center;
  gap: 6px;
  color: var(--muted);
  background: #f8f9fb;
  text-align: center;
}
.empty-state strong {
  color: var(--ink);
}
.pagination {
  justify-content: center;
  gap: 12px;
  margin-top: 18px;
  color: var(--muted);
  font-size: 12px;
}
.pagination button {
  padding: 6px 10px;
}
.error-banner,
.not-ready-notice {
  margin-top: 22px;
  padding: 18px;
  border: 1px solid #f0c5c8;
  border-radius: 10px;
  background: #fff4f4;
}
.error-banner {
  display: flex;
  justify-content: space-between;
}
.not-ready-notice h2 {
  margin: 0 0 6px;
}
.not-ready-notice p {
  margin: 0 0 14px;
  color: var(--muted);
}
.error-text {
  color: #b33d45;
  font-size: 13px;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
@media (max-width: 820px) {
  .report-export { padding: 24px 14px 48px; }
  .export-grid { grid-template-columns: 1fr; }
  .format-options { grid-template-columns: 1fr; }
  .format-option { min-height: 62px; }
}
</style>
