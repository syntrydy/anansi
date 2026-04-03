"""
Audio infrastructure — OpenAI Text-to-Speech (async-friendly).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time

from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def _client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("Environment variable OPENAI_API_KEY is not set")
    return OpenAI(api_key=key)


async def synthesize_audio(text: str, language_code: str) -> bytes:
    """
    Synthesize speech as MP3 bytes using OpenAI TTS.

    ``language_code`` is accepted for API compatibility but not forwarded —
    OpenAI TTS detects the input language automatically.
    """
    loop = asyncio.get_running_loop()

    def sync_call() -> bytes:
        client = _client()
        for attempt in range(MAX_RETRIES):
            try:
                response = client.audio.speech.create(
                    model="tts-1-hd",
                    voice="nova",
                    input=text,
                    response_format="mp3",
                )
                return response.content
            except OpenAIError as err:
                logger.warning(
                    "TTS attempt %s failed: %s",
                    attempt + 1,
                    err,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)
        raise RuntimeError(f"TTS failed after {MAX_RETRIES} attempts")

    return await loop.run_in_executor(None, sync_call)
