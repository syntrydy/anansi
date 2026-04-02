import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from anansi.core.models.script import PanelScript
from anansi.agent.nodes.cartoon import generate_cartoon_panels
from anansi.agent.nodes.narrator import generate_panel_audio, generate_full_narration

# -----------------------------
# Fixture for PanelScript
# -----------------------------
@pytest.fixture
def panel_scripts():
    return [
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
        PanelScript(
            panel_id="3",
            caption="Resolution",
            dialogue="All good",
            prompt="Resolution prompt",
            narration="The end"
        )
    ]

# -----------------------------
# Node 4: Cartoon Generator
# -----------------------------
@pytest.mark.asyncio
@patch("anansi.agent.nodes.cartoon.gather_context")
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_generate_cartoon_panels(
    mock_get, mock_post, mock_gather, panel_scripts, monkeypatch
):
    monkeypatch.setenv("BFL_API_KEY", "test-key")
    class DummyContext:
        visual_cues = ["tree", "river"]
        avoids = ["snow"]
    mock_gather.return_value = DummyContext()
    mock_post.return_value.json = MagicMock(
        return_value={"data": {"image_url": "https://fake.image/url"}}
    )
    mock_post.return_value.raise_for_status = MagicMock()
    mock_get.return_value.json = MagicMock(return_value={})
    mock_get.return_value.raise_for_status = MagicMock()

    images = await generate_cartoon_panels(panel_scripts, country="Kenya", audience="kid")
    assert len(images) == 3
    for img in images:
        assert img.url.startswith("https://fake.image")
        assert img.panel_number in (1, 2, 3)

# -----------------------------
# Node 6: TTS (Narrator)
# -----------------------------
@pytest.mark.asyncio
@patch("anansi.agent.nodes.narrator.synthesize_speech", new_callable=AsyncMock)
async def test_generate_panel_audio(mock_synth, panel_scripts):
    mock_synth.return_value = b"FAKE_AUDIO_BYTES"
    outputs = await generate_panel_audio(panel_scripts, country="Kenya")
    assert len(outputs) == 3
    for out in outputs:
        assert out.audio_url.endswith(".mp3")

@pytest.mark.asyncio
@patch("anansi.agent.nodes.narrator.synthesize_speech", new_callable=AsyncMock)
async def test_generate_full_narration(mock_synth, panel_scripts):
    mock_synth.return_value = b"FAKE_AUDIO_BYTES"
    output = await generate_full_narration(panel_scripts, country="Kenya")
    assert output.audio_url.endswith(".mp3")