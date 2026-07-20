import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { usePolling } from '../composables/usePolling'
import { createRouter, createMemoryHistory } from 'vue-router'

function createMockRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' } },
      { path: '/login', name: 'login', component: { template: '<div/>' } },
    ],
  })
}

function mountPolling(router: ReturnType<typeof createMockRouter>) {
  let polling!: ReturnType<typeof usePolling>
  const wrapper = mount(defineComponent({
    setup() {
      polling = usePolling(100)
      return () => h('div')
    },
  }), {
    global: { plugins: [router] },
  })
  return { polling, wrapper }
}

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('resumes polling after refresh and reaches terminal state', async () => {
    const router = createMockRouter()
    router.push('/')
    await router.isReady()

    const pushSpy = vi.spyOn(router, 'push')
    let callCount = 0
    const fetcher = vi.fn(async () => {
      callCount++
      return { status: callCount >= 3 ? 'SUCCEEDED' : 'RUNNING' }
    })
    const onUpdate = vi.fn()
    const isTerminal = (data: { status: string }) => data.status !== 'RUNNING' && data.status !== 'PENDING'

    const { polling, wrapper } = mountPolling(router)
    const { startPolling, stopPolling, isPolling } = polling

    startPolling(fetcher, onUpdate, isTerminal)

    expect(isPolling.value).toBe(true)

    await vi.advanceTimersByTimeAsync(100)
    await nextTick()
    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(onUpdate).toHaveBeenCalledWith({ status: 'RUNNING' })

    await vi.advanceTimersByTimeAsync(100)
    await nextTick()
    expect(fetcher).toHaveBeenCalledTimes(2)

    await vi.advanceTimersByTimeAsync(100)
    await nextTick()
    expect(fetcher).toHaveBeenCalledTimes(3)
    expect(onUpdate).toHaveBeenCalledWith({ status: 'SUCCEEDED' })
    expect(isPolling.value).toBe(false)

    expect(pushSpy).not.toHaveBeenCalled()
    stopPolling()
    wrapper.unmount()
  })

  it('stops polling and redirects to login on 401', async () => {
    const router = createMockRouter()
    router.push('/')
    await router.isReady()

    const pushSpy = vi.spyOn(router, 'push')
    const fetcher = vi.fn(async () => {
      const err = new Error('Unauthorized') as any
      err.response = { status: 401 }
      throw err
    })
    const onUpdate = vi.fn()
    const isTerminal = () => false
    const onError = vi.fn()

    const { polling, wrapper } = mountPolling(router)
    const { startPolling, isPolling } = polling

    startPolling(fetcher, onUpdate, isTerminal, onError)

    await vi.advanceTimersByTimeAsync(100)
    await nextTick()

    expect(isPolling.value).toBe(false)
    expect(pushSpy).toHaveBeenCalledWith(expect.objectContaining({ name: 'login' }))
    expect(onError).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
