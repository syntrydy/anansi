"""Node 5 — assemble final teaching package from pipeline artifacts."""

from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.output import OutputPackage
from anansi.core.models.script import PanelScript
from anansi.core.models.state import AnansiState
from anansi.core.models.storyboard import Scene


def synthesize_output(
    state: AnansiState,
    panel_scripts: list[PanelScript],
    images: list[GeneratedImage],
    audios: list[GeneratedAudio],
    scenes: list[Scene],
) -> OutputPackage:
    """
    Assemble scripts, images, audio, and scenes into one output package.

    Args:
        state: Graph state (topic / language for the teacher guide).
        panel_scripts: Generated panel scripts (retained for future use).
        images: Generated panel images.
        audios: Generated narration clips.
        scenes: Storyboard scenes from the concept node.
    """
    teacher_guide = (
        f"Guide for {state['topic']} in {state['language']} "
        f"({len(panel_scripts)} panels)"
    )
    return OutputPackage(
        scenes=scenes,
        audios=audios,
        images=images,
        teacher_guide=teacher_guide,
    )
