# Anansi 🕷️

> **AI-Powered Multimodal Education for African Classrooms**  
> *Designed by SQUAD3 Wakanda*

Anansi turns a lesson topic into a culturally grounded teaching package: multi-panel cartoon art, optional narration audio, a printable **comic-style PDF**, a bundled **audio ZIP** download, and a markdown teacher guide. Names, places, and visual cues come from the selected country’s context pack.

Named after Anansi, the Akan spider deity and keeper of stories in West African folklore.

---

## What it does

A teacher provides:

| Input | Example |
|--------|---------|
| Topic | Photosynthesis |
| Country | Kenya |
| Grade | 5 |
| Language | English, Swahili, … |
| Audience | kid · adult · general |
| Aspect ratio | 1:1, 16:9, 4:3 |

Anansi returns an **output package** you can use in class:

- **Storyboard image** — single strip-style visual for the lesson (when generated)
- **Panels** — per-panel caption, dialogue, narration, image URL, and optional MP3
- **Teacher guide** — supporting notes (markdown)
- **Comic PDF export** — image-first pages, caption / dialogue / narration typography; no audio URLs or technical noise in the file
- **Download all audio** — ZIP of valid panel MP3s via the API (`panel_1.mp3`, …)
- **Teacher feedback** — optional rating after a run (API)

---

## Architecture

The default experience is a **React (Vite) frontend** talking to a **FastAPI** backend. The backend runs the **LangGraph** pipeline, streams progress over **SSE**, and serves PDF and audio ZIP exports. **FastMCP** cultural tools run **in-process** (no separate MCP process required for a normal lesson run).

```
React UI (Vite, :5173)
        │  HTTP /api/v1
        ▼
FastAPI — jobs, SSE stream, PDF, audio ZIP
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph (AnansiState)                  │
│                                                             │
│  concept → localizer → scriptor → safety ──┬── cartoon      │
│         (MCP tools in-process)              └── narrator    │
│                                    cartoon ──┐              │
│                                    narrator ─┴→ synthesizer │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
OutputPackage → UI, PDF builder, audio ZIP builder

Optional: Streamlit UI (`src/anansi/ui/app.py`) for the same pipeline-style workflow without the SPA.
```

After **scriptor**, **safety** runs once. **Cartoon** (images) and **narrator** (audio) run **in parallel**, then **synthesizer** merges everything into `OutputPackage`. Traces can be sent to **Langfuse** when keys are configured.

---

## Tech stack

| Layer | Technology | Role |
|-------|------------|------|
| Primary UI | React 19 + Vite + TypeScript | Lesson form, pipeline stepper, results, PDF link, audio ZIP download, feedback |
| API | FastAPI + Uvicorn | `POST /lessons`, `GET /lessons/{id}`, SSE stream, PDF + ZIP exports |
| Legacy UI | Streamlit | Alternate teacher UI (same domain concepts) |
| Agent | LangGraph | Stateful graph, async nodes, optional per-step streaming |
| Context | FastMCP (Python) | Five tools; loaded **in-process** from `context.server` |
| Images | Replicate — FLUX Schnell | Panel cartoons (`REPLICATE_API_TOKEN`) |
| Audio | OpenAI TTS (optional) | MP3 per panel when `OPENAI_API_KEY` is set |
| Text LLM | Anthropic Claude (or Ollama) | Concept, script, safety, etc. via `config.Settings` |
| Config | Pydantic Settings | `.env` → `anansi.config` (no ad-hoc `os.getenv` in business logic) |
| Observability | Langfuse (optional) | Pipeline tracing |

---

## Project structure

```
anansi/
├── frontend/                 # React + Vite app (proxies /api → backend)
├── src/anansi/
│   ├── agent/
│   │   ├── graph.py        # LangGraph definition and run_pipeline
│   │   ├── safety.py       # LLM-as-judge content check
│   │   └── nodes/          # concept, localizer, scriptor, cartoon, narrator, synthesizer
│   ├── api/
│   │   ├── main.py         # FastAPI app, CORS, lifespan
│   │   ├── router.py       # REST + SSE + PDF + audio ZIP
│   │   ├── store.py        # In-memory job store
│   │   ├── streaming.py    # SSE snapshot stream
│   │   ├── schemas.py      # Request/response models
│   │   └── export_audio_zip.py
│   ├── context/            # FastMCP server + JSON country packs
│   ├── core/models/        # Pydantic models (state, inputs, output, …)
│   ├── infrastructure/   # llm, image (Replicate), audio (OpenAI)
│   ├── observability/      # Langfuse pipeline helpers
│   ├── config.py           # Settings
│   └── ui/                 # Streamlit app + components (e.g. export_pdf.py)
├── tests/
├── .env.example
├── pyproject.toml          # uv / dependencies
├── uv.lock
└── README.md
```

---

## Getting started

### Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** for Python deps
- **Node.js 20+** and npm (for the React UI)
- API keys as needed: **Anthropic** (required for cloud LLM), **Replicate** (images), **OpenAI** (optional TTS)

### Install

```bash
git clone https://github.com/squad3wakanda/anansi
cd anansi

# Python environment
curl -LsSf https://astral.sh/uv/install.sh | sh   # if needed
uv sync

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env` — at minimum set **`ANTHROPIC_API_KEY`** and **`REPLICATE_API_TOKEN`**. Set **`OPENAI_API_KEY`** if you want narration audio. Langfuse keys are optional.

