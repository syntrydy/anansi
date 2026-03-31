from anansi.core.models.script import PanelScript

def generate_narration(panel_scripts: list[PanelScript]) -> list[str]:
    """
    Node 6 - Narrator
    Generates audio narration URLs for each panel script.

    Returns:
        List of audio file URLs (placeholders)
    """
    return [f"https://placeholder.audio/{p.panel_number}.mp3" for p in panel_scripts]