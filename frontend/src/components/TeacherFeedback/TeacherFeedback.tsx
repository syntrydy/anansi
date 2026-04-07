import { useState } from 'react'
import { api } from '../../api/client'
import styles from './TeacherFeedback.module.css'

interface Props {
  jobId: string
}

export function TeacherFeedback({ jobId }: Props) {
  const [comment, setComment] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)

  async function send(rating: 'positive' | 'negative') {
    setLoading(true)
    try {
      await api.submitFeedback(jobId, { rating, comment: comment.trim() })
      setSubmitted(true)
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return <p className={styles.thanks}>Thank you — your feedback has been recorded!</p>
  }

  return (
    <details className={styles.wrapper}>
      <summary className={styles.summary}>Teacher Feedback</summary>

      <div className={styles.body}>
        <p className={styles.caption}>Was this lesson package useful? Your feedback helps improve future lessons.</p>

        <textarea
          className={styles.textarea}
          placeholder="Optional comment (e.g. what worked, what did not)…"
          value={comment}
          onChange={e => setComment(e.target.value)}
          rows={3}
          disabled={loading}
        />

        <div className={styles.buttons}>
          <button
            className={styles.thumbUp}
            onClick={() => send('positive')}
            disabled={loading}
          >
            👍 Useful
          </button>
          <button
            className={styles.thumbDown}
            onClick={() => send('negative')}
            disabled={loading}
          >
            👎 Not useful
          </button>
        </div>
      </div>
    </details>
  )
}
