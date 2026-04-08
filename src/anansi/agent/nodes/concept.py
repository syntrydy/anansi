"""
Node 1 — Concept Analyzer.

Calls Claude Sonnet with structured output to decompose a teaching topic into
4-6 visual scenes that build progressively. Falls back to a simple comma-split
when no LLM is available.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from anansi.core.models.state import AnansiState
from anansi.core.models.storyboard import Scene
from anansi.infrastructure.llm import get_cerebras_llm, get_llm


# ---------------------------------------------------------------------------
# Simple internal schemas for LLM structured output
# (Scene itself has a nested panels: list[PanelScript] that confuses the LLM)
# ---------------------------------------------------------------------------
class _SceneSchema(BaseModel):
    scene_id: str = Field(description="String panel number e.g. '1', '2'")
    title: str = Field(description="Short panel title")
    description: str = Field(description="What happens visually in this panel")
    panel_number: int = Field(description="1-based sequence number")
    key_concept: str = Field(description="One-sentence core learning point")
    characters: list[str] = Field(description="Character placeholders like [CHILD_NAME_1]")
    setting: str = Field(description="Brief location description e.g. 'village market at midday'")


class _StoryboardSchema(BaseModel):
    title: str = Field(description="Lesson title")
    scenes: list[_SceneSchema] = Field(description="exactly 6 sequential visual scenes")
    total_panels: int = Field(description="Must equal len(scenes)")

    @classmethod
    def _parse_scenes(cls, v):
        if isinstance(v, str):
            import json
            import ast
            try:
                return json.loads(v)
            except Exception:
                try:
                    return ast.literal_eval(v)
                except Exception:
                    pass
        return v

    try:
        from pydantic import field_validator
        _scenes_validator = field_validator("scenes", mode="before")(_parse_scenes)
    except ImportError:
        from pydantic import validator
        _scenes_validator = validator("scenes", pre=True, allow_reuse=True)(_parse_scenes)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are an expert curriculum designer specialising in visual storytelling for
African K-12 classrooms. Given a teaching topic, grade level, and language,
decompose the subject into exactly 6 sequential visual panels that build progressively.

Rules:
- Each panel must be describable as a single still image — visual-first.
- Adapt vocabulary and narrative depth to the grade level.
- Use placeholder names in brackets for characters ([CHILD_NAME_1], [CHILD_NAME_2])
  and locations ([LOCAL_RIVER], [LOCAL_MARKET], [LOCAL_CITY]). Do NOT use real
  names or places — those are filled in later from cultural context.
- key_concept is one sentence: the core learning point of this panel.
- setting is a brief phrase like "village market at midday" or "river bank at sunrise".
- The final panel should summarise or test understanding.
- scene_id must be the string representation of the panel number (e.g. "1", "2").
- total_panels must equal len(scenes) and must be 6.
"""


def _user_prompt(state: AnansiState) -> str:
    extra = state.get("extra_context") or {}
    extra_str = f"\nExtra context from teacher: {extra}" if extra else ""
    return (
        f"Topic: {state['topic']}\n"
        f"Grade: {state['grade']}\n"
        f"Language: {state['language']}\n"
        f"Country: {state['country']}{extra_str}\n\n"
        "Produce a StoryboardOutput with exactly 6 scenes."
    )


# ---------------------------------------------------------------------------
# Fallback when LLM is unavailable
# ---------------------------------------------------------------------------
def _fallback_scenes(state: AnansiState) -> list[Scene]:
    topics = state["topic"].split(",")
    return [
        Scene(
            scene_id=str(i + 1),
            title=f"Concept {i + 1}",
            description=f"Illustrate concept: {concept.strip()}",
            panel_number=i + 1,
            key_concept=concept.strip(),
        )
        for i, concept in enumerate(topics)
    ]


# ---------------------------------------------------------------------------
# Main — async, called by graph.py node_concept
# ---------------------------------------------------------------------------
async def analyze_concept(state: AnansiState) -> list[Scene]:
    """
    Node 1 - Concept Analyzer.

    Returns a list of Scene objects. Uses Claude Sonnet with structured output
    for proper pedagogical scene decomposition. Falls back to a simple
    comma-split of the topic string when the LLM is unavailable.
    """
    llm = get_llm(capability="reasoning")
    if llm is None:
        logger.info("N1: LLM unavailable — using fallback scene generation")
        return _fallback_scenes(state)

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from anansi.infrastructure.observability import get_langchain_callback_handler

        structured_llm = llm.with_structured_output(_StoryboardSchema)
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=_user_prompt(state)),
        ]
        cb = get_langchain_callback_handler()
        config = {"callbacks": [cb]} if cb else {}

        result: _StoryboardSchema = await structured_llm.ainvoke(  # type: ignore[assignment]
            messages, config=config
        )

        scenes: list[Scene] = []
        for i, s in enumerate(result.scenes):
            scenes.append(
                Scene(
                    scene_id=s.scene_id or str(i + 1),
                    title=s.title or f"Panel {i + 1}",
                    description=s.description,
                    panel_number=s.panel_number or (i + 1),
                    key_concept=s.key_concept,
                    characters=s.characters,
                    setting=s.setting,
                )
            )

        logger.info("N1: Generated %s scenes for topic %r", len(scenes), state["topic"])
        return scenes

    except Exception as exc:
        if "529" in str(exc) or "overloaded" in str(exc).lower():
            logger.warning("N1: Anthropic overloaded (%s) — retrying with Cerebras", exc)
            cerebras_llm = get_cerebras_llm(capability="reasoning")
            if cerebras_llm is not None:
                try:
                    from langchain_core.messages import HumanMessage, SystemMessage

                    structured_llm = cerebras_llm.with_structured_output(_StoryboardSchema)
                    messages = [
                        SystemMessage(content=_SYSTEM_PROMPT),
                        HumanMessage(content=_user_prompt(state)),
                    ]
                    result: _StoryboardSchema = await structured_llm.ainvoke(messages)  # type: ignore[assignment]
                    scenes: list[Scene] = []
                    for i, s in enumerate(result.scenes):
                        scenes.append(
                            Scene(
                                scene_id=s.scene_id or str(i + 1),
                                title=s.title or f"Panel {i + 1}",
                                description=s.description,
                                panel_number=s.panel_number or (i + 1),
                                key_concept=s.key_concept,
                                characters=s.characters,
                                setting=s.setting,
                            )
                        )
                    logger.info("N1: Cerebras generated %s scenes for topic %r", len(scenes), state["topic"])
                    return scenes
                except Exception as cerebras_exc:
                    logger.warning("N1: Cerebras fallback failed (%s) — falling back to template", cerebras_exc)
        else:
            logger.warning("N1: LLM call failed (%s) — falling back to template", exc)
        return _fallback_scenes(state)
