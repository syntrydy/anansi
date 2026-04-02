"""
Node 5 — Assemble final teaching package (panels + teacher guide).
"""

from typing import Any

from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.output import OutputPackage, PanelOutput
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
    Merge scripts, media, and ``safety_results`` from state into ``PanelOutput`` rows.
    """
    safety_results = state.get("safety_results") or []
    safety_by_pn: dict[int, dict[str, Any]] = {
        int(r["panel_number"]): r for r in safety_results
    }
    audience = state.get("audience", "general")

    by_img = {img.panel_number: img for img in images}
    by_aud = {aud.panel_number: aud for aud in audios}

    panels: list[PanelOutput] = []
    for script in panel_scripts:
        pn = script.panel_number
        sr = safety_by_pn.get(
            pn, {"panel_number": pn, "safe": True, "reason": None}
        )
        img = by_img.get(pn)
        aud = by_aud.get(pn)
        image_url = (img.url if img else "") or ""
        audio_url = (aud.audio_url if aud else "") or ""
        panels.append(
            PanelOutput(
                panel_number=pn,
                panel_id=script.panel_id,
                caption=script.caption,
                dialogue=script.dialogue,
                narration=script.narration,
                image_url=image_url,
                audio_url=audio_url,
                audio_error=aud.error if aud else None,
                safe=bool(sr.get("safe", True)),
                safety_reason=sr.get("reason"),
            )
        )

    guide_lines = [
        f"# Teacher Guide: {state['topic']}",
        f"- Language: {state['language']}",
        f"- Audience: {audience}",
        f"- Panels: {len(panel_scripts)}",
        "",
        "## Panels overview",
    ]
    for p in panels:
        mark = "" if p.safe else "⚠️ "
        guide_lines.append(
            f"- {mark}Panel {p.panel_number}: "
            f"{p.caption[:120]}{'…' if len(p.caption) > 120 else ''}"
        )
    teacher_guide = "\n".join(guide_lines)

    return OutputPackage(
        scenes=scenes,
        images=images,
        audios=audios,
        panels=panels,
        safety_results=list(safety_results),
        teacher_guide=teacher_guide,
    )
