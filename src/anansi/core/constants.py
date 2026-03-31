"""
System-wide constants for the Anansi application.
"""

from pathlib import Path

# Absolute path to the country context pack JSON files.
# Resolved relative to this file so it is CWD-independent.
DATA_DIR: Path = Path(__file__).parent.parent / "context" / "data"

# Countries supported in Phase 1.  The canonical form is Title-Case.
SUPPORTED_COUNTRIES: frozenset[str] = frozenset(
    {
        "Kenya",
        "Nigeria",
        "Senegal",
        "Ghana",
        "Cameroon",
    }
)

# Google Cloud TTS BCP-47 fallback codes keyed by lowercase country name.
# Tools use these when the JSON pack's tts_code is empty or unavailable.
DEFAULT_TTS_CODES: dict[str, str] = {
    "kenya": "sw-KE",
    "nigeria": "en-NG",
    "senegal": "fr-SN",
    "ghana": "en-GH",
    "cameroon": "fr-CM",
}

# Maximum number of panels the agent graph will generate in a single request.
MAX_PANELS: int = 6

# LLM model identifiers used in config.py.
MODEL_REASONING: str = "claude-sonnet-4-6"
MODEL_STANDARD: str = "claude-haiku-4-5-20251001"
MODEL_OLLAMA_STANDARD: str = "llama3.2"
MODEL_OLLAMA_REASONING: str = "mistral"
