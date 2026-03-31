from anansi.core.models.script import PanelScript
from anansi.core.models.state import AnansiState

def synthesize_output(state: AnansiState, panel_scripts: list[PanelScript], images: list[str]) -> dict:
    """
    Node 5 - Synthesizer
    Assembles all generated assets into a teaching package.

    Returns:
        dict with keys: 'scripts', 'images', 'teacher_guide'
    """
    return {
        "scripts": [p.dict() for p in panel_scripts],
        "images": images,
        "teacher_guide": f"Guide for {state.topic} in {state.language}"
    }