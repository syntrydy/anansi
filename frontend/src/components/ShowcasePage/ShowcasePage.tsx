import styles from './ShowcasePage.module.css'

/* ─── data ─────────────────────────────────────────────────── */

const problems = [
  {
    icon: '🌍',
    title: 'No culturally relevant content',
    body: 'Teachers in sub-Saharan Africa struggle to find lesson materials that reflect local names, places, food, and cultural norms — most EdTech content is western-centric.',
  },
  {
    icon: '🎨',
    title: 'Visual learning is out of reach',
    body: 'Creating illustrated comic-style lessons requires graphic designers and significant budget. Most classrooms have neither.',
  },
  {
    icon: '🔊',
    title: 'Language & accessibility barriers',
    body: 'Multilingual classrooms in Kenya, Senegal, Cameroon, Ghana, and Nigeria need content in English, French, and Swahili — with matching audio narrations.',
  },
  {
    icon: '⏱️',
    title: 'Lesson prep takes too long',
    body: 'Designing a single illustrated lesson with comprehension questions and a vocabulary guide can take hours. Anansi produces a full package in under a minute.',
  },
  {
    icon: '🛡️',
    title: 'Child-safe content at scale',
    body: 'Automated content generation poses safety risks for young learners. Anansi applies heuristic and LLM-based safety filtering on every panel before delivery.',
  },
  {
    icon: '📦',
    title: 'Nothing is export-ready',
    body: 'Even where digital content exists, it rarely ships as a printable PDF, audio package, and teacher guide simultaneously.',
  },
]

const pipelineNodes = [
  {
    id: 'concept',
    label: 'Concept',
    color: '#4f46e5',
    icon: '💡',
    desc: 'Decomposes any topic into 6 sequential visual scenes with Claude Sonnet.',
  },
  {
    id: 'localizer',
    label: 'Localizer',
    color: '#0891b2',
    icon: '🌐',
    desc: 'Fetches cultural context (names, places, art style) via 5 FastMCP tools.',
  },
  {
    id: 'scriptor',
    label: 'Scriptor',
    color: '#7c3aed',
    icon: '✍️',
    desc: 'Writes captions, dialogue, FLUX prompts and narration with Claude Haiku.',
  },
  {
    id: 'safety',
    label: 'Safety',
    color: '#b45309',
    icon: '🛡️',
    desc: 'Heuristic + LLM review flags harmful or age-inappropriate panel content.',
  },
  {
    id: 'cartoon',
    label: 'Cartoon',
    color: '#be185d',
    icon: '🎨',
    desc: 'Generates one illustration per panel via Replicate FLUX Schnell.',
    parallel: true,
  },
  {
    id: 'narrator',
    label: 'Narrator',
    color: '#be185d',
    icon: '🔊',
    desc: 'Synthesises MP3 audio narrations per panel with OpenAI TTS.',
    parallel: true,
  },
  {
    id: 'synthesizer',
    label: 'Synthesizer',
    color: '#15803d',
    icon: '📦',
    desc: 'Assembles the output package and generates the teacher guide.',
  },
]

const tools = [
  { name: 'LangGraph', category: 'Orchestration', icon: '🔗', color: '#4f46e5', desc: 'Stateful multi-agent pipeline with streaming' },
  { name: 'Claude Sonnet & Haiku', category: 'LLM', icon: '🤖', color: '#9e3d00', desc: 'Anthropic models for reasoning, scripting & guides' },
  { name: 'FLUX Schnell', category: 'Image AI', icon: '🖼️', color: '#be185d', desc: 'Fast text-to-image via Replicate' },
  { name: 'OpenAI TTS', category: 'Audio AI', icon: '🔊', color: '#0891b2', desc: 'Neural text-to-speech in multiple languages' },
  { name: 'FastMCP', category: 'Context Layer', icon: '🌍', color: '#15803d', desc: '5 cultural context tools for 5 African countries' },
  { name: 'FastAPI', category: 'Backend', icon: '⚡', color: '#7c3aed', desc: 'Async API with SSE streaming for live updates' },
  { name: 'React 19', category: 'Frontend', icon: '⚛️', color: '#0891b2', desc: 'Component-driven UI with TypeScript & Vite' },
  { name: 'Langfuse', category: 'Observability', icon: '📊', color: '#b45309', desc: 'Pipeline tracing & LLM cost monitoring' },
  { name: 'Cerebras + Ollama', category: 'LLM Fallback', icon: '🔄', color: '#6b7280', desc: 'Automatic fallback when primary LLM is overloaded' },
  { name: 'Guardrails AI', category: 'Safety', icon: '🛡️', color: '#dc2626', desc: 'Content validation layer for child-safe outputs' },
  { name: 'FPDF + Pillow', category: 'Export', icon: '📄', color: '#374151', desc: 'Branded comic PDF with async image prefetch' },
  { name: 'Replicate', category: 'Infra', icon: '☁️', color: '#1d4ed8', desc: 'Scalable inference API for image generation' },
]

