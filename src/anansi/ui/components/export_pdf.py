"""Build a lesson PDF from the serialized ``OutputPackage`` dict."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import streamlit as st
from fpdf import FPDF


def _image_bytes(url: str) -> bytes | None:
    """Load image bytes from ``http(s)`` URL or local path."""
    u = (url or "").strip()
    if not u:
        return None
    if u.startswith("http://") or u.startswith("https://"):
        try:
            with urlopen(u, timeout=30) as resp:
                return resp.read()
        except (URLError, OSError, ValueError, TypeError):
            return None
    path = Path(u)
    try:
        if path.is_file():
            return path.read_bytes()
    except OSError:
        return None
    return None


def export_pdf(
    package: dict[str, Any] | None,
    *,
    exclude_unsafe: bool = True,
    download_key: str = "pdf_download",
) -> None:
    """
    Render a download button for a PDF.

    Remote ``image_url`` values are downloaded first; missing images get a
    placeholder line. Blocked panels can be omitted when ``exclude_unsafe``.
    """
    if not package:
        st.warning("No lesson package to export.")
        return

    panels: list[dict[str, Any]] = list(package.get("panels") or [])
    if not panels:
        st.warning("No panels available to export PDF.")
        return

    include = [
        p
        for p in panels
        if not (exclude_unsafe and not p.get("safe", True))
    ]
    if exclude_unsafe and not include:
        st.warning(
            "Every panel is blocked; nothing to put in the PDF. "
            "Uncheck “Exclude blocked panels from PDF” to include flagged text."
        )
        return

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Teacher Lesson Package", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 10)
    guide = str(package.get("teacher_guide", ""))[:4000]
    pdf.multi_cell(0, 5, guide)
    pdf.ln(4)

    for panel in include:
        pn = panel.get("panel_number", "?")
        blocked = not panel.get("safe", True)
        pdf.set_font("Arial", "B", 11)
        label = f"Panel {pn}"
        if blocked:
            label += " (flagged — included as text only)"
        pdf.multi_cell(0, 6, label)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 5, f"Caption: {panel.get('caption', '')}")
        pdf.multi_cell(0, 5, f"Dialogue: {panel.get('dialogue', '')}")
        pdf.multi_cell(0, 5, f"Narration: {panel.get('narration', '')}")
        if blocked and panel.get("safety_reason"):
            pdf.set_text_color(180, 0, 0)
            pdf.multi_cell(0, 5, f"Safety: {panel['safety_reason']}")
            pdf.set_text_color(0, 0, 0)

        img_url = panel.get("image_url") or ""
        blob = _image_bytes(img_url) if img_url else None
        if blob:
            try:
                pdf.image(BytesIO(blob), w=110)
            except (OSError, ValueError, TypeError):
                pdf.multi_cell(0, 5, "[Image could not be embedded]")
        elif img_url:
            pdf.multi_cell(0, 5, "[Image unavailable — URL fetch failed]")
        else:
            pdf.multi_cell(0, 5, "[No image for this panel]")

        if panel.get("audio_error"):
            pdf.set_text_color(200, 0, 0)
            pdf.multi_cell(0, 5, f"Audio error: {panel['audio_error']}")
            pdf.set_text_color(0, 0, 0)
        elif panel.get("audio_url"):
            pdf.multi_cell(0, 5, f"Audio file: {panel['audio_url']}")

        pdf.ln(6)

    raw = pdf.output(dest="S")
    pdf_bytes = raw.encode("latin-1") if isinstance(raw, str) else raw

    st.download_button(
        "📄 Download PDF",
        data=pdf_bytes,
        file_name="lesson_package.pdf",
        mime="application/pdf",
        key=download_key,
    )
