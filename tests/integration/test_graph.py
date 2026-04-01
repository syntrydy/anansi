"""
Integration tests for the LangGraph teaching pipeline.
"""

from __future__ import annotations

import pytest

from anansi.agent.graph import build_graph, run_pipeline
from anansi.core.models.output import OutputPackage
from anansi.core.models.state import initialize_state


@pytest.mark.asyncio
async def test_full_graph_execution_mock_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end graph with mocked image/TTS APIs (no external keys)."""
    monkeypatch.setenv("ANANSI_MOCK_PIPELINE", "1")

    initial = initialize_state(
        {
            "topic": "Photosynthesis",
            "country": "Kenya",
            "grade": 5,
            "language": "Swahili",
            "extra_context": {},
        }
    )
    graph = build_graph()
    final = await graph.ainvoke(initial)

    assert "package" in final
    pkg_raw = final["package"]
    assert isinstance(pkg_raw, dict)

    pkg = OutputPackage.model_validate(pkg_raw)
    assert pkg.teacher_guide
    assert "# Teacher guide:" in pkg.teacher_guide
    assert pkg.panels
    assert len(pkg.panels) >= 1
    for p in pkg.panels:
        assert p.panel_number >= 1
        assert p.caption
        assert p.image_url
        assert p.audio_url


@pytest.mark.asyncio
async def test_run_pipeline_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANANSI_MOCK_PIPELINE", "1")
    initial = initialize_state(
        {
            "topic": "A,B",
            "country": "Ghana",
            "grade": 3,
            "language": "English",
            "extra_context": {},
        }
    )
    final = await run_pipeline(initial)
    pkg = OutputPackage.model_validate(final["package"])
    assert len(pkg.panels) == 2
    assert len(pkg.scenes) == 2
