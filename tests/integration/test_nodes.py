import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from anansi.core.models.script import PanelScript
from anansi.agent.nodes.cartoon import generate_cartoon_panels
from anansi.agent.nodes.narrator import generate_panel_audio, generate_full_narration

@pytest.mark.asyncio
@patch("anansi.agent.nodes.cartoon.gather_context")
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("anansi.agent.nodes.narrator.synthesize_speech", new_callable=AsyncMock)
async def test_end_to_end_cartoon_and_tts(
    mock_synth, mock_get, mock_post, mock_gather, monkeypatch
):
    monkeypatch.setenv("BFL_API_KEY", "test-key")
    # Sample panel scripts
    scripts = [
        PanelScript(
            panel_id="1",
            caption="Intro",
            dialogue="Hello world",
            prompt="Intro prompt",
            narration="Welcome to the story"
        ),
        PanelScript(
            panel_id="2",
            caption="Conflict",
            dialogue="Uh oh",
            prompt="Conflict prompt",
            narration="Something went wrong"
        ),
    ]

    # Mock cartoon context and API
    class DummyContext:
        visual_cues = ["tree", "river"]
        avoids = ["snow"]
    mock_gather.return_value = DummyContext()
    mock_post.return_value.json = MagicMock(
        return_value={"data": {"task_id": "123"}}
    )
    mock_post.return_value.raise_for_status = MagicMock()
    mock_get.return_value.json = MagicMock(
        return_value={
            "data": {
                "status": "SUCCESS",
                "result": {"sample": "https://fake.image/url"},
            }
        }
    )
    mock_get.return_value.raise_for_status = MagicMock()

    # Mock TTS
    mock_synth.return_value = b"FAKE_AUDIO_BYTES"

    # Generate cartoons
    images = await generate_cartoon_panels(scripts, country="Kenya", audience="kid")
    assert len(images) == 2
    for img in images:
        assert img.url.startswith("https://fake.image")

    # Generate panel-level audio
    panel_audio = await generate_panel_audio(scripts, country="Kenya")
    assert len(panel_audio) == 2
    for aud in panel_audio:
        assert aud.audio_url.endswith(".mp3")

    # Generate full narration
    full_audio = await generate_full_narration(scripts, country="Kenya")
    assert full_audio.audio_url.endswith(".mp3")