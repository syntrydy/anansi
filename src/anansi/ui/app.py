import streamlit as st
import asyncio
import os
import hashlib
import json

from anansi.agent.graph import run_pipeline
from anansi.core.models.state import initialize_state

from anansi.ui.session import init_session, set_loading, set_result, set_progress, reset
from anansi.ui.components.input_form import render_input_form
from anansi.ui.components.panel_viewer import render_panel_viewer
from anansi.ui.components.progress import render_progress
from anansi.ui.components.export_pdf import export_pdf

# -------------------
# Page config
# -------------------
st.set_page_config(page_title="Anansi Teacher Tool", page_icon="📚", layout="wide")
os.environ.setdefault("ANANSI_MOCK_PIPELINE", "1")

init_session()

def _hash_input(data: dict) -> str:
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

@st.cache_data(show_spinner=False)
def run_cached_pipeline(input_data: dict):
    state = initialize_state(input_data)
    return asyncio.run(run_pipeline(state))

# -------------------
# Header
# -------------------
st.title("📚 Anansi Teaching Assistant")
st.caption("Generate culturally-aware visual lessons with audio narration")

# -------------------
# Input form
# -------------------
form_data = render_input_form()

if form_data:
    input_hash = _hash_input(form_data)

    if st.session_state.last_input == input_hash:
        st.info("Using cached result")
    else:
        reset()
        st.session_state.last_input = input_hash
        set_loading(True)

        try:
            set_progress(10, "Analyzing concept...")
            set_progress(30, "Localizing content...")
            set_progress(50, "Writing script...")
            set_progress(70, "Generating images & audio...")
            result = run_cached_pipeline(form_data)
            set_progress(100, "Finalizing lesson...")
            set_result(result.get("package"))

        except Exception as e:
            st.error(f"Pipeline failed: {e}")
        finally:
            set_loading(False)

# -------------------
# Progress
# -------------------
render_progress()

# -------------------
# Output
# -------------------
if st.session_state.result:
    st.success("Lesson generated successfully ✅")

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("🔄 Regenerate All"):
            reset()
            st.experimental_rerun()
    with col2:
        if st.button("🗑 Clear"):
            reset()
            st.experimental_rerun()

    # Panels
    render_panel_viewer(st.session_state.result)

    # PDF
    export_pdf(st.session_state.result)