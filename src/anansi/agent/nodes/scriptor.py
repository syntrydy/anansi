from anansi.core.models.script import PanelScript
from anansi.core.models.storyboard import Scene
from anansi.core.models.state import AnansiState
from anansi.core.models.context import CountryData

def write_script(state: AnansiState, scenes: list[Scene], context: CountryData) -> list[PanelScript]:
    """
    Node 3 - Scriptor
    Generates captions, dialogue, narration, and image prompts for each scene.

    Args:
        state: AnansiState
        scenes: List of Scene objects
        context: CountryData

    Returns:
        List of PanelScript objects
    """
    panel_scripts = []

    for scene in scenes:
        caption = f"{scene.description}, featuring {', '.join(context.culture.food[:2])}"
        dialogue = f"Teacher explains {state['topic']} in {state['language']}"
        narration = f"Include local elements like {', '.join(context.places.cities[:2])}"
        image_prompt = f"{scene.description}, avoid {', '.join(context.avoids)}"

        panel_scripts.append(PanelScript(
            panel_number=scene.panel_number,
            caption=caption,
            dialogue=dialogue,
            narration=narration,
            prompt=image_prompt
        ))

    return panel_scripts