import { useState } from 'react'
import { api } from '../api/client'
import type { JobStatus, LessonRequest, OutputPackage } from '../api/types'
import { usePipelineStream } from './usePipelineStream'

interface UseLessonJobResult {
  jobId: string | null
  status: JobStatus
  result: OutputPackage | null
  error: string | null
  snapshots: ReturnType<typeof usePipelineStream>['snapshots']
  submit: (req: LessonRequest) => Promise<void>
  reset: () => void
}

export function useLessonJob(): UseLessonJobResult {
  const [jobId, setJobId] = useState<string | null>(null)
  const [status, setStatus] = useState<JobStatus>('idle')
  const [result, setResult] = useState<OutputPackage | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { snapshots, close } = usePipelineStream(status === 'running' ? jobId : null)

  // Poll for final result once SSE closes
  async function pollUntilDone(id: string) {
    const maxAttempts = 60
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(r => setTimeout(r, 1000))
      try {
        const job = await api.getLesson(id)
        if (job.status === 'done' && job.result) {
          setResult(job.result)
          setStatus('done')
          return
        }
        if (job.status === 'error') {
          setError(job.error ?? 'Pipeline failed')
          setStatus('error')
          return
        }
      } catch {
        // network hiccup — keep retrying
      }
    }
    setError('Timed out waiting for result')
    setStatus('error')
  }

  const submit = async (req: LessonRequest) => {
    close()
    setStatus('running')
    setResult(null)
    setError(null)
    setJobId(null)
    try {
      const { job_id } = await api.createLesson(req)
      setJobId(job_id)
      // SSE hook will connect automatically; poll as fallback when it closes
      await pollUntilDone(job_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setStatus('error')
    }
  }

  const reset = () => {
    close()
    setJobId(null)
    setStatus('idle')
    setResult(null)
    setError(null)
  }

  return { jobId, status, result, error, snapshots, submit, reset }
}
