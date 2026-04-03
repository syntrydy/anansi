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

  getMeta: () => request<MetaResponse>('/meta/countries'),
}
