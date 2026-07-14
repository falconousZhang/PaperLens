<template>
  <div class="metric-analysis" v-if="paper">
    <div class="header">
      <h2>{{ paper.title }}</h2>
      <div class="meta">
        <span>文件: {{ paper.filename }}</span>
        <span>页数: {{ paper.page_count ?? '-' }}</span>
        <span :class="'status-' + paper.status.toLowerCase()">{{ paper.status }}</span>
      </div>
      <div class="nav-links">
        <router-link :to="{ name: 'paper-detail', params: { id: paper.id } }">返回论文详情</router-link>
        <router-link to="/papers">返回论文列表</router-link>
      </div>
    </div>

    <div v-if="paper.status !== 'PARSED'" class="not-ready-notice">
      <p>{{ notReadyMessage }}</p>
      <router-link :to="{ name: 'paper-detail', params: { id: paper.id } }">返回论文详情</router-link>
    </div>

    <template v-else>
      <div v-if="loadError" class="error-msg">
        <p>{{ loadError }}</p>
        <button @click="loadAll" class="retry-btn">重试</button>
      </div>

      <div v-if="activeTask" class="task-progress" aria-live="polite">
        <p>指标提取进行中...</p>
        <div class="progress-bar-wrapper">
          <div
            class="progress-bar-fill"
            :style="{ width: activeProgress + '%' }"
            role="progressbar"
            :aria-valuenow="activeProgress"
            aria-valuemin="0"
            aria-valuemax="100"
          ></div>
        </div>
        <span class="progress-text">{{ activeProgress }}%</span>
        <div v-if="pollError" class="poll-error">
          <p>轮询失败：{{ pollError }}</p>
          <button @click="retryPoll" class="retry-btn">重试轮询</button>
          <button @click="loadAll" class="retry-btn">重新加载</button>
        </div>
      </div>

      <div v-if="failedTask && !activeTask" class="failed-notice">
        <p>{{ failedTask.status === 'CANCELLED' ? '指标提取已取消' : '指标提取失败' }}{{ failedTask.error_message ? '：' + failedTask.error_message : '' }}</p>
        <button @click="submitMetricTask" :disabled="submitting || !!activeTask" class="retry-btn">重新提取指标</button>
      </div>

      <div v-if="succeededMetricTasks.length > 1" class="task-selector">
        <label for="task-select">指标任务：</label>
        <select id="task-select" v-model="selectedTaskId" @change="onTaskChange">
          <option v-for="t in succeededMetricTasks" :key="t.id" :value="t.id">
            {{ formatTaskLabel(t) }}
          </option>
        </select>
      </div>

      <div v-if="selectedTaskId" class="metrics-section" :aria-busy="metricsLoading">
        <div class="filter-bar">
          <label for="filter-metric-name">指标名：</label>
          <input id="filter-metric-name" type="text" v-model="filterMetricName" placeholder="精确筛选" @change="onFilterChange" />
          <label for="filter-dataset">数据集：</label>
          <input id="filter-dataset" type="text" v-model="filterDatasetName" placeholder="精确筛选" @change="onFilterChange" />
          <label for="filter-checkpoint">Checkpoint：</label>
          <select id="filter-checkpoint" v-model="filterCheckpointType" @change="onFilterChange">
            <option value="">全部</option>
            <option v-for="ct in checkpointTypes" :key="ct" :value="ct">{{ checkpointLabel(ct) }}</option>
          </select>
          <button v-if="hasActiveFilters" @click="clearFilters" class="clear-btn">清空筛选</button>
        </div>

        <div v-if="metrics.length > 0" class="metrics-table-wrapper">
          <table class="metrics-table" role="table">
            <thead>
              <tr>
                <th scope="col">模型</th>
                <th scope="col">数据集</th>
                <th scope="col">指标名</th>
                <th scope="col">指标值</th>
                <th scope="col">Checkpoint</th>
                <th scope="col">来源</th>
                <th scope="col">来源原文</th>
                <th scope="col">时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in metrics" :key="m.id">
                <td>{{ m.model_name || '-' }}</td>
                <td>{{ m.dataset_name || '-' }}</td>
                <td>{{ m.metric_name }}</td>
                <td>
                  <span>{{ formatMetricValue(m.metric_name, m.metric_value) }}</span>
                  <small class="stored-value">存储值：{{ formatStoredValue(m.metric_value) }}</small>
                </td>
                <td><span :class="'checkpoint-' + m.checkpoint_type.toLowerCase()">{{ checkpointLabel(m.checkpoint_type) }}</span></td>
                <td>
                  <router-link
                    v-if="sourceKind(m) === 'evidence'"
                    :to="{ name: 'paper-detail', params: { id: paper.id }, query: { evidence: m.evidence_id! } }"
                    class="evidence-link"
                  >查看证据</router-link>
                  <span v-else-if="sourceKind(m) === 'table'" class="table-source">
                    表格 {{ m.table_id }} / 0-based 行 {{ m.row_index ?? '-' }}
                  </span>
                  <span v-else class="unavailable-source">来源不可用</span>
                </td>
                <td>
                  <details class="raw-text">
                    <summary>查看原文</summary>
                    <span>{{ m.raw_text || '-' }}</span>
                  </details>
                </td>
                <td>{{ formatTime(m.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="metrics.length > 0" class="pagination">
          <button :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">上一页</button>
          <span>第 {{ currentPage }} / {{ totalPages }} 页（共 {{ totalMetrics }} 条）</span>
          <button :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">下一页</button>
        </div>

        <div v-else class="result-empty-state">
          <p v-if="hasActiveFilters">当前筛选条件下没有匹配指标。</p>
          <p v-else>该次指标提取已完成，但没有可展示的指标结果。</p>
          <button
            v-if="!hasActiveFilters"
            @click="submitMetricTask"
            :disabled="submitting || !!activeTask || !!activeTaskId"
            class="primary-btn"
          >重新提取指标</button>
        </div>
      </div>

      <div v-if="!selectedTaskId && !activeTask && !failedTask" class="empty-state">
        <p>尚未提取指标</p>
        <button @click="submitMetricTask" :disabled="submitting || !!activeTaskId" class="primary-btn">提取指标</button>
      </div>
    </template>
  </div>
  <div v-else-if="loadError" class="error-msg">
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
  createMetricExtractionTask,
  getTask,
  listMetrics,
  type PaperDetail,
  type TaskDetail,
  type MetricRecord,
  type CheckpointType,
} from '../api'

const route = useRoute()

const PERCENT_METRICS = new Set([
  'accuracy', 'precision', 'recall', 'f1', 'auc', 'map', 'bleu', 'rouge', 'iou', 'miou',
])

const CHECKPOINT_LABELS: Record<string, string> = {
  BEST: '最佳',
  FINAL: '最终',
  MAX: '最大',
  MEAN: '均值',
  LAST: '最近',
  UNKNOWN: '未知',
}

const checkpointTypes: CheckpointType[] = ['BEST', 'FINAL', 'MAX', 'MEAN', 'LAST', 'UNKNOWN']

function checkpointLabel(ct: string): string {
  return CHECKPOINT_LABELS[ct] || ct
}

function isPercentMetric(name: string): boolean {
  return PERCENT_METRICS.has(name.toLowerCase())
}

function formatMetricValue(name: string, value: number): string {
  if (!Number.isFinite(value)) return '-'
  if (isPercentMetric(name)) {
    return (value * 100).toFixed(2) + '%'
  }
  return String(value)
}

function formatStoredValue(value: number): string {
  return Number.isFinite(value) ? String(value) : '-'
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

type MetricSourceKind = 'evidence' | 'table' | 'unavailable'

function sourceKind(m: MetricRecord): MetricSourceKind {
  const hasEvidence = typeof m.evidence_id === 'string' && m.evidence_id.length > 0
  const hasTable = typeof m.table_id === 'string' && m.table_id.length > 0
  const validRow = m.row_index === null || (Number.isInteger(m.row_index) && m.row_index >= 0)
  if (hasEvidence && !hasTable && m.row_index === null) return 'evidence'
  if (hasTable && !hasEvidence && validRow) return 'table'
  return 'unavailable'
}

function formatTaskLabel(t: TaskDetail): string {
  const time = formatTime(t.created_at)
  const status = t.status === 'SUCCEEDED' ? '成功' : t.status === 'FAILED' ? '失败' : t.status
  return `${time} (${status})`
}

const paper = ref<PaperDetail | null>(null)
const tasks = ref<TaskDetail[]>([])
const metrics = ref<MetricRecord[]>([])
const totalMetrics = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const loadError = ref('')
const pollError = ref('')
const submitting = ref(false)
const metricsLoading = ref(false)
const activeTaskId = ref<string | null>(null)
const activeTask = ref<TaskDetail | null>(null)
const selectedTaskId = ref<string | null>(null)
const filterMetricName = ref('')
const filterDatasetName = ref('')
const filterCheckpointType = ref<CheckpointType | ''>('')

let pollTimer: ReturnType<typeof setInterval> | null = null
let requestGeneration = 0
let metricRequestId = 0

const notReadyMessage = computed(() => {
  if (!paper.value) return ''
  const s = paper.value.status
  if (s === 'UPLOADING') return '论文正在上传中，请稍候...'
  if (s === 'PROCESSING') return '论文正在解析中，请稍候...'
  if (s === 'FAILED') return '论文解析失败，无法提取指标。'
  return '论文尚未解析完成，无法提取指标。'
})

const metricTasks = computed(() =>
  tasks.value.filter(t => t.task_type === 'METRIC_EXTRACTION'),
)

const succeededMetricTasks = computed(() =>
  metricTasks.value.filter(t => t.status === 'SUCCEEDED'),
)

const latestMetricTask = computed(() => metricTasks.value[0] ?? null)

const failedTask = computed(() => {
  const t = latestMetricTask.value
  if (!t) return null
  if (t.status === 'FAILED' || t.status === 'CANCELLED') return t
  return null
})

const activeProgress = computed(() => {
  const progress = Number(activeTask.value?.progress ?? 0)
  if (!Number.isFinite(progress)) return 0
  return Math.min(100, Math.max(0, Math.round(progress)))
})

const totalPages = computed(() => Math.max(1, Math.ceil(totalMetrics.value / pageSize.value)))

const hasActiveFilters = computed(() =>
  filterMetricName.value !== '' || filterDatasetName.value !== '' || filterCheckpointType.value !== '',
)

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function updateTask(task: TaskDetail) {
  const index = tasks.value.findIndex(t => t.id === task.id)
  if (index === -1) {
    tasks.value.unshift(task)
  } else {
    tasks.value.splice(index, 1, task)
  }
}

function startPolling(taskId: string) {
  stopPolling()
  const gen = requestGeneration
  activeTaskId.value = taskId
  let requestInFlight = false
  pollTimer = setInterval(async () => {
    if (requestInFlight) return
    requestInFlight = true
    try {
      const t = await getTask(taskId)
      if (gen !== requestGeneration) return
      if (
        t.id !== taskId
        || t.paper_id !== route.params.id
        || t.task_type !== 'METRIC_EXTRACTION'
      ) {
        stopPolling()
        activeTask.value = null
        activeTaskId.value = null
        loadError.value = '任务上下文不一致，请重新加载。'
        return
      }
      activeTask.value = t
      updateTask(t)
      if (t.status === 'PENDING' || t.status === 'RUNNING') return
      stopPolling()
      activeTask.value = null
      activeTaskId.value = null
      if (t.status === 'SUCCEEDED') {
        try {
          await refreshData(gen)
          if (gen !== requestGeneration) return
          selectedTaskId.value = t.id
          currentPage.value = 1
          await loadMetrics(gen)
        } catch (e: any) {
          if (gen !== requestGeneration) return
          loadError.value = '任务已完成，但刷新指标结果失败：' + (
            e?.response?.data?.error?.message || e?.message || '加载失败'
          )
        }
      } else if (t.status !== 'FAILED' && t.status !== 'CANCELLED') {
        loadError.value = '任务返回未知状态，请重新加载。'
      }
    } catch (e: any) {
      if (gen !== requestGeneration) return
      stopPolling()
      pollError.value = e?.response?.data?.error?.message || e?.message || '轮询失败'
    } finally {
      requestInFlight = false
    }
  }, 3000)
}

function retryPoll() {
  pollError.value = ''
  if (activeTaskId.value) {
    startPolling(activeTaskId.value)
  } else {
    loadAll()
  }
}

async function refreshData(gen = requestGeneration) {
  const id = route.params.id as string
  const t = await listTasks(id)
  if (gen !== requestGeneration) return
  tasks.value = t.items
}

async function loadMetrics(gen = requestGeneration) {
  const id = route.params.id as string
  const taskId = selectedTaskId.value
  const requestId = ++metricRequestId
  if (!taskId) {
    metrics.value = []
    totalMetrics.value = 0
    metricsLoading.value = false
    return
  }
  metricsLoading.value = true
  loadError.value = ''
  try {
    const params: Record<string, string | number> = {
      task_id: taskId,
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (filterMetricName.value) params.metric_name = filterMetricName.value
    if (filterDatasetName.value) params.dataset_name = filterDatasetName.value
    if (filterCheckpointType.value) params.checkpoint_type = filterCheckpointType.value
    const result = await listMetrics(id, params)
    if (
      gen !== requestGeneration
      || requestId !== metricRequestId
      || route.params.id !== id
      || selectedTaskId.value !== taskId
    ) return
    metrics.value = result.items
    totalMetrics.value = result.total
  } catch (e: any) {
    if (
      gen !== requestGeneration
      || requestId !== metricRequestId
      || route.params.id !== id
      || selectedTaskId.value !== taskId
    ) return
    loadError.value = e?.response?.data?.error?.message || e?.message || '加载指标失败'
  } finally {
    if (
      gen === requestGeneration
      && requestId === metricRequestId
      && route.params.id === id
      && selectedTaskId.value === taskId
    ) metricsLoading.value = false
  }
}

async function loadAll() {
  const id = route.params.id as string
  const gen = ++requestGeneration
  metricRequestId++
  loadError.value = ''
  pollError.value = ''
  metricsLoading.value = false
  stopPolling()
  activeTask.value = null
  activeTaskId.value = null
  selectedTaskId.value = null
  metrics.value = []
  totalMetrics.value = 0
  currentPage.value = 1

  try {
    const [p, t] = await Promise.all([
      getPaper(id),
      listTasks(id),
    ])
    if (gen !== requestGeneration) return
    paper.value = p
    tasks.value = t.items

    if (p.status !== 'PARSED') return

    const activeMetricTask = t.items.find(
      t => t.task_type === 'METRIC_EXTRACTION' && (t.status === 'PENDING' || t.status === 'RUNNING'),
    )
    if (activeMetricTask) {
      activeTask.value = activeMetricTask
      startPolling(activeMetricTask.id)
    }

    const latestSucceeded = succeededMetricTasks.value[0]
    if (latestSucceeded) {
      selectedTaskId.value = latestSucceeded.id
      await loadMetrics(gen)
    }
  } catch (e: any) {
    if (gen !== requestGeneration) return
    loadError.value = e?.response?.data?.error?.message || e?.message || '加载失败'
  }
}

async function submitMetricTask() {
  if (!paper.value) return
  if (activeTask.value || activeTaskId.value) return
  if (submitting.value) return
  submitting.value = true
  const gen = requestGeneration
  const paperId = paper.value.id

  try {
    const resp = await createMetricExtractionTask(paperId)
    if (gen !== requestGeneration || route.params.id !== paperId) return
    activeTask.value = {
      id: resp.id,
      paper_id: resp.paper_id,
      task_type: resp.task_type,
      status: resp.status,
      progress: resp.progress,
      error_message: null,
      started_at: null,
      completed_at: null,
      created_at: resp.created_at,
    }
    updateTask(activeTask.value)
    startPolling(resp.id)
  } catch (e: any) {
    if (gen !== requestGeneration) return
    if (e?.response?.status === 409) {
      submitting.value = false
      await loadAll()
      return
    }
    loadError.value = e?.response?.data?.error?.message || e?.message || '创建指标提取任务失败'
  } finally {
    if (gen === requestGeneration) submitting.value = false
  }
}

function onTaskChange() {
  if (!succeededMetricTasks.value.some(t => t.id === selectedTaskId.value)) {
    selectedTaskId.value = succeededMetricTasks.value[0]?.id ?? null
  }
  currentPage.value = 1
  loadMetrics()
}

function onFilterChange() {
  currentPage.value = 1
  loadMetrics()
}

function clearFilters() {
  filterMetricName.value = ''
  filterDatasetName.value = ''
  filterCheckpointType.value = ''
  currentPage.value = 1
  loadMetrics()
}

function goPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadMetrics()
}

watch(() => route.params.id, (newId, oldId) => {
  if (newId && newId !== oldId) {
    stopPolling()
    requestGeneration++
    metricRequestId++
    activeTask.value = null
    activeTaskId.value = null
    paper.value = null
    tasks.value = []
    metrics.value = []
    totalMetrics.value = 0
    currentPage.value = 1
    loadError.value = ''
    pollError.value = ''
    submitting.value = false
    metricsLoading.value = false
    selectedTaskId.value = null
    filterMetricName.value = ''
    filterDatasetName.value = ''
    filterCheckpointType.value = ''
    loadAll()
  }
})

onMounted(loadAll)
onUnmounted(() => {
  stopPolling()
  requestGeneration++
  metricRequestId++
})
</script>

<style scoped>
.metric-analysis { max-width: 960px; margin: 2rem auto; padding: 0 1rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
h2 { color: #1a1a2e; margin: 0 0 0.5rem; }
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
.task-progress { padding: 1rem; background: #fff3e0; border-radius: 8px; margin: 1rem 0; }
.progress-bar-wrapper { background: #e0e0e0; border-radius: 4px; height: 20px; overflow: hidden; margin: 0.5rem 0; }
.progress-bar-fill { background: #f57c00; height: 100%; transition: width 0.3s; }
.progress-text { font-size: 0.85rem; color: #e65100; }
.poll-error { margin-top: 0.5rem; color: #c62828; }
.failed-notice { padding: 1rem; background: #ffebee; border-radius: 8px; color: #c62828; margin: 1rem 0; }
.task-selector { margin: 1rem 0; display: flex; align-items: center; gap: 0.5rem; }
.task-selector label { font-size: 0.9rem; color: #333; }
.task-selector select { padding: 0.4rem; border: 1px solid #e0e0e0; border-radius: 4px; }
.filter-bar { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; margin: 1rem 0; }
.filter-bar label { font-size: 0.85rem; color: #333; }
.filter-bar input { padding: 0.3rem 0.5rem; border: 1px solid #e0e0e0; border-radius: 4px; font-size: 0.85rem; width: 120px; }
.filter-bar select { padding: 0.3rem 0.5rem; border: 1px solid #e0e0e0; border-radius: 4px; font-size: 0.85rem; }
.clear-btn { padding: 0.3rem 0.8rem; border: 1px solid #e0e0e0; border-radius: 4px; background: #fafafa; cursor: pointer; font-size: 0.85rem; }
.metrics-table-wrapper { overflow-x: auto; }
.metrics-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.metrics-table th, .metrics-table td { padding: 0.5rem 0.75rem; border: 1px solid #e0e0e0; text-align: left; white-space: nowrap; }
.metrics-table th { background: #f5f5f5; color: #333; font-weight: 600; }
.metrics-table td { color: #333; }
.stored-value { display: block; margin-top: 0.2rem; color: #666; font-size: 0.75rem; }
.evidence-link { color: #1565c0; }
.table-source, .unavailable-source { white-space: normal; }
.unavailable-source { color: #777; }
.raw-text { width: min(260px, 40vw); white-space: normal; }
.raw-text summary { color: #1565c0; cursor: pointer; }
.raw-text span { display: block; margin-top: 0.35rem; overflow-wrap: anywhere; line-height: 1.4; }
.checkpoint-best { color: #2e7d32; font-weight: 600; }
.checkpoint-final { color: #1565c0; font-weight: 600; }
.checkpoint-max { color: #6a1b9a; font-weight: 600; }
.checkpoint-mean { color: #f57c00; font-weight: 600; }
.checkpoint-last { color: #00838f; font-weight: 600; }
.checkpoint-unknown { color: #888; font-style: italic; }
.pagination { display: flex; align-items: center; gap: 1rem; margin: 1rem 0; font-size: 0.85rem; color: #666; }
.pagination button { padding: 0.4rem 1rem; border: 1px solid #e0e0e0; border-radius: 4px; background: #fafafa; cursor: pointer; }
.pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
.empty-state, .result-empty-state { padding: 2rem; text-align: center; color: #666; }
.primary-btn { padding: 0.6rem 1.5rem; background: #1a1a2e; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.primary-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.loading-msg { color: #888; padding: 2rem; text-align: center; }

@media (max-width: 640px) {
  .metric-analysis { padding: 0 0.5rem; }
  .meta { flex-direction: column; gap: 0.25rem; }
  .filter-bar { flex-direction: column; align-items: flex-start; }
  .filter-bar input { width: 100%; }
}
</style>
