import streamlit as st
from fpdf import FPDF
from io import BytesIO
import requests

def export_pdf(result: dict):
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
        pdf.cell(0, 10, f"Panel {panel.get('panel_number')}: {panel.get('caption')}", ln=True)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 8, panel.get("dialogue", ""))

        img_url = panel.get("image_url")
        if img_url:
            try:
                resp = requests.get(img_url)
                pdf.image(BytesIO(resp.content), w=120)
            except:
                pdf.cell(0, 10, "Image failed to load", ln=True)
        pdf.ln(5)

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    st.download_button("📄 Download PDF", pdf_output, file_name="lesson.pdf", mime="application/pdf")