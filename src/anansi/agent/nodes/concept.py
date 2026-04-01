from anansi.core.models.storyboard import Scene
from anansi.core.models.state import AnansiState


def analyze_concept(state: AnansiState) -> list[Scene]:
    """
    Node 1 - Concept Analyzer
    Analyzes the teacher input topic and breaks it into storyboard scenes.

    Args:
        state: AnansiState containing topic, grade, language, extra context.

    Returns:
        List of Scene objects.
    """
    scenes = []
    topics = state["topic"].split(",")  # split comma-separated topics
    for i, concept in enumerate(topics):
        scenes.append(Scene(
            panel_number=i + 1,
            description=f"Illustrate concept: {concept.strip()}"
        ))
    return scenes