See `.env.example` for the full list (`USE_LOCAL`, `OLLAMA_URL`, MCP transport, etc.).

### Run the app (recommended)

**Terminal 1 — API (port 8000)**

```bash
cd anansi
uv run uvicorn anansi.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — React UI (port 5173)**

```bash
cd anansi/frontend
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies **`/api`** to the FastAPI app.

### Run Streamlit (optional)

```bash
uv run streamlit run src/anansi/ui/app.py
```

Opens **http://localhost:8501**. Uses the same Python package; PDF export uses `export_pdf.py` from this UI path as well.

### Makefile shortcuts

```bash
make install    # uv sync
make run-ui     # Streamlit
make test-all   # pytest
make lint       # ruff check
```

---

## HTTP API (overview)

All routes are under **`/api/v1`**.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/lessons` | Create a lesson job (`LessonRequest` JSON) → `job_id` |
| GET | `/lessons/{job_id}` | Poll status and `result` (`OutputPackage`) |
| GET | `/lessons/{job_id}/stream` | SSE: pipeline snapshots until done/error |
| GET | `/lessons/{job_id}/pdf` | Comic-style PDF download |
| GET | `/lessons/{job_id}/export/audio` | ZIP of panel MP3s (skips bad URLs; 404 if none) |
| POST | `/lessons/{job_id}/feedback` | Teacher feedback |
| GET | `/meta/countries` | Countries, languages, audiences, aspect ratios |

OpenAPI docs: **http://localhost:8000/docs** (when the API is running).

---

## FastMCP cultural context

The **localizer** node calls five tools (names, places, culture, language, avoids) through a **FastMCP** app defined in `src/anansi/context/server.py`. In production runs this is **in-process** via `fastmcp.Client(mcp)` — you do **not** need `python -m anansi.context.server` unless you are debugging or exposing MCP over stdio/HTTP separately.

### Adding a new country

Add a JSON file under `src/anansi/context/data/` (see existing packs). Validate with:

```bash
make validate-data
```

---

## Offline / local LLM mode

Set **`USE_LOCAL=true`** and configure **`OLLAMA_URL`** / **`OLLAMA_MODEL`** in `.env`. The LLM factory in `src/anansi/infrastructure/llm.py` switches text generation to Ollama when enabled (see **`anansi.config.Settings`**). Image and audio still use their respective cloud keys unless you extend the project for local media.

---

## Structured outputs

Panels and state boundaries use **Pydantic** models (e.g. `PanelScript`, `CountryData`, `OutputPackage`). The graph state is the **`AnansiState`** TypedDict; the final **`OutputPackage`** is what the UI and exporters consume.

---

## Content safety

Anansi uses an **LLM-as-judge** step tuned for educational material in African contexts: local dress, food, and customs are treated as appropriate unless genuinely unsafe or misleading. Unsafe panels can be omitted from image/audio generation and are handled explicitly in the comic PDF when included.

---

## Observability

When Langfuse env vars are set, pipeline nodes are traced (see `src/anansi/observability/langfuse_pipeline.py`). Useful metrics include end-to-end latency, safety flag rate, and per-request cost estimates from your provider dashboards.

---

## Estimated cost per lesson (order of magnitude)

Costs depend on panel count, model choice, and provider pricing. A rough cloud baseline:

| Component | Notes |
|-----------|--------|
| Text (concept, localize, script, safety, …) | Claude Haiku-class usage |
| Images | Replicate FLUX Schnell per panel |
| Audio | OpenAI TTS per panel (if enabled) |
| MCP + API | No extra vendor cost |

Treat numbers as **indicative**; monitor spend in Anthropic, Replicate, and OpenAI consoles.

---

## Supported countries (Phase 1)

| Country | Status |
|---------|--------|
| Kenya, Nigeria, Senegal, Ghana, Cameroon | Context packs in repo |

More countries: add JSON under `context/data/` and wire into supported-country constants if needed.

---

## Roadmap

### Phase 1 — Cloud MVP
- [x] LangGraph pipeline (concept → … → synthesizer)
- [x] FastMCP context tools (in-process)
- [x] React + FastAPI + SSE teacher flow
- [x] Comic-style PDF + audio ZIP export
- [x] Streamlit UI (parallel path)
- [x] Content safety (LLM-as-judge)
- [ ] Teacher feedback analytics loop

### Phase 2 — Scale
- [ ] More countries and curriculum alignment
- [ ] Durable job store / auth for multi-teacher deployments

### Phase 3 — Offline
- [ ] Deeper Ollama + local image/audio paths for air-gapped schools

---

## Contributing

- **Countries:** add or edit `src/anansi/context/data/<country>.json`, run `make validate-data`.
- **Tests:** `uv run pytest tests/`
- **Lint / format:** `make lint`, `make format` (Ruff); frontend: `cd frontend && npm run lint`

---

## License

MIT — see LICENSE.

---

## About the name

Anansi is the spider figure from Akan and West African folklore — the keeper of stories and wisdom. A tool that weaves lessons into visual narratives for African learners fits that spirit.

---

*Anansi — SQUAD3 Wakanda · 2026*
