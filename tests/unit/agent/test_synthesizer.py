"""Unit tests for Node 5 (synthesizer)."""

from anansi.agent.nodes.synthesizer import build_output_package, render_teacher_guide
from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.script import PanelScript
from anansi.core.models.state import initialize_state
from anansi.core.models.storyboard import Scene


def test_render_teacher_guide_includes_topic() -> None:
    state = initialize_state(
        {
            "topic": "Water cycle",
            "country": "Nigeria",
            "grade": 4,
            "language": "English",
            "extra_context": {},
        }
    )
    scripts = [
        PanelScript(
            panel_number=1,
            caption="Evaporation from the lagoon",
            dialogue="Discuss",
            prompt="p",
            narration="n",
        )
    ]
    scenes = [Scene(panel_number=1, description="Beat 1")]
    text = render_teacher_guide(state, scripts, scenes)
    assert "Water cycle" in text
    assert "Nigeria" in text
    assert "Panel 1" in text


def test_build_output_package_merges_by_panel_number() -> None:
    state = initialize_state(
        {
            "topic": "T",
            "country": "Kenya",
            "grade": 5,
            "language": "English",
            "extra_context": {},
        }
    )
    scenes = [Scene(panel_number=1, description="d")]
    scripts = [
        PanelScript(
            panel_number=1,
            caption="c",
            dialogue="d",
            prompt="p",
            narration="n",
        )
    ]
    images = [
        GeneratedImage(
            panel_number=1,
            url="https://img.example/1.png",
            caption="c",
            dialogue="d",
            narration="n",
        )
    ]
    audios = [
        GeneratedAudio(panel_number=1, audio_url="/tmp/a.mp3", duration_seconds=1.0)
    ]
    pkg = build_output_package(state, scenes, scripts, images, audios)
    assert len(pkg.panels) == 1
    assert pkg.panels[0].image_url == "https://img.example/1.png"
    assert pkg.panels[0].audio_url == "/tmp/a.mp3"
    assert pkg.teacher_guide
