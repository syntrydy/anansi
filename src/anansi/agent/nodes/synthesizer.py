"""
Node 5 — Assemble final teaching package (panels + teacher guide).
"""

from __future__ import annotations

import logging
from typing import Any

from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.output import OutputPackage, PanelOutput
from anansi.core.models.script import PanelScript
from anansi.core.models.state import AnansiState
from anansi.core.models.storyboard import Scene
from anansi.infrastructure.llm import get_llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Teacher guide prompt
# ---------------------------------------------------------------------------
_GUIDE_SYSTEM = """\
You are an experienced African primary-school teacher writing a lesson guide.
Use clear, practical language suitable for classroom teachers.

Structure your response with EXACTLY these three markdown headings:

## Vocabulary
List 5-8 key terms from the lesson with a brief child-friendly definition each.
Format: **term** — definition

## Comprehension Questions
Provide 4-5 questions that check understanding of the lesson content.
Mix recall and reasoning questions. Number them 1, 2, 3...

## Lesson Plan
Write a brief suggested lesson plan with timing:
- Introduction (5 min)
- Main activity (15 min)
- Discussion (10 min)
- Wrap-up (5 min)
Include how to use the cartoon panels in each phase.
"""


def _guide_user_prompt(
    state: AnansiState,
    panels: list[PanelOutput],
) -> str:
    panels_text = "\n".join(
        f"Panel {p.panel_number}: {p.caption} | Dialogue: {p.dialogue} | Narration: {p.narration}"
        for p in panels
        if p.safe
    )
    return (
        f"Topic: {state['topic']}\n"
        f"Grade: {state['grade']}\n"
        f"Language: {state['language']}\n"
        f"Country: {state['country']}\n\n"
        f"Lesson panel content:\n{panels_text}\n\n"
        "Generate the complete teacher guide with the three sections above."
    )


# ---------------------------------------------------------------------------
# Fallback teacher guide (no LLM)
# ---------------------------------------------------------------------------
def _fallback_guide(
    state: AnansiState,
    panels: list[PanelOutput],
) -> str:
    audience = state.get("audience", "general")
    guide_lines = [
        f"# Teacher Guide: {state['topic']}",
        f"- Language: {state['language']}",
        f"- Audience: {audience}",
        f"- Panels: {len(panels)}",
        "",
        "## Panels overview",
    ]
    for p in panels:
        mark = "" if p.safe else "⚠️ "
        guide_lines.append(
            f"- {mark}Panel {p.panel_number}: "
            f"{p.caption[:120]}{'…' if len(p.caption) > 120 else ''}"
        )
    return "\n".join(guide_lines)


# ---------------------------------------------------------------------------
# Async teacher guide generation
# ---------------------------------------------------------------------------
async def _generate_teacher_guide(
    state: AnansiState,
    panels: list[PanelOutput],
) -> str:
    llm = get_llm(capability="standard")
    if llm is None:
        return _fallback_guide(state, panels)
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from anansi.infrastructure.observability import get_langchain_callback_handler

        messages = [
            SystemMessage(content=_GUIDE_SYSTEM),
            HumanMessage(content=_guide_user_prompt(state, panels)),
        ]
        cb = get_langchain_callback_handler()
        config = {"callbacks": [cb]} if cb else {}
        resp = await llm.ainvoke(messages, config=config)
        guide = (getattr(resp, "content", None) or str(resp)).strip()
        header = f"# Teacher Guide: {state['topic']}\n\n"
        return header + guide
    except Exception as exc:
        logger.warning("N5: Teacher guide LLM failed (%s) — using fallback", exc)
        return _fallback_guide(state, panels)


# ---------------------------------------------------------------------------
# Main — async to support the guide LLM call
# ---------------------------------------------------------------------------
async def synthesize_output(
    state: AnansiState,
    panel_scripts: list[PanelScript],
    images: list[GeneratedImage],
    audios: list[GeneratedAudio],
    scenes: list[Scene],
) -> OutputPackage:
    """
    Merge scripts, media, and ``safety_results`` from state into ``PanelOutput`` rows,
    then generate a rich teacher guide (vocabulary, comprehension questions, lesson
    plan) via Claude Haiku.
    """
    safety_results = state.get("safety_results") or []
    safety_by_pn: dict[int, dict[str, Any]] = {
        int(r["panel_number"]): r for r in safety_results
    }

    # panel_number=0 holds the single comic-strip image (from cartoon node).
    storyboard_img = next((img for img in images if img.panel_number == 0), None)
    storyboard_image_url = storyboard_img.url if storyboard_img else ""

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

    teacher_guide = await _generate_teacher_guide(state, panels)

    return OutputPackage(
        storyboard_image_url=storyboard_image_url,
        scenes=scenes,
        images=images,
        audios=audios,
        panels=panels,
        safety_results=list(safety_results),
        teacher_guide=teacher_guide,
    )
