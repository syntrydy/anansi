"""Display and lightly edit generated panels with safety affordances."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import streamlit as st

from anansi.agent.graph import run_pipeline
from anansi.core.models.state import initialize_state


def _rerun() -> None:
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
        return
    legacy = getattr(st, "experimental_rerun", None)
    if callable(legacy):
        legacy()


def _audio_bytes_for_download(audio_url: str) -> tuple[bytes | None, str]:
    """Return MP3 bytes and a suggested filename segment for ``st.download_button``."""
    u = (audio_url or "").strip()
    if not u:
        return None, "audio.mp3"
    if u.startswith("http://") or u.startswith("https://"):
        try:
            with urlopen(u, timeout=45) as resp:
                return resp.read(), "audio.mp3"
        except (URLError, OSError, ValueError, TypeError):
            return None, "audio.mp3"
    path = Path(u)
    try:
        if path.is_file():
            return path.read_bytes(), path.name
    except OSError:
        return None, "audio.mp3"
    return None, "audio.mp3"


def render_panel_viewer(result: dict[str, Any] | None) -> None:
    """
    Show each panel with caption/dialogue, media, safety callouts, and regen.
    """
    if not result:
        return

    panels: list[dict[str, Any]] = list(result.get("panels") or [])
    safety_results: list[dict[str, Any]] = list(result.get("safety_results") or [])
    btn_disabled = bool(st.session_state.get("loading", False))

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
            err = panel.get("audio_error")
            if audio_url and not unsafe:
                st.audio(audio_url)
                blob, fname = _audio_bytes_for_download(audio_url)
                if blob:
                    st.download_button(
                        label="💾 Download narration (MP3)",
                        data=blob,
                        file_name=f"panel_{panel_number}_{fname}",
                        mime="audio/mpeg",
                        key=f"audio_dl_{idx}_{panel_number}",
                        disabled=btn_disabled,
                        help="Save this panel’s narration audio to your device.",
                    )
            elif err:
                st.warning(f"Audio unavailable: {err}")
                st.caption(
                    "No audio file was produced for this panel; download is disabled."
                )
            elif not unsafe:
                st.caption("No audio URL for this panel.")

        with col_side:
            if unsafe and display_reason:
                st.error(display_reason)
            if st.button(
                f"🔄 Regenerate panel {panel_number}",
                key=f"regen_{idx}",
                disabled=btn_disabled,
                help="Re-run the full lesson pipeline using your saved form inputs.",
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
    urls: list[str] = []
    for i in images:
        if not isinstance(i, dict):
            continue
        u = (i.get("url") or "").strip()
        if u:
            urls.append(u)
    if not urls:
        return
    st.caption("Preview (updates as images complete)")
    st.image(urls, width=220)
