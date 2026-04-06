import { useCallback, useEffect, useRef, useState } from 'react'
import type { PipelineSnapshot } from '../api/types'

interface UsePipelineStreamResult {
  snapshots: PipelineSnapshot[]
  connected: boolean
  close: () => void
}

export function usePipelineStream(jobId: string | null): UsePipelineStreamResult {
  const [snapshots, setSnapshots] = useState<PipelineSnapshot[]>([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)
  const retryRef = useRef(0)
  const maxRetries = 5

  const close = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
    setConnected(false)
  }, [])

  useEffect(() => {
    if (!jobId) return
    /* New job: drop stale snapshots before opening EventSource. */
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset when jobId changes
    setSnapshots([])
    retryRef.current = 0

    function connect() {
      const es = new EventSource(`/api/v1/lessons/${jobId}/stream`)
      esRef.current = es
      setConnected(true)

      es.addEventListener('snapshot', (e: MessageEvent) => {
        try {
          const snap = JSON.parse(e.data) as PipelineSnapshot
          setSnapshots(prev => [...prev, snap])
        } catch {
          // malformed event — ignore
        }
      })

      es.addEventListener('done', () => {
        close()
      })

      es.addEventListener('error', () => {
        es.close()
        setConnected(false)
        if (retryRef.current < maxRetries) {
          retryRef.current += 1
          const delay = Math.min(1000 * 2 ** retryRef.current, 16000)
          setTimeout(connect, delay)
        }
      })
    }

    connect()
    return close
  }, [jobId, close])

  return { snapshots, connected, close }
}
