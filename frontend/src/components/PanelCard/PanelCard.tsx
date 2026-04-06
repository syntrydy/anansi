import { useState } from 'react'
import type { PanelOutput } from '../../api/types'
import styles from './PanelCard.module.css'

interface Props {
  panel: PanelOutput
}

export function PanelCard({ panel }: Props) {
  const [caption, setCaption] = useState(panel.caption)
  const [dialogue, setDialogue] = useState(panel.dialogue)
  const unsafe = !panel.safe

  return (
    <article
      className={[styles.card, unsafe ? styles.unsafe : ''].join(' ')}
    >
      {/* Image-first */}
      <div className={styles.media}>
        {!unsafe && panel.image_url ? (
          <img
            className={styles.image}
            src={panel.image_url}
            alt={`Panel ${panel.panel_number}`}
            loading="lazy"
          />
        ) : null}
        {unsafe ? (
          <div className={styles.safetyBlock}>
            <span className={styles.safetyBadge}>⚠ Needs review</span>
            <p className={styles.safetyReason}>
              {panel.safety_reason ?? 'This panel was flagged for safety review.'}
            </p>
          </div>
        ) : null}
      </div>

      <div className={styles.content}>
        <div className={styles.meta}>
          <span className={styles.number}>Panel {panel.panel_number}</span>
          {panel.title ? (
            <span className={styles.panelTitle}>{panel.title}</span>
          ) : null}
        </div>

        <div className={styles.fields}>
          <label className={styles.fieldLabel} htmlFor={`cap-${panel.panel_id}`}>Caption</label>
          <textarea
            id={`cap-${panel.panel_id}`}
            className={styles.inlineInput}
            value={caption}
            onChange={e => setCaption(e.target.value)}
            rows={2}
            readOnly={unsafe}
            aria-readonly={unsafe}
          />

          <label className={styles.fieldLabel} htmlFor={`dlg-${panel.panel_id}`}>Dialogue</label>
          <textarea
            id={`dlg-${panel.panel_id}`}
            className={styles.inlineInput}
            value={dialogue}
            onChange={e => setDialogue(e.target.value)}
            rows={2}
            readOnly={unsafe}
            aria-readonly={unsafe}
          />

          {panel.narration ? (
            <>
              <label className={styles.fieldLabel}>Narration</label>
              <p className={styles.narration}>{panel.narration}</p>
            </>
          ) : null}
        </div>

        {panel.audio_error ? (
          <p className={styles.audioError}>Audio error: {panel.audio_error}</p>
        ) : panel.audio_url ? (
          <div className={styles.audio}>
            <audio controls src={panel.audio_url} className={styles.audioEl} />
            <a className={styles.audioDownload} href={panel.audio_url} download>
              Download MP3
            </a>
          </div>
        ) : null}
      </div>
    </article>
  )
}
