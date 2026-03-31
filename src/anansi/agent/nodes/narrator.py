"""
Node 6 – Narrator (TTS)
Generates panel-level and full narration audio asynchronously using Google Cloud TTS.
"""

from typing import List
import asyncio
import logging
import os
from pathlib import Path

from google.cloud import texttospeech
from google.api_core.exceptions import GoogleAPIError

from anansi.core.models.script import PanelScript
from anansi.core.models.audio import GeneratedAudio
from anansi.core.constants import DEFAULT_TTS_CODES

logger = logging.getLogger(__name__)
MAX_RETRIES = 2

OUTPUT_DIR = Path(os.getenv("AUDIO_OUTPUT_DIR", "/tmp"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_tts_client() -> texttospeech.TextToSpeechClient:
    """
    Returns a Google TTS client.
    Requires GOOGLE_APPLICATION_CREDENTIALS env variable to be set.
    """
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise RuntimeError("Environment variable GOOGLE_APPLICATION_CREDENTIALS is not set")
    return texttospeech.TextToSpeechClient()


async def synthesize_speech(text: str, language_code: str) -> bytes:
    """
    Asynchronously calls Google TTS to synthesize speech using an executor.
    Returns audio content as bytes.
    """
    loop = asyncio.get_running_loop()

    def sync_call():
        client = get_tts_client()
        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        for attempt in range(MAX_RETRIES):
            try:
                response = client.synthesize_speech(
                    input=input_text, voice=voice, audio_config=audio_config
                )
                return response.audio_content
            except GoogleAPIError as e:
                logger.warning(f"TTS attempt {attempt+1} failed for language {language_code}: {e}")
                if attempt < MAX_RETRIES - 1:
                    import time; time.sleep(1)
        raise RuntimeError(f"TTS generation failed after {MAX_RETRIES} attempts for language {language_code}")

    return await loop.run_in_executor(None, sync_call)


async def generate_panel_audio(
    scripts: List[PanelScript], country: str
) -> List[GeneratedAudio]:
    """
    Generate panel-level audio for each panel script.
    Returns list of GeneratedAudio objects with panel_number and local file path.
    """
    language_code = DEFAULT_TTS_CODES.get(country.lower(), "en-US")
    outputs: List[GeneratedAudio] = []

    async def _generate(panel: PanelScript, idx: int) -> GeneratedAudio:
        try:
            audio_bytes = await synthesize_speech(panel.narration, language_code)
            file_path = OUTPUT_DIR / f"panel_{idx+1}.mp3"
            with open(file_path, "wb") as f:
                f.write(audio_bytes)
            return GeneratedAudio(panel_number=idx + 1, url=str(file_path))
        except Exception as e:
            logger.error(f"Failed to generate audio for panel {idx+1}: {e}")
            return GeneratedAudio(panel_number=idx + 1, url="", error=str(e))

    tasks = [_generate(s, i) for i, s in enumerate(scripts)]
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
        audio_bytes = await synthesize_speech(full_text, language_code)
        file_path = OUTPUT_DIR / "full_narration.mp3"
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
        return GeneratedAudio(panel_number=0, url=str(file_path))
    except Exception as e:
        logger.error(f"Failed to generate full narration: {e}")
        return GeneratedAudio(panel_number=0, url="", error=str(e))