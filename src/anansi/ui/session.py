"""Streamlit session state helpers for the Anansi UI."""

from __future__ import annotations

from typing import Any

import streamlit as st


def init_session() -> None:
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("loading", False)
    st.session_state.setdefault("progress", 0)
    st.session_state.setdefault("step", "")
    st.session_state.setdefault("last_input", None)


def set_loading(value: bool) -> None:
    st.session_state.loading = value


def set_result(result: Any) -> None:
    st.session_state.result = result


def set_progress(value: int, step: str) -> None:
    st.session_state.progress = value
    st.session_state.step = step


def reset() -> None:
    st.session_state.result = None
    st.session_state.progress = 0
    st.session_state.step = ""