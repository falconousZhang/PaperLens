<template>
  <div class="paper-list">
    <h2>论文库</h2>

    <div class="toolbar">
      <input v-model="keyword" class="search-input" maxlength="100" placeholder="搜索标题或文件名..." @input="debouncedFetch" />
      <select v-model="filterStatus" class="filter-select" @change="applyFilters">
        <option value="">全部阅读状态</option>
        <option value="TO_READ">待读</option>
        <option value="READING">在读</option>
        <option value="COMPLETED">已读</option>
        <option value="ARCHIVED">归档</option>
      </select>
      <select v-model="filterFavorite" class="filter-select" @change="applyFilters">
        <option value="">全部收藏状态</option>
        <option value="true">已收藏</option>
        <option value="false">未收藏</option>
      </select>
      <input v-model="filterCollection" class="collection-filter" maxlength="100" placeholder="精确集合名称" @change="applyFilters" />
      <router-link to="/upload" class="upload-btn">上传新论文</router-link>
    </div>

    <p v-if="actionError" class="action-error">{{ actionError }}</p>
    <div v-if="loading">加载中...</div>
    <div v-else-if="error" class="error-msg">
      <p>{{ error }}</p>
      <button @click="fetchLibrary">重试</button>
    </div>
    <div v-else-if="papers.length === 0" class="empty">
      <p>当前筛选下暂无论文</p>
      <router-link to="/upload">上传第一篇</router-link>
    </div>
    <div v-else class="library-cards">
      <article v-for="item in papers" :key="item.paper_id" class="paper-card">
        <div class="card-heading">
          <div>
            <router-link :to="{ name: 'paper-detail', params: { id: item.paper_id } }" class="title-link">{{ item.title }}</router-link>
            <div class="filename-sub">{{ item.filename }}</div>
          </div>
          <button
            class="fav-btn"
            :class="{ active: item.favorite }"
            :disabled="isActionBusy(item.paper_id)"
            :title="item.favorite ? '取消收藏' : '收藏'"
            @click="toggleFavorite(item)"
          >{{ item.favorite ? '★' : '☆' }}</button>
        </div>

        <div class="metadata-row">
          <span>解析：{{ paperStatusLabel(item.status) }}</span>
          <span :class="'rs-' + item.reading_status.toLowerCase()">阅读：{{ readingStatusLabel(item.reading_status) }}</span>
          <span>最后阅读：{{ item.last_read_at ? formatDate(item.last_read_at) : '尚未阅读' }}</span>
        </div>

        <div class="progress-row">
          <div class="progress-bar-wrap"><div class="progress-bar" :style="{ width: item.progress_percent + '%' }"></div></div>
          <span>{{ item.progress_percent }}% · 最远 {{ item.furthest_page || 0 }}/{{ item.page_count || 0 }} 页</span>
        </div>

        <div class="record-counts">
          <span>高亮 {{ item.highlight_count }}</span>
          <span>书签 {{ item.bookmark_count }}</span>
          <span>笔记 {{ item.note_count }}</span>
          <span>知识卡 {{ item.card_count }}</span>
        </div>

        <div class="card-actions">
          <router-link :to="{ name: 'paper-read', params: { id: item.paper_id } }" class="read-link">继续阅读</router-link>
          <button :disabled="isActionBusy(item.paper_id)" @click="cycleStatus(item)">{{ nextStatusLabel(item.reading_status) }}</button>
          <input v-model="collectionDrafts[item.paper_id]" maxlength="100" placeholder="集合名称（留空清除）" />
          <button :disabled="isActionBusy(item.paper_id)" @click="saveCollection(item)">保存集合</button>
        </div>
      </article>
    </div>

    <div v-if="totalPages > 1" class="pagination">
      <button :disabled="page <= 1 || loading" @click="goPage(page - 1)">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages || loading" @click="goPage(page + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { listLibraryPapers, patchLibraryEntry, type LibraryPaperItem, type ReadingStatus } from '../api'

const papers = ref<LibraryPaperItem[]>([])
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const page = ref(1)
const total = ref(0)
const pageSize = 20
const keyword = ref('')
const filterStatus = ref<ReadingStatus | ''>('')
const filterFavorite = ref<'' | 'true' | 'false'>('')
const filterCollection = ref('')
const collectionDrafts = ref<Record<string, string>>({})
const actionBusy = ref<Record<string, boolean>>({})
let debounceTimer: ReturnType<typeof setTimeout> | null = null
let listGeneration = 0
const actionGenerations = new Map<string, number>()

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function readingStatusLabel(status: ReadingStatus): string {
  return { TO_READ: '待读', READING: '在读', COMPLETED: '已读', ARCHIVED: '归档' }[status]
}

function paperStatusLabel(status: string): string {
  return { UPLOADING: '上传中', PARSING: '解析中', PARSED: '已解析', FAILED: '失败' }[status] || status
}

function nextStatusLabel(status: ReadingStatus): string {
  return { TO_READ: '标为在读', READING: '标为已读', COMPLETED: '归档', ARCHIVED: '恢复待读' }[status]
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '时间未知' : date.toLocaleString('zh-CN')
}

function safeError(reason: unknown, fallback: string): string {
  const response = (reason as { response?: { data?: { error?: { message?: string } } } })?.response
  return response?.data?.error?.message || fallback
}

function debouncedFetch(): void {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    void fetchLibrary()
  }, 300)
}

