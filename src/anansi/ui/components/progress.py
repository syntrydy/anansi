"""Pipeline stepper — renders a 5-step visual progress indicator."""

from __future__ import annotations

from typing import Any

import streamlit as st

# Maps state key → (display label)
_STEPS: list[tuple[str, str]] = [
    ("scenes",        "Concept"),
    ("context_pack",  "Localize"),
    ("panel_scripts", "Script"),
    ("images",        "Images"),
    ("package",       "Assemble"),
]


def render_stepper(snap: dict[str, Any] | None = None) -> None:
    """Render the pipeline stepper; ``snap`` is the latest LangGraph state."""
    snap = snap or {}
    loading = bool(st.session_state.get("loading", False))

    done_flags = [bool(snap.get(key)) for key, _ in _STEPS]
    n_done = sum(done_flags)
    active_idx = n_done if loading and n_done < len(_STEPS) else -1

    progress_pct = int(n_done / len(_STEPS) * 100)

    steps_html = ""
    for i, (_, label) in enumerate(_STEPS):
        if done_flags[i]:
            state, icon = "done", "&#10003;"
        elif i == active_idx:
            state, icon = "active", str(i + 1)
        else:
            state, icon = "pending", str(i + 1)

        steps_html += (
            f'<div class="anansi-step">'
            f'  <div class="anansi-step-circle {state}">{icon}</div>'
            f'  <span class="anansi-step-label {state}">{label}</span>'
            f'</div>'
        )

    status_line = ""
    if loading:
        step_text = st.session_state.get("step", "Running pipeline…")
        status_line = (
            f'<div class="anansi-status-line">'
            f'  <span class="anansi-dot-ping"></span>'
            f'  <span>{step_text}</span>'
            f'</div>'
        )

    html = (
        f'<div class="anansi-stepper-wrap">'
        f'  <div class="anansi-stepper">'
        f'    <div class="anansi-stepper-track">'
        f'      <div class="anansi-stepper-fill" style="width:{progress_pct}%"></div>'
        f'    </div>'
        f'    {steps_html}'
        f'  </div>'
        f'  {status_line}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_progress() -> None:
    """Compatibility shim — renders the stepper with no snapshot data."""
    render_stepper()
