import streamlit as st

def init_session():
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("loading", False)
    st.session_state.setdefault("progress", 0)
    st.session_state.setdefault("step", "")
    st.session_state.setdefault("last_input", None)

def set_loading(value: bool):
    st.session_state.loading = value

def set_result(result):
    st.session_state.result = result

def set_progress(value: int, step: str):
    st.session_state.progress = value
    st.session_state.step = step

def reset():
    st.session_state.result = None
    st.session_state.progress = 0
    st.session_state.step = ""