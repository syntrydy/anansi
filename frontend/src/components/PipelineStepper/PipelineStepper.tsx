import type { JobStatus, PipelineSnapshot } from '../../api/types'
import styles from './PipelineStepper.module.css'

interface Props {
  snapshots: PipelineSnapshot[]
  status: JobStatus
}

const STEPS = [
  { label: 'Concept', key: 'scenes', statusMsg: 'Analyzing concept…' },
  { label: 'Context', key: 'context_pack', statusMsg: 'Gathering cultural context…' },
  { label: 'Script', key: 'panel_scripts', statusMsg: 'Writing panel scripts…' },
  { label: 'Safety', key: 'safety_results', statusMsg: 'Reviewing content safety…' },
  { label: 'Images', key: 'images', statusMsg: 'Generating panel artwork…' },
  { label: 'Audio', key: 'audios', statusMsg: 'Creating narration audio…' },
  { label: 'Assemble', key: 'package', statusMsg: 'Assembling your lesson…' },
] as const

function getReachedStep(snapshots: PipelineSnapshot[]): number {
  const merged: Record<string, unknown> = Object.assign({}, ...snapshots)
  for (let i = STEPS.length - 1; i >= 0; i--) {
    const v = merged[STEPS[i].key]
    if (v !== undefined && v !== null) {
      return i
    }
  }
  return -1
}

export function PipelineStepper({ snapshots, status }: Props) {
  if (status === 'idle') {
    return null
  }

  const reached = getReachedStep(snapshots)
  const isRunning = status === 'running'
  const activeIndex = isRunning ? Math.min(reached + 1, STEPS.length - 1) : reached
  const progressPct =
    STEPS.length > 0
      ? Math.round(((isRunning ? activeIndex : reached + 1) / STEPS.length) * 100)
      : 0
  const clampedProgress = Math.min(100, Math.max(0, progressPct))

  const statusLine =
    status === 'error'
      ? 'Generation failed — see message below.'
      : isRunning && activeIndex >= 0
        ? STEPS[activeIndex]?.statusMsg ?? 'Working…'
        : status === 'done'
          ? 'Lesson ready.'
          : ''

  return (
    <div className={styles.wrap}>
      <div className={styles.statusRow}>
        <span className={styles.statusIcon} aria-hidden>✦</span>
        <div className={styles.statusText}>
          <span className={styles.statusTitle}>AI status</span>
          <span className={styles.statusMessage}>{statusLine || '\u00a0'}</span>
        </div>
      </div>

      <div
        className={styles.progressTrack}
        role="progressbar"
        aria-valuenow={clampedProgress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Pipeline progress"
      >
        <div
          className={styles.progressFill}
          style={{ width: `${clampedProgress}%` }}
        />
      </div>

      <div className={styles.stepper}>
        {STEPS.map((step, i) => {
          const done = i <= reached
          const active = i === activeIndex && isRunning
          return (
            <div key={step.key} className={styles.step}>
              <div
                className={[
                  styles.dot,
                  done ? styles.done : '',
                  active ? styles.active : '',
                ].join(' ')}
              >
                {done ? '✓' : i + 1}
              </div>
              <span
                className={[styles.stepLabel, done ? styles.doneLabel : ''].join(' ')}
              >
                {step.label}
              </span>
              {i < STEPS.length - 1 && (
                <div
                  className={[styles.connector, done ? styles.connectorDone : ''].join(' ')}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
