import { forwardRef, useEffect, useImperativeHandle, useState } from 'react'
import { api } from '../../api/client'
import type { LessonRequest, MetaResponse } from '../../api/types'
import styles from './LessonForm.module.css'

export interface LessonFormHandle {
  /** Current field values as a lesson request, or null if topic is empty. */
  getRequest: () => LessonRequest | null
}

interface Props {
  onSubmit: (req: LessonRequest) => void
  disabled?: boolean
  isSubmitting?: boolean
}

const DEFAULT_META: MetaResponse = {
  countries: ['Cameroon', 'Ghana', 'Kenya', 'Nigeria', 'Senegal'],
  languages: ['English', 'French', 'Swahili'],
  audiences: ['general', 'kid', 'adult'],
  aspect_ratios: ['1:1', '16:9', '4:3'],
}

export const LessonForm = forwardRef<LessonFormHandle, Props>(function LessonForm(
  { onSubmit, disabled = false, isSubmitting = false },
  ref,
) {
  const [meta, setMeta] = useState<MetaResponse>(DEFAULT_META)
  const [topic, setTopic] = useState('')
  const [country, setCountry] = useState('Kenya')
  const [grade, setGrade] = useState(5)
  const [language, setLanguage] = useState('English')
  const [audience, setAudience] = useState<'kid' | 'adult' | 'general'>('general')
  const [aspectRatio, setAspectRatio] = useState('1:1')
  const [extraNotes, setExtraNotes] = useState('')
  const [error, setError] = useState('')

  useImperativeHandle(ref, () => ({
    getRequest: () => {
      const t = topic.trim()
      if (!t) {
        return null
      }
      const notes = extraNotes.trim()
      return {
        topic: t,
        country,
        grade,
        language,
        audience,
        aspect_ratio: aspectRatio,
        ...(notes ? { extra_context: { notes } } : {}),
      }
    },
  }), [
    topic,
    country,
    grade,
    language,
    audience,
    aspectRatio,
    extraNotes,
  ])

  useEffect(() => {
    api.getMeta().then(setMeta).catch(() => {/* defaults */})
  }, [])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!topic.trim()) {
      setError('Topic is required')
      return
    }
    setError('')
    const notes = extraNotes.trim()
    onSubmit({
      topic: topic.trim(),
      country,
      grade,
      language,
      audience,
      aspect_ratio: aspectRatio,
      ...(notes ? { extra_context: { notes } } : {}),
    })
  }

  const busy = disabled || isSubmitting

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.formHeader}>
        <h2 className={styles.title}>Lesson controls</h2>
        <p className={styles.subtitle}>Configure topic and classroom context, then generate.</p>
      </div>

      <div className={styles.section}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="topic">Topic</label>
          <input
            id="topic"
            className={styles.input}
            type="text"
            value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder="e.g. Water cycle"
            disabled={busy}
            autoComplete="off"
          />
          <p className={styles.helper}>What students should learn in this storyboard.</p>
          {error ? <span className={styles.error}>{error}</span> : null}
        </div>
      </div>

      <div className={styles.section}>
        <h3 className={styles.sectionLabel}>Classroom</h3>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="country">Country</label>
          <select
            id="country"
            className={styles.select}
            value={country}
            onChange={e => setCountry(e.target.value)}
            disabled={busy}
          >
            {meta.countries.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="grade">Grade</label>
          <input
            id="grade"
            className={styles.input}
            type="number"
            min={1}
            max={12}
            value={grade}
            onChange={e => setGrade(Number(e.target.value))}
            disabled={busy}
          />
        </div>
      </div>

      <div className={styles.section}>
        <h3 className={styles.sectionLabel}>Delivery</h3>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="language">Language</label>
          <select
            id="language"
            className={styles.select}
            value={language}
            onChange={e => setLanguage(e.target.value)}
            disabled={busy}
          >
            {meta.languages.map(l => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="audience">Audience</label>
          <select
            id="audience"
            className={styles.select}
            value={audience}
            onChange={e => setAudience(e.target.value as 'kid' | 'adult' | 'general')}
            disabled={busy}
          >
            {meta.audiences.map(a => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="ratio">Aspect ratio</label>
          <select
            id="ratio"
            className={styles.select}
            value={aspectRatio}
            onChange={e => setAspectRatio(e.target.value)}
            disabled={busy}
          >
            {meta.aspect_ratios.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <p className={styles.helper}>Shape of generated panel images.</p>
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="extra">Extra context</label>
          <textarea
            id="extra"
            className={styles.textarea}
            value={extraNotes}
            onChange={e => setExtraNotes(e.target.value)}
            placeholder="Optional instructions for tone, examples, or constraints…"
            rows={3}
            disabled={busy}
          />
          <p className={styles.helper}>Passed through to the lesson pipeline as optional hints.</p>
        </div>
      </div>

      <button
        className={styles.submit}
        type="submit"
        disabled={busy || !topic.trim()}
        title={busy ? 'Generation in progress' : 'Generate a new lesson package'}
      >
        {isSubmitting ? (
          <span className={styles.submitInner}>
            <span className={styles.spinner} aria-hidden />
            Generating…
          </span>
        ) : (
          <span className={styles.submitInner}>
            <span className={styles.icon} aria-hidden>⚡</span>
            Generate lesson
          </span>
        )}
      </button>
    </form>
  )
})

LessonForm.displayName = 'LessonForm'
