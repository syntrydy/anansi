"""
Node 5 — Synthesizer: merge scripts, images, audio; build teacher guide.
"""

from __future__ import annotations

from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.output import OutputPackage, PanelOutput
from anansi.core.models.script import PanelScript
from anansi.core.models.state import AnansiState
from anansi.core.models.storyboard import Scene


def render_teacher_guide(
    state: AnansiState,
    scripts: list[PanelScript],
    scenes: list[Scene],
) -> str:
    """Structured markdown teacher guide (deterministic; no LLM)."""
    topic = state["topic"]
    grade = state["grade"]
    country = state["country"]
    language = state["language"]
    lines = [
        f"# Teacher guide: {topic}",
        "",
        "## Class context",
        f"- **Grade:** {grade}",
        f"- **Country / culture pack:** {country}",
        f"- **Instruction language:** {language}",
        f"- **Storyboard beats:** {len(scenes)}",
        "",
        "## Learning objectives",
        f"- Students connect **{topic}** to everyday examples from **{country}**.",
        "- Students can retell the panel sequence in their own words.",
        "",
        "## Vocabulary & phrases",
    ]
    for p in scripts:
        lines.append(
            f"- **Panel {p.panel_number}:** {p.caption[:120]}{'…' if len(p.caption) > 120 else ''}"
        )
    lines.extend(
        [
            "",
            "## Comprehension questions",
            f"- What is the main idea of **{topic}** in this lesson?",
            "- Which panel best shows the concept in action? Why?",
            "- Name one local place or cultural detail shown in the story.",
            "",
            "## Lesson outline (suggested)",
            "1. **Hook (5 min):** Show panel 1; ask what students notice.",
            "2. **Teach (10 min):** Walk panels in order; use narration audio if available.",
            "3. **Discuss (10 min):** Use comprehension questions above.",
            "4. **Check (5 min):** Quick oral recap or draw-your-own-panel exit ticket.",
            "",
            "## Printable / projector use",
            "- Use merged panel list from the app for A4 print or projector view.",
            "- Audio files are per-panel when generation succeeds.",
        ]
    )
    return "\n".join(lines)


def build_output_package(
    state: AnansiState,
    scenes: list[Scene],
    scripts: list[PanelScript],
    images: list[GeneratedImage],
    audios: list[GeneratedAudio],
) -> OutputPackage:
    """Align images and audio to scripts by `panel_number`; build `PanelOutput` rows."""
    by_img = {g.panel_number: g for g in images}
    by_aud = {a.panel_number: a for a in audios if a.panel_number > 0}

    panels: list[PanelOutput] = []
    for s in scripts:
        pn = s.panel_number
        img = by_img.get(pn)
        aud = by_aud.get(pn)
        panels.append(
            PanelOutput(
                panel_number=pn,
                caption=s.caption,
                dialogue=s.dialogue,
                narration=s.narration,
                image_url=img.url if img else "",
                audio_url=aud.audio_url if aud else "",
                audio_error=aud.error if aud else None,
            )
        )

    guide = render_teacher_guide(state, scripts, scenes)
    return OutputPackage(
        scenes=scenes,
        images=images,
        audios=sorted(audios, key=lambda a: a.panel_number),
        panels=panels,
        teacher_guide=guide,
    )


def synthesize_output(
    state: AnansiState,
    panel_scripts: list[PanelScript],
    images: list[GeneratedImage],
    audios: list[GeneratedAudio],
    scenes: list[Scene],
) -> OutputPackage:
    """Public API for Node 5 (graph node wraps this)."""
    return build_output_package(state, scenes, panel_scripts, images, audios)
