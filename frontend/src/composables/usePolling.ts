import { onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export const SAFE_POLLING_ERROR = '请求失败，请稍后重试'

export function usePolling(intervalMs = 3000) {
  const route = useRoute()
  const router = useRouter()
  let timer: ReturnType<typeof setInterval> | null = null
  let generation = 0
  let requestInFlight = false
  const isPolling = ref(false)

  function startPolling<T>(
    fetcher: () => Promise<T>,
    onUpdate: (data: T) => void | Promise<void>,
    isTerminal: (data: T) => boolean,
    onError?: (error: unknown) => void,
  ) {
    stopPolling()
    const gen = ++generation
    requestInFlight = false
    isPolling.value = true

    timer = setInterval(async () => {
      if (requestInFlight) return
      if (gen !== generation) return
      requestInFlight = true
      try {
        const data = await fetcher()
        if (gen !== generation) return
        await onUpdate(data)
        if (gen !== generation) return
        if (isTerminal(data)) {
          stopPolling()
        }
      } catch (e: unknown) {
        if (gen !== generation) return
        const err = e as { response?: { status?: number } }
        const status = err?.response?.status
        if (status === 401) {
          stopPolling()
          void router.push({
            name: 'login',
            query: { redirect: route.fullPath },
          })
          return
        }
        stopPolling()
        if (onError) {
          onError(e)
        }
      } finally {
        requestInFlight = false
      }
    }, intervalMs)
  }

  function stopPolling() {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
    generation++
    isPolling.value = false
  }

  onUnmounted(() => {
    stopPolling()
  })

  return { startPolling, stopPolling, isPolling }
}
