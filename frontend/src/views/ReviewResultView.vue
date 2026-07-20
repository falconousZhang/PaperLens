<template>
  <div class="review-result" v-if="paper">
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
      <div v-if="loadError" class="error-msg">
        <p>{{ loadError }}</p>
        <button @click="loadAll" class="retry-btn">重试</button>
      </div>

      <div v-if="activeTask" class="task-progress">
        <p>审阅进行中...</p>
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
        <p>{{ failedTask.status === 'CANCELLED' ? '审阅已取消' : '审阅失败' }}{{ failedTask.error_message ? '：' + failedTask.error_message : '' }}</p>
        <button @click="openCreateForm" class="retry-btn">重新发起审阅</button>
      </div>

      <div v-if="succeededWithoutResults && currentReviews.length > 0" class="inconsistency-notice">
        最新审阅已完成但未获取到新结果，当前继续显示上一轮结果。
        <button @click="loadAll" class="retry-btn">重新加载</button>
      </div>

      <div v-if="currentReviews.length > 0" class="results-section">
        <div class="overview">
          <div class="overview-item">
            <span class="overview-label">总评</span>
            <span class="overview-value">{{ overallRating ?? '-' }}</span>
          </div>
          <div class="overview-item">
            <span class="overview-label">维度数</span>
            <span class="overview-value">{{ currentReviews.length }}</span>
          </div>
          <div class="overview-item">
            <span class="overview-label">Finding 数</span>
            <span class="overview-value">{{ totalFindings }}</span>
          </div>
          <div v-if="overallVerdict" class="overview-item">
            <span class="overview-label">结论</span>
            <span :class="'verdict-' + overallVerdict.toLowerCase().replace('_', '-')" class="overview-value">{{ verdictLabel(overallVerdict) }}</span>
          </div>
        </div>

        <div class="filter-bar">
          <button
            v-for="ft in findingFilterOptions"
            :key="ft.value"
            :class="{ active: findingFilter === ft.value }"
            @click="findingFilter = ft.value"
            class="filter-btn"
          >{{ ft.label }}</button>
        </div>

        <div v-for="review in sortedReviews" :key="review.id" class="dimension-card">
          <div class="dimension-header">
            <h3>{{ dimensionLabel(review.dimension) }}</h3>
            <span class="dimension-rating">评分: {{ review.rating ?? '-' }}</span>
          </div>
          <p v-if="review.summary" class="dimension-summary">{{ review.summary }}</p>

          <div
            v-for="finding in filteredFindings(review.findings)"
            :key="finding.id"
            :class="'finding-card finding-' + finding.finding_type.toLowerCase()"
          >
            <div class="finding-header">
              <span :class="'finding-type-' + finding.finding_type.toLowerCase()" class="finding-type-label">{{ findingTypeLabel(finding.finding_type) }}</span>
              <span class="finding-sequence">#{{ finding.sequence }}</span>
            </div>
            <p class="finding-content">{{ finding.content }}</p>
            <div class="finding-footer">
              <span v-if="finding.confidence != null" class="finding-confidence">置信度: {{ formatConfidence(finding.confidence) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="currentReviews.length === 0 && !activeTask && !failedTask" class="empty-state">
        <p v-if="succeededWithoutResults">审阅已完成但未获取到结果，请尝试重新加载。</p>
        <p v-else>尚未发起审阅</p>
        <button v-if="!showCreateForm" @click="openCreateForm" class="primary-btn">发起审阅</button>
        <button v-if="succeededWithoutResults" @click="loadAll" class="retry-btn">重新加载</button>
      </div>

      <div v-if="showCreateForm" class="create-form">
        <h3>审阅配置</h3>
        <div class="form-group">
          <label>审阅维度（至少选择一个）</label>
          <div class="dimension-checks">
            <label v-for="dim in allDimensions" :key="dim" class="dim-check">
              <input type="checkbox" :value="dim" v-model="selectedDimensions" />
              {{ dimensionLabel(dim) }}
            </label>
          </div>
          <p v-if="dimensionError" class="field-error">{{ dimensionError }}</p>
        </div>
        <div class="form-group">
          <label>审阅语言</label>
          <select v-model="selectedLanguage">
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
        </div>
        <div class="form-actions">
          <button @click="submitReview" :disabled="submitting || !!activeTask || selectedDimensions.length === 0" class="primary-btn">
            {{ submitting ? '提交中...' : '发起审阅' }}
          </button>
          <button v-if="currentReviews.length > 0" @click="showCreateForm = false" class="cancel-btn">取消</button>
        </div>
      </div>

      <div v-if="currentReviews.length > 0 && !showCreateForm && !activeTask" class="re-review-section">
        <button @click="openCreateForm" class="secondary-btn">重新审阅</button>
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
  createTask,
  getTask,
  listReviews,
  type PaperDetail,
  type TaskDetail,
  type ReviewResult,
  type ReviewDimension,
  type FindingType,
  type OverallVerdict,
} from '../api'
import { SAFE_POLLING_ERROR, usePolling } from '../composables/usePolling'

const route = useRoute()
const { startPolling: startSharedPolling, stopPolling } = usePolling()
const paper = ref<PaperDetail | null>(null)
const tasks = ref<TaskDetail[]>([])
const reviews = ref<ReviewResult[]>([])
const loadError = ref('')
const pollError = ref('')
const submitting = ref(false)
const showCreateForm = ref(false)
const selectedDimensions = ref<ReviewDimension[]>([
  'SOUNDNESS', 'NOVELTY', 'CLARITY', 'COMPLETENESS', 'REPRODUCIBILITY', 'SIGNIFICANCE', 'OVERALL',
])
const selectedLanguage = ref<'zh' | 'en'>('zh')
const dimensionError = ref('')
const findingFilter = ref<'all' | FindingType>('all')
const activeTaskId = ref<string | null>(null)
const activeTask = ref<TaskDetail | null>(null)

let requestGeneration = 0

const allDimensions: ReviewDimension[] = [
  'SOUNDNESS', 'NOVELTY', 'CLARITY', 'COMPLETENESS', 'REPRODUCIBILITY', 'SIGNIFICANCE', 'OVERALL',
]

const findingFilterOptions: { label: string; value: 'all' | FindingType }[] = [
  { label: '全部', value: 'all' },
  { label: '优点', value: 'STRENGTH' },
  { label: '不足', value: 'WEAKNESS' },
  { label: '建议', value: 'SUGGESTION' },
]

const DIMENSION_ORDER: ReviewDimension[] = [
  'SOUNDNESS', 'NOVELTY', 'CLARITY', 'COMPLETENESS', 'REPRODUCIBILITY', 'SIGNIFICANCE', 'OVERALL',
]

const DIMENSION_LABELS: Record<string, string> = {
  SOUNDNESS: '合理性',
  NOVELTY: '新颖性',
  CLARITY: '清晰度',
  COMPLETENESS: '完整性',
  REPRODUCIBILITY: '可复现性',
  SIGNIFICANCE: '重要性',
  OVERALL: '总体评价',
}

const FINDING_TYPE_LABELS: Record<string, string> = {
  STRENGTH: '优点',
  WEAKNESS: '不足',
  SUGGESTION: '建议',
}

const VERDICT_LABELS: Record<string, string> = {
  ACCEPT: '接受',
  WEAK_ACCEPT: '弱接受',
  BORDERLINE: '边界',
  WEAK_REJECT: '弱拒绝',
  REJECT: '拒绝',
}

function dimensionLabel(dim: string): string {
  return DIMENSION_LABELS[dim] || dim
}

function findingTypeLabel(ft: string): string {
  return FINDING_TYPE_LABELS[ft] || ft
}

function verdictLabel(v: string): string {
  return VERDICT_LABELS[v] || v
}

function formatConfidence(c: number | null): string {
  if (c == null || isNaN(c)) return '-'
  const pct = Math.round(c * 100)
  if (pct < 0) return '0%'
  if (pct > 100) return '100%'
  return pct + '%'
}

const notReadyMessage = computed(() => {
  if (!paper.value) return ''
  const s = paper.value.status
  if (s === 'UPLOADING') return '论文正在上传中，请稍候...'
  if (s === 'PROCESSING') return '论文正在解析中，请稍候...'
  if (s === 'FAILED') return '论文解析失败，无法发起审阅。'
  return '论文尚未解析完成，无法发起审阅。'
})


const reviewTasks = computed(() => tasks.value.filter(t => t.task_type === 'REVIEW'))

const latestReviewTask = computed(() => reviewTasks.value[0] ?? null)

const latestResultTaskId = computed(() => {
  const taskIdsWithResults = new Set(reviews.value.map(r => r.task_id))
  const latestTaskWithResults = reviewTasks.value.find(t => taskIdsWithResults.has(t.id))
  if (latestTaskWithResults) return latestTaskWithResults.id
  if (reviews.value.length > 0) {
    let latest = reviews.value[0]!.task_id
    let latestTime = reviews.value[0]!.created_at
    for (const r of reviews.value) {
      if (r.created_at > latestTime) {
        latestTime = r.created_at
        latest = r.task_id
      }
    }
    return latest
  }
  return null
})

const currentReviews = computed(() => {
  if (!latestResultTaskId.value) return []
  return reviews.value.filter(r => r.task_id === latestResultTaskId.value)
})

const sortedReviews = computed(() => {
  return [...currentReviews.value].sort((a, b) => {
    const ai = DIMENSION_ORDER.indexOf(a.dimension)
    const bi = DIMENSION_ORDER.indexOf(b.dimension)
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
  })
})

const overallReview = computed(() =>
  currentReviews.value.find(r => r.dimension === 'OVERALL'),
)

const overallRating = computed(() => overallReview.value?.rating ?? null)

const overallVerdict = computed<OverallVerdict | null>(() =>
  overallReview.value?.overall_verdict ?? null,
)

const totalFindings = computed(() =>
  currentReviews.value.reduce((sum, r) => sum + r.findings.length, 0),
)

const failedTask = computed(() => {
  const t = latestReviewTask.value
  if (!t) return null
  if (t.status === 'FAILED' || t.status === 'CANCELLED') return t
  return null
})

const succeededWithoutResults = computed(() => {
  const t = latestReviewTask.value
  if (!t) return false
  return t.status === 'SUCCEEDED' && !reviews.value.some(r => r.task_id === t.id)
})

const activeProgress = computed(() => {
  const progress = Number(activeTask.value?.progress ?? 0)
  if (!Number.isFinite(progress)) return 0
  return Math.min(100, Math.max(0, Math.round(progress)))
})

function filteredFindings(findings: ReviewResult['findings']) {
  if (findingFilter.value === 'all') return findings
  return findings.filter(f => f.finding_type === findingFilter.value)
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
  const gen = requestGeneration
  activeTaskId.value = taskId
  startSharedPolling(
    () => getTask(taskId),
    async t => {
      if (gen !== requestGeneration) return
      activeTask.value = t
      updateTask(t)
      if (t.status === 'PENDING' || t.status === 'RUNNING') return
      activeTask.value = null
      activeTaskId.value = null
      if (t.status === 'SUCCEEDED') {
        try {
          await refreshData(gen)
        } catch (e: any) {
          if (gen !== requestGeneration) return
          loadError.value = '任务已完成，但刷新审阅结果失败：' + (
            e?.response?.data?.error?.message || e?.message || '加载失败'
          )
        }
      }
    },
    t => t.status !== 'PENDING' && t.status !== 'RUNNING',
    () => {
      if (gen !== requestGeneration) return
      pollError.value = SAFE_POLLING_ERROR
    },
  )
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
  const [t, r] = await Promise.all([listTasks(id), listReviews(id)])
  if (gen !== requestGeneration) return
  tasks.value = t.items
  reviews.value = r.reviews
}

async function loadAll() {
  const id = route.params.id as string
  const gen = ++requestGeneration
  loadError.value = ''
  pollError.value = ''
  stopPolling()
  activeTask.value = null
  activeTaskId.value = null

  try {
    const [p, t, r] = await Promise.all([
      getPaper(id),
      listTasks(id),
      listReviews(id),
    ])
    if (gen !== requestGeneration) return
    paper.value = p
    tasks.value = t.items
    reviews.value = r.reviews

    const activeReviewTask = t.items.find(
      t => t.task_type === 'REVIEW' && (t.status === 'PENDING' || t.status === 'RUNNING'),
    )
    if (activeReviewTask) {
      activeTask.value = activeReviewTask
      startPolling(activeReviewTask.id)
    }
  } catch (e: any) {
    if (gen !== requestGeneration) return
    loadError.value = e?.response?.data?.error?.message || e?.message || '加载失败'
  }
}

function openCreateForm() {
  dimensionError.value = ''
  showCreateForm.value = true
}

async function submitReview() {
  if (!paper.value) return
  if (activeTask.value || activeTaskId.value) return
  if (selectedDimensions.value.length === 0) {
    dimensionError.value = '请至少选择一个审阅维度'
    return
  }
  dimensionError.value = ''
  if (submitting.value) return
  submitting.value = true
  const gen = requestGeneration
  const paperId = paper.value.id

  try {
    const resp = await createTask(paperId, {
      task_type: 'REVIEW',
      options: {
        dimensions: [...selectedDimensions.value],
        language: selectedLanguage.value,
      },
    })
    if (gen !== requestGeneration || route.params.id !== paperId) return
    showCreateForm.value = false
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
    loadError.value = e?.response?.data?.error?.message || e?.message || '创建审阅任务失败'
  } finally {
    if (gen === requestGeneration) submitting.value = false
  }
}

watch(() => route.params.id, (newId, oldId) => {
  if (newId && newId !== oldId) {
    stopPolling()
    requestGeneration++
    activeTask.value = null
    activeTaskId.value = null
    paper.value = null
    tasks.value = []
    reviews.value = []
    loadError.value = ''
    pollError.value = ''
    submitting.value = false
    showCreateForm.value = false
    selectedDimensions.value = [...allDimensions]
    selectedLanguage.value = 'zh'
    dimensionError.value = ''
    findingFilter.value = 'all'
    loadAll()
  }
})

onMounted(loadAll)
onUnmounted(() => {
  stopPolling()
  requestGeneration++
})
</script>

<style scoped>
.review-result { max-width: 960px; margin: 2rem auto; padding: 0 1rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
h2 { color: #1a1a2e; margin: 0 0 0.5rem; }
.header { margin-bottom: 1.5rem; }
.meta { display: flex; gap: 1.5rem; flex-wrap: wrap; color: #666; font-size: 0.9rem; margin: 0.5rem 0; }
.status-parsed { color: #2e7d32; font-weight: 600; }
.status-processing { color: #f57c00; font-weight: 600; }
.status-failed { color: #c62828; font-weight: 600; }
.status-uploading { color: #888; font-weight: 600; }
.nav-links { display: flex; gap: 1rem; margin-top: 0.5rem; }
.nav-links a { color: #1a1a2e; font-size: 0.9rem; }
.nav-links .button-link--primary { color: #fff; }
.not-ready-notice, .inconsistency-notice { padding: 1rem; background: #fff3e0; border-radius: 8px; color: #e65100; }
.not-ready-notice a { display: inline-block; margin-top: 0.5rem; color: #1a1a2e; }
.error-msg { color: #c62828; padding: 1rem; }
.retry-btn { margin-top: 0.5rem; padding: 0.4rem 1rem; border: 1px solid #c62828; border-radius: 4px; background: #fff; color: #c62828; cursor: pointer; }
.retry-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.task-progress { padding: 1rem; background: #fff3e0; border-radius: 8px; margin: 1rem 0; }
.progress-bar-wrapper { background: #e0e0e0; border-radius: 4px; height: 20px; overflow: hidden; margin: 0.5rem 0; }
.progress-bar-fill { background: #f57c00; height: 100%; transition: width 0.3s; }
.progress-text { font-size: 0.85rem; color: #e65100; }
.poll-error { margin-top: 0.5rem; color: #c62828; }
.poll-error .retry-btn { border-color: #c62828; color: #c62828; margin-right: 0.5rem; }
.failed-notice { padding: 1rem; background: #ffebee; border-radius: 8px; color: #c62828; margin: 1rem 0; }
.results-section { margin-top: 1.5rem; }
.overview { display: flex; gap: 1.5rem; flex-wrap: wrap; padding: 1rem; background: #f5f5ff; border-radius: 8px; margin-bottom: 1rem; }
.overview-item { display: flex; flex-direction: column; align-items: center; }
.overview-label { font-size: 0.8rem; color: #888; }
.overview-value { font-size: 1.2rem; font-weight: 600; color: #1a1a2e; }
.verdict-accept { color: #2e7d32; }
.verdict-weak-accept { color: #558b2f; }
.verdict-borderline { color: #f57c00; }
.verdict-weak-reject { color: #e65100; }
.verdict-reject { color: #c62828; }
.filter-bar { display: flex; gap: 0.5rem; margin: 1rem 0; }
.filter-btn { padding: 0.4rem 1rem; border: 1px solid #e0e0e0; border-radius: 6px; background: #fafafa; cursor: pointer; font-size: 0.85rem; }
.filter-btn.active { background: #1a1a2e; color: #fff; border-color: #1a1a2e; }
.dimension-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.dimension-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.dimension-header h3 { margin: 0; color: #1a1a2e; font-size: 1.05rem; }
.dimension-rating { color: #666; font-size: 0.9rem; }
.dimension-summary { color: #333; font-size: 0.9rem; margin: 0.5rem 0; white-space: pre-wrap; word-break: break-word; }
.finding-card { padding: 0.75rem; border-left: 3px solid #e0e0e0; margin: 0.5rem 0; border-radius: 0 4px 4px 0; background: #fafafa; }
.finding-strength { border-left-color: #2e7d32; }
.finding-weakness { border-left-color: #c62828; }
.finding-suggestion { border-left-color: #1565c0; }
.finding-header { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 0.25rem; }
.finding-type-label { font-size: 0.8rem; font-weight: 600; padding: 0.15rem 0.5rem; border-radius: 3px; }
.finding-type-strength { background: #e8f5e9; color: #2e7d32; }
.finding-type-weakness { background: #ffebee; color: #c62828; }
.finding-type-suggestion { background: #e3f2fd; color: #1565c0; }
.finding-sequence { font-size: 0.8rem; color: #888; }
.finding-content { font-size: 0.9rem; color: #333; margin: 0.25rem 0; white-space: pre-wrap; word-break: break-word; }
.finding-footer { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; margin-top: 0.25rem; }
.finding-confidence { font-size: 0.8rem; color: #888; }
.empty-state { padding: 2rem; text-align: center; color: #888; }
.primary-btn { padding: 0.6rem 1.5rem; background: #1a1a2e; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.primary-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.secondary-btn { padding: 0.5rem 1.2rem; background: #fafafa; color: #1a1a2e; border: 1px solid #e0e0e0; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.cancel-btn { padding: 0.5rem 1.2rem; background: #fff; color: #888; border: 1px solid #e0e0e0; border-radius: 6px; cursor: pointer; margin-left: 0.5rem; }
.create-form { padding: 1rem; border: 1px solid #e0e0e0; border-radius: 8px; margin: 1rem 0; }
.create-form h3 { margin: 0 0 1rem; color: #1a1a2e; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; font-size: 0.9rem; color: #333; margin-bottom: 0.25rem; }
.dimension-checks { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.dim-check { display: flex; align-items: center; gap: 0.25rem; font-size: 0.85rem; cursor: pointer; }
.dim-check input { cursor: pointer; }
.form-group select { padding: 0.4rem; border: 1px solid #e0e0e0; border-radius: 4px; }
.field-error { color: #c62828; font-size: 0.85rem; margin-top: 0.25rem; }
.form-actions { display: flex; gap: 0.5rem; align-items: center; }
.re-review-section { margin: 1rem 0; }
.loading-msg { color: #888; padding: 2rem; text-align: center; }

@media (max-width: 480px) {
  .review-result { padding: 0 0.5rem; }
  .meta { flex-direction: column; gap: 0.25rem; }
  .overview { flex-direction: column; gap: 0.5rem; }
  .dimension-checks { flex-direction: column; }
}
</style>
