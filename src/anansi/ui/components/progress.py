import streamlit as st

def render_progress():
    """Render the progress bar and step info."""
    if st.session_state.get("loading", False):
        st.info(f"{st.session_state.get('step', '')} ({st.session_state.get('progress', 0)}%)")
        with st.spinner(f"{st.session_state.get('step', '')}..."):
            pass