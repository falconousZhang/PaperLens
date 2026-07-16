<template>
  <div class="report-export" v-if="paper">
    <div class="header">
      <h2>{{ paper.title }}</h2>
      <div class="meta">
        <span>文件: {{ paper.filename }}</span>
        <span>页数: {{ paper.page_count ?? '-' }}</span>
      </div>
      <div class="nav-links">
        <router-link :to="{ name: 'paper-detail', params: { id: paper.id } }">返回论文详情</router-link>
        <router-link to="/papers">返回论文列表</router-link>
      </div>
    </div>

    <div v-if="paper.status !== 'PARSED'" class="not-ready-notice">
      <p>论文尚未解析完成，无法导出报告。</p>
      <router-link :to="{ name: 'paper-detail', params: { id: paper.id } }">返回论文详情</router-link>
    </div>

    <template v-else>
      <div v-if="loadError" class="error-msg">
        <p>{{ loadError }}</p>
        <button @click="loadData" class="btn">重试</button>
      </div>

      <div class="export-form">
        <h3>创建导出报告</h3>
        <div class="form-row">
          <label for="report-type">格式</label>
          <select id="report-type" v-model="form.report_type">
            <option value="MARKDOWN">Markdown</option>
            <option value="PDF">PDF</option>
            <option value="DOCX">DOCX</option>
          </select>
        </div>
        <div class="form-row">
          <label for="report-lang">语言</label>
          <select id="report-lang" v-model="form.language">
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
        </div>
        <div class="form-row">
          <label>
            <input type="checkbox" v-model="form.include_metrics" />
            包含指标数据
          </label>
        </div>
        <div class="form-row">
          <label>
            <input type="checkbox" v-model="form.include_experiment_analysis" />
            包含实验分析
          </label>
        </div>
        <button
          @click="submitExport"
          :disabled="submitting"
          class="btn btn-primary"
        >
          {{ submitting ? '提交中...' : '导出报告' }}
        </button>
        <p v-if="submitError" class="error-text">{{ submitError }}</p>
      </div>

      <div class="export-history">
        <h3>导出历史</h3>
        <p v-if="historyError" class="error-text">
          {{ historyError }}
          <button @click="loadExports" class="btn btn-small">重试</button>
        </p>
        <div v-if="loadingHistory" class="loading-text">加载中...</div>
        <div v-else-if="exports.length === 0 && !historyError" class="empty-text">暂无导出记录</div>
        <table v-else-if="exports.length > 0" class="export-table">
          <thead>
            <tr>
              <th>格式</th>
              <th>语言</th>
              <th>状态</th>
              <th>大小</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="exp in exports" :key="exp.id">
              <td>{{ exp.report_type }}</td>
              <td>{{ exp.language === 'zh' ? '中文' : 'English' }}</td>
              <td>
                <span v-if="exp.status === 'PENDING'">等待生成</span>
                <span v-else-if="exp.status === 'GENERATING'">生成中</span>
                <span v-else-if="exp.status === 'READY'">已完成</span>
                <span v-else-if="exp.status === 'FAILED'">生成失败</span>
                <span v-else>{{ exp.status }}</span>
              </td>
              <td>{{ exp.file_size != null ? formatSize(exp.file_size) : '-' }}</td>
              <td>{{ formatDate(exp.created_at) }}</td>
              <td>
                <button
                  v-if="exp.status === 'READY'"
                  @click="downloadExport(exp.id, exp.report_type)"
                  :disabled="downloadingId === exp.id"
                  class="btn btn-small"
                >
                  {{ downloadingId === exp.id ? '下载中...' : '下载' }}
                </button>
                <button
                  v-if="exp.status === 'FAILED'"
                  @click="retryExport(exp)"
                  class="btn btn-small"
                >
                  重试
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="downloadError" class="error-text">{{ downloadError }}</p>
        <div v-if="totalPages > 1" class="pagination">
          <button class="btn btn-small" :disabled="page <= 1 || loadingHistory" @click="changePage(page - 1)">上一页</button>
          <span>第 {{ page }} / {{ totalPages }} 页，共 {{ total }} 条</span>
          <button class="btn btn-small" :disabled="page >= totalPages || loadingHistory" @click="changePage(page + 1)">下一页</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  getPaper,
  createExport,
  listExports,
  downloadExportBlob,
  type ExportListItem,
  type ExportReportType,
  type ExportReportResponse,
} from '../api'

