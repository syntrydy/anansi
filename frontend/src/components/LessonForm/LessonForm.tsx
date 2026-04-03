import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { LessonRequest, MetaResponse } from '../../api/types'
import styles from './LessonForm.module.css'

interface Props {
  onSubmit: (req: LessonRequest) => void
  disabled?: boolean
}

const DEFAULT_META: MetaResponse = {
  countries: ['Cameroon', 'Ghana', 'Kenya', 'Nigeria', 'Senegal'],
  languages: ['English', 'French', 'Swahili'],
  audiences: ['general', 'kid', 'adult'],
  aspect_ratios: ['1:1', '16:9', '4:3'],
}

export function LessonForm({ onSubmit, disabled = false }: Props) {
  const [meta, setMeta] = useState<MetaResponse>(DEFAULT_META)
  const [topic, setTopic] = useState('')
  const [country, setCountry] = useState('Kenya')
  const [grade, setGrade] = useState(5)
  const [language, setLanguage] = useState('English')
  const [audience, setAudience] = useState<'kid' | 'adult' | 'general'>('general')
  const [aspectRatio, setAspectRatio] = useState('1:1')
  const [error, setError] = useState('')

  useEffect(() => {
    api.getMeta().then(setMeta).catch(() => {/* use defaults */})
  }, [])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!topic.trim()) { setError('Topic is required'); return }
    setError('')
    onSubmit({
      topic: topic.trim(),
      country,
      grade,
      language,
      audience,
      aspect_ratio: aspectRatio,
    })
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <h2 className={styles.title}>Create New Lesson Storyboard</h2>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="topic">Topic</label>
        <input
          id="topic"
          className={styles.input}
          type="text"
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="e.g. The water cycle"
          disabled={disabled}
        />
        {error && <span className={styles.error}>{error}</span>}
      </div>

      <div className={styles.row}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="country">Country</label>
          <select
            id="country"
            className={styles.select}
            value={country}
            onChange={e => setCountry(e.target.value)}
            disabled={disabled}
          >
            {meta.countries.map(c => <option key={c} value={c}>{c}</option>)}
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
            disabled={disabled}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="language">Language</label>
          <select
            id="language"
            className={styles.select}
            value={language}
            onChange={e => setLanguage(e.target.value)}
            disabled={disabled}
          >
            {meta.languages.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>
      </div>

      <div className={styles.row}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="audience">Audience</label>
          <select
            id="audience"
            className={styles.select}
            value={audience}
            onChange={e => setAudience(e.target.value as 'kid' | 'adult' | 'general')}
            disabled={disabled}
          >
            {meta.audiences.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="ratio">Aspect Ratio</label>
          <select
            id="ratio"
            className={styles.select}
            value={aspectRatio}
            onChange={e => setAspectRatio(e.target.value)}
            disabled={disabled}
          >
            {meta.aspect_ratios.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      </div>

      <button className={styles.submit} type="submit" disabled={disabled}>
        {disabled ? 'Generating…' : 'Generate Lesson'}
      </button>
    </form>
  )
}
