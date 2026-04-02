from anansi.core.models import Scene, AnansiState


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
        sid = str(i + 1)
        scenes.append(
            Scene(
                scene_id=sid,
                title=f"Concept {sid}",
                description=f"Illustrate concept: {concept.strip()}",
            )
        )
    return scenes