import { useState } from 'react'
import type { PanelOutput } from '../../api/types'
import styles from './PanelCard.module.css'

interface Props {
  panel: PanelOutput
}

export function PanelCard({ panel }: Props) {
  const [caption, setCaption] = useState(panel.caption)
  const [dialogue, setDialogue] = useState(panel.dialogue)

  return (
    <article className={[styles.card, !panel.safe ? styles.unsafe : ''].join(' ')}>
      <header className={styles.header}>
        <span className={styles.number}>#{panel.panel_number}</span>
        <span className={styles.panelTitle}>{panel.title}</span>
        {!panel.safe && <span className={styles.badge}>Flagged</span>}
      </header>

      <div className={styles.body}>
        {/* Image */}
        {panel.image_url && panel.safe ? (
          <img
            className={styles.image}
            src={panel.image_url}
            alt={`Panel ${panel.panel_number}`}
            loading="lazy"
          />
        ) : !panel.safe ? (
          <div className={styles.safetyOverlay}>
            <span className={styles.safetyIcon}>⚠️</span>
            <p className={styles.safetyReason}>{panel.safety_reason ?? 'Content flagged for review'}</p>
          </div>
        ) : null}

        {/* Editable text fields */}
        <div className={styles.fields}>
          <label className={styles.fieldLabel}>Caption</label>
          <textarea
            className={styles.textarea}
            value={caption}
            onChange={e => setCaption(e.target.value)}
            rows={2}
          />

          <label className={styles.fieldLabel}>Dialogue</label>
          <textarea
            className={styles.textarea}
            value={dialogue}
            onChange={e => setDialogue(e.target.value)}
            rows={2}
          />

          {panel.narration && (
            <>
              <label className={styles.fieldLabel}>Narration</label>
              <p className={styles.narration}>{panel.narration}</p>
            </>
          )}
        </div>

        {/* Audio */}
        {panel.audio_error ? (
          <p className={styles.audioError}>Audio error: {panel.audio_error}</p>
        ) : panel.audio_url ? (
          <div className={styles.audio}>
            <audio controls src={panel.audio_url} />
            <a className={styles.audioDownload} href={panel.audio_url} download>
              Download MP3
            </a>
          </div>
        ) : null}
      </div>
    </article>
  )
}
