import { afterEach, describe, expect, it } from 'vitest'
import type { InternalAxiosRequestConfig } from 'axios'
import api, {
  uploadExperimentFile,
  listExperimentFiles,
  getExperimentFile,
  createExperimentAnalysis,
  getExperimentResult,
  createComparisons,
  setAccessToken,
} from '../api'
import router from '../router'

const originalAdapter = api.defaults.adapter

function responseFor(config: InternalAxiosRequestConfig, data: any, status: number) {
  return { data, status, statusText: 'OK', headers: {}, config }
}

afterEach(() => {
  api.defaults.adapter = originalAdapter
  setAccessToken(null)
})

describe('Experiment API and route contract', () => {
  it('marks the experiment page as a protected route', () => {
    const route = router.getRoutes().find(item => item.name === 'paper-experiment')
    expect(route?.path).toBe('/papers/:id/experiment')
    expect(route?.meta.requiresAuth).toBe(true)
  })

  it('uploadExperimentFile sends FormData to correct URL', async () => {
    let captured!: InternalAxiosRequestConfig
    api.defaults.adapter = async config => {
      captured = config
      return responseFor(config, {
        id: 'ef-1',
        paper_id: 'paper-1',
        filename: 'test.csv',
        file_type: 'CSV',
        file_size: 1024,
        row_count: 10,
        column_count: 3,
        columns_info: { version: 1, encoding: 'utf-8', delimiter: ',', sheet_name: null, columns: [{ name: 'a', dtype: 'float', nullable: false, null_count: 0 }] },
        created_at: '2026-01-01T00:00:00Z',
        duplicate: false,
      }, 201)
    }
    const file = new File(['data'], 'test.csv', { type: 'text/csv' })
    await uploadExperimentFile('paper-1', file)
    expect(captured.url).toBe('/papers/paper-1/experiment-files/upload')
    expect(captured.method).toBe('post')
    expect(captured.data).toBeInstanceOf(FormData)
    expect(String(captured.headers['Content-Type'])).not.toContain('multipart/form-data')
  })

  it('listExperimentFiles sends GET with pagination params', async () => {
    let captured!: InternalAxiosRequestConfig
    api.defaults.adapter = async config => {
      captured = config
      return responseFor(config, { items: [], total: 0, page: 1, page_size: 20 }, 200)
    }
    await listExperimentFiles('paper-1', 2, 10)
    expect(captured.url).toBe('/papers/paper-1/experiment-files')
    expect(captured.method).toBe('get')
    expect(captured.params).toEqual({ page: 2, page_size: 10 })
  })

  it('listExperimentFiles clamps invalid pagination params', async () => {
    let captured!: InternalAxiosRequestConfig
    api.defaults.adapter = async config => {
      captured = config
      return responseFor(config, { items: [], total: 0, page: 1, page_size: 100 }, 200)
    }
    await listExperimentFiles('paper-1', Number.NaN, 999)
    expect(captured.params).toEqual({ page: 1, page_size: 100 })
  })

  it('getExperimentFile sends GET to the trusted detail endpoint', async () => {
    let captured!: InternalAxiosRequestConfig
    api.defaults.adapter = async config => {
      captured = config
      return responseFor(config, {
        id: 'ef-1', paper_id: 'paper-1', filename: 'test.csv', file_type: 'CSV',
        file_size: 1024, row_count: 10, column_count: 1,
        columns_info: { version: 1, encoding: 'utf-8', delimiter: ',', sheet_name: null, columns: [] },
        created_at: '2026-01-01T00:00:00Z',
      }, 200)
    }
    await getExperimentFile('ef-1')
    expect(captured.url).toBe('/experiment-files/ef-1')
    expect(captured.method).toBe('get')
  })

  it('createExperimentAnalysis sends POST to correct URL', async () => {
    let captured!: InternalAxiosRequestConfig
    api.defaults.adapter = async config => {
      captured = config
      return responseFor(config, {
        id: 'at-1',
        paper_id: 'paper-1',
        task_type: 'EXPERIMENT_ANALYSIS',
        status: 'PENDING',
        progress: 0,
        experiment_file_id: 'ef-1',
        created_at: '2026-01-01T00:00:00Z',
        duplicate: false,
      }, 201)
    }
    await createExperimentAnalysis('ef-1')
    expect(captured.url).toBe('/experiment-files/ef-1/analysis')
    expect(captured.method).toBe('post')
  })

  it('getExperimentResult sends GET to correct URL', async () => {
    let captured!: InternalAxiosRequestConfig
    api.defaults.adapter = async config => {
      captured = config
      return responseFor(config, {
        id: 'er-1',
        file_id: 'ef-1',
        task_id: 'at-1',
        summary_stats: { version: 1, row_count: 10, column_count: 1, columns: [{ name: 'a', dtype: 'float', count: 10, null_count: 0, stats: { mean: 1, stddev: null, min: 1, max: 1, median: 1 } }] },
        metric_comparisons: null,
        created_at: '2026-01-01T00:00:00Z',
      }, 200)
    }
    await getExperimentResult('ef-1')
    expect(captured.url).toBe('/experiment-files/ef-1/result')
    expect(captured.method).toBe('get')
  })

  it('createComparisons sends POST with metric_task_id', async () => {
    let captured!: InternalAxiosRequestConfig
    api.defaults.adapter = async config => {
      captured = config
      return responseFor(config, {
        file_id: 'ef-1',
        experiment_result_id: 'er-1',
        metric_task_id: 'mt-1',
        comparisons: [],
        duplicate: false,
      }, 201)
    }
    await createComparisons('ef-1', { metric_task_id: 'mt-1' })
    expect(captured.url).toBe('/experiment-files/ef-1/comparisons')
    expect(captured.method).toBe('post')
    const body = typeof captured.data === 'string' ? JSON.parse(captured.data) : captured.data
    expect(body).toEqual({ metric_task_id: 'mt-1' })
  })
})