function applyFilters(): void {
  page.value = 1
  void fetchLibrary()
}

async function fetchLibrary(): Promise<void> {
  const generation = ++listGeneration
  error.value = ''
  loading.value = true
  try {
    const response = await listLibraryPapers({
      page: page.value,
      page_size: pageSize,
      reading_status: filterStatus.value || undefined,
      favorite: filterFavorite.value === 'true' ? true : filterFavorite.value === 'false' ? false : undefined,
      collection_name: filterCollection.value.trim() || undefined,
      keyword: keyword.value.trim() || undefined,
    })
    if (generation !== listGeneration) return
    papers.value = response.items
    total.value = response.total
    page.value = response.page
    collectionDrafts.value = Object.fromEntries(response.items.map(item => [item.paper_id, item.collection_name || '']))
  } catch (reason) {
    if (generation === listGeneration) error.value = safeError(reason, '加载论文库失败')
  } finally {
    if (generation === listGeneration) loading.value = false
  }
}

function goPage(target: number): void {
  if (target < 1 || target > totalPages.value) return
  page.value = target
  void fetchLibrary()
}

function isActionBusy(paperId: string): boolean {
  return Boolean(actionBusy.value[paperId])
}

async function updateEntry(item: LibraryPaperItem, body: { reading_status?: ReadingStatus; favorite?: boolean; collection_name?: string | null }): Promise<void> {
  const paperId = item.paper_id
  const generation = (actionGenerations.get(paperId) || 0) + 1
  actionGenerations.set(paperId, generation)
  actionBusy.value = { ...actionBusy.value, [paperId]: true }
  actionError.value = ''
  try {
    const updated = await patchLibraryEntry(paperId, body)
    if (actionGenerations.get(paperId) !== generation) return
    const index = papers.value.findIndex(paper => paper.paper_id === paperId)
    const current = papers.value[index]
    if (index >= 0 && current) papers.value[index] = { ...current, ...updated }
    collectionDrafts.value = { ...collectionDrafts.value, [paperId]: updated.collection_name || '' }
  } catch (reason) {
    if (actionGenerations.get(paperId) === generation) actionError.value = safeError(reason, '论文库更新失败，请重试')
  } finally {
    if (actionGenerations.get(paperId) === generation) actionBusy.value = { ...actionBusy.value, [paperId]: false }
  }
}

function toggleFavorite(item: LibraryPaperItem): void {
  void updateEntry(item, { favorite: !item.favorite })
}

function cycleStatus(item: LibraryPaperItem): void {
  const next: Record<ReadingStatus, ReadingStatus> = { TO_READ: 'READING', READING: 'COMPLETED', COMPLETED: 'ARCHIVED', ARCHIVED: 'TO_READ' }
  void updateEntry(item, { reading_status: next[item.reading_status] })
}

function saveCollection(item: LibraryPaperItem): void {
  const value = (collectionDrafts.value[item.paper_id] || '').trim()
  void updateEntry(item, { collection_name: value || null })
}

onMounted(() => void fetchLibrary())
onUnmounted(() => {
  listGeneration++
  if (debounceTimer) clearTimeout(debounceTimer)
  for (const paperId of actionGenerations.keys()) actionGenerations.set(paperId, (actionGenerations.get(paperId) || 0) + 1)
})
</script>

<style scoped>
.paper-list { max-width: 1120px; margin: 2rem auto; padding: 0 1rem; color: #25243a; }
.toolbar { display: flex; gap: .6rem; margin: 1rem 0; flex-wrap: wrap; }
.toolbar input, .toolbar select, .card-actions input { padding: .55rem; border: 1px solid #d8d7e2; border-radius: .35rem; }
.search-input { flex: 1; min-width: 13rem; }
.collection-filter { width: 11rem; }
.upload-btn, .read-link { padding: .55rem .9rem; border-radius: .35rem; background: #25234f; color: #fff; text-decoration: none; }
.library-cards { display: grid; gap: 1rem; }
.paper-card { padding: 1rem; border: 1px solid #dedee8; border-radius: .6rem; background: #fff; }
.card-heading, .metadata-row, .progress-row, .record-counts, .card-actions { display: flex; align-items: center; gap: .8rem; flex-wrap: wrap; }
.card-heading { justify-content: space-between; }
.title-link { color: #25234f; font-weight: 650; text-decoration: none; }
.filename-sub, .metadata-row, .record-counts { color: #77758d; font-size: .82rem; }
.progress-row, .record-counts, .card-actions { margin-top: .75rem; }
.progress-bar-wrap { width: 10rem; height: .5rem; overflow: hidden; border-radius: .25rem; background: #e5e4ec; }
.progress-bar { height: 100%; border-radius: .25rem; background: #4b478c; }
.fav-btn { border: 0; background: transparent; color: #aaa; font-size: 1.5rem; cursor: pointer; }
.fav-btn.active { color: #e3a008; }
.rs-reading { color: #bd6400; }.rs-completed { color: #24743a; }.rs-archived { color: #777; }
.card-actions button, .pagination button { padding: .45rem .7rem; border: 1px solid #d8d7e2; border-radius: .35rem; background: #fff; cursor: pointer; }
.card-actions input { flex: 1; min-width: 12rem; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 1rem; margin: 1.2rem 0; }
.action-error, .error-msg { color: #b42318; }.empty, .error-msg { padding: 2rem; text-align: center; }
button:disabled { cursor: not-allowed; opacity: .55; }
</style>