const route = useRoute()
const paperId = computed(() => String(route.params.id))

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
let pollTimer: ReturnType<typeof setTimeout> | null = null
let loadRequestId = 0
let historyRequestId = 0
let downloadRequestId = 0
let destroyed = false

const form = ref({
  report_type: 'MARKDOWN' as 'MARKDOWN' | 'PDF' | 'DOCX',
  language: 'zh' as 'zh' | 'en',
  include_metrics: true,
  include_experiment_analysis: true,
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
    loadError.value = '加载失败'
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
    if (
      destroyed
      || requestId !== historyRequestId
      || requestedPaperId !== paperId.value
      || requestedPage !== page.value
    ) return
    exports.value = resp.items
    total.value = resp.total
    if (page.value > totalPages.value) {
      page.value = totalPages.value
      await loadExports()
      return
    }
    const hasPending = resp.items.some(e => e.status === 'PENDING' || e.status === 'GENERATING')
    if (hasPending) {
      startPolling()
    } else {
      stopPolling()
    }
  } catch {
    if (destroyed || requestId !== historyRequestId) return
    historyError.value = '导出历史加载失败'
    stopPolling()
  } finally {
    if (!destroyed && requestId === historyRequestId) loadingHistory.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setTimeout(async () => {
    pollTimer = null
    await loadExports()
  }, 3000)
}

function stopPolling() {
  if (pollTimer !== null) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

async function submitExport() {
  submitting.value = true
  submitError.value = ''
  try {
    const created = await createExport(paperId.value, {
      report_type: form.value.report_type,
      language: form.value.language,
      include_metrics: form.value.include_metrics,
      include_experiment_analysis: form.value.include_experiment_analysis,
    })
    page.value = 1
    upsertExport(created)
    await loadExports()
  } catch (e: any) {
    if (e?.response?.status === 409) {
      submitError.value = '审阅结果尚未就绪，请先完成论文审阅'
    } else if (e?.response?.status === 413) {
      submitError.value = '报告超过大小上限'
    } else {
      submitError.value = '导出失败，请稍后重试'
    }
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
    const ext = { MARKDOWN: '.md', PDF: '.pdf', DOCX: '.docx' }[reportType] || '.md'
    url = URL.createObjectURL(blob)
    anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `report_${exportId.slice(0, 8)}${ext}`
    document.body.appendChild(anchor)
    anchor.click()
  } catch {
    if (!destroyed && requestId === downloadRequestId) downloadError.value = '下载失败，请稍后重试'
  } finally {
    if (anchor?.parentNode) anchor.parentNode.removeChild(anchor)
    if (url !== null) URL.revokeObjectURL(url)
    if (!destroyed && requestId === downloadRequestId) downloadingId.value = null
  }
}

function changePage(nextPage: number) {
  if (nextPage < 1 || nextPage > totalPages.value || nextPage === page.value) return
  page.value = nextPage
  stopPolling()
  void loadExports()
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dt: string): string {
  try {
    return new Date(dt).toLocaleString('zh-CN')
  } catch {
    return dt
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
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}
.header h2 {
  margin: 0 0 8px;
}
.meta {
  display: flex;
  gap: 16px;
  color: #666;
  margin-bottom: 12px;
}
.nav-links {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}
.nav-links a {
  color: #409eff;
  text-decoration: none;
}
.not-ready-notice {
  padding: 20px;
  background: #fff3e0;
  border-radius: 6px;
}
.export-form {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 6px;
  margin-bottom: 24px;
}
.export-form h3 {
  margin: 0 0 16px;
}
.form-row {
  margin-bottom: 12px;
}
.form-row label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
}
.form-row select {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  background: #fff;
}
.btn-primary {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}
.btn-primary:disabled {
  background: #a0cfff;
  border-color: #a0cfff;
  cursor: not-allowed;
}
.btn-small {
  padding: 4px 10px;
  font-size: 13px;
}
.error-text {
  color: #f56c6c;
  margin-top: 8px;
}
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}
.export-history h3 {
  margin: 0 0 12px;
}
.export-table {
  width: 100%;
  border-collapse: collapse;
}
.export-table th,
.export-table td {
  padding: 8px 12px;
  border: 1px solid #eee;
  text-align: left;
}
.export-table th {
  background: #f5f5f5;
  font-weight: 500;
}
.loading-text,
.empty-text {
  color: #999;
  padding: 12px 0;
}
</style>
