"""
Node 3 — Scriptor.

Generates panel captions, dialogue, FLUX image prompts, and TTS narration text
using Claude Haiku with structured output. Falls back to template-based
generation when no LLM is available.
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from anansi.core.models.context import CountryData
from anansi.core.models.script import PanelScript
from anansi.core.models.state import AnansiState
from anansi.core.models.storyboard import Scene
from anansi.infrastructure.llm import get_cerebras_llm, get_llm


# ---------------------------------------------------------------------------
# Simple internal schema for LLM structured output
# ---------------------------------------------------------------------------
class _PanelScriptSchema(BaseModel):
    panel_number: int = Field(description="1-based panel index")
    caption: str = Field(description="Max 20 words, child-friendly summary")
    dialogue: str = Field(description="Character dialogue as 'Name: line.  Name2: line.'")
    prompt: str = Field(description="FLUX image generation prompt with cultural cues and avoids")
    narration: str = Field(description="1-3 sentences of teacher narration for TTS")


class _ScriptOutputSchema(BaseModel):
    panels: list[_PanelScriptSchema] = Field(description="One per scene")
    full_narration: str = Field(default="", description="All narration texts joined")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are a children's educational cartoon scriptwriter specialising in African
K-12 classrooms. You receive a storyboard and a cultural context pack and
produce panel scripts.

For EACH panel output exactly:
- caption: max 20 words, child-friendly, in {language}. Summarises what happens.
- dialogue: a single string with character names and spoken lines formatted as
  "CharacterName: spoken line.  OtherCharacter: response."
  Replace placeholder names like [CHILD_NAME_1] with culturally accurate names
  from the context pack names list.  Keep lines short and age-appropriate.
- prompt: a detailed FLUX.1 image generation prompt.
  * Include explicit cultural visual cues from the art style and cultural elements.
  * Replace placeholder names/places with names from the context pack.
  * For PANEL 1 ONLY: start the prompt with a full character description
    (skin tone, clothing, hairstyle, age) that will be reused in later panels
    for visual consistency. Begin with "Characters: [description]. Scene: ..."
  * For panels 2+: begin with "Continuing the same characters. Scene: ..."
  * End every prompt with exactly: "Do not show: {avoids_list}"
- narration: 1-3 calm teacher narration sentences for text-to-speech delivery.
  Written in {language}. Should explain the key concept clearly for the grade level.

full_narration is all narration texts joined with two newlines.

Cultural accuracy is critical: use names, places, foods, and clothing from the
context pack. Grade level is {grade} — adjust vocabulary accordingly.
"""


def _format_system(state: AnansiState, context: CountryData) -> str:
    avoids = ", ".join(context.avoids) if context.avoids else "none"
    return _SYSTEM_PROMPT.format(
        language=state.get("language", "English"),
        avoids_list=avoids,
        grade=state.get("grade", 3),
    )


def _build_user_prompt(
    state: AnansiState,
    scenes: list[Scene],
    context: CountryData,
) -> str:
    avoids = ", ".join(context.avoids) if context.avoids else "none"
    scenes_json = json.dumps(
        [
            {
                "panel_number": s.panel_number or (i + 1),
                "scene_id": s.scene_id,
                "title": s.title,
                "description": s.description,
                "key_concept": s.key_concept,
                "characters": s.characters,
                "setting": s.setting,
            }
            for i, s in enumerate(scenes)
        ],
        ensure_ascii=False,
        indent=2,
    )
    names_sample = []
    if context.names:
        names_sample = context.names.male[:3] + context.names.female[:3]

    context_summary = (
        f"Country: {context.country}\n"
        f"Suggested character names: {', '.join(names_sample)}\n"
        f"Cities/places: {', '.join(context.places.cities[:4])}\n"
        f"Cultural elements:\n"
        f"  Food: {', '.join(context.culture.food[:4])}\n"
        f"  Clothing: {', '.join(context.culture.clothing[:3])}\n"
        f"  Housing: {', '.join(context.culture.housing[:3])}\n"
        f"  Animals: {', '.join(context.culture.animals[:3])}\n"
        f"Art style cues: {context.art_style_cues}\n"
        f"Avoids: {avoids}"
    )
    return (
        f"Storyboard scenes (JSON):\n{scenes_json}\n\n"
        f"Cultural context:\n{context_summary}\n\n"
        "Produce a ScriptOutput with exactly one PanelScript per scene above."
    )


