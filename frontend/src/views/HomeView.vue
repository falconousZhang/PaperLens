<template>
  <div class="home">
    <header class="hero">
      <h1>PaperLens</h1>
      <p class="subtitle">AI 驱动的个人论文阅读学习助手</p>
    </header>

    <section class="status-section">
      <div v-if="appStore.backendStatus === 'unknown'" class="status-card loading">
        <span>正在检测后端服务...</span>
      </div>
      <div v-else-if="appStore.backendStatus === 'healthy'" class="status-card healthy">
        <span class="status-dot green"></span>
        <span>后端服务正常 (v{{ appStore.backendVersion }})</span>
      </div>
      <div v-else class="status-card unhealthy">
        <span class="status-dot red"></span>
        <span>{{ appStore.errorMessage || '后端服务不可用' }}</span>
      </div>
    </section>

    <section class="actions">
      <router-link to="/upload" class="action-btn primary">上传论文</router-link>
      <router-link to="/papers" class="action-btn">论文库</router-link>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from '../stores/app'

const appStore = useAppStore()

onMounted(() => {
  appStore.fetchHealth()
})
</script>

<style scoped>
.home {
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.hero { text-align: center; padding: 3rem 0 2rem; }
.hero h1 { font-size: 2.5rem; margin: 0; color: #1a1a2e; }
.subtitle { font-size: 1.2rem; color: #666; margin-top: 0.5rem; }
.status-section { margin: 2rem 0; }
.status-card { display: flex; align-items: center; gap: 0.5rem; padding: 1rem 1.5rem; border-radius: 8px; font-size: 0.95rem; }
.status-card.loading { background: #f5f5f5; color: #888; }
.status-card.healthy { background: #e8f5e9; color: #2e7d32; }
.status-card.unhealthy { background: #ffebee; color: #c62828; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.status-dot.green { background: #4caf50; }
.status-dot.red { background: #f44336; }
.actions { display: flex; gap: 1rem; justify-content: center; margin-top: 2rem; }
.action-btn { padding: 0.75rem 2rem; border-radius: 8px; text-decoration: none; font-size: 1rem; border: 1px solid #e0e0e0; color: #333; background: #fafafa; }
.action-btn.primary { background: #1a1a2e; color: #fff; border-color: #1a1a2e; }
.action-btn:hover { opacity: 0.85; }
</style>
