import type { PipelineSnapshot } from '../../api/types'
import type { JobStatus } from '../../api/types'
import styles from './PipelineStepper.module.css'

interface Props {
  snapshots: PipelineSnapshot[]
  status: JobStatus
}

const STEPS = [
  { label: 'Concept',  key: 'scenes' },
  { label: 'Localize', key: 'context_pack' },
  { label: 'Script',   key: 'panel_scripts' },
  { label: 'Images',   key: 'images' },
  { label: 'Assemble', key: 'package' },
] as const

function getReachedStep(snapshots: PipelineSnapshot[]): number {
  const merged = Object.assign({}, ...snapshots)
  for (let i = STEPS.length - 1; i >= 0; i--) {
    if (merged[STEPS[i].key]) return i
  }
  return -1
}

export function PipelineStepper({ snapshots, status }: Props) {
  if (status === 'idle') return null

  const reached = getReachedStep(snapshots)
  const isRunning = status === 'running'
  const activeIndex = isRunning ? reached + 1 : reached

  return (
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
            <span className={[styles.stepLabel, done ? styles.doneLabel : ''].join(' ')}>
              {step.label}
            </span>
            {i < STEPS.length - 1 && (
              <div className={[styles.connector, done ? styles.connectorDone : ''].join(' ')} />
            )}
          </div>
        )
      })}
    </div>
  )
}
