"""Build a simple lesson PDF from pipeline output for download."""

from io import BytesIO
from typing import Any

import requests
import streamlit as st
from fpdf import FPDF


def export_pdf(result: dict[str, Any] | None) -> None:
    """Render a download button that exports ``teacher_guide`` and panels to a PDF."""
    if not result:
        return

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, result.get("teacher_guide", ""))
    pdf.ln(10)

    for panel in result.get("panels", []):
        pdf.set_font("Arial", "B", 14)
        pdf.cell(
            0,
            10,
            f"Panel {panel.get('panel_number')}: {panel.get('caption')}",
            ln=True,
        )
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 8, panel.get("dialogue", ""))

        img_url = panel.get("image_url")
        if img_url:
            try:
                resp = requests.get(img_url, timeout=30)
                resp.raise_for_status()
                pdf.image(BytesIO(resp.content), w=120)
            except (OSError, requests.RequestException, ValueError):
                pdf.cell(0, 10, "Image failed to load", ln=True)
        pdf.ln(5)

    raw = pdf.output(dest="S")
    pdf_bytes = raw.encode("latin-1") if isinstance(raw, str) else raw

    st.download_button(
        "📄 Download PDF",
        data=pdf_bytes,
        file_name="lesson.pdf",
        mime="application/pdf",
    )
