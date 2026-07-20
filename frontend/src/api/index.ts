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

export interface PaperOutlineItem {
  title: string
  level: number
  page_number: number
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

export interface PageTextWord {
  text: string
  x0: number
  y0: number
  x1: number
  y1: number
  char_start: number
  char_end: number
}

export interface PageTextLayerResponse {
  page_number: number
  width: number
  height: number
  words: PageTextWord[]
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

export async function deletePaper(paperId: string): Promise<void> {
  await api.delete(`/papers/${paperId}`)
}

export async function getPaperFile(paperId: string): Promise<Blob> {
  const { data } = await api.get<Blob>(`/papers/${paperId}/file`, { responseType: 'blob' })
  return data
}

export async function getPaperPageImage(paperId: string, pageNumber: number): Promise<Blob> {
  const { data } = await api.get<Blob>(`/papers/${paperId}/pages/${pageNumber}/image`, { responseType: 'blob' })
  return data
}

export async function getPaperPageTextLayer(
  paperId: string,
  pageNumber: number,
): Promise<PageTextLayerResponse> {
  const { data } = await api.get<PageTextLayerResponse>(
    `/papers/${paperId}/pages/${pageNumber}/text-layer`,
  )
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

export async function getPaperOutline(paperId: string): Promise<PaperOutlineItem[]> {
  const { data } = await api.get<{ items: PaperOutlineItem[] }>(`/papers/${paperId}/outline`)
  return data.items
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
  experiment_file_id?: string | null
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

export type ExperimentFileType = 'CSV' | 'XLSX' | 'XLS'

export type ColumnDtype = 'integer' | 'float' | 'boolean' | 'datetime' | 'string' | 'empty'

export type CsvEncoding = 'utf-8' | 'utf-8-sig' | 'gb18030'

export type CsvDelimiter = ',' | ';' | '\t'

export interface ExperimentColumnInfo {
  name: string
  dtype: ColumnDtype
  nullable: boolean
  null_count: number
}

export interface ExperimentColumnsInfo {
  version: 1
  encoding: CsvEncoding | null
  delimiter: CsvDelimiter | null
  sheet_name: string | null
  columns: ExperimentColumnInfo[]
}

export interface ExperimentFileMetadata {
  id: string
  paper_id: string
  filename: string
  file_type: ExperimentFileType
  file_size: number
  row_count: number
  column_count: number
  columns_info: ExperimentColumnsInfo
  created_at: string
}

export interface ExperimentFileUploadResponse extends ExperimentFileMetadata {
  duplicate: boolean
}

export interface ExperimentFileListItem {
  id: string
  paper_id: string
  filename: string
  file_type: ExperimentFileType
  file_size: number
  row_count: number
  column_count: number
  created_at: string
}

export interface ExperimentFileListResponse {
  items: ExperimentFileListItem[]
  total: number
  page: number
  page_size: number
}

export interface NumericStats {
  mean: number
  stddev: number | null
  min: number
  max: number
  median: number
}

export interface ColumnStats {
  name: string
  dtype: ColumnDtype
  count: number
  null_count: number
  stats: NumericStats | null
}

export interface SummaryStatsResponse {
  version: 1
  row_count: number
  column_count: number
  columns: ColumnStats[]
}

export type ComparisonStatus = 'MATCH' | 'MISMATCH' | 'UNVERIFIABLE'

export type ComparisonReason =
  | 'AMBIGUOUS_PAPER_METRIC'
  | 'NO_EXPERIMENT_COLUMN'
  | 'AMBIGUOUS_EXPERIMENT_COLUMN'
  | 'UNSUPPORTED_CHECKPOINT'
  | 'EMPTY_NORMALIZED_NAME'

export type ComparisonStatistic = 'MEAN' | 'MAX'

export interface ComparisonItem {
  metric_record_id: string
  metric_task_id: string
  metric_name: string
  checkpoint_type: CheckpointType
  column_name: string | null
  statistic: ComparisonStatistic | null
  paper_value: number
  experiment_value: number | null
  diff: number | null
  absolute_diff: number | null
  relative_diff: number | null
  allowed_diff: number | null
  status: ComparisonStatus
  reason: ComparisonReason | null
}

export interface ExperimentAnalysisTaskResponse {
  id: string
  paper_id: string
  task_type: 'EXPERIMENT_ANALYSIS'
  status: TaskStatus
  progress: number
  experiment_file_id: string
  created_at: string
  duplicate: boolean
}

export interface ExperimentResultResponse {
  id: string
  file_id: string
  task_id: string
  summary_stats: SummaryStatsResponse
  metric_comparisons: ComparisonItem[] | null
  created_at: string
}

export interface PostComparisonsRequest {
  metric_task_id: string
}

export interface PostComparisonsResponse {
  file_id: string
  experiment_result_id: string
  metric_task_id: string
  comparisons: ComparisonItem[]
  duplicate: boolean
}

export async function uploadExperimentFile(
  paperId: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<ExperimentFileUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data, status } = await api.post<ExperimentFileUploadResponse>(
    `/papers/${paperId}/experiment-files/upload`,
    form,
    {
      onUploadProgress(e) {
        if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
      },
      validateStatus: (s) => s === 201 || s === 200,
    },
  )
  if (status === 200) {
    return { ...data, duplicate: true }
  }
  return data
}

export async function listExperimentFiles(
  paperId: string,
  page = 1,
  pageSize = 20,
): Promise<ExperimentFileListResponse> {
  const normalizedPage = Number.isFinite(page) ? Math.max(1, Math.trunc(page)) : 1
  const normalizedPageSize = Number.isFinite(pageSize)
    ? Math.min(100, Math.max(1, Math.trunc(pageSize)))
    : 20
  const { data } = await api.get<ExperimentFileListResponse>(
    `/papers/${paperId}/experiment-files`,
    { params: { page: normalizedPage, page_size: normalizedPageSize } },
  )
  return data
}

export async function getExperimentFile(fileId: string): Promise<ExperimentFileMetadata> {
  const { data } = await api.get<ExperimentFileMetadata>(`/experiment-files/${fileId}`)
  return data
}

export async function createExperimentAnalysis(
  fileId: string,
): Promise<ExperimentAnalysisTaskResponse> {
  const { data, status } = await api.post<ExperimentAnalysisTaskResponse>(
    `/experiment-files/${fileId}/analysis`,
    null,
    { validateStatus: (s) => s === 201 || s === 200 },
  )
  if (status === 200) {
    return { ...data, duplicate: true }
  }
  return data
}

export async function getExperimentResult(fileId: string): Promise<ExperimentResultResponse> {
  const { data } = await api.get<ExperimentResultResponse>(
    `/experiment-files/${fileId}/result`,
  )
  return data
}

export async function createComparisons(
  fileId: string,
  body: PostComparisonsRequest,
): Promise<PostComparisonsResponse> {
  const { data, status } = await api.post<PostComparisonsResponse>(
    `/experiment-files/${fileId}/comparisons`,
    body,
    { validateStatus: (s) => s === 201 || s === 200 },
  )
  if (status === 200) {
    return { ...data, duplicate: true }
  }
  return data
}

export type ExportReportType = 'MARKDOWN' | 'PDF' | 'DOCX'

export type ExportStatus = 'PENDING' | 'GENERATING' | 'READY' | 'FAILED'

export interface CreateExportRequest {
  report_type: ExportReportType
  language: 'zh' | 'en'
  include_metrics: boolean
  include_experiment_analysis: boolean
}

export interface ExportReportResponse {
  id: string
  paper_id: string
  report_type: ExportReportType
  language: 'zh' | 'en'
  include_metrics: boolean
  include_experiment_analysis: boolean
  status: ExportStatus
  file_size: number | null
  error_message: string | null
  created_at: string
  completed_at: string | null
  duplicate: boolean
}

export interface ExportListItem {
  id: string
  paper_id: string
  report_type: ExportReportType
  language: 'zh' | 'en'
  include_metrics: boolean
  include_experiment_analysis: boolean
  status: ExportStatus
  file_size: number | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface ExportListResponse {
  items: ExportListItem[]
  total: number
  page: number
  page_size: number
}

export async function createExport(
  paperId: string,
  body: CreateExportRequest,
): Promise<ExportReportResponse> {
  const { data, status } = await api.post<ExportReportResponse>(
    `/papers/${paperId}/exports`,
    body,
    { validateStatus: (s) => s === 201 || s === 200 },
  )
  return { ...data, duplicate: status === 200 }
}

export async function listExports(
  paperId: string,
  page = 1,
  pageSize = 20,
): Promise<ExportListResponse> {
  const { data } = await api.get<ExportListResponse>(
    `/papers/${paperId}/exports`,
    { params: { page, page_size: pageSize } },
  )
  return data
}

export async function downloadExportBlob(exportId: string): Promise<Blob> {
  const { data } = await api.get(`/exports/${exportId}/download`, {
    responseType: 'blob',
  })
  return data
}

export default api

export type LearningMode = 'SUMMARY' | 'EXPLAIN' | 'TRANSLATE'

export type LearningScopeType = 'SECTION' | 'PAGE' | 'EVIDENCE'

export type LearningStatus = 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED'

export interface CreateLearningExplanationRequest {
  mode: LearningMode
  scope_type: LearningScopeType
  output_language: 'zh' | 'en'
  section_id?: string | null
  page_number?: number | null
  evidence_id?: string | null
  selection_text?: string | null
  selection_start?: number | null
  selection_end?: number | null
}

export interface LearningCitationItem {
  evidence_id: string
  sequence: number
  page_number: number
  evidence_type: string
  quoted_text: string
  char_start: number | null
  char_end: number | null
}

export interface LearningTermItem {
  term: string
  explanation: string
}

export interface LearningExplanationResponse {
  id: string
  paper_id: string
  mode: LearningMode
  scope_type: LearningScopeType
  output_language: 'zh' | 'en'
  section_id: string | null
  page_number: number | null
  evidence_id: string | null
  selection_text: string | null
  selection_start: number | null
  selection_end: number | null
  status: LearningStatus
  duplicate: boolean
  answer: string | null
  key_points: string[] | null
  terms: LearningTermItem[] | null
  error_message: string | null
  citations: LearningCitationItem[] | null
  created_at: string
  completed_at: string | null
}

export interface LearningExplanationListItem {
  id: string
  paper_id: string
  mode: LearningMode
  scope_type: LearningScopeType
  output_language: 'zh' | 'en'
  section_id: string | null
  page_number: number | null
  evidence_id: string | null
  selection_start: number | null
  selection_end: number | null
  status: LearningStatus
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface LearningExplanationListResponse {
  items: LearningExplanationListItem[]
  total: number
  page: number
  page_size: number
}

export async function createLearningExplanation(
  paperId: string,
  body: CreateLearningExplanationRequest,
): Promise<LearningExplanationResponse> {
  const { data } = await api.post<LearningExplanationResponse>(
    `/papers/${paperId}/learning-explanations`,
    body,
    { validateStatus: (s) => s === 201 || s === 200 },
  )
  return data
}

export async function getLearningExplanation(
  explanationId: string,
): Promise<LearningExplanationResponse> {
  const { data } = await api.get<LearningExplanationResponse>(
    `/learning-explanations/${explanationId}`,
  )
  return data
}

export async function listLearningExplanations(
  paperId: string,
  page = 1,
  pageSize = 20,
  pageNumber?: number,
): Promise<LearningExplanationListResponse> {
  const { data } = await api.get<LearningExplanationListResponse>(
    `/papers/${paperId}/learning-explanations`,
    { params: { page, page_size: pageSize, page_number: pageNumber } },
  )
  return data
}

export async function deleteLearningExplanation(explanationId: string): Promise<void> {
  await api.delete(`/learning-explanations/${explanationId}`)
}

export type QATurnStatus = 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED'

export interface QACitationItem {
  evidence_id: string
  sequence: number
  page_number: number
  evidence_type: string
  quoted_text: string
  char_start: number | null
  char_end: number | null
}

export interface QATurnResponse {
  id: string
  conversation_id: string
  sequence: number
  question: string
  output_language: 'zh' | 'en'
  status: QATurnStatus
  duplicate: boolean
  answer: string | null
  grounded: boolean | null
  error_message: string | null
  citations: QACitationItem[] | null
  created_at: string
  completed_at: string | null
}

export interface QAConversationResponse {
  id: string
  paper_id: string
  created_at: string
  updated_at: string
  turns: QATurnResponse[] | null
  total: number
  page: number
  page_size: number
}

export interface QAConversationListItem {
  id: string
  paper_id: string
  created_at: string
  updated_at: string
  turn_count: number
  last_question_preview: string | null
  last_status: QATurnStatus | null
}

export interface QAConversationListResponse {
  items: QAConversationListItem[]
  total: number
  page: number
  page_size: number
}

export type CreateQAConversationRequest = Record<string, never>

export interface CreateQATurnRequest {
  question: string
  output_language: 'zh' | 'en'
  client_request_id: string
  current_page?: number | null
}

export async function createQAConversation(
  paperId: string,
  body: CreateQAConversationRequest,
): Promise<QAConversationResponse> {
  const { data } = await api.post<QAConversationResponse>(
    `/papers/${paperId}/qa-conversations`,
    body,
  )
  return data
}

export async function listQAConversations(
  paperId: string,
  page = 1,
  pageSize = 20,
): Promise<QAConversationListResponse> {
  const { data } = await api.get<QAConversationListResponse>(
    `/papers/${paperId}/qa-conversations`,
    { params: { page, page_size: pageSize } },
  )
  return data
}

export async function getQAConversation(
  conversationId: string,
  page = 1,
  pageSize = 20,
): Promise<QAConversationResponse> {
  const { data } = await api.get<QAConversationResponse>(
    `/qa-conversations/${conversationId}`,
    { params: { page, page_size: pageSize } },
  )
  return data
}

export async function deleteQAConversation(conversationId: string): Promise<void> {
  await api.delete(`/qa-conversations/${conversationId}`)
}

export async function createQATurn(
  conversationId: string,
  body: CreateQATurnRequest,
): Promise<QATurnResponse> {
  const { data, status } = await api.post<QATurnResponse>(
    `/qa-conversations/${conversationId}/turns`,
    body,
    { validateStatus: (s) => s === 201 || s === 200 },
  )
  return { ...data, duplicate: status === 200 }
}

export async function getQATurn(
  turnId: string,
): Promise<QATurnResponse> {
  const { data } = await api.get<QATurnResponse>(
    `/qa-turns/${turnId}`,
  )
  return data
}

export type ReadingStatus = 'TO_READ' | 'READING' | 'COMPLETED' | 'ARCHIVED'

export type HighlightColor = 'YELLOW' | 'GREEN' | 'BLUE' | 'PINK'

export type AnchorType = 'PAPER' | 'PAGE' | 'HIGHLIGHT'

export type MasteryStatus = 'NEW' | 'LEARNING' | 'MASTERED'

export interface LibraryPaperItem {
  paper_id: string
  title: string
  filename: string
  page_count: number | null
  status: string
  created_at: string
  reading_status: ReadingStatus
  favorite: boolean
  collection_name: string | null
  last_page: number | null
  furthest_page: number | null
  progress_percent: number
  last_read_at: string | null
  completed_at: string | null
  updated_at: string
  highlight_count: number
  bookmark_count: number
  note_count: number
  card_count: number
}

export interface LibraryPaperListResponse {
  items: LibraryPaperItem[]
  total: number
  page: number
  page_size: number
}

export interface LibraryEntryResponse {
  paper_id: string
  reading_status: ReadingStatus
  favorite: boolean
  collection_name: string | null
  last_page: number | null
  furthest_page: number | null
  last_read_at: string | null
  completed_at: string | null
  updated_at: string
}

export interface ReadingProgressResponse {
  paper_id: string
  reading_status: ReadingStatus
  last_page: number | null
  furthest_page: number | null
  progress_percent: number
  last_read_at: string | null
  updated_at: string
}

export interface HighlightResponse {
  id: string
  paper_id: string
  page_number: number
  char_start: number
  char_end: number
  quoted_text: string
  color: HighlightColor
  created_at: string
  updated_at: string
  duplicate?: boolean
}

export interface HighlightListResponse {
  items: HighlightResponse[]
  total: number
  page: number
  page_size: number
}

export interface BookmarkResponse {
  id: string
  paper_id: string
  page_number: number
  label: string | null
  created_at: string
  duplicate: boolean
}

export interface BookmarkListResponse {
  items: BookmarkResponse[]
  total: number
  page: number
  page_size: number
}

export interface NoteResponse {
  id: string
  paper_id: string
  anchor_type: AnchorType
  page_number: number | null
  highlight_id: string | null
  content: string
  created_at: string
  updated_at: string
}

export interface NoteListResponse {
  items: NoteResponse[]
  total: number
  page: number
  page_size: number
}

export interface KnowledgeCardResponse {
  id: string
  paper_id: string
  source_note_id: string | null
  source_highlight_id: string | null
  front: string
  back: string
  mastery_status: MasteryStatus
  last_reviewed_at: string | null
  archived: boolean
  created_at: string
  updated_at: string
}

export interface KnowledgeCardListResponse {
  items: KnowledgeCardResponse[]
  total: number
  page: number
  page_size: number
}

export interface LibraryListParams {
  page?: number
  page_size?: number
  reading_status?: ReadingStatus | null
  favorite?: boolean | null
  collection_name?: string | null
  keyword?: string | null
}

export async function listLibraryPapers(params: LibraryListParams = {}): Promise<LibraryPaperListResponse> {
  const filtered: Record<string, string | number | boolean> = {}
  if (params.page) filtered.page = params.page
  if (params.page_size) filtered.page_size = params.page_size
  if (params.reading_status) filtered.reading_status = params.reading_status
  if (params.favorite != null) filtered.favorite = params.favorite
  if (params.collection_name) filtered.collection_name = params.collection_name
  if (params.keyword) filtered.keyword = params.keyword
  const { data } = await api.get<LibraryPaperListResponse>('/library/papers', { params: filtered })
  return data
}

export async function patchLibraryEntry(
  paperId: string,
  body: { reading_status?: ReadingStatus; favorite?: boolean; collection_name?: string | null },
): Promise<LibraryEntryResponse> {
  const { data } = await api.patch<LibraryEntryResponse>(
    `/papers/${paperId}/library-entry`,
    body,
  )
  return data
}

export async function patchReadingProgress(
  paperId: string,
  pageNumber: number,
): Promise<ReadingProgressResponse> {
  const { data } = await api.patch<ReadingProgressResponse>(
    `/papers/${paperId}/reading-progress`,
    { page_number: pageNumber },
  )
  return data
}

export async function createHighlight(
  paperId: string,
  body: { page_number: number; char_start: number; char_end: number; color?: HighlightColor },
): Promise<HighlightResponse> {
  const { data, status } = await api.post<HighlightResponse>(
    `/papers/${paperId}/highlights`,
    body,
    { validateStatus: (s) => s === 201 || s === 200 },
  )
  return { ...data, duplicate: status === 200 }
}

export async function listHighlights(
  paperId: string,
  params: { page_number?: number; page?: number; page_size?: number } = {},
): Promise<HighlightListResponse> {
  const { data } = await api.get<HighlightListResponse>(
    `/papers/${paperId}/highlights`,
    { params },
  )
  return data
}

export async function deleteHighlight(highlightId: string): Promise<void> {
  await api.delete(`/highlights/${highlightId}`)
}

export async function createBookmark(
  paperId: string,
  body: { page_number: number; label?: string | null },
): Promise<BookmarkResponse> {
  const { data, status } = await api.post<BookmarkResponse>(
    `/papers/${paperId}/bookmarks`,
    body,
    { validateStatus: (s) => s === 201 || s === 200 },
  )
  return { ...data, duplicate: status === 200 }
}

export async function listBookmarks(
  paperId: string,
  params: { page?: number; page_size?: number } = {},
): Promise<BookmarkListResponse> {
  const { data } = await api.get<BookmarkListResponse>(
    `/papers/${paperId}/bookmarks`,
    { params },
  )
  return data
}

export async function deleteBookmark(bookmarkId: string): Promise<void> {
  await api.delete(`/bookmarks/${bookmarkId}`)
}

export async function createNote(
  paperId: string,
  body: { anchor_type: AnchorType; page_number?: number | null; highlight_id?: string | null; content: string },
): Promise<NoteResponse> {
  const { data } = await api.post<NoteResponse>(
    `/papers/${paperId}/notes`,
    body,
  )
  return data
}

export async function listNotes(
  paperId: string,
  params: { anchor_type?: AnchorType; page_number?: number; highlight_id?: string; page?: number; page_size?: number } = {},
): Promise<NoteListResponse> {
  const { data } = await api.get<NoteListResponse>(
    `/papers/${paperId}/notes`,
    { params },
  )
  return data
}

export async function patchNote(noteId: string, content: string): Promise<NoteResponse> {
  const { data } = await api.patch<NoteResponse>(
    `/notes/${noteId}`,
    { content },
  )
  return data
}

export async function deleteNote(noteId: string): Promise<void> {
  await api.delete(`/notes/${noteId}`)
}

export async function createKnowledgeCard(
  paperId: string,
  body: { source_note_id?: string | null; source_highlight_id?: string | null; front: string; back: string },
): Promise<KnowledgeCardResponse> {
  const { data } = await api.post<KnowledgeCardResponse>(
    `/papers/${paperId}/knowledge-cards`,
    body,
  )
  return data
}

export async function listKnowledgeCards(
  paperId: string,
  params: { mastery_status?: MasteryStatus; archived?: boolean; page?: number; page_size?: number } = {},
): Promise<KnowledgeCardListResponse> {
  const { data } = await api.get<KnowledgeCardListResponse>(
    `/papers/${paperId}/knowledge-cards`,
    { params },
  )
  return data
}

export async function patchKnowledgeCard(
  cardId: string,
  body: { front?: string; back?: string; mastery_status?: MasteryStatus; archived?: boolean },
): Promise<KnowledgeCardResponse> {
  const { data } = await api.patch<KnowledgeCardResponse>(
    `/knowledge-cards/${cardId}`,
    body,
  )
  return data
}

export async function deleteKnowledgeCard(cardId: string): Promise<void> {
  await api.delete(`/knowledge-cards/${cardId}`)
}

export interface AdminDashboardResponse {
  users_by_role: Record<string, number>
  users_by_status: Record<string, number>
  papers_by_status: Record<string, number>
  tasks_by_type: Record<string, number>
  tasks_by_status: Record<string, number>
  exports_by_type: Record<string, number>
  exports_by_status: Record<string, number>
}

export interface AdminUserItem {
  id: string
  email: string
  display_name: string
  role: string
  status: string
  failed_login_count: number
  locked_until: string | null
  created_at: string
  updated_at: string
  active_session_count: number
  paper_count: number
  task_count: number
  export_count: number
}

export interface AdminUserListResponse {
  items: AdminUserItem[]
  total: number
  page: number
  page_size: number
}

export interface AdminUserPatchRequest {
  role?: 'USER' | 'ADMIN'
  status?: 'ACTIVE' | 'DISABLED'
  reason: string
}

export interface AdminUserPatchResponse {
  changed: boolean
  audit_ids: string[]
  user: AdminUserItem
}

export interface AdminPaperItem {
  id: string
  user_id: string
  owner_email: string
  title: string
  filename: string
  file_size: number
  page_count: number | null
  status: string
  created_at: string
  updated_at: string
}

export interface AdminPaperListResponse {
  items: AdminPaperItem[]
  total: number
  page: number
  page_size: number
}

export interface AdminTaskItem {
  id: string
  paper_id: string
  user_id: string
  task_type: string
  status: string
  progress: number
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface AdminTaskListResponse {
  items: AdminTaskItem[]
  total: number
  page: number
  page_size: number
}

export interface AdminExportItem {
  id: string
  paper_id: string
  user_id: string
  report_type: string
  status: string
  file_size: number | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface AdminExportListResponse {
  items: AdminExportItem[]
  total: number
  page: number
  page_size: number
}

export interface AuditLogActorInfo {
  id: string
  email: string
}

export interface AuditLogItem {
  id: string
  actor: AuditLogActorInfo
  action: string
  resource_type: string
  resource_id: string
  reason: string
  before_state: Record<string, string>
  after_state: Record<string, string>
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLogItem[]
  total: number
  page: number
  page_size: number
}

export async function getAdminDashboard(): Promise<AdminDashboardResponse> {
  const { data } = await api.get<AdminDashboardResponse>('/admin/dashboard')
  return data
}

export async function listAdminUsers(params: {
  page?: number
  page_size?: number
  role?: string
  status?: string
  q?: string
} = {}): Promise<AdminUserListResponse> {
  const { data } = await api.get<AdminUserListResponse>('/admin/users', { params })
  return data
}

export async function getAdminUser(userId: string): Promise<AdminUserItem> {
  const { data } = await api.get<AdminUserItem>(`/admin/users/${userId}`)
  return data
}

export async function patchAdminUser(
  userId: string,
  body: AdminUserPatchRequest,
): Promise<AdminUserPatchResponse> {
  const { data } = await api.patch<AdminUserPatchResponse>(`/admin/users/${userId}`, body)
  return data
}

export async function listAdminPapers(params: {
  page?: number
  page_size?: number
  status?: string
  user_id?: string
  q?: string
} = {}): Promise<AdminPaperListResponse> {
  const { data } = await api.get<AdminPaperListResponse>('/admin/papers', { params })
  return data
}

export async function listAdminTasks(params: {
  page?: number
  page_size?: number
  task_type?: string
  status?: string
  user_id?: string
  paper_id?: string
} = {}): Promise<AdminTaskListResponse> {
  const { data } = await api.get<AdminTaskListResponse>('/admin/tasks', { params })
  return data
}

export async function listAdminExports(params: {
  page?: number
  page_size?: number
  report_type?: string
  status?: string
  user_id?: string
  paper_id?: string
} = {}): Promise<AdminExportListResponse> {
  const { data } = await api.get<AdminExportListResponse>('/admin/exports', { params })
  return data
}

export async function listAuditLogs(params: {
  page?: number
  page_size?: number
  actor_user_id?: string
  action?: string
  resource_id?: string
  created_from?: string
  created_to?: string
} = {}): Promise<AuditLogListResponse> {
  const { data } = await api.get<AuditLogListResponse>('/admin/audit-logs', { params })
  return data
}
