<template>
  <div class="experiment-data" v-if="paper">
    <div class="header">
      <h2>{{ paper.title }}</h2>
      <div class="meta">
        <span>文件: {{ paper.filename }}</span>
        <span>页数: {{ paper.page_count ?? '-' }}</span>
        <span :class="'status-' + paper.status.toLowerCase()">{{ paper.status }}</span>
      </div>
      <div class="nav-links">
        <router-link :to="{ name: 'paper-read', params: { id: paper.id } }" class="button-link button-link--primary">返回阅读</router-link>
        <router-link to="/papers" class="button-link">返回论文列表</router-link>
      </div>
    </div>

    <div v-if="paper.status !== 'PARSED'" class="not-ready-notice">
      <p>{{ notReadyMessage }}</p>
      <router-link :to="{ name: 'paper-read', params: { id: paper.id } }" class="button-link">返回阅读</router-link>
    </div>

    <template v-else>
      <div v-if="loadError" class="error-msg" role="alert">
        <p>{{ loadError }}</p>
        <button @click="loadAll" class="retry-btn">重试</button>
      </div>

      <div class="upload-section">
        <h3>上传实验数据</h3>
        <div class="upload-hint">支持非空 .csv、.xlsx、.xls 文件，最大 20MB</div>
        <div class="upload-row">
          <label for="experiment-file-input">选择实验文件：</label>
          <input
            id="experiment-file-input"
            ref="fileInputRef"
            type="file"
            accept=".csv,.xlsx,.xls"
            :disabled="uploading"
            @change="onFileSelected"
            class="file-input"
          />
          <button
            v-if="selectedFile"
            @click="onUpload"
            :disabled="uploading"
            class="primary-btn"
          >{{ uploading ? '上传中...' : '上传' }}</button>
        </div>
        <div v-if="uploadError" class="upload-error" role="alert">{{ uploadError }}</div>
      </div>

      <div v-if="filesLoading" class="loading-msg">加载实验文件列表...</div>

      <div v-else-if="files.length > 0" class="files-section">
        <h3>实验文件</h3>
        <table class="files-table" role="table">
          <thead>
            <tr>
              <th scope="col">选择</th>
              <th scope="col">文件名</th>
              <th scope="col">类型</th>
              <th scope="col">大小</th>
              <th scope="col">行数</th>
              <th scope="col">列数</th>
              <th scope="col">上传时间</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="f in files"
              :key="f.id"
              :class="{ 'selected-row': selectedFileId === f.id }"
              @click="selectFile(f.id)"
              class="file-row"
            >
              <td><input type="radio" :checked="selectedFileId === f.id" :value="f.id" name="file-select" :aria-label="'选择 ' + f.filename" @change.stop="selectFile(f.id)" /></td>
              <td>{{ f.filename }}</td>
              <td>{{ f.file_type }}</td>
              <td>{{ (f.file_size / 1024 / 1024).toFixed(1) }} MB</td>
              <td>{{ f.row_count }}</td>
              <td>{{ f.column_count }}</td>
              <td>{{ formatTime(f.created_at) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-if="filesTotal > filesPageSize" class="pagination" aria-label="实验文件分页">
          <button :disabled="filesPage <= 1 || filesLoading" @click="changeFilesPage(filesPage - 1)">上一页</button>
          <span>第 {{ filesPage }} / {{ filesTotalPages }} 页，共 {{ filesTotal }} 个文件</span>
          <button :disabled="filesPage >= filesTotalPages || filesLoading" @click="changeFilesPage(filesPage + 1)">下一页</button>
        </div>
      </div>

      <div v-else class="empty-files">
        <p>暂无实验数据文件，请上传</p>
      </div>

      <div v-if="selectedFileId" class="analysis-section">
        <div class="file-detail-section">
          <h3>可信文件结构</h3>
          <div v-if="fileDetailLoading" class="loading-msg">加载文件结构...</div>
          <div v-else-if="fileDetailError" class="error-msg" role="alert">
            <p>{{ fileDetailError }}</p>
            <button @click="retryFileDetail" class="retry-btn">重试文件详情</button>
          </div>
          <template v-else-if="selectedFileDetail">
            <p class="detail-meta">
              {{ selectedFileDetail.file_type }} · {{ selectedFileDetail.row_count }} 行 · {{ selectedFileDetail.column_count }} 列
              <span v-if="selectedFileDetail.columns_info.sheet_name"> · 工作表：{{ selectedFileDetail.columns_info.sheet_name }}</span>
            </p>
            <table class="columns-table" role="table">
              <thead>
                <tr>
                  <th scope="col">列名</th>
                  <th scope="col">类型</th>
                  <th scope="col">允许空值</th>
                  <th scope="col">空值数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="column in selectedFileDetail.columns_info.columns" :key="column.name">
                  <td>{{ column.name }}</td>
                  <td>{{ column.dtype }}</td>
                  <td>{{ column.nullable ? '是' : '否' }}</td>
                  <td>{{ column.null_count }}</td>
                </tr>
              </tbody>
            </table>
          </template>
        </div>

        <div class="analysis-header">
          <h3>统计分析</h3>
          <button
            v-if="!experimentResult && !analysisActive"
            @click="startAnalysis"
            :disabled="analysisSubmitting"
            class="primary-btn"
          >{{ analysisSubmitting ? '提交中...' : '开始分析' }}</button>
        </div>

        <div v-if="analysisActive" class="task-progress" aria-live="polite">
          <p>实验数据分析进行中...</p>
          <div class="progress-bar-wrapper">
            <div
              class="progress-bar-fill"
              :style="{ width: analysisProgress + '%' }"
              role="progressbar"
              :aria-valuenow="analysisProgress"
              aria-valuemin="0"
              aria-valuemax="100"
            ></div>
          </div>
          <span class="progress-text">{{ analysisProgress }}%</span>
          <div v-if="pollError" class="poll-error" role="alert">
            <p>轮询失败：{{ pollError }}</p>
            <button @click="retryPoll" class="retry-btn">重试轮询</button>
          </div>
        </div>

        <div v-if="analysisFailed && !analysisActive" class="failed-notice" role="alert">
          <p>实验数据分析失败{{ analysisTaskError ? '：' + analysisTaskError : '' }}</p>
          <button @click="startAnalysis" :disabled="analysisSubmitting" class="retry-btn">重新分析</button>
        </div>

        <div v-if="experimentResult" class="result-section">
          <h4>统计摘要</h4>
          <table class="stats-table" role="table">
            <thead>
              <tr>
                <th scope="col">列名</th>
                <th scope="col">类型</th>
                <th scope="col">有效值数</th>
                <th scope="col">空值数</th>
                <th scope="col">均值</th>
                <th scope="col">标准差</th>
                <th scope="col">最小值</th>
                <th scope="col">最大值</th>
                <th scope="col">中位数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="col in experimentResult.summary_stats.columns" :key="col.name">
                <td>{{ col.name }}</td>
                <td>{{ col.dtype }}</td>
                <td>{{ col.count }}</td>
                <td>{{ col.null_count }}</td>
                <td>{{ formatStat(col.stats?.mean) }}</td>
                <td>{{ formatStat(col.stats?.stddev) }}</td>
                <td>{{ formatStat(col.stats?.min) }}</td>
                <td>{{ formatStat(col.stats?.max) }}</td>
                <td>{{ formatStat(col.stats?.median) }}</td>
              </tr>
            </tbody>
          </table>

          <div class="comparison-section">
            <h4>指标交叉验证</h4>

            <div v-if="succeededMetricTasks.length === 0 && !comparisonResult" class="no-metrics-notice">
              <p>当前论文没有成功的指标提取任务，无法进行交叉验证</p>
              <router-link :to="{ name: 'paper-metrics', params: { id: paper.id } }" class="button-link button-link--primary">前往指标分析</router-link>
            </div>

            <template v-else>
              <div class="comparison-controls">
                <label for="metric-task-select">指标任务：</label>
                <select id="metric-task-select" v-model="selectedMetricTaskId" :disabled="comparisonSubmitting || comparisonResult !== null">
                  <option v-if="comparisonSourceMissing && comparisonResult" :value="comparisonResult.metric_task_id">
                    已有交叉验证来源
                  </option>
                  <option v-for="t in succeededMetricTasks" :key="t.id" :value="t.id">
                    {{ formatTaskLabel(t) }}
                  </option>
                </select>
                <button
                  v-if="!comparisonResult"
                  @click="startComparison"
                  :disabled="comparisonSubmitting || !selectedMetricTaskId"
                  class="primary-btn"
                >{{ comparisonSubmitting ? '提交中...' : '开始交叉验证' }}</button>
              </div>

              <p v-if="comparisonResult" class="comparison-locked" role="status">交叉验证结果已生成，来源指标任务已锁定，不能在此页面覆盖。</p>
              <div v-if="comparisonError" class="comparison-error" role="alert">{{ comparisonError }}</div>

              <div v-if="comparisonResult" class="comparison-table-wrapper">
                <table class="comparison-table" role="table">
                  <thead>
                    <tr>
                      <th scope="col">指标名</th>
                      <th scope="col">Checkpoint</th>
                      <th scope="col">列名</th>
                      <th scope="col">统计量</th>
                      <th scope="col">论文值</th>
                      <th scope="col">实验值</th>
                      <th scope="col">差值（实验值 - 论文值）</th>
                      <th scope="col">绝对差值</th>
                      <th scope="col">相对差值</th>
                      <th scope="col">允许差值</th>
                      <th scope="col">状态</th>
                      <th scope="col">原因</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(c, idx) in comparisonResult.comparisons" :key="idx">
                      <td>{{ c.metric_name }}</td>
                      <td>{{ checkpointLabel(c.checkpoint_type) }}</td>
                      <td>{{ c.column_name ?? '—' }}</td>
                      <td>{{ c.statistic ?? '—' }}</td>
                      <td>{{ formatFinite(c.paper_value) }}</td>
                      <td>{{ formatFiniteNull(c.experiment_value) }}</td>
                      <td>{{ formatFiniteNull(c.diff) }}</td>
                      <td>{{ formatFiniteNull(c.absolute_diff) }}</td>
                      <td>{{ formatFiniteNull(c.relative_diff) }}</td>
                      <td>{{ formatFiniteNull(c.allowed_diff) }}</td>
                      <td><span :class="'status-' + c.status.toLowerCase()">{{ comparisonStatusLabel(c.status) }}</span></td>
                      <td>{{ reasonLabel(c.reason) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </div>
        </div>

        <div v-else-if="!analysisActive && !analysisFailed && !resultNotFound" class="no-result">
          <p>尚未分析，请点击"开始分析"</p>
        </div>

        <div v-if="resultNotFound" class="no-result">
          <p>尚未分析，请点击"开始分析"</p>
        </div>
      </div>
    </template>
  </div>
  <div v-else-if="loadError" class="error-msg" role="alert">
    <p>{{ loadError }}</p>
    <button @click="loadAll" class="retry-btn">重试</button>
  </div>
  <div v-else class="loading-msg">加载中...</div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  getPaper,
  listTasks,
  getTask,
  listExperimentFiles,
  getExperimentFile,
  uploadExperimentFile,
  createExperimentAnalysis,
  getExperimentResult,
  createComparisons,
  type PaperDetail,
  type TaskDetail,
  type ExperimentFileListItem,
  type ExperimentFileMetadata,
  type ExperimentResultResponse,
  type PostComparisonsResponse,
} from '../api'
import { SAFE_POLLING_ERROR, usePolling } from '../composables/usePolling'

const route = useRoute()
const { startPolling: startSharedPolling, stopPolling } = usePolling()
const CHECKPOINT_LABELS: Record<string, string> = {
  BEST: '最佳',
  FINAL: '最终',
  MAX: '最大',
  MEAN: '均值',
  LAST: '最近',
  UNKNOWN: '未知',
}

const COMPARISON_STATUS_LABELS: Record<string, string> = {
  MATCH: '匹配',
  MISMATCH: '不匹配',
  UNVERIFIABLE: '不可验证',
}

const REASON_LABELS: Record<string, string> = {
  AMBIGUOUS_PAPER_METRIC: '论文指标歧义',
  NO_EXPERIMENT_COLUMN: '无对应实验列',
  AMBIGUOUS_EXPERIMENT_COLUMN: '实验列歧义',
  UNSUPPORTED_CHECKPOINT: '不支持的检查点',
  EMPTY_NORMALIZED_NAME: '标准化名称为空',
}

const MAX_UPLOAD_BYTES = 20 * 1024 * 1024
const ALLOWED_UPLOAD_EXTENSIONS = new Set(['csv', 'xlsx', 'xls'])
const SAFE_ANALYSIS_ERRORS = new Set([
  '实验文件完整性校验失败',
  '统计分析计算失败',
  '数值安全检查失败',
  '文件类型不匹配',
  '文件存储读取失败',
  '实验分析失败，请稍后重试',
])

function checkpointLabel(ct: string): string {
  return CHECKPOINT_LABELS[ct] || ct
}

function comparisonStatusLabel(s: string): string {
  return COMPARISON_STATUS_LABELS[s] || s
}

function reasonLabel(r: string | null): string {
  if (r === null) return '-'
  return REASON_LABELS[r] || r
}

function formatTime(iso: string): string {
  const value = new Date(iso)
  return Number.isNaN(value.getTime()) ? '—' : value.toLocaleString()
}

function formatStat(value: number | null | undefined): string {
  if (value === null || value === undefined) return '\u2014'
  if (!Number.isFinite(value)) return '\u2014'
  return String(value)
}

function formatFinite(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return String(value)
}

function formatFiniteNull(value: number | null): string {
  if (value === null) return '—'
  if (!Number.isFinite(value)) return '—'
  return String(value)
}

function responseStatus(error: unknown): number | undefined {
  return (error as { response?: { status?: number } })?.response?.status
}

function safeRequestError(error: unknown, fallback: string): string {
  const status = responseStatus(error)
  if (status === 401) return '登录状态已失效，请重新登录。'
  if (status === 404) return '请求的资源不存在或无权访问。'
  if (status === 413) return '文件或数据超过允许大小。'
  if (status === 415) return '文件格式不支持，请选择 CSV、XLSX 或 XLS。'
  if (status === 422) return '提交内容无效，请检查后重试。'
  if (status === 409) return fallback
  if (status === undefined) return '网络连接失败，请稍后重试。'
  return fallback
}

function safeAnalysisError(value: string | null | undefined): string {
  if (value && SAFE_ANALYSIS_ERRORS.has(value)) return value
  return '实验分析失败，请稍后重试'
}

function formatTaskLabel(t: TaskDetail): string {
  const time = formatTime(t.created_at)
  const status = t.status === 'SUCCEEDED' ? '成功' : t.status === 'FAILED' ? '失败' : t.status
  return `${time} (${status})`
}

const paper = ref<PaperDetail | null>(null)
const tasks = ref<TaskDetail[]>([])
const files = ref<ExperimentFileListItem[]>([])
const filesTotal = ref(0)
const filesPage = ref(1)
const filesPageSize = 20
const loadError = ref('')
const filesLoading = ref(false)
const selectedFileId = ref<string | null>(null)
const selectedFileDetail = ref<ExperimentFileMetadata | null>(null)
const fileDetailLoading = ref(false)
const fileDetailError = ref('')
const experimentResult = ref<ExperimentResultResponse | null>(null)
const resultNotFound = ref(false)
const uploading = ref(false)
const uploadError = ref('')
const selectedFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const analysisSubmitting = ref(false)
const analysisActive = ref(false)
const analysisProgress = ref(0)
const analysisTaskId = ref<string | null>(null)
const analysisFailed = ref(false)
const analysisTaskError = ref('')
const pollError = ref('')
const selectedMetricTaskId = ref<string | null>(null)
const comparisonResult = ref<PostComparisonsResponse | null>(null)
const comparisonSubmitting = ref(false)
const comparisonError = ref('')

let requestGeneration = 0
let selectionGeneration = 0
let filesRequestId = 0

const notReadyMessage = computed(() => {
  if (!paper.value) return ''
  const s = paper.value.status
  if (s === 'UPLOADING') return '论文正在上传中，请稍候...'
  if (s === 'PROCESSING') return '论文正在解析中，请稍候...'
  if (s === 'FAILED') return '论文解析失败，无法查看实验数据。'
  return '论文尚未解析完成，无法查看实验数据。'
})

const succeededMetricTasks = computed(() => tasks.value
  .filter(t => t.task_type === 'METRIC_EXTRACTION' && t.status === 'SUCCEEDED')
  .sort((left, right) => {
    const timeDiff = Date.parse(right.created_at) - Date.parse(left.created_at)
    return Number.isFinite(timeDiff) && timeDiff !== 0
      ? timeDiff
      : right.id.localeCompare(left.id)
  }))

const filesTotalPages = computed(() => Math.max(1, Math.ceil(filesTotal.value / filesPageSize)))
const comparisonSourceMissing = computed(() => comparisonResult.value !== null
  && !succeededMetricTasks.value.some(task => task.id === comparisonResult.value?.metric_task_id))

function selectedContextIsCurrent(pageGen: number, selectionGen: number, fileId: string): boolean {
  return pageGen === requestGeneration
    && selectionGen === selectionGeneration
    && selectedFileId.value === fileId
}

function startPolling(taskId: string, fileId: string) {
  const pageGen = requestGeneration
  const selectionGen = selectionGeneration
  analysisTaskId.value = taskId
  startSharedPolling(
    () => getTask(taskId),
    async t => {
      if (!selectedContextIsCurrent(pageGen, selectionGen, fileId)) return
      if (
        t.id !== taskId
        || t.paper_id !== paper.value?.id
        || t.task_type !== 'EXPERIMENT_ANALYSIS'
        || t.experiment_file_id !== fileId
      ) {
        stopPolling()
        analysisActive.value = false
        analysisTaskId.value = null
        loadError.value = '任务上下文不一致，请重新加载。'
        return
      }
      const progress = Number(t.progress ?? 0)
      analysisProgress.value = Number.isFinite(progress) ? Math.min(100, Math.max(0, Math.round(progress))) : 0
      if (t.status === 'PENDING' || t.status === 'RUNNING') return
      analysisActive.value = false
      analysisTaskId.value = null
      if (t.status === 'SUCCEEDED') {
        await loadExperimentResult(pageGen, selectionGen, fileId)
      } else {
        analysisFailed.value = true
        analysisTaskError.value = safeAnalysisError(t.error_message)
      }
    },
    t => t.status !== 'PENDING' && t.status !== 'RUNNING',
    () => {
      if (!selectedContextIsCurrent(pageGen, selectionGen, fileId)) return
      pollError.value = SAFE_POLLING_ERROR
    },
  )
}

function retryPoll() {
  pollError.value = ''
  if (analysisTaskId.value && selectedFileId.value) {
    startPolling(analysisTaskId.value, selectedFileId.value)
  } else {
    loadError.value = '分析任务上下文已失效，请重新加载页面。'
  }
}

function applyExperimentResult(result: ExperimentResultResponse) {
  experimentResult.value = result
  resultNotFound.value = false
  const comparisons = result.metric_comparisons
  if (!comparisons || comparisons.length === 0) {
    comparisonResult.value = null
    return
  }
  const metricTaskId = comparisons[0]!.metric_task_id
  if (!comparisons.every(item => item.metric_task_id === metricTaskId)) {
    experimentResult.value = null
    comparisonResult.value = null
    loadError.value = '交叉验证结果状态异常，请稍后重试。'
    return
  }
  selectedMetricTaskId.value = metricTaskId
  comparisonResult.value = {
    file_id: result.file_id,
    experiment_result_id: result.id,
    metric_task_id: metricTaskId,
    comparisons,
    duplicate: true,
  }
}

async function loadExperimentResult(
  pageGen = requestGeneration,
  selectionGen = selectionGeneration,
  fileId = selectedFileId.value,
) {
  if (!fileId) return
  try {
    const result = await getExperimentResult(fileId)
    if (!selectedContextIsCurrent(pageGen, selectionGen, fileId)) return
    if (result.file_id !== fileId) {
      loadError.value = '实验分析结果上下文异常，请稍后重试。'
      return
    }
    applyExperimentResult(result)
  } catch (error: unknown) {
    if (!selectedContextIsCurrent(pageGen, selectionGen, fileId)) return
    if (responseStatus(error) === 404) {
      experimentResult.value = null
      comparisonResult.value = null
      resultNotFound.value = true
    } else {
      loadError.value = safeRequestError(error, '加载分析结果失败，请重试。')
    }
  }
}

async function loadFileDetail(
  pageGen = requestGeneration,
  selectionGen = selectionGeneration,
  fileId = selectedFileId.value,
) {
  if (!fileId || !paper.value) return
  fileDetailLoading.value = true
  fileDetailError.value = ''
  try {
    const detail = await getExperimentFile(fileId)
    if (!selectedContextIsCurrent(pageGen, selectionGen, fileId)) return
    if (detail.id !== fileId || detail.paper_id !== paper.value.id) {
      selectedFileDetail.value = null
      fileDetailError.value = '实验文件详情上下文异常，请重新选择文件。'
      return
    }
    selectedFileDetail.value = detail
  } catch (error: unknown) {
    if (!selectedContextIsCurrent(pageGen, selectionGen, fileId)) return
    selectedFileDetail.value = null
    fileDetailError.value = safeRequestError(error, '加载文件结构失败，请重试。')
  } finally {
    if (selectedContextIsCurrent(pageGen, selectionGen, fileId)) fileDetailLoading.value = false
  }
}

function retryFileDetail() {
  loadFileDetail()
}

async function loadFiles(gen = requestGeneration, page = filesPage.value) {
  const id = typeof route.params.id === 'string' ? route.params.id : ''
  const requestId = ++filesRequestId
  filesLoading.value = true
  try {
    const result = await listExperimentFiles(id, page, filesPageSize)
    if (gen !== requestGeneration || requestId !== filesRequestId) return
    files.value = result.items
    filesTotal.value = result.total
    filesPage.value = result.page
  } catch (error: unknown) {
    if (gen !== requestGeneration || requestId !== filesRequestId) return
    loadError.value = safeRequestError(error, '加载实验文件失败，请重试。')
  } finally {
    if (gen === requestGeneration && requestId === filesRequestId) filesLoading.value = false
  }
}

function resetSelectedFileState() {
  selectionGeneration++
  stopPolling()
  selectedFileId.value = null
  selectedFileDetail.value = null
  fileDetailLoading.value = false
  fileDetailError.value = ''
  experimentResult.value = null
  resultNotFound.value = false
  analysisSubmitting.value = false
  analysisActive.value = false
  analysisProgress.value = 0
  analysisTaskId.value = null
  analysisFailed.value = false
  analysisTaskError.value = ''
  pollError.value = ''
  comparisonResult.value = null
  comparisonError.value = ''
  comparisonSubmitting.value = false
}

async function loadAll() {
  const id = typeof route.params.id === 'string' ? route.params.id : ''
  const gen = ++requestGeneration
  selectionGeneration++
  filesRequestId++
  loadError.value = ''
  pollError.value = ''
  uploading.value = false
  uploadError.value = ''
  selectedFile.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
  analysisSubmitting.value = false
  analysisActive.value = false
  analysisProgress.value = 0
  analysisTaskId.value = null
  analysisFailed.value = false
  analysisTaskError.value = ''
  files.value = []
  filesTotal.value = 0
  filesPage.value = 1
  selectedMetricTaskId.value = null
  resetSelectedFileState()
  stopPolling()

  try {
    const [p, t] = await Promise.all([
      getPaper(id),
      listTasks(id),
    ])
    if (gen !== requestGeneration) return
    paper.value = p
    tasks.value = t.items

    if (p.status !== 'PARSED') return

    await loadFiles(gen, 1)
    if (gen !== requestGeneration) return

    const latestSucceeded = succeededMetricTasks.value[0]
    if (latestSucceeded) {
      selectedMetricTaskId.value = latestSucceeded.id
    }

    const activeExperimentTask = t.items.find(
      t => t.task_type === 'EXPERIMENT_ANALYSIS' && (t.status === 'PENDING' || t.status === 'RUNNING'),
    )
    if (activeExperimentTask && activeExperimentTask.experiment_file_id) {
      analysisActive.value = true
      analysisTaskId.value = activeExperimentTask.id
      selectedFileId.value = activeExperimentTask.experiment_file_id
      const selectionGen = selectionGeneration
      void Promise.all([
        loadFileDetail(gen, selectionGen, activeExperimentTask.experiment_file_id),
        loadExperimentResult(gen, selectionGen, activeExperimentTask.experiment_file_id),
      ])
      startPolling(activeExperimentTask.id, activeExperimentTask.experiment_file_id)
    }
  } catch (error: unknown) {
    if (gen !== requestGeneration) return
    loadError.value = safeRequestError(error, '加载实验数据页面失败，请重试。')
  }
}

function selectFile(fileId: string) {
  if (selectedFileId.value === fileId) return
  resetSelectedFileState()
  selectedFileId.value = fileId
  const pageGen = requestGeneration
  const selectionGen = selectionGeneration
  void Promise.all([
    loadFileDetail(pageGen, selectionGen, fileId),
    loadExperimentResult(pageGen, selectionGen, fileId),
  ])
}

async function changeFilesPage(page: number) {
  const normalizedPage = Math.min(filesTotalPages.value, Math.max(1, page))
  if (normalizedPage === filesPage.value || filesLoading.value) return
  resetSelectedFileState()
  await loadFiles(requestGeneration, normalizedPage)
}

function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    selectedFile.value = null
    return
  }
  const extension = file.name.includes('.') ? file.name.split('.').pop()?.toLowerCase() ?? '' : ''
  if (!ALLOWED_UPLOAD_EXTENSIONS.has(extension)) {
    selectedFile.value = null
    uploadError.value = '文件格式不支持，请选择 CSV、XLSX 或 XLS。'
    input.value = ''
    return
  }
  if (file.size <= 0) {
    selectedFile.value = null
    uploadError.value = '实验文件不能为空。'
    input.value = ''
    return
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    selectedFile.value = null
    uploadError.value = '实验文件不能超过 20MB。'
    input.value = ''
    return
  }
  selectedFile.value = file
  uploadError.value = ''
}

async function onUpload() {
  if (!selectedFile.value || !paper.value) return
  if (uploading.value) return
  uploading.value = true
  uploadError.value = ''
  const gen = requestGeneration
  const paperId = paper.value.id

  try {
    const uploaded = await uploadExperimentFile(paperId, selectedFile.value)
    if (gen !== requestGeneration || paper.value?.id !== paperId) return
    if (uploaded.paper_id !== paperId) {
      uploadError.value = '上传响应上下文异常，请刷新页面后确认文件状态。'
      return
    }
    selectedFile.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
    resetSelectedFileState()
    filesPage.value = 1
    await loadFiles(gen, 1)
    if (gen !== requestGeneration || paper.value?.id !== paperId) return
    selectFile(uploaded.id)
  } catch (error: unknown) {
    if (gen !== requestGeneration) return
    uploadError.value = safeRequestError(error, '上传失败，请检查文件后重试。')
  } finally {
    if (gen === requestGeneration) uploading.value = false
  }
}

async function startAnalysis() {
  if (!selectedFileId.value) return
  if (analysisSubmitting.value || analysisActive.value) return
  analysisSubmitting.value = true
  analysisFailed.value = false
  analysisTaskError.value = ''
  pollError.value = ''
  const pageGen = requestGeneration
  const selectionGen = selectionGeneration
  const fileId = selectedFileId.value
  const paperId = paper.value?.id

  try {
    const resp = await createExperimentAnalysis(fileId)
    if (!selectedContextIsCurrent(pageGen, selectionGen, fileId)) return
    if (
      !paperId
      || resp.paper_id !== paperId
      || resp.experiment_file_id !== fileId
      || resp.task_type !== 'EXPERIMENT_ANALYSIS'
    ) {
      loadError.value = '分析任务响应上下文异常，请重新选择文件后重试。'
      return
    }
    if (resp.status === 'PENDING' || resp.status === 'RUNNING') {
      analysisActive.value = true
      const progress = Number(resp.progress ?? 0)
      analysisProgress.value = Number.isFinite(progress) ? Math.min(100, Math.max(0, Math.round(progress))) : 0
      startPolling(resp.id, fileId)
    } else if (resp.status === 'SUCCEEDED') {
      await loadExperimentResult(pageGen, selectionGen, fileId)
    } else {
      analysisFailed.value = true
      analysisTaskError.value = '实验分析失败，请稍后重试'
    }
  } catch (error: unknown) {
    if (!selectedContextIsCurrent(pageGen, selectionGen, fileId)) return
    loadError.value = safeRequestError(error, '创建分析任务失败，请稍后重试。')
  } finally {
    if (selectedContextIsCurrent(pageGen, selectionGen, fileId)) analysisSubmitting.value = false
  }
}

async function startComparison() {
  if (!selectedFileId.value || !selectedMetricTaskId.value) return
  if (comparisonSubmitting.value) return
  comparisonSubmitting.value = true
  comparisonError.value = ''
  const pageGen = requestGeneration
  const selectionGen = selectionGeneration
  const fileId = selectedFileId.value
  const metricTaskId = selectedMetricTaskId.value

  try {
    const resp = await createComparisons(fileId, { metric_task_id: metricTaskId })
    if (
      !selectedContextIsCurrent(pageGen, selectionGen, fileId)
      || selectedMetricTaskId.value !== metricTaskId
    ) return
    if (
      resp.file_id !== fileId
      || resp.metric_task_id !== metricTaskId
      || !resp.comparisons.every(item => item.metric_task_id === metricTaskId)
    ) {
      comparisonError.value = '交叉验证响应上下文异常，请重新选择指标任务后重试。'
      return
    }
    comparisonResult.value = resp
  } catch (error: unknown) {
    if (
      !selectedContextIsCurrent(pageGen, selectionGen, fileId)
      || selectedMetricTaskId.value !== metricTaskId
    ) return
    if (responseStatus(error) === 409) {
      comparisonError.value = '交叉验证结果已存在或指标任务不可用。'
    } else {
      comparisonError.value = safeRequestError(error, '交叉验证失败，请稍后重试。')
    }
  } finally {
    if (
      selectedContextIsCurrent(pageGen, selectionGen, fileId)
      && selectedMetricTaskId.value === metricTaskId
    ) comparisonSubmitting.value = false
  }
}

watch(() => route.params.id, (newId, oldId) => {
  if (newId && newId !== oldId) {
    stopPolling()
    requestGeneration++
    selectionGeneration++
    filesRequestId++
    paper.value = null
    tasks.value = []
    files.value = []
    void loadAll()
  }
})

onMounted(loadAll)
onUnmounted(() => {
  stopPolling()
  requestGeneration++
  selectionGeneration++
  filesRequestId++
})
</script>

<style scoped>
.experiment-data { max-width: 960px; margin: 2rem auto; padding: 0 1rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
h2 { color: #1a1a2e; margin: 0 0 0.5rem; }
h3 { color: #1a1a2e; margin: 1rem 0 0.5rem; }
h4 { color: #333; margin: 1rem 0 0.5rem; }
.header { margin-bottom: 1.5rem; }
.meta { display: flex; gap: 1.5rem; flex-wrap: wrap; color: #666; font-size: 0.9rem; margin: 0.5rem 0; }
.status-parsed { color: #2e7d32; font-weight: 600; }
.status-processing { color: #f57c00; font-weight: 600; }
.status-failed { color: #c62828; font-weight: 600; }
.status-uploading { color: #888; font-weight: 600; }
.nav-links { display: flex; gap: 1rem; margin-top: 0.5rem; }
.nav-links a { color: #1a1a2e; font-size: 0.9rem; }
.not-ready-notice { padding: 1rem; background: #fff3e0; border-radius: 8px; color: #e65100; }
.not-ready-notice a { display: inline-block; margin-top: 0.5rem; color: #1a1a2e; }
.error-msg { color: #c62828; padding: 1rem; }
.retry-btn { margin-top: 0.5rem; padding: 0.4rem 1rem; border: 1px solid #c62828; border-radius: 4px; background: #fff; color: #c62828; cursor: pointer; }
.retry-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.upload-section { padding: 1rem; border: 1px solid #e0e0e0; border-radius: 8px; margin: 1rem 0; }
.upload-hint { font-size: 0.85rem; color: #666; margin-bottom: 0.5rem; }
.upload-row { display: flex; gap: 0.5rem; align-items: center; }
.file-input { font-size: 0.85rem; }
.upload-error { color: #c62828; font-size: 0.85rem; margin-top: 0.5rem; }
.files-section { margin: 1rem 0; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 0.75rem; margin-top: 0.75rem; font-size: 0.85rem; color: #555; }
.pagination button { padding: 0.35rem 0.75rem; border: 1px solid #bbb; border-radius: 4px; background: #fff; cursor: pointer; }
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
.files-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.files-table th, .files-table td { padding: 0.5rem 0.75rem; border: 1px solid #e0e0e0; text-align: left; white-space: nowrap; }
.files-table th { background: #f5f5f5; color: #333; font-weight: 600; }
.file-row { cursor: pointer; }
.file-row:hover { background: #f5f5ff; }
.selected-row { background: #e8eaf6; }
.empty-files { padding: 1rem; text-align: center; color: #666; }
.analysis-section { margin: 1.5rem 0; }
.file-detail-section { margin: 1rem 0; }
.detail-meta { color: #555; font-size: 0.9rem; }
.columns-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-bottom: 1rem; }
.columns-table th, .columns-table td { padding: 0.5rem 0.75rem; border: 1px solid #e0e0e0; text-align: left; }
.columns-table th { background: #f5f5f5; color: #333; font-weight: 600; }
.analysis-header { display: flex; align-items: center; gap: 1rem; }
.task-progress { padding: 1rem; background: #fff3e0; border-radius: 8px; margin: 1rem 0; }
.progress-bar-wrapper { background: #e0e0e0; border-radius: 4px; height: 20px; overflow: hidden; margin: 0.5rem 0; }
.progress-bar-fill { background: #f57c00; height: 100%; transition: width 0.3s; }
.progress-text { font-size: 0.85rem; color: #e65100; }
.poll-error { margin-top: 0.5rem; color: #c62828; }
.failed-notice { padding: 1rem; background: #ffebee; border-radius: 8px; color: #c62828; margin: 1rem 0; }
.result-section { margin: 1rem 0; }
.stats-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-bottom: 1.5rem; }
.stats-table th, .stats-table td { padding: 0.5rem 0.75rem; border: 1px solid #e0e0e0; text-align: left; white-space: nowrap; }
.stats-table th { background: #f5f5f5; color: #333; font-weight: 600; }
.comparison-section { margin-top: 1.5rem; }
.no-metrics-notice { padding: 1rem; background: #fff3e0; border-radius: 8px; color: #e65100; }
.comparison-controls { display: flex; gap: 0.5rem; align-items: center; margin: 0.5rem 0; flex-wrap: wrap; }
.comparison-controls label { font-size: 0.9rem; color: #333; }
.comparison-controls select { padding: 0.4rem; border: 1px solid #e0e0e0; border-radius: 4px; }
.comparison-error { color: #c62828; font-size: 0.85rem; margin: 0.5rem 0; }
.comparison-locked { padding: 0.75rem; background: #e8f5e9; border-radius: 6px; color: #2e7d32; }
.comparison-table-wrapper { overflow-x: auto; margin-top: 0.5rem; }
.comparison-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.comparison-table th, .comparison-table td { padding: 0.5rem 0.75rem; border: 1px solid #e0e0e0; text-align: left; white-space: nowrap; }
.comparison-table th { background: #f5f5f5; color: #333; font-weight: 600; }
.status-match { color: #2e7d32; font-weight: 600; }
.status-mismatch { color: #c62828; font-weight: 600; }
.status-unverifiable { color: #f57c00; font-weight: 600; }
.no-result { padding: 1rem; text-align: center; color: #666; }
.primary-btn { padding: 0.6rem 1.5rem; background: #1a1a2e; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.primary-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.loading-msg { color: #888; padding: 2rem; text-align: center; }

@media (max-width: 640px) {
  .experiment-data { padding: 0 0.5rem; }
  .meta { flex-direction: column; gap: 0.25rem; }
  .upload-row { flex-direction: column; align-items: flex-start; }
  .comparison-controls { flex-direction: column; align-items: flex-start; }
}
</style>
