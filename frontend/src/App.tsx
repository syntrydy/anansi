import { useRef, useState } from 'react'
import './styles/tokens.css'
import ReactMarkdown from 'react-markdown'
import { LessonForm, type LessonFormHandle } from './components/LessonForm/LessonForm'
import { OutputActionBar } from './components/OutputActionBar/OutputActionBar'
import { PanelCard } from './components/PanelCard/PanelCard'
import { PipelineStepper } from './components/PipelineStepper/PipelineStepper'
import { TeacherFeedback } from './components/TeacherFeedback/TeacherFeedback'
import { useLessonJob } from './hooks/useLessonJob'
import styles from './App.module.css'

export default function App() {
  const {
    jobId,
    status,
    result,
    error,
    lastRequest,
    snapshots,
    submit,
    reset,
  } = useLessonJob()

  const [formKey, setFormKey] = useState(0)
  const formRef = useRef<LessonFormHandle>(null)

  function handleClear() {
    reset()
    setFormKey(k => k + 1)
  }

  function handleRegenerate() {
    const req = formRef.current?.getRequest() ?? lastRequest
    if (req) {
      void submit(req)
    }
  }

  const running = status === 'running'

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div>
            <h1 className={styles.logo}>Anansi</h1>
            <p className={styles.tagline}>Teaching assistant</p>
          </div>
        </div>
      </header>

      <div className={styles.workspace}>
        <aside className={styles.sidebar}>
          <div className={styles.sidebarInner}>
            <LessonForm
              ref={formRef}
              key={formKey}
              onSubmit={submit}
              disabled={running}
              isSubmitting={running}
            />
          </div>
        </aside>

        <main className={styles.output}>
          <div className={styles.outputInner}>
            <PipelineStepper snapshots={snapshots} status={status} />

            {running && (
              <p className={styles.runningHint}>
                This usually takes about a minute. You can prepare your next topic on the left while you wait.
              </p>
            )}

            {status === 'error' && (
              <div className={styles.errorBox} role="alert">
                <div className={styles.errorBody}>
                  <strong className={styles.errorTitle}>Something went wrong</strong>
                  <p className={styles.errorMsg}>{error}</p>
                </div>
                <button
                  type="button"
                  className={styles.errorBtn}
                  onClick={handleClear}
                >
                  Reset workspace
                </button>
              </div>
            )}

            {status === 'done' && result && jobId && (
              <>
                <OutputActionBar
                  jobId={jobId}
                  topic={result.lesson_title}
                  country={lastRequest?.country}
                  grade={lastRequest?.grade}
                    panels={result.panels}
                    running={running}
                  onRegenerate={handleRegenerate}
                  onClear={handleClear}
                />

                <section className={styles.section}>
                  <h2 className={styles.sectionTitle}>Storyboard</h2>
                  {result.storyboard_image_url ? (
                    <img
                      className={styles.storyboard}
                      src={result.storyboard_image_url}
                      alt="Lesson storyboard"
                    />
                  ) : (
                    <p className={styles.muted}>Storyboard image not available.</p>
                  )}
                </section>

                <section className={styles.section}>
                  <h2 className={styles.sectionTitle}>Panels</h2>
                  <div className={styles.panelGrid}>
                    {result.panels.map(panel => (
                      <PanelCard key={panel.panel_id} panel={panel} />
                    ))}
                  </div>
                </section>

                {result.teacher_guide ? (
                  <details className={styles.guide}>
                    <summary className={styles.guideSummary}>Teacher guide</summary>
                    <div className={styles.guideText}>
                      <ReactMarkdown>{result.teacher_guide}</ReactMarkdown>
                    </div>
                  </details>
                ) : null}

                <TeacherFeedback jobId={jobId} />
              </>
            )}

            {status === 'idle' && !result && !error && (
              <div className={styles.emptyState}>
                <p className={styles.emptyTitle}>Ready when you are</p>
                <p className={styles.emptyText}>
                  Set your topic and classroom options on the left, then generate a full lesson package with images, audio, and exports.
                </p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
