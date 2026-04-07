import hashlib
from collections.abc import Callable
from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from anansi.agent.nodes.cartoon import generate_cartoon_panels
from anansi.agent.nodes.concept import analyze_concept
from anansi.agent.nodes.localizer import gather_context
from anansi.agent.nodes.narrator import generate_panel_audio
from anansi.agent.nodes.scriptor import write_script
from anansi.agent.nodes.synthesizer import synthesize_output
from anansi.agent.safety import run_safety_check
from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.cartoon import GeneratedImage
from anansi.core.models.context import CountryData
from anansi.core.models.script import PanelScript
from anansi.core.models.state import AnansiState
from anansi.core.models.storyboard import Scene
from anansi.observability.langfuse_pipeline import (
    flush_langfuse,
    reset_pipeline_trace_state,
    set_pipeline_trace_state,
    trace_pipeline_node,
)

# ----------------------
# Node implementations (async for LangGraph streaming / ainvoke)
# ----------------------


async def node_concept(state: AnansiState) -> dict[str, Any]:
    with trace_pipeline_node("concept", state):
        scenes = await analyze_concept(state)
        return {"scenes": [s.model_dump() for s in scenes]}


async def node_localizer(state: AnansiState) -> dict[str, Any]:
    with trace_pipeline_node("localizer", state):
        ctx = await gather_context(state["country"])
        return {"context_pack": ctx.model_dump()}


async def node_scriptor(state: AnansiState) -> dict[str, Any]:
    with trace_pipeline_node("scriptor", state):
        scenes = [Scene(**s) for s in state["scenes"]]
        context = CountryData.model_validate(state.get("context_pack", {}))
        scripts = await write_script(state, scenes, context)
        return {"panel_scripts": [p.model_dump() for p in scripts]}


async def node_safety(state: AnansiState) -> dict[str, Any]:
    token = set_pipeline_trace_state(state)
    try:
        with trace_pipeline_node("safety", state):
            scripts = [PanelScript(**p) for p in state.get("panel_scripts", [])]
            audience = state.get("audience", "general")
            results = await run_safety_check(scripts, state, audience=audience)
            return {"safety_results": results}
    finally:
        reset_pipeline_trace_state(token)


async def node_cartoon(state: AnansiState) -> dict[str, Any]:
    token = set_pipeline_trace_state(state)
    try:
        with trace_pipeline_node("cartoon", state):
            scripts = [PanelScript(**p) for p in state["panel_scripts"]]
            unsafe_pns = {
                int(r["panel_number"])
                for r in state.get("safety_results", [])
                if not r.get("safe", True)
            }
            audience = state.get("audience", "general")
            context_pack = state.get("context_pack") or {}

            seed: int | None = None
            topic = state.get("topic", "")
            country_val = state.get("country", "")
            if topic or country_val:
                seed = int(hashlib.md5((topic + "|" + country_val).encode()).hexdigest(), 16) & 0x7FFFFFFF

            images = await generate_cartoon_panels(
                scripts,
                country=state["country"],
                audience=audience,
                language=state["language"],
                aspect_ratio=state.get("aspect_ratio", "1:1"),
                skip_panel_numbers=unsafe_pns,
                context_pack=context_pack,
                seed=seed,
            )
            return {"images": [img.model_dump() for img in images]}
    finally:
        reset_pipeline_trace_state(token)


async def node_narrator(state: AnansiState) -> dict[str, Any]:
    token = set_pipeline_trace_state(state)
    try:
        with trace_pipeline_node("narrator", state):
            scripts = [PanelScript(**p) for p in state["panel_scripts"]]
            unsafe_pns = {
                int(r["panel_number"])
                for r in state.get("safety_results", [])
                if not r.get("safe", True)
            }
            audios = await generate_panel_audio(
                scripts, country=state["country"], skip_panel_numbers=unsafe_pns
            )
            return {"audios": [a.model_dump() for a in audios]}
    finally:
        reset_pipeline_trace_state(token)


async def node_synthesizer(state: AnansiState) -> dict[str, Any]:
    with trace_pipeline_node("synthesizer", state):
        scenes = [Scene(**s) for s in state["scenes"]]
        scripts = [PanelScript(**p) for p in state["panel_scripts"]]
        images = [GeneratedImage(**i) for i in state.get("images", [])]
        audios = [GeneratedAudio(**a) for a in state.get("audios", [])]
        package = await synthesize_output(state, scripts, images, audios, scenes)
        return {"package": package.model_dump(mode="json")}


# ----------------------
# Graph compilation
# ----------------------
def build_graph() -> Any:
    workflow = StateGraph(AnansiState)
    workflow.add_node("concept", node_concept)
    workflow.add_node("localizer", node_localizer)
    workflow.add_node("scriptor", node_scriptor)
    workflow.add_node("safety", node_safety)
    workflow.add_node("cartoon", node_cartoon)
    workflow.add_node("narrator", node_narrator)
    workflow.add_node("synthesizer", node_synthesizer)

    workflow.add_edge(START, "concept")
    workflow.add_edge("concept", "localizer")
    workflow.add_edge("localizer", "scriptor")
    workflow.add_edge("scriptor", "safety")
    workflow.add_edge("safety", "cartoon")
    workflow.add_edge("safety", "narrator")
    workflow.add_edge("cartoon", "synthesizer")
    workflow.add_edge("narrator", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()


async def run_pipeline(
    initial: AnansiState,
    *,
    on_state_update: Callable[[AnansiState], None] | None = None,
) -> AnansiState:
    """
    Execute the lesson graph. When ``on_state_update`` is set, stream full state
    after each step (``stream_mode="values"``) so the UI can refresh progressively.
    """
    graph = build_graph()
    try:
        if on_state_update is None:
            return cast(AnansiState, await graph.ainvoke(initial))
        final: AnansiState | None = None
        async for snapshot in graph.astream(initial, stream_mode="values"):
            typed = cast(AnansiState, snapshot)
            final = typed
            on_state_update(typed)
        return final if final is not None else initial
    finally:
        flush_langfuse()
