import { afterEach, describe, expect, it } from 'vitest'
import type { InternalAxiosRequestConfig } from 'axios'
import api, {
  createMetricExtractionTask,
  listMetrics,
  setAccessToken,
} from '../api'
import router from '../router'

const originalAdapter = api.defaults.adapter

function responseFor(config: InternalAxiosRequestConfig) {
  const data = config.method === 'post'
    ? {
        id: 'task-1',
        paper_id: 'paper-1',
        task_type: 'METRIC_EXTRACTION',
        status: 'PENDING',
        progress: 0,
        created_at: '2026-07-14T00:00:00Z',
      }
    : { items: [], total: 0, page: 1, page_size: 20 }
  return {
    data,
    status: config.method === 'post' ? 201 : 200,
    statusText: 'OK',
    headers: {},
    config,
  }
}

afterEach(() => {
  api.defaults.adapter = originalAdapter
  setAccessToken(null)
})

describe('metric API and route contract', () => {
  it('creates METRIC_EXTRACTION with an empty options object', async () => {
    let captured!: InternalAxiosRequestConfig
    api.defaults.adapter = async config => {
      captured = config
      return responseFor(config)
    }
    await createMetricExtractionTask('paper-1')
    expect(captured.url).toBe('/papers/paper-1/tasks')
    expect(captured.method).toBe('post')
    const body = typeof captured.data === 'string' ? JSON.parse(captured.data) : captured.data
    expect(body).toEqual({ task_type: 'METRIC_EXTRACTION', options: {} })
  })

  it('serializes only supported metric filters and clamps pagination', async () => {
    let captured!: InternalAxiosRequestConfig
    api.defaults.adapter = async config => {
      captured = config
      return responseFor(config)
    }
    await listMetrics('paper-1', {
      task_id: 'task-1',
      metric_name: 'accuracy',
      dataset_name: 'SQuAD',
      checkpoint_type: 'BEST',
      page: 0,
      page_size: 500,
    })
    expect(captured.params).toEqual({
      task_id: 'task-1',
      metric_name: 'accuracy',
      dataset_name: 'SQuAD',
      checkpoint_type: 'BEST',
      page: 1,
      page_size: 100,
    })
  })

  it('omits empty filters and non-finite pagination values', async () => {
    let captured!: InternalAxiosRequestConfig
    api.defaults.adapter = async config => {
      captured = config
      return responseFor(config)
    }
    await listMetrics('paper-1', {
      task_id: '',
      metric_name: '',
      dataset_name: '',
      page: Number.NaN,
      page_size: Number.POSITIVE_INFINITY,
    })
    expect(captured.params).toEqual({})
  })

  it('marks the metric page as a protected route', () => {
    const route = router.getRoutes().find(item => item.name === 'paper-metrics')
    expect(route?.path).toBe('/papers/:id/metrics')
    expect(route?.meta.requiresAuth).toBe(true)
  })
})
