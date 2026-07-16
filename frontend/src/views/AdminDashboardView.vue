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
            @click="contentTab = ct.key; loadContent()"
          >{{ ct.label }}</button>
        </div>

        <div v-if="contentTab === 'papers'">
          <table v-if="paperList.items.length">
            <thead><tr><th>标题</th><th>所有者</th><th>状态</th><th>页数</th><th>创建时间</th></tr></thead>
            <tbody>
              <tr v-for="p in paperList.items" :key="p.id">
                <td>{{ p.title }}</td><td>{{ p.owner_email }}</td><td>{{ p.status }}</td><td>{{ p.page_count }}</td><td>{{ formatTime(p.created_at) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty">暂无论文</p>
          <div v-if="paperList.total > contentFilters.page_size" class="pagination">
            <button :disabled="contentFilters.page <= 1" @click="contentFilters.page--; loadContent()">上一页</button>
            <span>{{ contentFilters.page }} / {{ Math.ceil(paperList.total / contentFilters.page_size) }}</span>
            <button :disabled="contentFilters.page * contentFilters.page_size >= paperList.total" @click="contentFilters.page++; loadContent()">下一页</button>
          </div>
        </div>

        <div v-if="contentTab === 'tasks'">
          <table v-if="taskList.items.length">
            <thead><tr><th>类型</th><th>状态</th><th>用户</th><th>创建时间</th></tr></thead>
            <tbody>
              <tr v-for="t in taskList.items" :key="t.id">
                <td>{{ t.task_type }}</td><td>{{ t.status }}</td><td>{{ t.user_id }}</td><td>{{ formatTime(t.created_at) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty">暂无任务</p>
          <div v-if="taskList.total > contentFilters.page_size" class="pagination">
            <button :disabled="contentFilters.page <= 1" @click="contentFilters.page--; loadContent()">上一页</button>
            <span>{{ contentFilters.page }} / {{ Math.ceil(taskList.total / contentFilters.page_size) }}</span>
            <button :disabled="contentFilters.page * contentFilters.page_size >= taskList.total" @click="contentFilters.page++; loadContent()">下一页</button>
          </div>
        </div>

        <div v-if="contentTab === 'exports'">
          <table v-if="exportList.items.length">
            <thead><tr><th>类型</th><th>状态</th><th>用户</th><th>创建时间</th></tr></thead>
            <tbody>
              <tr v-for="e in exportList.items" :key="e.id">
                <td>{{ e.report_type }}</td><td>{{ e.status }}</td><td>{{ e.user_id }}</td><td>{{ formatTime(e.created_at) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty">暂无报告</p>
          <div v-if="exportList.total > contentFilters.page_size" class="pagination">
            <button :disabled="contentFilters.page <= 1" @click="contentFilters.page--; loadContent()">上一页</button>
            <span>{{ contentFilters.page }} / {{ Math.ceil(exportList.total / contentFilters.page_size) }}</span>
            <button :disabled="contentFilters.page * contentFilters.page_size >= exportList.total" @click="contentFilters.page++; loadContent()">下一页</button>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'audit'">
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
          <button :disabled="auditFilters.page <= 1" @click="auditFilters.page--; loadAudit()">上一页</button>
          <span>{{ auditFilters.page }} / {{ Math.ceil(auditList.total / auditFilters.page_size) }}</span>
          <button :disabled="auditFilters.page * auditFilters.page_size >= auditList.total" @click="auditFilters.page++; loadAudit()">下一页</button>
        </div>
      </section>
    </div>

    <div v-if="confirmOpen" class="modal-overlay" @click.self="confirmOpen = false">
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
          <button :disabled="actionLoading" @click="confirmOpen = false">取消</button>
          <button :disabled="actionLoading || confirmReason.length < 8" @click="executeConfirm">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  getAdminDashboard,
  listAdminUsers,
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
let loadSeq = 0

const dashboard = ref<AdminDashboardResponse | null>(null)

const userList = reactive<AdminUserListResponse>({ items: [], total: 0, page: 1, page_size: 20 })
const userFilters = reactive({ role: '', status: '', q: '', page: 1, page_size: 20 })

const paperList = reactive<AdminPaperListResponse>({ items: [], total: 0, page: 1, page_size: 20 })
const taskList = reactive<AdminTaskListResponse>({ items: [], total: 0, page: 1, page_size: 20 })
const exportList = reactive<AdminExportListResponse>({ items: [], total: 0, page: 1, page_size: 20 })
const contentFilters = reactive({ page: 1, page_size: 20 })

const auditList = reactive<AuditLogListResponse>({ items: [], total: 0, page: 1, page_size: 20 })
const auditFilters = reactive({ page: 1, page_size: 20 })

const confirmOpen = ref(false)
const confirmTarget = ref<AdminUserItem | null>(null)
const confirmField = ref<'role' | 'status'>('role')
const confirmValue = ref('')
const confirmReason = ref('')
const confirmError = ref('')
const actionLoading = ref(false)

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
  refresh()
}

async function refresh() {
  const seq = ++loadSeq
  loading.value = true
  error.value = ''
  try {
    if (activeTab.value === 'overview') {
      dashboard.value = await getAdminDashboard()
    } else if (activeTab.value === 'users') {
      await loadUsers()
    } else if (activeTab.value === 'content') {
      await loadContent()
    } else if (activeTab.value === 'audit') {
      await loadAudit()
    }
  } catch (e: any) {
    if (seq === loadSeq) {
      error.value = e.response?.status === 401 ? '请重新登录' : e.response?.data?.error?.message || '加载失败'
    }
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

async function loadUsers(page?: number) {
  if (page !== undefined) userFilters.page = page
  const seq = ++loadSeq
  try {
    const params: Record<string, any> = { page: userFilters.page, page_size: userFilters.page_size }
    if (userFilters.role) params.role = userFilters.role
    if (userFilters.status) params.status = userFilters.status
    if (userFilters.q) params.q = userFilters.q
    const res = await listAdminUsers(params)
    if (seq === loadSeq) Object.assign(userList, res)
  } catch (e: any) {
    if (seq === loadSeq) error.value = e.response?.data?.error?.message || '加载失败'
  }
}

async function loadContent() {
  const seq = ++loadSeq
  try {
    const params = { page: contentFilters.page, page_size: contentFilters.page_size }
    if (contentTab.value === 'papers') {
      const res = await listAdminPapers(params)
      if (seq === loadSeq) Object.assign(paperList, res)
    } else if (contentTab.value === 'tasks') {
      const res = await listAdminTasks(params)
      if (seq === loadSeq) Object.assign(taskList, res)
    } else {
      const res = await listAdminExports(params)
      if (seq === loadSeq) Object.assign(exportList, res)
    }
  } catch (e: any) {
    if (seq === loadSeq) error.value = e.response?.data?.error?.message || '加载失败'
  }
}

async function loadAudit() {
  const seq = ++loadSeq
  try {
    const res = await listAuditLogs({ page: auditFilters.page, page_size: auditFilters.page_size })
    if (seq === loadSeq) Object.assign(auditList, res)
  } catch (e: any) {
    if (seq === loadSeq) error.value = e.response?.data?.error?.message || '加载失败'
  }
}

function openConfirm(user: AdminUserItem, field: 'role' | 'status', value: string) {
  confirmTarget.value = user
  confirmField.value = field
  confirmValue.value = value
  confirmReason.value = ''
  confirmError.value = ''
  confirmOpen.value = true
}

async function executeConfirm() {
  if (!confirmTarget.value || confirmReason.value.length < 8) return
  actionLoading.value = true
  confirmError.value = ''
  try {
    const body: { reason: string; role?: string; status?: string } = { reason: confirmReason.value }
    body[confirmField.value] = confirmValue.value
    await patchAdminUser(confirmTarget.value.id, body as any)
    confirmOpen.value = false
    await loadUsers()
  } catch (e: any) {
    const status = e.response?.status
    if (status === 401) {
      auth.clearAuth()
    } else if (status === 409) {
      confirmError.value = '操作冲突，可能违反最后管理员保护'
    } else {
      confirmError.value = e.response?.data?.error?.message || '操作失败'
    }
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  if (!auth.isAdmin) return
  refresh()
})

onUnmounted(() => {
  loadSeq++
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
</style>