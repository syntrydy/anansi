"""
Node 6 – Narrator (TTS via infrastructure.audio).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time as time_module
from pathlib import Path
from typing import List

from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.script import PanelScript
from anansi.core.constants import DEFAULT_TTS_CODES
from anansi.infrastructure.audio import synthesize_audio
from anansi.observability.langfuse_pipeline import trace_panel_observation

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(os.getenv("AUDIO_OUTPUT_DIR", "/tmp"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def synthesize_speech(text: str, language_code: str) -> bytes:
    """Backward-compatible alias for tests and callers."""
    return await synthesize_audio(text, language_code)


async def generate_panel_audio(
    scripts: List[PanelScript],
    country: str,
    skip_panel_numbers: set[int] | None = None,
) -> List[GeneratedAudio]:
    """
    Generate panel-level audio for each panel script.
    Skipped panel numbers (e.g. safety-blocked) get empty audio with an error note.
    """
    skip = skip_panel_numbers or set()
    language_code = DEFAULT_TTS_CODES.get(country.lower(), "en-US")

    async def _generate(panel: PanelScript) -> GeneratedAudio:
        pn = panel.panel_number
        if pn in skip:
            trace_panel_observation(
                kind="audio",
                panel_number=pn,
                duration_ms=0.0,
                success=False,
                extra={"skipped_safety": True},
            )
            return GeneratedAudio(
                panel_number=pn,
                audio_url="",
                duration_seconds=0.0,
                error="Skipped (safety)",
            )
        t0 = time_module.perf_counter()
        try:
            audio_bytes = await synthesize_audio(panel.narration, language_code)
            file_path = OUTPUT_DIR / f"panel_{pn}.mp3"
            with open(file_path, "wb") as f:
                f.write(audio_bytes)
            elapsed_ms = (time_module.perf_counter() - t0) * 1000
            trace_panel_observation(
                kind="audio",
                panel_number=pn,
                duration_ms=elapsed_ms,
                success=True,
            )
            return GeneratedAudio(
                panel_number=pn,
                audio_url=str(file_path),
                duration_seconds=0.0,
            )
        except Exception as e:
            logger.error("Failed to generate audio for panel %s: %s", pn, e)
            elapsed_ms = (time_module.perf_counter() - t0) * 1000
            trace_panel_observation(
                kind="audio",
                panel_number=pn,
                duration_ms=elapsed_ms,
                success=False,
                extra={"error": str(e)},
            )
            return GeneratedAudio(
                panel_number=pn,
                audio_url="",
                duration_seconds=0.0,
                error=str(e),
            )

    tasks = [_generate(s) for s in scripts]
    return await asyncio.gather(*tasks)


async def generate_full_narration(
    scripts: List[PanelScript], country: str
) -> GeneratedAudio:
    """
    Generate full narration audio concatenating all captions and dialogues.
    Returns a single GeneratedAudio object with panel_number=0.
    """
    full_text = " ".join([f"{s.caption}. {s.dialogue}" for s in scripts])
    language_code = DEFAULT_TTS_CODES.get(country.lower(), "en-US")
    try:
        audio_bytes = await synthesize_audio(full_text, language_code)
        file_path = OUTPUT_DIR / "full_narration.mp3"
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
        return GeneratedAudio(
            panel_number=0,
            audio_url=str(file_path),
            duration_seconds=0.0,
        )
    except Exception as e:
        logger.error("Failed to generate full narration: %s", e)
        return GeneratedAudio(
            panel_number=0,
            audio_url="",
            duration_seconds=0.0,
            error=str(e),
        )
