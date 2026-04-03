// TypeScript mirrors of Python Pydantic models (AnansiState, OutputPackage, etc.)

export interface LessonRequest {
  topic: string
  country: string
  grade: number
  language: string
  audience: 'kid' | 'adult' | 'general'
  aspect_ratio: string
  extra_context?: Record<string, unknown>
}

export interface FeedbackRequest {
  rating: 'positive' | 'negative'
  comment?: string
}

export interface PanelOutput {
  panel_number: number
  panel_id: string
  title: string
  caption: string
  dialogue: string
  narration: string
  image_url: string
  audio_url: string
  audio_error: string | null
  safe: boolean
  safety_reason: string | null
}

export interface OutputPackage {
  storyboard_image_url: string
  panels: PanelOutput[]
  teacher_guide: string
  safety_results: unknown[]
  lesson_title?: string
}

// Partial snapshot emitted after each pipeline node
export interface PipelineSnapshot {
  type: 'snapshot'
  scenes?: unknown[]
  context_pack?: Record<string, unknown>
  panel_scripts?: unknown[]
  safety_results?: unknown[]
  images?: unknown[]
  audios?: unknown[]
  package?: OutputPackage
}

export interface JobCreatedResponse {
  job_id: string
  status: 'queued'
}

export interface JobStatusResponse {
  job_id: string
  status: 'running' | 'done' | 'error'
  result: OutputPackage | null
  error: string | null
}

export interface MetaResponse {
  countries: string[]
  languages: string[]
  audiences: string[]
  aspect_ratios: string[]
}

export type JobStatus = 'idle' | 'running' | 'done' | 'error'
