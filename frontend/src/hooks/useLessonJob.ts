import { useState } from 'react'
import { api } from '../api/client'
import type { JobStatus, LessonRequest, OutputPackage } from '../api/types'
import { usePipelineStream } from './usePipelineStream'

interface UseLessonJobResult {
  jobId: string | null
  status: JobStatus
  result: OutputPackage | null
  error: string | null
  lastRequest: LessonRequest | null
  snapshots: ReturnType<typeof usePipelineStream>['snapshots']
  submit: (req: LessonRequest) => Promise<void>
  reset: () => void
}

export function useLessonJob(): UseLessonJobResult {
  const [jobId, setJobId] = useState<string | null>(null)
  const [status, setStatus] = useState<JobStatus>('idle')
  const [result, setResult] = useState<OutputPackage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastRequest, setLastRequest] = useState<LessonRequest | null>(null)

  const { snapshots, close, onDoneRef } = usePipelineStream(status === 'running' ? jobId : null)

  // Poll for final result — SSE done event triggers this immediately,
  // or it falls back to polling every second for up to 5 minutes.
  async function pollUntilDone(id: string, signal: AbortSignal) {
    const maxAttempts = 300
    for (let i = 0; i < maxAttempts; i++) {
      if (signal.aborted) return
      await new Promise(r => setTimeout(r, 1000))
      if (signal.aborted) return
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
    setLastRequest(req)
    setStatus('running')
    setResult(null)
    setError(null)
    setJobId(null)
    const abortCtrl = new AbortController()
    try {
      const { job_id } = await api.createLesson(req)
      setJobId(job_id)
      // When SSE fires 'done', immediately do a final fetch instead of waiting for the next poll tick
      onDoneRef.current = async () => {
        abortCtrl.abort()
        try {
          const job = await api.getLesson(job_id)
          if (job.status === 'done' && job.result) {
            setResult(job.result)
            setStatus('done')
          } else if (job.status === 'error') {
            setError(job.error ?? 'Pipeline failed')
            setStatus('error')
          }
        } catch {
          // ignore; polling loop already handles this
        }
      }
      await pollUntilDone(job_id, abortCtrl.signal)
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
    setLastRequest(null)
  }

  return { jobId, status, result, error, lastRequest, snapshots, submit, reset }
}