const countries = [
  { flag: '🇰🇪', name: 'Kenya', lang: 'Swahili' },
  { flag: '🇳🇬', name: 'Nigeria', lang: 'English' },
  { flag: '🇸🇳', name: 'Senegal', lang: 'French' },
  { flag: '🇬🇭', name: 'Ghana', lang: 'English' },
  { flag: '🇨🇲', name: 'Cameroon', lang: 'French' },
]

/* ─── component ─────────────────────────────────────────────── */

export function ShowcasePage() {
  return (
    <div className={styles.page}>

      {/* ── Hero ── */}
      <section className={styles.hero}>
        <div className={styles.heroInner}>
          <span className={styles.heroBadge}>Open-source · Phase 1</span>
          <h1 className={styles.heroTitle}>
            AI-powered lesson generation<br />
            <span className={styles.heroAccent}>built for African classrooms</span>
          </h1>
          <p className={styles.heroSub}>
            Anansi turns any teaching topic into a fully illustrated cartoon lesson — complete
            with localised cultural context, multilingual audio narrations, a teacher guide,
            and a print-ready PDF. In under 60 seconds.
          </p>
          <div className={styles.heroCountries}>
            {countries.map(c => (
              <div key={c.name} className={styles.countryPill}>
                <span>{c.flag}</span>
                <span>{c.name}</span>
                <span className={styles.countryLang}>{c.lang}</span>
              </div>
            ))}
          </div>
        </div>
        <div className={styles.heroBg} aria-hidden />
      </section>

      {/* ── Problems ── */}
      <section className={styles.section}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionLabel}>The problem</span>
            <h2 className={styles.sectionTitle}>Why Anansi exists</h2>
            <p className={styles.sectionSub}>
              Six real pain points that keep quality education out of reach for millions of learners.
            </p>
          </div>
          <div className={styles.problemGrid}>
            {problems.map(p => (
              <div key={p.title} className={styles.problemCard}>
                <span className={styles.problemIcon}>{p.icon}</span>
                <h3 className={styles.problemTitle}>{p.title}</h3>
                <p className={styles.problemBody}>{p.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Architecture ── */}
      <section className={styles.sectionDark}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionLabelLight}>System design</span>
            <h2 className={styles.sectionTitleLight}>Architecture overview</h2>
            <p className={styles.sectionSubLight}>
              A layered stack that goes from teacher input to a full lesson package, streamed in real time.
            </p>
          </div>

          <div className={styles.archDiagram}>
            {/* Layer 1 */}
            <div className={styles.archLayer}>
              <div className={styles.archLayerLabel}>Client</div>
              <div className={styles.archBox} style={{ '--box-color': '#4f46e5' } as React.CSSProperties}>
                <span className={styles.archBoxIcon}>⚛️</span>
                <strong>React 19 + Vite</strong>
                <span>TypeScript · SSE streaming · PDF/Audio exports</span>
              </div>
            </div>

            <div className={styles.archArrow}>↓</div>

            {/* Layer 2 */}
            <div className={styles.archLayer}>
              <div className={styles.archLayerLabel}>API</div>
              <div className={styles.archBox} style={{ '--box-color': '#7c3aed' } as React.CSSProperties}>
                <span className={styles.archBoxIcon}>⚡</span>
                <strong>FastAPI + SSE</strong>
                <span>Job queue · streaming state updates · PDF/Audio endpoints</span>
              </div>
            </div>

            <div className={styles.archArrow}>↓</div>

            {/* Layer 3 */}
            <div className={styles.archLayer}>
              <div className={styles.archLayerLabel}>Pipeline</div>
              <div className={styles.archBox} style={{ '--box-color': '#9e3d00' } as React.CSSProperties}>
                <span className={styles.archBoxIcon}>🔗</span>
                <strong>LangGraph</strong>
                <span>7-node async pipeline · parallel image + audio generation</span>
              </div>
            </div>

            <div className={styles.archArrow}>↓</div>

            {/* Layer 4 — services */}
            <div className={styles.archLayer}>
              <div className={styles.archLayerLabel}>Services</div>
              <div className={styles.archServicesRow}>
                {[
                  { icon: '🤖', name: 'Anthropic Claude', sub: 'LLM reasoning' },
                  { icon: '🖼️', name: 'Replicate FLUX', sub: 'Image gen' },
                  { icon: '🔊', name: 'OpenAI TTS', sub: 'Audio narration' },
                  { icon: '🌍', name: 'FastMCP', sub: 'Cultural context' },
                  { icon: '📊', name: 'Langfuse', sub: 'Observability' },
                ].map(s => (
                  <div key={s.name} className={styles.archService}>
                    <span>{s.icon}</span>
                    <strong>{s.name}</strong>
                    <span>{s.sub}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── LangGraph Pipeline ── */}
      <section className={styles.section}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionLabel}>LangGraph</span>
            <h2 className={styles.sectionTitle}>Pipeline structure</h2>
            <p className={styles.sectionSub}>
              Seven nodes execute in sequence, with cartoon and narrator running in parallel after the safety check.
            </p>
          </div>

          <div className={styles.pipeline}>
            {/* START */}
            <div className={styles.pipelineEndpoint}>START</div>
            <div className={styles.pipelineEdge} />

            {/* Linear nodes up to safety */}
            {pipelineNodes.filter(n => !n.parallel && n.id !== 'synthesizer').map((node, i, arr) => (
              <div key={node.id} className={styles.pipelineStep}>
                <div
                  className={styles.pipelineNode}
                  style={{ '--node-color': node.color } as React.CSSProperties}
                >
                  <span className={styles.pipelineNodeIcon}>{node.icon}</span>
                  <strong className={styles.pipelineNodeLabel}>{node.label}</strong>
                  <p className={styles.pipelineNodeDesc}>{node.desc}</p>
                </div>
                {i < arr.length - 1 && <div className={styles.pipelineEdge} />}
              </div>
            ))}

            {/* Fork */}
            <div className={styles.pipelineFork}>
              <div className={styles.pipelineForkLine} aria-hidden />
              <div className={styles.pipelineForkBranches}>
                {pipelineNodes.filter(n => n.parallel).map(node => (
                  <div key={node.id} className={styles.pipelineBranch}>
                    <div className={styles.pipelineBranchEdge} />
                    <div
                      className={styles.pipelineNode}
                      style={{ '--node-color': node.color } as React.CSSProperties}
                    >
                      <span className={styles.pipelineNodeIcon}>{node.icon}</span>
                      <strong className={styles.pipelineNodeLabel}>{node.label}</strong>
                      <p className={styles.pipelineNodeDesc}>{node.desc}</p>
                    </div>
                    <div className={styles.pipelineBranchEdge} />
                  </div>
                ))}
              </div>
              <div className={styles.pipelineForkLine} aria-hidden />
            </div>

            {/* Join */}
            <div className={styles.pipelineEdge} />
            {pipelineNodes.filter(n => n.id === 'synthesizer').map(node => (
              <div key={node.id} className={styles.pipelineStep}>
                <div
                  className={styles.pipelineNode}
                  style={{ '--node-color': node.color } as React.CSSProperties}
                >
                  <span className={styles.pipelineNodeIcon}>{node.icon}</span>
                  <strong className={styles.pipelineNodeLabel}>{node.label}</strong>
                  <p className={styles.pipelineNodeDesc}>{node.desc}</p>
                </div>
              </div>
            ))}

            <div className={styles.pipelineEdge} />
            {/* END */}
            <div className={styles.pipelineEndpoint}>END</div>
          </div>
        </div>
      </section>

      {/* ── Tools ── */}
      <section className={styles.sectionTinted}>
        <div className={styles.sectionInner}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionLabel}>Stack</span>
            <h2 className={styles.sectionTitle}>Tools & technologies</h2>
            <p className={styles.sectionSub}>
              Every component of the Anansi stack, from LLM to export.
            </p>
          </div>
          <div className={styles.toolGrid}>
            {tools.map(t => (
              <div key={t.name} className={styles.toolCard}>
                <div className={styles.toolTop}>
                  <span className={styles.toolIcon}>{t.icon}</span>
                  <span
                    className={styles.toolCategory}
                    style={{ '--cat-color': t.color } as React.CSSProperties}
                  >
                    {t.category}
                  </span>
                </div>
                <strong className={styles.toolName}>{t.name}</strong>
                <p className={styles.toolDesc}>{t.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <span className={styles.footerLogo}>Anansi AI</span>
          <span className={styles.footerSub}>Teaching assistant · Phase 1 · 5 countries</span>
        </div>
      </footer>
    </div>
  )
}
