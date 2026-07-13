import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
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

export default api
