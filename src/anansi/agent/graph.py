from typing import Any, cast
from langgraph.graph import END, START, StateGraph
from anansi.agent.nodes.cartoon import generate_cartoon_panels
from anansi.agent.nodes.concept import analyze_concept
from anansi.agent.nodes.localizer import gather_context
from anansi.agent.nodes.narrator import generate_panel_audio
from anansi.agent.nodes.scriptor import write_script
from anansi.agent.nodes.synthesizer import synthesize_output
from anansi.core.models.context import CountryData
from anansi.core.models.state import AnansiState
from anansi.core.models.script import PanelScript
from anansi.core.models.storyboard import Scene
from anansi.core.models.audio import GeneratedAudio
from anansi.core.models.cartoon import GeneratedImage

# ----------------------
# Node implementations
# ----------------------
def node_concept(state: AnansiState) -> dict[str, Any]:
    scenes = analyze_concept(state)
    return {"scenes": [s.model_dump() for s in scenes]}

def node_localizer(state: AnansiState) -> dict[str, Any]:
    ctx = gather_context(state["country"])
    return {"context_pack": ctx.model_dump()}

def node_scriptor(state: AnansiState) -> dict[str, Any]:
    scenes = [Scene(**s) for s in state["scenes"]]
    context = CountryData.model_validate(state.get("context_pack", {}))
    scripts = write_script(state, scenes, context)
    return {"panel_scripts": [p.model_dump() for p in scripts]}

async def node_cartoon(state: AnansiState) -> dict[str, Any]:
    scripts = [PanelScript(**p) for p in state["panel_scripts"]]
    images = await generate_cartoon_panels(scripts, country=state["country"], audience="kid")
    return {"images": [img.model_dump() for img in images]}

async def node_narrator(state: AnansiState) -> dict[str, Any]:
    scripts = [PanelScript(**p) for p in state["panel_scripts"]]
    audios = await generate_panel_audio(scripts, country=state["country"])
    return {"audios": [a.model_dump() for a in audios]}

def node_synthesizer(state: AnansiState) -> dict[str, Any]:
    scenes = [Scene(**s) for s in state["scenes"]]
    scripts = [PanelScript(**p) for p in state["panel_scripts"]]
    images = [GeneratedImage(**i) for i in state.get("images", [])]
    audios = [GeneratedAudio(**a) for a in state.get("audios", [])]
    package = synthesize_output(state, scripts, images, audios, scenes)
    return {"package": package.model_dump(mode="json")}

# ----------------------
# Graph compilation
# ----------------------
def build_graph() -> Any:
    workflow = StateGraph(AnansiState)
    workflow.add_node("concept", node_concept)
    workflow.add_node("localizer", node_localizer)
    workflow.add_node("scriptor", node_scriptor)
    workflow.add_node("cartoon", node_cartoon)
    workflow.add_node("narrator", node_narrator)
    workflow.add_node("synthesizer", node_synthesizer)
    workflow.add_edge(START, "concept")
    workflow.add_edge("concept", "localizer")
    workflow.add_edge("localizer", "scriptor")
    workflow.add_edge("scriptor", "cartoon")
    workflow.add_edge("scriptor", "narrator")
    workflow.add_edge("cartoon", "synthesizer")
    workflow.add_edge("narrator", "synthesizer")
    workflow.add_edge("synthesizer", END)
    return workflow.compile()

async def run_pipeline(initial: AnansiState) -> AnansiState:
    """Run the full async pipeline and return final state."""
    graph = build_graph()
    return cast(AnansiState, await graph.ainvoke(initial))

# ----------------------
# Explicit exports
# ----------------------
__all__ = [
    "build_graph",
    "run_pipeline",
]