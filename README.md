# Anansi 🕷️

> **AI-Powered Multimodal Education for African Classrooms**  
> *Designed by SQUAD3 Wakanda*

Anansi transforms any educational topic into a culturally accurate, multilingual cartoon teaching package — complete with narration audio, printable PDF, and a teacher guide. Built specifically for African classrooms, every name, place, food, and landscape detail is drawn from the selected country's cultural context.

Named after Anansi, the Akan spider deity and keeper of all stories and knowledge in West African folklore.

---

## What it does

A teacher provides three inputs:

```
Topic:    Photosynthesis
Country:  Kenya
Grade:    Grade 5
Language: Swahili
```

Anansi produces a complete teaching package:

- **Multi-panel cartoon** — culturally accurate illustrations (Kamau and Achieng near the Tana River, not John and Sarah in a generic suburb)
- **Panel-by-panel audio narration** — in the selected language via Google Cloud TTS
- **Printable PDF** — A4, low-ink mode for classroom printing
- **Projector view** — high-contrast for display
- **Discussion cards** — cut-out panels for group activity
- **Teacher guide** — vocabulary list, comprehension questions, lesson plan

---

## Architecture

Anansi is a **6-node LangGraph stateful agent** with a FastMCP cultural context server, Streamlit teacher UI, and Langfuse observability.

```
Teacher Input (Topic · Country · Grade · Language)
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                  LangGraph Agent Graph                │
│                                                       │
│  N1 Concept Analyzer → N2 Localizer → N3 Scriptor    │
│                              │              │         │
│                    FastMCP   │    ┌──────── ┘         │
│                    Context   │    │                   │
│                    Server    │    ├── N4 Cartoon Gen  │
│                              │    │   (FLUX Kontext)  │
│                              │    │                   │
│                              │    └── N6 Narrator     │
│                              │        (Google TTS)    │
│                              │              │         │
│                              └──── N5 Synthesizer ───┘│
└───────────────────────────────────────────────────────┘
        │
        ▼
Output: Panels · Audio · PDF · Teacher Guide

              ↕ All nodes traced via Langfuse
```

Nodes 4 and 6 run **in parallel** after Node 3 completes — image generation and audio narration are produced simultaneously.

---

## Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| UI | Streamlit | Teacher input form, live progress, panel viewer, audio, download |
| Agent core | LangGraph | 6-node stateful graph, parallel branches, shared TypedDict state |
| Context server | FastMCP (Python) | 5 MCP tools returning per-country cultural context packs |
| Image generation | FLUX.1 Kontext Pro | Multi-panel cartoon generation with character consistency |
| Audio narration | Google Cloud TTS | Panel-by-panel narration in local African languages |
| Observability | Langfuse | Full trace, prompt analytics, cost and latency per node |
| Validation | Pydantic + Guardrails AI | Structured outputs at every node boundary |
| Content safety | LLM-as-judge (Claude Haiku) | African-context-aware age and cultural appropriateness check |

---

## Project Structure

```
anansi/
├── anansi/
│   ├── agent/
│   │   ├── graph.py          # LangGraph graph definition
│   │   ├── state.py          # TypedDict AnansiState
│   │   ├── nodes/
│   │   │   ├── concept.py    # Node 1 — Concept Analyzer
│   │   │   ├── localizer.py  # Node 2 — Localizer (calls MCP)
│   │   │   ├── scriptor.py   # Node 3 — Scriptor
│   │   │   ├── cartoon.py    # Node 4 — Cartoon Generator
│   │   │   ├── narrator.py   # Node 6 — Narrator
│   │   │   └── synthesizer.py # Node 5 — Synthesizer
│   │   └── safety.py         # LLM-as-judge content check
│   ├── mcp/
│   │   ├── server.py         # FastMCP server entry point
│   │   ├── tools.py          # @mcp.tool() definitions
│   │   └── data/             # Country JSON context packs
│   │       ├── kenya.json
│   │       ├── nigeria.json
│   │       ├── senegal.json
│   │       ├── ghana.json
│   │       └── cameroon.json
│   ├── models/
│   │   ├── inputs.py         # TeacherInput Pydantic model
│   │   ├── outputs.py        # All output Pydantic models
│   │   └── context.py        # ContextPack model
│   ├── config.py             # LLM factory — cloud or Ollama
│   └── ui/
│       └── app.py            # Streamlit application
├── tests/
│   ├── test_nodes.py
│   ├── test_mcp.py
│   └── test_safety.py
├── .env.example
├── pyproject.toml        # uv project config and dependencies
├── uv.lock               # locked dependency versions
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — dependency management
- API keys: Anthropic, Replicate (or SiliconFlow), Google Cloud, Langfuse

### Installation

```bash
git clone https://github.com/squad3wakanda/anansi
cd anansi

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env`:

```env
# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Image generation (choose one)
REPLICATE_API_TOKEN=r8_...
# or
SILICONFLOW_API_KEY=...

