import { useEffect, useState } from 'react'
import type { PanelOutput } from '../../api/types'
import { PanelCard } from '../PanelCard/PanelCard'
import styles from './PanelCarousel.module.css'

interface Props {
  panels: PanelOutput[]
}

export function PanelCarousel({ panels }: Props) {
  const [active, setActive] = useState(0)
  const total = panels.length

  // Reset to first panel when panels change (new lesson generated)
  useEffect(() => { setActive(0) }, [panels])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'ArrowLeft')  setActive(i => Math.max(0, i - 1))
      if (e.key === 'ArrowRight') setActive(i => Math.min(total - 1, i + 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [total])

  if (total === 0) return null

  return (
    <div className={styles.carousel}>
      <div className={styles.nav}>
        <button
          className={styles.navBtn}
          onClick={() => setActive(i => i - 1)}
          disabled={active === 0}
          aria-label="Previous panel"
        >
          ←
        </button>
        <span className={styles.counter}>Panel {active + 1} of {total}</span>
        <button
          className={styles.navBtn}
          onClick={() => setActive(i => i + 1)}
          disabled={active === total - 1}
          aria-label="Next panel"
        >
          →
        </button>
      </div>

      <PanelCard panel={panels[active]} />

      <div className={styles.strip} role="tablist" aria-label="Panel thumbnails">
        {panels.map((p, i) => (
          <button
            key={p.panel_id}
            role="tab"
            aria-selected={i === active}
            className={`${styles.thumb} ${i === active ? styles.thumbActive : ''}`}
            onClick={() => setActive(i)}
            aria-label={`Go to panel ${i + 1}`}
          >
            {p.image_url ? (
              <img src={p.image_url} alt={`Panel ${i + 1}`} loading="lazy" />
            ) : (
              <span className={styles.thumbNum}>{i + 1}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
