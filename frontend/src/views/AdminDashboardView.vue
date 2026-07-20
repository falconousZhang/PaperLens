<template>
  <div class="admin-dashboard">
    <h1>管理后台</h1>

    <div class="admin-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-btn', { active: activeTab === tab.key }]"
        @click="switchTab(tab.key)"
      >{{ tab.label }}</button>
    </div>

    <p v-if="notice" class="notice">{{ notice }}</p>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="refresh">重试</button>
    </div>

    <div v-else>
      <section v-if="activeTab === 'overview'">
        <div v-if="dashboard" class="overview-cards">
          <div class="card">
            <h3>用户</h3>
            <p>管理员: {{ dashboard.users_by_role.ADMIN || 0 }}</p>
            <p>普通用户: {{ dashboard.users_by_role.USER || 0 }}</p>
            <p>活跃: {{ dashboard.users_by_status.ACTIVE || 0 }}</p>
            <p>禁用: {{ dashboard.users_by_status.DISABLED || 0 }}</p>
          </div>
          <div class="card">
            <h3>论文</h3>
            <p v-for="(count, status) in dashboard.papers_by_status" :key="status">{{ status }}: {{ count }}</p>
          </div>
          <div class="card">
            <h3>任务</h3>
            <p v-for="(count, tt) in dashboard.tasks_by_type" :key="tt">{{ tt }}: {{ count }}</p>
          </div>
          <div class="card">
            <h3>报告</h3>
            <p v-for="(count, rt) in dashboard.exports_by_type" :key="rt">{{ rt }}: {{ count }}</p>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'users'">
        <div class="filters">
          <select v-model="userFilters.role" @change="loadUsers(1)">
            <option value="">全部角色</option>
            <option value="USER">USER</option>
            <option value="ADMIN">ADMIN</option>
          </select>
          <select v-model="userFilters.status" @change="loadUsers(1)">
            <option value="">全部状态</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="DISABLED">DISABLED</option>
          </select>
          <input
            v-model="userFilters.q"
            placeholder="搜索邮箱/名称"
            @keyup.enter="loadUsers(1)"
          />
          <button @click="loadUsers(1)">搜索</button>
        </div>
        <table v-if="userList.items.length">
          <thead>
            <tr>
              <th>邮箱</th><th>名称</th><th>角色</th><th>状态</th><th>论文</th><th>任务</th><th>报告</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in userList.items" :key="u.id">
              <td>{{ u.email }}</td>
              <td>{{ u.display_name }}</td>
              <td>{{ u.role }}</td>
              <td>{{ u.status }}</td>
              <td>{{ u.paper_count }}</td>
              <td>{{ u.task_count }}</td>
              <td>{{ u.export_count }}</td>
              <td>
                <button :disabled="actionLoading" @click="loadUserDetail(u.id)">详情</button>
                <button
                  v-if="u.role !== 'ADMIN' && u.id !== currentUserId"
                  :disabled="actionLoading"
                  @click="openConfirm(u, 'role', 'ADMIN')"
                >设为管理员</button>
                <button
                  v-if="u.role === 'ADMIN' && u.id !== currentUserId"
                  :disabled="actionLoading"
                  @click="openConfirm(u, 'role', 'USER')"
                >设为用户</button>
                <button
                  v-if="u.status === 'ACTIVE' && u.id !== currentUserId"
                  :disabled="actionLoading"
                  @click="openConfirm(u, 'status', 'DISABLED')"
                >禁用</button>
                <button
                  v-if="u.status === 'DISABLED' && u.id !== currentUserId"
                  :disabled="actionLoading"
                  @click="openConfirm(u, 'status', 'ACTIVE')"
                >启用</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty">暂无用户</p>
        <div v-if="userList.total > userFilters.page_size" class="pagination">
          <button :disabled="userFilters.page <= 1" @click="loadUsers(userFilters.page - 1)">上一页</button>
          <span>{{ userFilters.page }} / {{ Math.ceil(userList.total / userFilters.page_size) }}</span>
          <button :disabled="userFilters.page * userFilters.page_size >= userList.total" @click="loadUsers(userFilters.page + 1)">下一页</button>
        </div>
      </section>

      <section v-if="activeTab === 'content'">
        <div class="content-tabs">
          <button
            v-for="ct in contentTabs"
            :key="ct.key"
            :class="['tab-btn', { active: contentTab === ct.key }]"
            @click="switchContent(ct.key)"
          >{{ ct.label }}</button>
        </div>

        <div v-if="contentTab === 'papers'">
          <div class="filters">
            <select v-model="paperFilters.status"><option value="">全部状态</option><option value="UPLOADING">UPLOADING</option><option value="PROCESSING">PROCESSING</option><option value="PARSED">PARSED</option><option value="FAILED">FAILED</option></select>
            <input v-model="paperFilters.user_id" placeholder="用户 UUID" />
            <input v-model="paperFilters.q" placeholder="标题/文件名" @keyup.enter="loadContent(1)" />
            <button @click="loadContent(1)">筛选</button>
          </div>
          <table v-if="paperList.items.length">
            <thead><tr><th>标题</th><th>所有者</th><th>状态</th><th>页数</th><th>创建时间</th></tr></thead>
            <tbody>
              <tr v-for="p in paperList.items" :key="p.id">
                <td>{{ p.title }}</td><td>{{ p.owner_email }}</td><td>{{ p.status }}</td><td>{{ p.page_count }}</td><td>{{ formatTime(p.created_at) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty">暂无论文</p>
          <div v-if="paperList.total > paperFilters.page_size" class="pagination">
            <button :disabled="paperFilters.page <= 1" @click="loadContent(paperFilters.page - 1)">上一页</button>
            <span>{{ paperFilters.page }} / {{ Math.ceil(paperList.total / paperFilters.page_size) }}</span>
            <button :disabled="paperFilters.page * paperFilters.page_size >= paperList.total" @click="loadContent(paperFilters.page + 1)">下一页</button>
          </div>
        </div>

        <div v-if="contentTab === 'tasks'">
          <div class="filters">
            <select v-model="taskFilters.task_type"><option value="">全部类型</option><option value="REVIEW">REVIEW</option><option value="METRIC_EXTRACTION">METRIC_EXTRACTION</option><option value="EXPERIMENT_ANALYSIS">EXPERIMENT_ANALYSIS</option></select>
            <select v-model="taskFilters.status"><option value="">全部状态</option><option value="PENDING">PENDING</option><option value="RUNNING">RUNNING</option><option value="SUCCEEDED">SUCCEEDED</option><option value="FAILED">FAILED</option><option value="CANCELLED">CANCELLED</option></select>
            <input v-model="taskFilters.user_id" placeholder="用户 UUID" />
            <input v-model="taskFilters.paper_id" placeholder="论文 UUID" />
            <button @click="loadContent(1)">筛选</button>
          </div>
          <table v-if="taskList.items.length">
            <thead><tr><th>类型</th><th>状态</th><th>用户</th><th>创建时间</th></tr></thead>
            <tbody>
              <tr v-for="t in taskList.items" :key="t.id">
                <td>{{ t.task_type }}</td><td>{{ t.status }}</td><td>{{ t.user_id }}</td><td>{{ formatTime(t.created_at) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty">暂无任务</p>
          <div v-if="taskList.total > taskFilters.page_size" class="pagination">
            <button :disabled="taskFilters.page <= 1" @click="loadContent(taskFilters.page - 1)">上一页</button>
            <span>{{ taskFilters.page }} / {{ Math.ceil(taskList.total / taskFilters.page_size) }}</span>
            <button :disabled="taskFilters.page * taskFilters.page_size >= taskList.total" @click="loadContent(taskFilters.page + 1)">下一页</button>
          </div>
        </div>

        <div v-if="contentTab === 'exports'">
          <div class="filters">
            <select v-model="exportFilters.report_type"><option value="">全部类型</option><option value="MARKDOWN">MARKDOWN</option><option value="PDF">PDF</option><option value="DOCX">DOCX</option></select>
            <select v-model="exportFilters.status"><option value="">全部状态</option><option value="PENDING">PENDING</option><option value="GENERATING">GENERATING</option><option value="READY">READY</option><option value="FAILED">FAILED</option></select>
            <input v-model="exportFilters.user_id" placeholder="用户 UUID" />
            <input v-model="exportFilters.paper_id" placeholder="论文 UUID" />
            <button @click="loadContent(1)">筛选</button>
          </div>
          <table v-if="exportList.items.length">
            <thead><tr><th>类型</th><th>状态</th><th>用户</th><th>创建时间</th></tr></thead>
            <tbody>
              <tr v-for="e in exportList.items" :key="e.id">
                <td>{{ e.report_type }}</td><td>{{ e.status }}</td><td>{{ e.user_id }}</td><td>{{ formatTime(e.created_at) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty">暂无报告</p>
          <div v-if="exportList.total > exportFilters.page_size" class="pagination">
            <button :disabled="exportFilters.page <= 1" @click="loadContent(exportFilters.page - 1)">上一页</button>
            <span>{{ exportFilters.page }} / {{ Math.ceil(exportList.total / exportFilters.page_size) }}</span>
            <button :disabled="exportFilters.page * exportFilters.page_size >= exportList.total" @click="loadContent(exportFilters.page + 1)">下一页</button>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'audit'">
        <div class="filters">
          <select v-model="auditFilters.action"><option value="">全部动作</option><option value="ADMIN_BOOTSTRAPPED">ADMIN_BOOTSTRAPPED</option><option value="USER_ROLE_CHANGED">USER_ROLE_CHANGED</option><option value="USER_STATUS_CHANGED">USER_STATUS_CHANGED</option></select>
          <input v-model="auditFilters.actor_user_id" placeholder="操作者 UUID" />
          <input v-model="auditFilters.resource_id" placeholder="目标 UUID" />
          <input v-model="auditFilters.created_from" type="datetime-local" aria-label="开始时间" />
          <input v-model="auditFilters.created_to" type="datetime-local" aria-label="结束时间" />
          <button @click="loadAudit(1)">筛选</button>
        </div>
        <table v-if="auditList.items.length">
          <thead><tr><th>时间</th><th>操作者</th><th>动作</th><th>目标</th><th>原因</th><th>变更</th></tr></thead>
          <tbody>
            <tr v-for="a in auditList.items" :key="a.id">
              <td>{{ formatTime(a.created_at) }}</td>
              <td>{{ a.actor.email }}</td>
              <td>{{ a.action }}</td>
              <td>{{ a.resource_id }}</td>
              <td>{{ a.reason }}</td>
              <td>{{ formatState(a.before_state) }} → {{ formatState(a.after_state) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty">暂无审计记录</p>
        <div v-if="auditList.total > auditFilters.page_size" class="pagination">
          <button :disabled="auditFilters.page <= 1" @click="loadAudit(auditFilters.page - 1)">上一页</button>
          <span>{{ auditFilters.page }} / {{ Math.ceil(auditList.total / auditFilters.page_size) }}</span>
          <button :disabled="auditFilters.page * auditFilters.page_size >= auditList.total" @click="loadAudit(auditFilters.page + 1)">下一页</button>
        </div>
      </section>
    </div>

    <div v-if="detailOpen" class="modal-overlay" @click.self="closeDetail">
      <div class="modal">
        <h3>用户详情</h3>
        <div v-if="detailLoading" class="loading">加载中...</div>
        <div v-else-if="detailError" class="error">{{ detailError }}</div>
        <dl v-else-if="detailUser" class="detail-grid">
          <dt>邮箱</dt><dd>{{ detailUser.email }}</dd>
          <dt>名称</dt><dd>{{ detailUser.display_name }}</dd>
          <dt>角色/状态</dt><dd>{{ detailUser.role }} / {{ detailUser.status }}</dd>
          <dt>活动会话</dt><dd>{{ detailUser.active_session_count }}</dd>
          <dt>论文/任务/报告</dt><dd>{{ detailUser.paper_count }} / {{ detailUser.task_count }} / {{ detailUser.export_count }}</dd>
        </dl>
        <div class="modal-actions"><button @click="closeDetail">关闭</button></div>
      </div>
    </div>

    <div v-if="confirmOpen" class="modal-overlay" @click.self="closeConfirm">
      <div class="modal">
        <h3>确认操作</h3>
        <p>目标用户: {{ confirmTarget?.email }}</p>
        <p>操作: {{ confirmDesc }}</p>
        <div>
          <label>原因 (8~500字):</label>
          <textarea v-model="confirmReason" rows="3" maxlength="500"></textarea>
        </div>
        <div v-if="confirmError" class="error">{{ confirmError }}</div>
        <div class="modal-actions">
          <button :disabled="actionLoading" @click="closeConfirm">取消</button>
          <button :disabled="actionLoading || !confirmReasonValid" @click="executeConfirm">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  getAdminDashboard,
  listAdminUsers,
  getAdminUser,
  patchAdminUser,
  listAdminPapers,
  listAdminTasks,
  listAdminExports,
  listAuditLogs,
  type AdminDashboardResponse,
  type AdminUserItem,
  type AdminUserListResponse,
  type AdminPaperListResponse,
  type AdminTaskListResponse,
  type AdminExportListResponse,
  type AuditLogListResponse,
} from '../api'

const auth = useAuthStore()
const router = useRouter()
const currentUserId = computed(() => auth.user?.id ?? '')

const tabs = [
  { key: 'overview', label: '总览' },
  { key: 'users', label: '用户' },
  { key: 'content', label: '内容' },
  { key: 'audit', label: '审计' },
]
const contentTabs = [
  { key: 'papers', label: '论文' },
  { key: 'tasks', label: '任务' },
  { key: 'exports', label: '报告' },
]

const activeTab = ref('overview')
const contentTab = ref('papers')
const loading = ref(false)
const error = ref('')
const notice = ref('')
let loadSeq = 0
let detailSeq = 0
let actionSeq = 0

const dashboard = ref<AdminDashboardResponse | null>(null)

const userList = reactive<AdminUserListResponse>({ items: [], total: 0, page: 1, page_size: 20 })
const userFilters = reactive({ role: '', status: '', q: '', page: 1, page_size: 20 })

const paperList = reactive<AdminPaperListResponse>({ items: [], total: 0, page: 1, page_size: 20 })
const taskList = reactive<AdminTaskListResponse>({ items: [], total: 0, page: 1, page_size: 20 })
const exportList = reactive<AdminExportListResponse>({ items: [], total: 0, page: 1, page_size: 20 })
const paperFilters = reactive({ status: '', user_id: '', q: '', page: 1, page_size: 20 })
const taskFilters = reactive({ task_type: '', status: '', user_id: '', paper_id: '', page: 1, page_size: 20 })
const exportFilters = reactive({ report_type: '', status: '', user_id: '', paper_id: '', page: 1, page_size: 20 })

const auditList = reactive<AuditLogListResponse>({ items: [], total: 0, page: 1, page_size: 20 })
const auditFilters = reactive({ action: '', actor_user_id: '', resource_id: '', created_from: '', created_to: '', page: 1, page_size: 20 })

const detailOpen = ref(false)
const detailLoading = ref(false)
const detailError = ref('')
const detailUser = ref<AdminUserItem | null>(null)

const confirmOpen = ref(false)
const confirmTarget = ref<AdminUserItem | null>(null)
const confirmField = ref<'role' | 'status'>('role')
const confirmValue = ref('')
const confirmReason = ref('')
const confirmError = ref('')
const actionLoading = ref(false)
const confirmReasonValid = computed(() => {
  const value = confirmReason.value.trim()
  return value.length >= 8 && value.length <= 500 && !/[\u0000-\u001f\u007f]/.test(value)
})

const confirmDesc = computed(() => {
  if (!confirmTarget.value) return ''
  if (confirmField.value === 'role') return confirmValue.value === 'ADMIN' ? '设为管理员' : '设为普通用户'
  return confirmValue.value === 'ACTIVE' ? '启用账户' : '禁用账户'
})

function formatTime(t: string) {
  return new Date(t).toLocaleString()
}

function formatState(s: Record<string, string>) {
  return Object.entries(s).map(([k, v]) => `${k}=${v}`).join(', ')
}

function switchTab(key: string) {
  activeTab.value = key
  void refresh()
}

async function refresh() {
  if (activeTab.value === 'users') {
    await loadUsers()
    return
  }
  if (activeTab.value === 'content') {
    await loadContent()
    return
  }
  if (activeTab.value === 'audit') {
    await loadAudit()
    return
  }
  const seq = ++loadSeq
  loading.value = true
  error.value = ''
  try {
    const result = await getAdminDashboard()
    if (seq === loadSeq && activeTab.value === 'overview') dashboard.value = result
  } catch (e: unknown) {
    if (seq === loadSeq) error.value = safeApiError(e, '总览加载失败')
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

async function loadUsers(page?: number) {
  if (page !== undefined) userFilters.page = page
  const seq = ++loadSeq
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { page: userFilters.page, page_size: userFilters.page_size }
    if (userFilters.role) params.role = userFilters.role
    if (userFilters.status) params.status = userFilters.status
    if (userFilters.q.trim()) params.q = userFilters.q.trim()
    const res = await listAdminUsers(params)
    if (seq === loadSeq && activeTab.value === 'users') Object.assign(userList, res)
  } catch (e: unknown) {
    if (seq === loadSeq) error.value = safeApiError(e, '用户列表加载失败')
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

function switchContent(key: string) {
  contentTab.value = key
  void loadContent()
}

async function loadContent(page?: number) {
  const current = contentTab.value
  const filters = current === 'papers' ? paperFilters : current === 'tasks' ? taskFilters : exportFilters
  if (page !== undefined) filters.page = page
  const seq = ++loadSeq
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { page: filters.page, page_size: filters.page_size }
    for (const [key, value] of Object.entries(filters)) {
      if (key !== 'page' && key !== 'page_size' && typeof value === 'string' && value.trim()) params[key] = value.trim()
    }
    if (current === 'papers') {
      const res = await listAdminPapers(params)
      if (seq === loadSeq && activeTab.value === 'content' && contentTab.value === current) Object.assign(paperList, res)
    } else if (current === 'tasks') {
      const res = await listAdminTasks(params)
      if (seq === loadSeq && activeTab.value === 'content' && contentTab.value === current) Object.assign(taskList, res)
    } else {
      const res = await listAdminExports(params)
      if (seq === loadSeq && activeTab.value === 'content' && contentTab.value === current) Object.assign(exportList, res)
    }
  } catch (e: unknown) {
    if (seq === loadSeq) error.value = safeApiError(e, '内容列表加载失败')
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

async function loadAudit(page?: number) {
  if (page !== undefined) auditFilters.page = page
  const seq = ++loadSeq
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { page: auditFilters.page, page_size: auditFilters.page_size }
    if (auditFilters.action) params.action = auditFilters.action
    if (auditFilters.actor_user_id.trim()) params.actor_user_id = auditFilters.actor_user_id.trim()
    if (auditFilters.resource_id.trim()) params.resource_id = auditFilters.resource_id.trim()
    if (auditFilters.created_from) params.created_from = new Date(auditFilters.created_from).toISOString()
    if (auditFilters.created_to) params.created_to = new Date(auditFilters.created_to).toISOString()
    const res = await listAuditLogs(params)
    if (seq === loadSeq && activeTab.value === 'audit') Object.assign(auditList, res)
  } catch (e: unknown) {
    if (seq === loadSeq) error.value = safeApiError(e, '审计记录加载失败')
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

function safeApiError(errorValue: unknown, fallback: string) {
  const response = (errorValue as { response?: { status?: number } })?.response
  if (response?.status === 401) {
    auth.clearAuth()
    void router.replace('/login')
    return '登录已失效，请重新登录'
  }
  if (response?.status === 403) return '当前账户无权访问管理后台'
  if (response?.status === 409) return '操作冲突，请刷新后重试'
  if (response?.status === 422) return '筛选或操作参数不合法'
  return fallback
}

async function loadUserDetail(userId: string) {
  const seq = ++detailSeq
  detailOpen.value = true
  detailLoading.value = true
  detailError.value = ''
  detailUser.value = null
  try {
    const result = await getAdminUser(userId)
    if (seq === detailSeq && detailOpen.value) detailUser.value = result
  } catch (e: unknown) {
    if (seq === detailSeq) detailError.value = safeApiError(e, '用户详情加载失败')
  } finally {
    if (seq === detailSeq) detailLoading.value = false
  }
}

function closeDetail() {
  detailSeq++
  detailOpen.value = false
}

function openConfirm(user: AdminUserItem, field: 'role' | 'status', value: string) {
  confirmTarget.value = user
  confirmField.value = field
  confirmValue.value = value
  confirmReason.value = ''
  confirmError.value = ''
  confirmOpen.value = true
}

function closeConfirm() {
  if (actionLoading.value) return
  confirmOpen.value = false
}

async function executeConfirm() {
  if (!confirmTarget.value || !confirmReasonValid.value || actionLoading.value) return
  const seq = ++actionSeq
  actionLoading.value = true
  confirmError.value = ''
  notice.value = ''
  try {
    const body: { reason: string; role?: 'USER' | 'ADMIN'; status?: 'ACTIVE' | 'DISABLED' } = { reason: confirmReason.value.trim() }
    if (confirmField.value === 'role') {
      body.role = confirmValue.value as 'USER' | 'ADMIN'
    } else {
      body.status = confirmValue.value as 'ACTIVE' | 'DISABLED'
    }
    const result = await patchAdminUser(confirmTarget.value.id, body as Parameters<typeof patchAdminUser>[1])
    if (seq !== actionSeq) return
    confirmOpen.value = false
    notice.value = result.changed ? '用户权限状态已更新' : '请求值与当前状态相同，未产生变更'
    await loadUsers(userFilters.page)
  } catch (e: unknown) {
    if (seq === actionSeq) confirmError.value = safeApiError(e, '操作失败，请稍后重试')
  } finally {
    if (seq === actionSeq) actionLoading.value = false
  }
}

onMounted(() => {
  if (!auth.isAdmin) return
  refresh()
})

onUnmounted(() => {
  loadSeq++
  detailSeq++
  actionSeq++
})
</script>

<style scoped>
.admin-dashboard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
}
.admin-tabs, .content-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 0.5rem;
}
.tab-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #ccc;
  background: #f5f5f5;
  cursor: pointer;
  border-radius: 4px 4px 0 0;
}
.tab-btn.active {
  background: #1a1a2e;
  color: #fff;
  border-color: #1a1a2e;
}
.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}
.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
}
.card h3 {
  margin: 0 0 0.5rem;
}
.card p {
  margin: 0.25rem 0;
  font-size: 0.9rem;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  padding: 0.5rem;
  border-bottom: 1px solid #eee;
  text-align: left;
  font-size: 0.85rem;
}
th {
  background: #f5f5f5;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.filters select, .filters input {
  padding: 0.4rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.pagination {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}
.pagination button {
  padding: 0.3rem 0.8rem;
  border: 1px solid #ccc;
  background: #fff;
  cursor: pointer;
  border-radius: 4px;
}
.pagination button:disabled {
  opacity: 0.5;
  cursor: default;
}
.loading, .empty {
  text-align: center;
  padding: 2rem;
  color: #888;
}
.error {
  color: #c00;
}
.notice {
  padding: 0.75rem;
  color: #1f6b37;
  background: #eaf7ee;
  border-radius: 4px;
}
.detail-grid {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.5rem 1rem;
}
.detail-grid dt {
  font-weight: 600;
}
.detail-grid dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal {
  background: #fff;
  padding: 1.5rem;
  border-radius: 8px;
  width: 420px;
  max-width: 90vw;
}
.modal h3 {
  margin-top: 0;
}
.modal textarea {
  width: 100%;
  margin-top: 0.5rem;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  resize: vertical;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
.modal-actions button {
  padding: 0.4rem 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
}
.modal-actions button:disabled {
  opacity: 0.5;
}
@media (max-width: 760px) {
  .admin-dashboard {
    padding: 0.75rem;
  }
  .admin-tabs, .content-tabs {
    overflow-x: auto;
  }
  section {
    overflow-x: auto;
  }
  .filters > * {
    min-width: 10rem;
    flex: 1 1 10rem;
  }
}
</style>