# ---------------------------------------------------------------------------
# Fallback when LLM is unavailable
# ---------------------------------------------------------------------------
def _fallback_scripts(
    state: AnansiState,
    scenes: list[Scene],
    context: CountryData,
) -> list[PanelScript]:
    avoids_str = ", ".join(context.avoids) if context.avoids else ""
    food = context.culture.food[:2] if context.culture else []
    cities = context.places.cities[:2] if context.places else []
    return [
        PanelScript(
            panel_number=i + 1,
            panel_id=scene.scene_id,
            caption=f"{scene.description}, featuring {', '.join(food)}",
            dialogue=f"Teacher explains {state['topic']} in {state['language']}",
            narration=f"Include local elements like {', '.join(cities)}",
            prompt=(
                f"{scene.description}, {context.art_style_cues}."
                f" Do not show: {avoids_str}"
            ),
        )
        for i, scene in enumerate(scenes)
    ]


# ---------------------------------------------------------------------------
# Main — async, called by graph.py node_scriptor
# ---------------------------------------------------------------------------
async def write_script(
    state: AnansiState,
    scenes: list[Scene],
    context: CountryData,
) -> list[PanelScript]:
    """
    Node 3 - Scriptor.

    Returns a list of PanelScript objects with LLM-generated content:
    captions, culturally-accurate dialogue, FLUX image prompts, and TTS
    narration. Falls back to templates when the LLM is unavailable.
    """
    llm = get_llm(capability="standard")
    if llm is None:
        logger.info("N3: LLM unavailable — using fallback script generation")
        return _fallback_scripts(state, scenes, context)

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from anansi.infrastructure.observability import get_langchain_callback_handler

        structured_llm = llm.with_structured_output(_ScriptOutputSchema)
        messages = [
            SystemMessage(content=_format_system(state, context)),
            HumanMessage(content=_build_user_prompt(state, scenes, context)),
        ]
        cb = get_langchain_callback_handler()
        config = {"callbacks": [cb]} if cb else {}

        result: _ScriptOutputSchema = await structured_llm.ainvoke(  # type: ignore[assignment]
            messages, config=config
        )

        # Convert to PanelScript and set panel_id from matching scene
        panels: list[PanelScript] = []
        for i, p in enumerate(result.panels):
            panel_id = scenes[i].scene_id if i < len(scenes) else str(i + 1)
            panels.append(
                PanelScript(
                    panel_number=p.panel_number,
                    panel_id=panel_id,
                    caption=p.caption,
                    dialogue=p.dialogue,
                    prompt=p.prompt,
                    narration=p.narration,
                )
            )

        logger.info("N3: Generated %s panel scripts", len(panels))
        return panels

    except Exception as exc:
        if "529" in str(exc) or "overloaded" in str(exc).lower():
            logger.warning("N3: Anthropic overloaded (%s) — retrying with Cerebras", exc)
            cerebras_llm = get_cerebras_llm(capability="standard")
            if cerebras_llm is not None:
                try:
                    from langchain_core.messages import HumanMessage, SystemMessage

                    structured_llm = cerebras_llm.with_structured_output(_ScriptOutputSchema)
                    messages = [
                        SystemMessage(content=_format_system(state, context)),
                        HumanMessage(content=_build_user_prompt(state, scenes, context)),
                    ]
                    result: _ScriptOutputSchema = await structured_llm.ainvoke(messages)  # type: ignore[assignment]
                    panels: list[PanelScript] = []
                    for i, p in enumerate(result.panels):
                        panel_id = scenes[i].scene_id if i < len(scenes) else str(i + 1)
                        panels.append(
                            PanelScript(
                                panel_number=p.panel_number,
                                panel_id=panel_id,
                                caption=p.caption,
                                dialogue=p.dialogue,
                                prompt=p.prompt,
                                narration=p.narration,
                            )
                        )
                    logger.info("N3: Cerebras generated %s panel scripts", len(panels))
                    return panels
                except Exception as cerebras_exc:
                    logger.warning("N3: Cerebras fallback failed (%s) — falling back to template", cerebras_exc)
        else:
            logger.warning("N3: LLM call failed (%s) — falling back to template", exc)
        return _fallback_scripts(state, scenes, context)