# Audio
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Observability
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Offline mode (Phase 3)
USE_LOCAL=false
USE_LOCAL_IMAGE=false
USE_LOCAL_AUDIO=false
OLLAMA_URL=http://localhost:11434
```

### Run

```bash
# Start the FastMCP cultural context server
uv run python -m anansi.mcp.server

# In a separate terminal, start the Streamlit UI
uv run streamlit run anansi/ui/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## The FastMCP Cultural Context Server

The FastMCP server exposes 5 tools called by the Localizer node (Node 2):

| Tool | Returns | Example (Kenya) |
|------|---------|-----------------|
| `get_names(country)` | Male and female first names | Kamau, Otieno, Achieng, Wanjiru |
| `get_places(country)` | Cities, rivers, landmarks | Kisumu, Tana River, Mount Kenya |
| `get_culture(country)` | Food, clothing, housing, transport, animals | Ugali, kanga, mabati roof, matatu, zebu |
| `get_language(country)` | Languages and TTS code | English, Swahili, sw-KE |
| `get_avoids(country)` | Things NOT to show | Snow, oak trees, dollars, subway |

### Adding a new country

Create a new JSON file in `anansi/mcp/data/`:

```json
{
  "country": "Ethiopia",
  "languages": {
    "official": "Amharic",
    "local": ["Amharic", "Oromo", "Tigrinya"],
    "tts_code": "am-ET"
  },
  "names": {
    "male": ["Abebe", "Tadesse", "Girma", "Haile", "Tesfaye"],
    "female": ["Tigist", "Selam", "Meron", "Hiwot", "Bethlehem"]
  },
  "places": {
    "cities": ["Addis Ababa", "Dire Dawa", "Gondar", "Hawassa"],
    "rivers": ["Blue Nile", "Awash River", "Omo River"],
    "landmarks": ["Simien Mountains", "Danakil Depression", "Lake Tana"]
  },
  "culture": {
    "food": ["injera", "wat", "teff bread", "tej"],
    "clothing": ["habesha kemis", "netela"],
    "housing": ["tukul", "stone house"],
    "transport": ["bajaj", "minibus", "donkey"],
    "animals": ["Ethiopian wolf", "gelada baboon", "zebu"]
  },
  "art_style_cues": "Ethiopian highlands, terraced farms, eucalyptus trees, stone churches",
  "avoids": ["snow in lowlands", "Western fast food", "dollars", "oak trees"]
}
```

No code changes required — the FastMCP server picks up new country files automatically.

---

## Offline Mode (Phase 3)

All text LLM nodes can be swapped to Ollama with a single environment variable. No graph code changes required.

```bash
# Switch to local models
USE_LOCAL=true
OLLAMA_URL=http://localhost:11434
```

```python
# config.py — the factory handles everything
def get_llm(capability: str = 'standard'):
    if os.getenv('USE_LOCAL') == 'true':
        return ChatOllama(model='llama3.2', base_url=os.getenv('OLLAMA_URL'))
    if capability == 'reasoning':
        return ChatAnthropic(model='claude-sonnet-4-6')
    return ChatAnthropic(model='claude-haiku-4-5-20261001')
```

| Component | Phase 1 (Cloud) | Phase 3 (Offline) |
|-----------|----------------|-------------------|
| Text LLMs | Claude Haiku / Sonnet | Ollama (Llama 3.2 / Mistral) |
| Image gen | FLUX Kontext Pro | Stable Diffusion 3.5 (local) |
| Audio | Google Cloud TTS | Kokoro TTS (Ollama) |
| FastMCP | Python process | Same — no change |

**Minimum hardware for full offline**: 16 GB RAM, GPU with 6 GB VRAM (e.g. NVIDIA GTX 1660).

---

## Structured Outputs

Every LLM node returns a validated Pydantic model. Nothing flows between nodes as unstructured text.

