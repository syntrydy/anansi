"""
Audio infrastructure — Google Cloud Text-to-Speech (async-friendly).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time

from google.api_core.exceptions import GoogleAPIError
from google.cloud import texttospeech

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def _tts_client() -> texttospeech.TextToSpeechClient:
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise RuntimeError("Environment variable GOOGLE_APPLICATION_CREDENTIALS is not set")
    return texttospeech.TextToSpeechClient()


async def synthesize_audio(text: str, language_code: str) -> bytes:
    """
    Synthesize speech as MP3 bytes for the given language (BCP-47 tag).
    """
    loop = asyncio.get_running_loop()

    def sync_call() -> bytes:
        client = _tts_client()
        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        for attempt in range(MAX_RETRIES):
            try:
                response = client.synthesize_speech(
                    input=input_text, voice=voice, audio_config=audio_config
                )
                return response.audio_content
            except GoogleAPIError as err:
                logger.warning(
                    "TTS attempt %s failed for %s: %s",
                    attempt + 1,
                    language_code,
                    err,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)
        raise RuntimeError(
            f"TTS failed after {MAX_RETRIES} attempts for {language_code}"
        )

    return await loop.run_in_executor(None, sync_call)
