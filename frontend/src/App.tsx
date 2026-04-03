import './styles/tokens.css'
import ReactMarkdown from 'react-markdown'
import { LessonForm } from './components/LessonForm/LessonForm'
import { PdfExport } from './components/PdfExport/PdfExport'
import { PipelineStepper } from './components/PipelineStepper/PipelineStepper'
import { TeacherFeedback } from './components/TeacherFeedback/TeacherFeedback'
import { useLessonJob } from './hooks/useLessonJob'
import styles from './App.module.css'

export default function App() {
  const { jobId, status, result, error, snapshots, submit, reset } = useLessonJob()

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <h1 className={styles.logo}>Anansi AI</h1>
        <p className={styles.tagline}>Teaching Assistant</p>
      </header>

      <main className={styles.main}>
        <PipelineStepper snapshots={snapshots} status={status} />

        {status !== 'done' && (
          <LessonForm onSubmit={submit} disabled={status === 'running'} />
        )}

        {status === 'running' && (
          <p className={styles.runningMsg}>Generating your lesson… this may take a minute.</p>
        )}

        {status === 'error' && (
          <div className={styles.errorBox}>
            <strong>Pipeline failed:</strong> {error}
            <button className={styles.retryBtn} onClick={reset}>Try again</button>
          </div>
        )}

        {status === 'done' && result && jobId && (
          <>
            <div className={styles.doneActions}>
              <button className={styles.resetBtn} onClick={reset}>New Lesson</button>
            </div>

            {/* Storyboard comic strip */}
            {result.storyboard_image_url ? (
              <img
                className={styles.storyboard}
                src={result.storyboard_image_url}
                alt="Lesson storyboard"
              />
            ) : (
              <p className={styles.noImage}>Storyboard image not available.</p>
            )}

            {/* Panel text list */}
            <section className={styles.panelList}>
              {result.panels.map(panel => (
                <div key={panel.panel_id} className={styles.panelRow}>
                  <span className={styles.panelNum}>#{panel.panel_number}</span>
                  <div>
                    <p className={styles.panelCaption}>{panel.caption}</p>
                    {panel.dialogue && (
                      <p className={styles.panelDialogue}>{panel.dialogue}</p>
                    )}
                  </div>
                </div>
              ))}
            </section>

            {result.teacher_guide && (
              <details className={styles.guide}>
                <summary>Teacher Guide</summary>
                <div className={styles.guideText}><ReactMarkdown>{result.teacher_guide}</ReactMarkdown></div>
              </details>
            )}

            <PdfExport jobId={jobId} topic={result.lesson_title} />

            <TeacherFeedback jobId={jobId} />
          </>
        )}
      </main>
    </div>
  )
}
