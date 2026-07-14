import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
  withCredentials: true,
})

export const authRefreshClient = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
  withCredentials: true,
})

let accessToken: string | null = null
let refreshPromise: Promise<AuthTokenResponse> | null = null
let authFailureHandler: (() => void) | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

export function setAuthFailureHandler(handler: (() => void) | null): void {
  authFailureHandler = handler
}

function isPublicAuthRequest(url = ''): boolean {
  return [
    '/auth/login',
    '/auth/register',
    '/auth/refresh',
    '/auth/forgot-password',
    '/auth/reset-password',
  ].some((path) => url.endsWith(path))
}

async function sharedRefresh(): Promise<AuthTokenResponse> {
  if (!refreshPromise) {
    refreshPromise = authRefreshClient
      .post<AuthTokenResponse>('/auth/refresh')
      .then(({ data }) => {
        setAccessToken(data.access_token)
        return data
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as typeof error.config & { _retry?: boolean }
    if (
      error.response?.status === 401
      && originalRequest
      && !originalRequest._retry
      && !isPublicAuthRequest(originalRequest.url)
    ) {
      originalRequest._retry = true
      try {
        const data = await sharedRefresh()
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        return api(originalRequest)
      } catch (refreshError) {
        setAccessToken(null)
        authFailureHandler?.()
        return Promise.reject(refreshError)
      }
    }
    if (error.response?.status === 401 && originalRequest?._retry) {
      setAccessToken(null)
      authFailureHandler?.()
    }
    const data = error.response?.data
    if (data?.error?.message) {
      error.message = data.error.message
    } else if (error.response?.status === 413) {
      error.message = '文件超过上传限制'
    }
    return Promise.reject(error)
  },
)

export interface HealthResponse {
  status: string
  version: string
}

export interface PaperUploadResponse {
  id: string
  title: string
  filename: string
  file_size: number
  status: string
  created_at: string
}

export interface PaperListItem {
  id: string
  title: string
  filename: string
  page_count: number | null
  status: string
  created_at: string
}

export interface PaperListResponse {
  items: PaperListItem[]
  total: number
  page: number
  page_size: number
}

export interface PaperDetail {
  id: string
  title: string
  filename: string
  file_size: number
  page_count: number | null
  status: string
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface SectionItem {
  id: string
  section_type: string
  title: string | null
  level: number
  sequence: number
  start_page: number | null
  end_page: number | null
  text_content: string | null
}

export interface EvidenceItem {
  id: string
  quoted_text: string
  page_number: number
  bbox_x0: number | null
  bbox_y0: number | null
  bbox_x1: number | null
  bbox_y1: number | null
  char_start: number | null
  char_end: number | null
  evidence_type: string
  section_id: string | null
  chunk_id: string | null
}

export interface PageDetail {
  id: string
  page_number: number
  text_content: string | null
  normalized_text_content: string | null
  width: number | null
  height: number | null
}

export async function checkHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health')
  return data
}

export async function uploadPaper(file: File, onProgress?: (pct: number) => void): Promise<PaperUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<PaperUploadResponse>('/papers/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress(e) {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data
}

export async function listPapers(page = 1, pageSize = 20): Promise<PaperListResponse> {
  const { data } = await api.get<PaperListResponse>('/papers', { params: { page, page_size: pageSize } })
  return data
}

export async function getPaper(paperId: string): Promise<PaperDetail> {
  const { data } = await api.get<PaperDetail>(`/papers/${paperId}`)
  return data
}

export async function getPage(paperId: string, pageNumber: number): Promise<PageDetail> {
  const { data } = await api.get<PageDetail>(`/papers/${paperId}/pages/${pageNumber}`)
  return data
}

export async function listSections(paperId: string): Promise<SectionItem[]> {
  const { data } = await api.get<{ sections: SectionItem[] }>(`/papers/${paperId}/sections`)
  return data.sections
}

export async function listEvidences(paperId: string): Promise<EvidenceItem[]> {
  const { data } = await api.get<{ evidences: EvidenceItem[] }>(`/papers/${paperId}/evidences`)
  return data.evidences
}

export type ReviewDimension =
  | 'SOUNDNESS'
  | 'NOVELTY'
  | 'CLARITY'
  | 'COMPLETENESS'
  | 'REPRODUCIBILITY'
  | 'SIGNIFICANCE'
  | 'OVERALL'

export type TaskStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'CANCELLED'

export type TaskType = 'REVIEW' | 'METRIC_EXTRACTION' | 'EXPERIMENT_ANALYSIS'

export type FindingType = 'STRENGTH' | 'WEAKNESS' | 'SUGGESTION'

export type VerificationStatus = 'VERIFIED' | 'UNVERIFIED' | 'PENDING'

export type OverallVerdict =
  | 'ACCEPT'
  | 'WEAK_ACCEPT'
  | 'BORDERLINE'
  | 'WEAK_REJECT'
  | 'REJECT'

export interface TaskDetail {
  id: string
  paper_id: string
  task_type: TaskType
  status: TaskStatus
  progress: number
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface TaskListResponse {
  items: TaskDetail[]
}

export interface ReviewTaskCreateRequest {
  task_type: 'REVIEW'
  options: {
    dimensions: ReviewDimension[]
    language: 'zh' | 'en'
  }
}

export interface MetricExtractionTaskCreateRequest {
  task_type: 'METRIC_EXTRACTION'
  options?: Record<string, never>
}

export type TaskCreateRequest = ReviewTaskCreateRequest | MetricExtractionTaskCreateRequest

export type CheckpointType = 'BEST' | 'FINAL' | 'MAX' | 'MEAN' | 'LAST' | 'UNKNOWN'

export interface MetricRecord {
  id: string
  paper_id: string
  task_id: string
  model_name: string | null
  dataset_name: string | null
  metric_name: string
  metric_value: number
  checkpoint_type: CheckpointType
  checkpoint_source: string | null
  evidence_id: string | null
  table_id: string | null
  row_index: number | null
  raw_text: string
  created_at: string
}

export interface MetricListParams {
  task_id?: string
  metric_name?: string
  dataset_name?: string
  checkpoint_type?: CheckpointType
  page?: number
  page_size?: number
}

export interface MetricListResponse {
  items: MetricRecord[]
  total: number
  page: number
  page_size: number
}

export interface TaskCreateResponse {
  id: string
  paper_id: string
  task_type: TaskType
  status: TaskStatus
  progress: number
  created_at: string
}

export interface Finding {
  id: string
  finding_type: FindingType
  content: string
  confidence: number | null
  verification_status: VerificationStatus
  sequence: number
  evidence_ids: string[]
}

export interface ReviewResult {
  id: string
  task_id: string
  dimension: ReviewDimension
  rating: number | null
  summary: string | null
  overall_verdict: OverallVerdict | null
  created_at: string
  findings: Finding[]
}

export interface ReviewListResponse {
  reviews: ReviewResult[]
}

export async function listTasks(paperId: string): Promise<TaskListResponse> {
  const { data } = await api.get<TaskListResponse>(`/papers/${paperId}/tasks`)
  return data
}

export async function createTask(
  paperId: string,
  body: TaskCreateRequest,
): Promise<TaskCreateResponse> {
  const { data } = await api.post<TaskCreateResponse>(`/papers/${paperId}/tasks`, body)
  return data
}

export async function getTask(taskId: string): Promise<TaskDetail> {
  const { data } = await api.get<TaskDetail>(`/tasks/${taskId}`)
  return data
}

export async function listReviews(paperId: string): Promise<ReviewListResponse> {
  const { data } = await api.get<ReviewListResponse>(`/papers/${paperId}/reviews`)
  return data
}

export interface AuthUser {
  id: string
  email: string
  display_name: string
  role: string
  status: string
  created_at: string
}

export interface AuthTokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}

export interface MessageResponse {
  message: string
}

export async function register(email: string, password: string, display_name: string): Promise<AuthTokenResponse> {
  const { data } = await api.post<AuthTokenResponse>('/auth/register', { email, password, display_name })
  return data
}

export async function login(email: string, password: string): Promise<AuthTokenResponse> {
  const { data } = await api.post<AuthTokenResponse>('/auth/login', { email, password })
  return data
}

export async function refreshToken(): Promise<AuthTokenResponse> {
  return sharedRefresh()
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}

export async function logoutAll(): Promise<void> {
  await api.post('/auth/logout-all')
}

export async function getMe(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>('/auth/me')
  return data
}

export async function updateMe(display_name?: string): Promise<AuthUser> {
  const { data } = await api.patch<AuthUser>('/auth/me', { display_name })
  return data
}

export async function changePassword(old_password: string, new_password: string): Promise<MessageResponse> {
  const { data } = await api.post<MessageResponse>('/auth/change-password', { old_password, new_password })
  return data
}

export async function forgotPassword(email: string): Promise<MessageResponse> {
  const { data } = await api.post<MessageResponse>('/auth/forgot-password', { email })
  return data
}

export async function resetPassword(token: string, new_password: string): Promise<MessageResponse> {
  const { data } = await api.post<MessageResponse>('/auth/reset-password', { token, new_password })
  return data
}

export async function listMetrics(paperId: string, params: MetricListParams = {}): Promise<MetricListResponse> {
  const filtered: Record<string, string | number> = {}
  if (params.task_id) filtered.task_id = params.task_id
  if (params.metric_name) filtered.metric_name = params.metric_name
  if (params.dataset_name) filtered.dataset_name = params.dataset_name
  if (params.checkpoint_type) filtered.checkpoint_type = params.checkpoint_type
  if (Number.isFinite(params.page)) filtered.page = Math.max(1, Math.trunc(params.page!))
  if (Number.isFinite(params.page_size)) {
    filtered.page_size = Math.min(100, Math.max(1, Math.trunc(params.page_size!)))
  }
  const { data } = await api.get<MetricListResponse>(`/papers/${paperId}/metrics`, { params: filtered })
  return data
}

export async function getMetric(metricId: string): Promise<MetricRecord> {
  const { data } = await api.get<MetricRecord>(`/metrics/${metricId}`)
  return data
}

export async function createMetricExtractionTask(paperId: string): Promise<TaskCreateResponse> {
  return createTask(paperId, {
    task_type: 'METRIC_EXTRACTION',
    options: {},
  })
}

export default api
