import type {
  FeedbackRequest,
  JobCreatedResponse,
  JobStatusResponse,
  LessonRequest,
  MetaResponse,
} from './types'

const BASE = '/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!resp.ok) {
    const text = await resp.text().catch(() => resp.statusText)
    throw new Error(`API ${resp.status}: ${text}`)
  }
  return resp.json() as Promise<T>
}

export const api = {
  createLesson: (body: LessonRequest) =>
    request<JobCreatedResponse>('/lessons', { method: 'POST', body: JSON.stringify(body) }),

  getLesson: (jobId: string) =>
    request<JobStatusResponse>(`/lessons/${jobId}`),

  submitFeedback: (jobId: string, body: FeedbackRequest) =>
    request<{ status: string }>(`/lessons/${jobId}/feedback`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  pdfUrl: (jobId: string, excludeUnsafe = true) =>
    `${BASE}/lessons/${jobId}/pdf?exclude_unsafe=${excludeUnsafe}`,

  /** Binary ZIP of panel audio; throws with a readable message on failure. */
  async fetchAudioZip(jobId: string): Promise<Blob> {
    const resp = await fetch(`${BASE}/lessons/${jobId}/export/audio`)
    if (!resp.ok) {
      let detail = await resp.text().catch(() => resp.statusText)
      try {
        const data = JSON.parse(detail) as { detail?: string | string[] }
        if (typeof data.detail === 'string') {
          detail = data.detail
        } else if (Array.isArray(data.detail)) {
          detail = data.detail.map(String).join(', ')
        }
      } catch {
        /* keep detail as text */
      }
      throw new Error(detail || `API ${resp.status}`)
    }
    return resp.blob()
  },

  getMeta: () => request<MetaResponse>('/meta/countries'),
}
