import { useState } from 'react'
import { api } from '../../api/client'
import styles from './PdfExport.module.css'

interface Props {
  jobId: string
  topic?: string
  country?: string
  grade?: number
}

export function PdfExport({ jobId, topic = '', country = '', grade }: Props) {
  const [excludeUnsafe, setExcludeUnsafe] = useState(true)

  function download() {
    const url = api.pdfUrl(jobId, excludeUnsafe)
      + (topic ? `&topic=${encodeURIComponent(topic)}` : '')
      + (country ? `&country=${encodeURIComponent(country)}` : '')
      + (grade != null ? `&grade=${grade}` : '')
    window.open(url, '_blank', 'noopener')
  }

  return (
    <div className={styles.wrapper}>
      <h3 className={styles.heading}>PDF Export</h3>
      <label className={styles.checkboxLabel}>
        <input
          type="checkbox"
          checked={excludeUnsafe}
          onChange={e => setExcludeUnsafe(e.target.checked)}
        />
        Exclude flagged panels from PDF
      </label>
      <button className={styles.button} onClick={download}>
        Download PDF
      </button>
    </div>
  )
}
