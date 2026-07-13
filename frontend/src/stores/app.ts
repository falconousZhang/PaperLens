import { defineStore } from 'pinia'
import { ref } from 'vue'
import { checkHealth, type HealthResponse } from '../api'

export const useAppStore = defineStore('app', () => {
  const backendStatus = ref<'unknown' | 'healthy' | 'unhealthy'>('unknown')
  const backendVersion = ref('')
  const errorMessage = ref('')

  async function fetchHealth() {
    try {
      const data: HealthResponse = await checkHealth()
      backendStatus.value = data.status === 'healthy' ? 'healthy' : 'unhealthy'
      backendVersion.value = data.version
      errorMessage.value = ''
    } catch {
      backendStatus.value = 'unhealthy'
      backendVersion.value = ''
      errorMessage.value = '无法连接到后端服务，请确认后端已启动。'
    }
  }

  return { backendStatus, backendVersion, errorMessage, fetchHealth }
})