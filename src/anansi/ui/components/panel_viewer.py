import streamlit as st
import asyncio
from anansi.agent.graph import run_pipeline

def render_panel_viewer(result):
    if not result:
        return

    panels = result.get("panels", [])
    for idx, panel in enumerate(panels):
        container = st.container()

        # Editable fields
        caption_key = f"caption_{idx}"
        dialogue_key = f"dialogue_{idx}"
        panel["caption"] = container.text_input(
            f"Caption {panel.get('panel_number')}", value=panel.get("caption", ""), key=caption_key
        )
        panel["dialogue"] = container.text_input(
            f"Dialogue {panel.get('panel_number')}", value=panel.get("dialogue", ""), key=dialogue_key
        )

        # Display image
        img_placeholder = container.empty()
        img_url = panel.get("image_url")
        if img_url:
            img_placeholder.image(img_url, caption=f"Panel {panel.get('panel_number')}", use_column_width=True)
        else:
            img_placeholder.text("Generating panel...")

        # Audio playback
        audio_url = panel.get("audio_url")
        if audio_url:
            container.audio(audio_url)
        if panel.get("audio_error"):
            container.warning(f"Audio error: {panel['audio_error']}")

        # Inline regenerate
        if container.button(f"Regenerate Panel {panel.get('panel_number')}", key=f"regen_{idx}"):
            st.session_state.loading = True
            st.session_state.step = f"Regenerating panel {panel.get('panel_number')}..."
            # For simplicity we rerun the full pipeline; can optimize later
            asyncio.run(run_pipeline(st.session_state.last_input))
            st.experimental_rerun()