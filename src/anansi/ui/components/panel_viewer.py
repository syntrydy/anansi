"""Display and lightly edit generated panels with safety affordances."""

from __future__ import annotations

import asyncio
from typing import Any

import streamlit as st

from anansi.agent.graph import run_pipeline
from anansi.core.models.state import initialize_state


def _rerun() -> None:
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
    else:
        st.experimental_rerun()


def render_panel_viewer(result: dict[str, Any] | None) -> None:
    """
    Show each panel with caption/dialogue, media, safety callouts, and regen.
    """
    if not result:
        return

    panels: list[dict[str, Any]] = list(result.get("panels") or [])
    safety_results: list[dict[str, Any]] = list(result.get("safety_results") or [])

    st.subheader("Generated Panels")

    for idx, panel in enumerate(panels):
        container = st.container()
        panel_number = panel.get("panel_number")
        safe = panel.get("safe", True)
        reason = panel.get("safety_reason")

        safety = next(
            (s for s in safety_results if s.get("panel_number") == panel_number),
            None,
        )
        unsafe = not safe or (safety is not None and not safety.get("safe", True))
        display_reason = reason or (safety or {}).get("reason")

        header = f"Panel {panel_number}"
        if unsafe:
            header = f"⚠️ {header} — review required"
        container.markdown(f"**{header}**")

        col_main, col_side = container.columns([2, 1])

        with col_main:
            caption_key = f"caption_{idx}"
            dialogue_key = f"dialogue_{idx}"
            panel["caption"] = st.text_input(
                f"Caption ({panel_number})",
                value=panel.get("caption", ""),
                key=caption_key,
            )
            panel["dialogue"] = st.text_input(
                f"Dialogue ({panel_number})",
                value=panel.get("dialogue", ""),
                key=dialogue_key,
            )

            img_slot = st.empty()
            image_url = panel.get("image_url") or ""
            if unsafe:
                img_slot.warning(
                    display_reason or "Panel blocked by safety check."
                )
            elif image_url:
                img_slot.image(
                    image_url,
                    caption=f"Panel {panel_number}",
                    use_column_width=True,
                )
            else:
                img_slot.info("No image URL for this panel.")

            audio_url = panel.get("audio_url") or ""
            if audio_url and not unsafe:
                st.audio(audio_url)
            err = panel.get("audio_error")
            if err:
                st.warning(f"Audio: {err}")

        with col_side:
            if unsafe and display_reason:
                st.error(display_reason)
            if st.button(
                f"🔄 Regenerate panel {panel_number}",
                key=f"regen_{idx}",
                disabled=st.session_state.get("loading", False),
            ):
                raw = st.session_state.get("last_input")
                if not raw:
                    st.error("Missing last input; submit the form again.")
                else:
                    st.session_state.loading = True
                    asyncio.run(run_pipeline(initialize_state(dict(raw))))
                    _rerun()


def render_pipeline_preview(snap: dict[str, Any]) -> None:
    """Show incremental thumbnails while the graph is streaming."""
    images = snap.get("images") or []
    urls = [
        i.get("url")
        for i in images
        if isinstance(i, dict) and (i.get("url") or "").strip()
    ]
    if not urls:
        return
    st.caption("Preview (updates as images complete)")
    st.image(urls, width=220)
