<template>
  <div class="paper-list">
    <h2>论文列表</h2>
    <div v-if="loading">加载中...</div>
    <div v-else-if="error" class="error-msg">
      <p>{{ error }}</p>
      <button @click="fetchPapers">重试</button>
    </div>
    <div v-else-if="papers.length === 0" class="empty">
      <p>暂无论文</p>
      <router-link to="/upload">上传第一篇</router-link>
    </div>
    <table v-else class="paper-table">
      <thead>
        <tr><th>标题</th><th>文件名</th><th>状态</th><th>页数</th><th>创建时间</th><th>操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="p in papers" :key="p.id">
          <td>{{ p.title }}</td>
          <td>{{ p.filename }}</td>
          <td><span :class="'status-' + p.status.toLowerCase()">{{ statusLabel(p.status) }}</span></td>
          <td>{{ p.page_count ?? '-' }}</td>
          <td>{{ formatDate(p.created_at) }}</td>
          <td><router-link :to="'/papers/' + p.id">查看</router-link></td>
        </tr>
      </tbody>
    </table>
    <router-link to="/upload" class="upload-link">上传新论文</router-link>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { listPapers, type PaperListItem } from '../api'

const papers = ref<PaperListItem[]>([])
const loading = ref(true)
const error = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchPapers() {
  error.value = ''
  try {
    const res = await listPapers()
    papers.value = res.items
    if (papers.value.some(p => p.status === 'PROCESSING')) {
      if (!pollTimer) pollTimer = setInterval(fetchPapers, 3000)
    } else if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  } catch (e: any) {
    error.value = e?.response?.data?.error?.message || '加载论文列表失败'
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  } finally {
    loading.value = false
  }
}

function statusLabel(s: string) {
  const m: Record<string, string> = { UPLOADING: '上传中', PROCESSING: '解析中', PARSED: '已解析', FAILED: '失败' }
  return m[s] || s
}

function formatDate(d: string) {
  return new Date(d).toLocaleString('zh-CN')
}

onMounted(fetchPapers)
onUnmounted(() => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
})
</script>

<style scoped>
.paper-list { max-width: 960px; margin: 2rem auto; padding: 0 1rem; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
h2 { color: #1a1a2e; }
.empty { text-align: center; color: #888; padding: 3rem; }
.error-msg { color: #c62828; padding: 1rem; text-align: center; }
.error-msg button { margin-top: 0.5rem; padding: 0.4rem 1rem; border: 1px solid #c62828; border-radius: 4px; background: #fff; color: #c62828; cursor: pointer; }
.paper-table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
.paper-table th, .paper-table td { padding: 0.75rem; border-bottom: 1px solid #e0e0e0; text-align: left; font-size: 0.9rem; }
.status-processing { color: #f57c00; font-weight: 600; }
.status-parsed { color: #2e7d32; }
.status-failed { color: #c62828; }
.upload-link { display: inline-block; margin-top: 1rem; color: #1a1a2e; }
</style>
