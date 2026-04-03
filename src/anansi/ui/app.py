"""Streamlit entrypoint for the Anansi teaching assistant."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, cast

logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from anansi.agent.graph import run_pipeline
from anansi.core.models.state import AnansiState, initialize_state
from anansi.observability.feedback import log_feedback
from anansi.ui.components.export_pdf import export_pdf
from anansi.ui.components.input_form import render_input_form
from anansi.ui.components.panel_viewer import render_panel_viewer, render_pipeline_preview
from anansi.ui.components.progress import render_progress, render_stepper
from anansi.ui.session import init_session, reset, set_loading, set_progress, set_result
from anansi.ui.styles import inject_styles


def _rerun() -> None:
    fn = getattr(st, "rerun", None)
    if callable(fn):
        fn()
        return
    legacy = getattr(st, "experimental_rerun", None)
    if callable(legacy):
        legacy()


def _hash_input(data: dict[str, Any]) -> str:
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()



def _pipeline_status_line(snap: AnansiState) -> str:
    parts: list[str] = []
    if snap.get("scenes"):
        parts.append(f"Concept ✓ ({len(snap['scenes'])} scenes)")
    if snap.get("context_pack"):
        parts.append("Localized ✓")
    if snap.get("panel_scripts"):
        parts.append(f"Script ✓ ({len(snap['panel_scripts'])} panels)")
    if snap.get("safety_results"):
        n_bad = sum(1 for r in snap["safety_results"] if not r.get("safe", True))
        parts.append(f"Safety ✓ ({n_bad} flagged)")
    if snap.get("images"):
        ok = sum(1 for i in snap["images"] if i.get("url"))
        parts.append(f"Images {ok}/{len(snap['images'])}")
    if snap.get("audios"):
        parts.append(f"Audio {len(snap['audios'])}")
    if snap.get("package"):
        parts.append("Package ✓")
    return " → ".join(parts) if parts else "Starting…"


st.set_page_config(page_title="Anansi Teacher Tool", layout="wide")
os.environ.setdefault("ANANSI_MOCK_PIPELINE", "1")
inject_styles()
init_session()
st.session_state.setdefault("pdf_build_id", 0)
st.session_state.setdefault("pipeline_summary_text", "")
st.session_state.setdefault("last_snap", {})

st.markdown(
    '<h1 style="font-family:\'Manrope\',sans-serif;font-weight:800;font-size:2.25rem;'
    'letter-spacing:-0.03em;margin-bottom:0.25rem;">Anansi AI</h1>'
    '<p style="font-size:0.75rem;font-weight:600;color:#8c7166;text-transform:uppercase;'
    'letter-spacing:0.12em;margin-top:0;">Teaching Assistant</p>',
    unsafe_allow_html=True,
)

top_pipeline_status = st.empty()
busy = bool(st.session_state.get("loading", False))
if busy or st.session_state.get("last_snap") or st.session_state.get("result"):
    render_stepper(st.session_state.get("last_snap", {}))

st.markdown(
    '<h2 style="font-family:\'Manrope\',sans-serif;font-weight:800;font-size:1.75rem;'
    'letter-spacing:-0.02em;margin-bottom:1.5rem;">Create New Lesson Storyboard</h2>',
    unsafe_allow_html=True,
)
form_data = render_input_form()

if form_data:
    input_hash = _hash_input(dict(form_data))

    if st.session_state.get("last_input_hash") == input_hash and st.session_state.result:
        st.info("Using cached result (same inputs). Change a field or clear to rerun.")
    else:
        reset()
        st.session_state["last_input_hash"] = input_hash
        st.session_state["last_input"] = dict(form_data)
        set_loading(True)

        try:
            initial = initialize_state(dict(form_data))
            status_slot = st.empty()
            preview_slot = st.empty()

            def on_update(snap: AnansiState) -> None:
                line = _pipeline_status_line(snap)
                st.session_state["pipeline_summary_text"] = line
                st.session_state["last_snap"] = dict(snap)
                top_pipeline_status.markdown(f"**Pipeline:** {line}")
                status_slot.markdown(f"**Pipeline:** {line}")
                with preview_slot.container():
                    render_pipeline_preview(cast(dict[str, Any], snap))

            set_progress(5, "Running pipeline…")
            final_state = asyncio.run(
                run_pipeline(initial, on_state_update=on_update)
            )
            pkg = final_state.get("package")
            if not isinstance(pkg, dict):
                raise RuntimeError("Pipeline finished without a package payload")
            set_result(pkg)
            st.session_state["last_snap"] = dict(final_state)
            st.session_state["pipeline_summary_text"] = _pipeline_status_line(
                final_state
            )
            top_pipeline_status.markdown(
                f"**Pipeline:** {st.session_state['pipeline_summary_text']} ✅"
            )
            set_progress(100, "Done")
            status_slot.markdown(
                f"**Pipeline:** {st.session_state['pipeline_summary_text']} ✅"
            )
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
        finally:
            set_loading(False)

if st.session_state.result:
    st.success("Lesson generated successfully ✅")

    btn_disabled = bool(st.session_state.get("loading", False))
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            "Regenerate All",
            disabled=btn_disabled,
            help="Clear the current lesson and run the full pipeline again from your last form inputs.",
        ):
            reset()
            st.session_state.pop("last_input_hash", None)
            st.session_state["pipeline_summary_text"] = ""
            _rerun()
    with c2:
        if st.button(
            "Clear",
            disabled=btn_disabled,
            help="Remove the generated lesson from this session (keeps your form until you submit again).",
        ):
            reset()
            st.session_state.pop("last_input_hash", None)
            st.session_state["pipeline_summary_text"] = ""
            _rerun()
    with c3:
        if st.button(
            "↻ Rebuild PDF",
            disabled=btn_disabled,
            help="Increment the PDF build id so the download button refreshes from the current on-screen panel text.",
        ):
            st.session_state["pdf_build_id"] = (
                int(st.session_state.get("pdf_build_id", 0)) + 1
            )
            _rerun()

    render_panel_viewer(cast(dict[str, Any], st.session_state.result))

    st.divider()
    st.subheader("PDF export")
    exclude_unsafe = st.checkbox(
        "Exclude blocked panels from PDF",
        value=True,
        key="pdf_exclude_unsafe",
        help="When enabled, flagged panels are omitted from the document.",
    )
    build_id = int(st.session_state.get("pdf_build_id", 0))
    _last = st.session_state.get("last_input") or {}
    export_pdf(
        cast(dict[str, Any], st.session_state.result),
        exclude_unsafe=exclude_unsafe,
        download_key=f"lesson_pdf_{build_id}_{exclude_unsafe}",
        topic=str(_last.get("topic", "")),
        country=str(_last.get("country", "")),
        grade=str(_last.get("grade", "")),
    )

    with st.expander("Teacher Guide"):
        st.markdown(st.session_state.result.get("teacher_guide", ""))

    # -----------------------------------------------------------------------
    # Teacher feedback (Phase 1 spec requirement)
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader("Teacher Feedback")
    st.caption(
        "Was this lesson package useful? Your feedback helps improve future lessons."
    )

    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        thumbs_up = st.button(
            "👍 Useful",
            key="feedback_up",
            disabled=btn_disabled,
            help="Mark this lesson as useful.",
        )
    with fb_col2:
        thumbs_down = st.button(
            "👎 Not useful",
            key="feedback_down",
            disabled=btn_disabled,
            help="Mark this lesson as not useful.",
        )

    feedback_comment = st.text_area(
        "Optional comment (e.g. what worked, what did not)",
        key="feedback_comment",
        height=80,
        placeholder="Add any notes for the Anansi team…",
    )

    if thumbs_up or thumbs_down:
        log_feedback(
            rating="positive" if thumbs_up else "negative",
            comment=feedback_comment.strip(),
            result=cast(dict[str, Any], st.session_state.result),
            last_input=st.session_state.get("last_input") or {},
        )
        st.success("Thank you — your feedback has been recorded!")
