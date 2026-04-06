import { useCallback, useEffect, useState } from 'react'
import type { PanelOutput } from '../../api/types'
import { api } from '../../api/client'
import styles from './AudioExport.module.css'

interface Props {
  jobId: string
  panels: PanelOutput[]
}

export function AudioExport({ jobId, panels }: Props) {
  const audioCount = panels.filter(p => (p.audio_url ?? '').trim().length > 0).length
  const [downloading, setDownloading] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    if (!toast) {
      return undefined
    }
    const t = window.setTimeout(() => setToast(null), 5000)
    return () => window.clearTimeout(t)
  }, [toast])

  const onDownload = useCallback(async () => {
    if (audioCount === 0 || downloading) {
      return
    }
    setDownloading(true)
    setToast(null)
    try {
      const blob = await api.fetchAudioZip(jobId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'lesson_audio.zip'
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Download failed.'
      setToast(message)
    } finally {
      setDownloading(false)
    }
  }, [audioCount, downloading, jobId])

  const disabled = audioCount === 0 || downloading

  return (
    <div className={styles.wrapper}>
      <h3 className={styles.heading}>Audio download</h3>
      {audioCount > 0 && (
        <p className={styles.count} role="status">
          {audioCount} audio file{audioCount === 1 ? '' : 's'} ready
        </p>
      )}
      <button
        type="button"
        className={styles.button}
        disabled={disabled}
        onClick={() => void onDownload()}
      >
        {downloading ? 'Preparing…' : 'Download Audio (.zip)'}
      </button>
      {audioCount === 0 && (
        <p className={styles.hint}>No panel audio is available for this lesson.</p>
      )}
      {toast && (
        <div className={styles.toast} role="alert">
          {toast}
        </div>
      )}
    </div>
  )
}