```python
# Node 1 output
class Scene(BaseModel):
    panel_number: int
    description: str
    key_concept: str
    characters: List[str]
    setting: str

# Node 2 output
class ContextPack(BaseModel):
    language: str
    character_names: List[str]
    place_names: List[str]
    cultural_elements: CultureElements
    avoids: List[str]
    art_style_cues: str

# Node 3 output
class PanelScript(BaseModel):
    panel_number: int
    caption: str           # Max 20 words
    dialogue: List[dict]   # [{character, line}]
    image_prompt: str      # Full FLUX prompt
    narration_text: str    # Text for TTS
```

---

## Content Safety

Anansi uses an **LLM-as-judge** approach rather than generic content filters. The safety check is explicitly African-context-aware — traditional farming, local food, cultural dress, and regional customs are never flagged.

```python
SAFETY_PROMPT = """
You are a content reviewer for African primary school educational materials.
Review this panel script for Grade {grade} students in {country}.

Traditional farming, local food, cultural clothing, and regional customs
are ALWAYS appropriate.

Check for:
- Age-appropriate language and scenes
- Cultural respect and accuracy  
- Educational accuracy for the topic

Return: {appropriate: bool, issues: List[str], suggestions: List[str]}
"""
```

---

## Observability

All requests are fully traced in Langfuse. One callback handler, zero instrumentation code inside nodes.

```python
from langfuse.callback import CallbackHandler

langfuse_handler = CallbackHandler(
    public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
    secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
)

result = graph.invoke(state, config={'callbacks': [langfuse_handler]})
```

**Key metrics tracked:**
- Total latency per request (target: < 45s for 5 panels)
- Cost per request by country and grade
- Image generation failure rate by country
- MCP tool call success rate (cultural data coverage)
- Safety check flag rate
- Teacher feedback rate

---

## Estimated Cost per Request

| Component | Model | Est. cost |
|-----------|-------|-----------|
| Text nodes (×4) | Claude Haiku | ~$0.02 |
| Image generation (×5 panels) | FLUX Kontext Pro | ~$0.20 |
| Audio narration | Google Cloud TTS | ~$0.02 |
| MCP tool calls | Local FastMCP | $0.00 |
| **Total** | | **~$0.24** |

---

## Supported Countries (Phase 1)

| Country | Languages | Status |
|---------|-----------|--------|
| Kenya | English, Swahili | ✅ Ready |
| Nigeria | English, Yoruba, Hausa, Igbo | ✅ Ready |
| Senegal | French, Wolof | ✅ Ready |
| Ghana | English, Twi | ✅ Ready |
| Cameroon | French, English | ✅ Ready |

More countries are added in Phase 2 based on usage data. See [Adding a new country](#adding-a-new-country).

---

## Roadmap

### Phase 1 — Cloud MVP
- [x] Architecture design
- [ ] LangGraph graph implementation (all 6 nodes)
- [ ] FastMCP server with 5 pilot country packs
- [ ] Streamlit UI with all output formats
- [ ] Langfuse observability
- [ ] Content safety (LLM-as-judge)
- [ ] Teacher feedback loop

### Phase 2 — Scale
- [ ] 15+ countries from usage patterns
- [ ] Curriculum alignment from teacher feedback data
- [ ] Region-level context packs
- [ ] SQLite backend for FastMCP
- [ ] Teacher correction submissions

### Phase 3 — Offline Infrastructure
- [ ] Ollama integration (tested from Phase 1 via USE_LOCAL flag)
- [ ] Stable Diffusion self-hosted
- [ ] Kokoro TTS offline
- [ ] School deployment guide

---

## Contributing

### Adding a country
See [Adding a new country](#adding-a-new-country) — just a JSON file, no code changes.

### Correcting cultural data
If you spot a wrong name, place, or cultural detail:
1. Open `anansi/mcp/data/<country>.json`
2. Make the correction
3. Submit a pull request with a brief explanation

### Running tests
```bash
uv run pytest tests/
```

---

## License

MIT — see LICENSE.

---

## About the name

Anansi is the spider deity from Akan and West African folklore — the keeper of all stories and wisdom in the world. According to legend, all stories belong to Anansi because he outwitted the Sky God to earn them.

A tool that weaves concepts into visual narratives for African children could have no more fitting a name.

---

*Anansi — SQUAD3 Wakanda · 2026*
