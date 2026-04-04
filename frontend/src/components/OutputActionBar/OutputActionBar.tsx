import { useCallback, useEffect, useState } from 'react'
import type { PanelOutput } from '../../api/types'
import { api } from '../../api/client'
import styles from './OutputActionBar.module.css'

interface Props {
  jobId: string
  topic?: string
  country?: string
  grade?: number
  panels: PanelOutput[]
  running: boolean
  onRegenerate: () => void
  onClear: () => void
}

export function OutputActionBar({
  jobId,
  topic = '',
  country = '',
  grade,
  panels,
  running,
  onRegenerate,
  onClear,
}: Props) {
  const [excludeUnsafe, setExcludeUnsafe] = useState(true)
  const [audioLoading, setAudioLoading] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const audioCount = panels.filter(p => (p.audio_url ?? '').trim().length > 0).length

  useEffect(() => {
    if (!toast) {
      return undefined
    }
    const t = window.setTimeout(() => setToast(null), 5000)
    return () => window.clearTimeout(t)
  }, [toast])

  const downloadPdf = useCallback(() => {
    const url =
      api.pdfUrl(jobId, excludeUnsafe)
      + (topic ? `&topic=${encodeURIComponent(topic)}` : '')
      + (country ? `&country=${encodeURIComponent(country)}` : '')
      + (grade != null ? `&grade=${grade}` : '')
    window.open(url, '_blank', 'noopener')
  }, [jobId, excludeUnsafe, topic, country, grade])

  const downloadAudioZip = useCallback(async () => {
    if (audioCount === 0 || audioLoading || running) {
      return
    }
    setAudioLoading(true)
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
      setToast(e instanceof Error ? e.message : 'Download failed.')
    } finally {
      setAudioLoading(false)
    }
  }, [audioCount, audioLoading, jobId, running])

  const regenDisabled = running
  const clearDisabled = running

  return (
    <>
      <div className={styles.bar}>
        <div className={styles.group}>
          <button
            type="button"
            className={styles.btnPrimary}
            disabled={regenDisabled}
            onClick={onRegenerate}
            title="Run the pipeline again using the lesson settings in the left panel (topic required)"
          >
            <span aria-hidden>🔄</span>
            Regenerate
          </button>
          <button
            type="button"
            className={styles.btnSecondary}
            disabled={clearDisabled}
            onClick={onClear}
            title="Clear results and reset the workspace"
          >
            Clear
          </button>
        </div>

        <div className={styles.divider} aria-hidden />

        <div className={styles.group}>
          <label className={styles.pdfOption} title="Omit flagged panels from the PDF">
            <input
              type="checkbox"
              checked={excludeUnsafe}
              onChange={e => setExcludeUnsafe(e.target.checked)}
              disabled={running}
            />
            <span>Safe PDF only</span>
          </label>
          <button
            type="button"
            className={styles.btnSecondary}
            disabled={running}
            onClick={downloadPdf}
            title="Download comic-style lesson PDF"
          >
            <span aria-hidden>⬇</span>
            PDF
          </button>
          <button
            type="button"
            className={styles.btnSecondary}
            disabled={running || audioCount === 0 || audioLoading}
            onClick={() => void downloadAudioZip()}
            title={
              audioCount === 0
                ? 'No panel audio available'
                : 'Download all panel audio as a ZIP file'
            }
          >
            <span aria-hidden>⬇</span>
            {audioLoading ? 'Audio…' : 'Audio'}
          </button>
        </div>
      </div>
      {toast ? (
        <div className={styles.toast} role="alert">
          {toast}
        </div>
      ) : null}
    </>
  )
}
