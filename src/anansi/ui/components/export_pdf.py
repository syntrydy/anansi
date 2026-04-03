"""Build a branded lesson PDF from the serialized ``OutputPackage`` dict."""

from __future__ import annotations

import re
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import streamlit as st
from fpdf import FPDF  # type: ignore[import-untyped]

# ── Brand palette (RGB) ────────────────────────────────────────────────────
_BRAND        = (158,  61,   0)   # #9e3d00  primary orange
_BRAND_DARK   = ( 53,  16,   0)   # #351000  deep brown
_BRAND_MID    = (198,  79,   0)   # #c64f00  mid orange
_BRAND_LIGHT  = (224, 192, 178)   # #e0c0b2  warm peach
_BG           = (250, 249, 248)   # #faf9f8  warm white
_LIGHT_BG     = (244, 243, 242)   # #f4f3f2  card bg
_TEXT         = ( 26,  28,  28)   # #1a1c1c  near-black
_TEXT_MUTED   = ( 89,  66,  56)   # #594238  warm brown
_ERROR        = (147,   0,  10)   # #93000a  red
_ERROR_BG     = (255, 218, 214)   # #ffdad6  error bg
_SUCCESS      = ( 27, 109,  36)   # #1b6d24  green
_WHITE        = (255, 255, 255)

# ── Unicode sanitisation ───────────────────────────────────────────────────
_UNICODE_MAP = {
    "\u2014": "--",
    "\u2013": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
    "\u00a0": " ",
}


def _to_latin1(text: str) -> str:
    """Replace common non-latin-1 characters, then drop the rest."""
    for ch, repl in _UNICODE_MAP.items():
        text = text.replace(ch, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _strip_markdown(text: str) -> str:
    """Convert markdown to clean plain text suitable for PDF rendering."""
    # Headings → plain text (uppercase for visual weight)
    text = re.sub(r"^#{1,6}\s+(.+)$", lambda m: m.group(1).upper(), text, flags=re.MULTILINE)
    # Bold + italic combined ***text***
    text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text)
    # Bold **text** or __text__
    text = re.sub(r"\*{2}(.+?)\*{2}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"_{2}(.+?)_{2}", r"\1", text, flags=re.DOTALL)
    # Italic *text* or _text_
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # Inline code `code`
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Links [label](url) → label
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # Unordered list bullets (-, *, +) → bullet character
    text = re.sub(r"^[ \t]*[-*+]\s+", "- ", text, flags=re.MULTILINE)
    # Ordered list items — keep the number, normalise spacing
    text = re.sub(r"^[ \t]*(\d+)\.\s+", r"\1. ", text, flags=re.MULTILINE)
    # Horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Blockquotes
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean(text: str) -> str:
    """Strip markdown then sanitise to latin-1 — apply to all user-visible text."""
    return _to_latin1(_strip_markdown(text))


def _image_bytes(url: str) -> bytes | None:
    """Load image bytes from an http(s) URL or local path."""
    u = (url or "").strip()
    if not u:
        return None
    if u.startswith("http://") or u.startswith("https://"):
        try:
            with urlopen(u, timeout=30) as resp:
                chunk = resp.read()
                return chunk if isinstance(chunk, bytes) else None
        except (URLError, OSError, ValueError, TypeError):
            return None
    path = Path(u)
    try:
        return path.read_bytes() if path.is_file() else None
    except OSError:
        return None


# ── Branded FPDF subclass ─────────────────────────────────────────────────

class _AnansiPDF(FPDF):
    """FPDF with a slim branded header and footer on every page."""

    def header(self) -> None:
        # Primary brand bar
        self.set_fill_color(*_BRAND)
        self.rect(0, 0, 210, 7.5, "F")
        # Accent underline
        self.set_fill_color(*_BRAND_LIGHT)
        self.rect(0, 7.5, 210, 1, "F")
        # Wordmark
        self.set_xy(15, 1.5)
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*_WHITE)
        self.cell(22, 5, "ANANSI", ln=False)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(255, 215, 190)
        self.cell(0, 5, "Teacher Tool", ln=False)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_draw_color(*_BRAND_LIGHT)
        self.set_line_width(0.4)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*_TEXT_MUTED)
        today = date.today().strftime("%B %d, %Y")
        self.cell(60, 4, "Anansi Teacher Tool", ln=False, align="L")
        self.cell(60, 4, today, ln=False, align="C")
        self.cell(60, 4, f"Page {self.page_no()}", align="R")


# ── Layout helpers ────────────────────────────────────────────────────────

def _section_header(pdf: _AnansiPDF, text: str) -> None:
    """Bold section label with a left accent bar."""
    y = pdf.get_y()
    pdf.set_fill_color(*_BRAND)
    pdf.rect(15, y, 3, 7, "F")
    pdf.set_xy(21, y + 0.5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_BRAND)
    pdf.cell(0, 6, _clean(text.upper()), ln=True)
    pdf.ln(3)


def _label_value(
    pdf: _AnansiPDF,
    label: str,
    value: str,
    content_x: float,
    content_w: float,
    label_color: tuple[int, int, int] = _TEXT_MUTED,
    value_color: tuple[int, int, int] = _TEXT,
    italic: bool = False,
) -> None:
    """Draw a small uppercase label then a multi-line value."""
    if not value.strip():
        return
    pdf.set_x(content_x)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*label_color)
    pdf.cell(content_w, 4, label.upper(), ln=True)
    old_margin = pdf.l_margin
    pdf.set_left_margin(content_x)
    pdf.set_x(content_x)
    pdf.set_font("Helvetica", "I" if italic else "", 9)
    pdf.set_text_color(*value_color)
    pdf.multi_cell(content_w, 5, value)
    pdf.set_left_margin(old_margin)
    pdf.ln(3)


# ── Main export function ──────────────────────────────────────────────────

def _build_filename(topic: str, country: str, grade: str | int) -> str:
    """Build a descriptive PDF filename from lesson metadata."""
    parts = []
    if topic:
        slug = topic.strip().lower().replace(" ", "_")
        # Keep only alphanumeric and underscores, cap at 30 chars
        slug = "".join(c for c in slug if c.isalnum() or c == "_")[:30]
        parts.append(slug)
    if country:
        parts.append(country.strip().lower().replace(" ", "_"))
    if grade:
        parts.append(f"grade{grade}")
    return ("_".join(parts) or "lesson_package") + ".pdf"


def build_pdf_bytes(
    package: dict[str, Any],
    *,
    exclude_unsafe: bool = True,
) -> bytes:
    """Build the branded lesson PDF and return raw bytes. No Streamlit dependency."""
    panels: list[dict[str, Any]] = list(package.get("panels") or [])
    include = [p for p in panels if not (exclude_unsafe and not p.get("safe", True))]

    pdf = _AnansiPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(left=15, top=14, right=15)
    pdf.add_page()

    # ── Hero cover section ────────────────────────────────────────────────
    # Main brand banner
    pdf.set_fill_color(*_BRAND)
    pdf.rect(0, 9, 210, 46, "F")
    # Right decorative block (lighter tone)
    pdf.set_fill_color(*_BRAND_MID)
    pdf.rect(145, 9, 65, 46, "F")
    # Bottom accent stripe
    pdf.set_fill_color(*_BRAND_LIGHT)
    pdf.rect(0, 55, 210, 1.5, "F")

    # Title
    pdf.set_xy(15, 17)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(*_WHITE)
    pdf.cell(135, 11, "Teacher Lesson", ln=True)
    pdf.set_x(15)
    pdf.cell(135, 11, "Package", ln=True)

    # Subtitle / lesson title
    lesson_title = _clean(
        str(package.get("lesson_title") or package.get("title") or "AI-Generated Lesson")
    )
    pdf.set_xy(15, 44)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(255, 215, 190)
    pdf.cell(135, 5, lesson_title, ln=True)

    # Meta line
    pdf.set_xy(15, 50)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(255, 195, 165)
    today = date.today().strftime("%B %d, %Y")
    pdf.cell(135, 4, f"Generated {today}  |  {len(include)} panel(s)", ln=True)

    pdf.set_y(63)

    # ── Teacher Guide ─────────────────────────────────────────────────────
    guide_text = _clean(str(package.get("teacher_guide", ""))[:4000])
    if guide_text.strip():
        _section_header(pdf, "Teacher Guide")

        # Left accent bar
        guide_start_y = pdf.get_y()
        pdf.set_fill_color(*_BRAND)
        pdf.rect(15, guide_start_y, 1.5, 3, "F")  # will grow below

        # Guide text with light fill
        old_margin = pdf.l_margin
        pdf.set_left_margin(18)
        pdf.set_x(18)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*_TEXT_MUTED)
        pdf.set_fill_color(*_LIGHT_BG)
        pdf.multi_cell(177, 5.5, guide_text, fill=True)
        pdf.set_left_margin(old_margin)

        # Extend the left accent bar to cover actual guide height
        guide_end_y = pdf.get_y()
        pdf.set_fill_color(*_BRAND)
        pdf.rect(15, guide_start_y, 1.5, guide_end_y - guide_start_y, "F")

        pdf.ln(8)

    # ── Panels ────────────────────────────────────────────────────────────
    _section_header(pdf, f"Lesson Panels  --  {len(include)} panel(s)")

    for panel in include:
        pn = panel.get("panel_number", "?")
        blocked = not panel.get("safe", True)
        panel_title = _clean(str(panel.get("title") or f"Panel {pn}"))

        caption   = _clean(str(panel.get("caption",   "") or ""))
        dialogue  = _clean(str(panel.get("dialogue",  "") or ""))
        narration = _clean(str(panel.get("narration", "") or ""))

        # ── Panel header bar ──────────────────────────────────────────────
        # Reserve space: if less than 50mm left on page, start a new page
        if pdf.get_y() > 248:
            pdf.add_page()
            pdf.ln(2)

        header_y = pdf.get_y()
        header_color = _ERROR if blocked else _BRAND

        # Full header rectangle
        pdf.set_fill_color(*header_color)
        pdf.rect(15, header_y, 180, 9.5, "F")

        # Dark panel-number badge on the left
        badge_color = (100, 0, 7) if blocked else _BRAND_DARK
        pdf.set_fill_color(*badge_color)
        pdf.rect(15, header_y, 20, 9.5, "F")

        pdf.set_xy(15, header_y + 1.8)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_WHITE)
        pdf.cell(20, 6, f"#{pn}", align="C", ln=False)

        # Panel title
        pdf.set_xy(37, header_y + 2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_WHITE)
        title_w = 118 if blocked else 138
        pdf.cell(title_w, 5.5, panel_title, ln=False)

        # Flagged badge (right side)
        if blocked:
            pdf.set_xy(157, header_y + 2.2)
            pdf.set_fill_color(*_ERROR_BG)
            pdf.set_text_color(*_ERROR)
            pdf.set_font("Helvetica", "B", 6.5)
            pdf.cell(36, 5, "FLAGGED", align="C", fill=True)

        pdf.set_y(header_y + 9.5)

        # ── Card body ─────────────────────────────────────────────────────
        body_y = pdf.get_y()
        card_x = 15
        card_w = 180
        pad = 3  # inner padding

        # Subtle warm background strip
        pdf.set_fill_color(*_BG)
        pdf.rect(card_x, body_y, card_w, 3, "F")
        pdf.set_y(body_y + pad)

        content_x = card_x + pad + 1
        content_w = card_w - (pad + 1) * 2

        # Text fields
        _label_value(pdf, "Caption",   caption,   content_x, content_w)
        _label_value(pdf, "Dialogue",  dialogue,  content_x, content_w, italic=True)
        _label_value(pdf, "Narration", narration, content_x, content_w)

        # Safety note
        if blocked and panel.get("safety_reason"):
            note_y = pdf.get_y()
            pdf.set_fill_color(*_ERROR_BG)
            pdf.rect(content_x, note_y, content_w, 3, "F")
            pdf.set_y(note_y + 1)
            _label_value(
                pdf,
                "Safety Note",
                _clean(str(panel["safety_reason"])),
                content_x,
                content_w,
                label_color=_ERROR,
                value_color=_ERROR,
            )

        # Audio info
        if panel.get("audio_error"):
            pdf.set_x(content_x)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*_ERROR)
            old_margin = pdf.l_margin
            pdf.set_left_margin(content_x)
            pdf.multi_cell(content_w, 4.5, _clean(f"Audio error: {panel['audio_error']}"))
            pdf.set_left_margin(old_margin)
        elif panel.get("audio_url"):
            pdf.set_x(content_x)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*_SUCCESS)
            old_margin = pdf.l_margin
            pdf.set_left_margin(content_x)
            pdf.multi_cell(content_w, 4.5, _clean(f"Audio: {panel['audio_url']}"))
            pdf.set_left_margin(old_margin)

        # Image
        img_url = panel.get("image_url") or ""
        blob = _image_bytes(img_url) if img_url else None
        if blob:
            pdf.ln(2)
            try:
                # Centered image, max 130mm wide
                img_w = 130
                img_x = card_x + (card_w - img_w) / 2
                pdf.image(BytesIO(blob), x=img_x, w=img_w)
                pdf.ln(2)
            except (OSError, ValueError, TypeError):
                pdf.set_x(content_x)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(*_TEXT_MUTED)
                pdf.cell(content_w, 5, "[Image could not be embedded]", ln=True)
        elif img_url:
            pdf.set_x(content_x)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*_TEXT_MUTED)
            pdf.cell(content_w, 5, "[Image unavailable -- URL fetch failed]", ln=True)

        # Card bottom: left accent bar + bottom separator line
        card_bottom_y = pdf.get_y() + 3
        pdf.set_fill_color(*_BRAND_LIGHT)
        pdf.rect(card_x, body_y, 2, card_bottom_y - body_y, "F")
        pdf.set_draw_color(*_BRAND_LIGHT)
        pdf.set_line_width(0.3)
        pdf.line(card_x, card_bottom_y, card_x + card_w, card_bottom_y)

        pdf.set_y(card_bottom_y + 6)

    # ── Serialize ─────────────────────────────────────────────────────────
    raw: str | bytes = pdf.output(dest="S")
    return raw.encode("latin-1") if isinstance(raw, str) else raw


def export_pdf(
    package: dict[str, Any] | None,
    *,
    exclude_unsafe: bool = True,
    download_key: str = "pdf_download",
    topic: str = "",
    country: str = "",
    grade: str | int = "",
) -> None:
    """Render a branded download button for a lesson PDF."""
    if not package:
        st.warning("No lesson package to export.")
        return

    panels: list[dict[str, Any]] = list(package.get("panels") or [])
    if not panels:
        st.warning("No panels available to export PDF.")
        return

    include = [p for p in panels if not (exclude_unsafe and not p.get("safe", True))]
    if exclude_unsafe and not include:
        st.warning(
            "Every panel is blocked; nothing to put in the PDF. "
            'Uncheck "Exclude blocked panels from PDF" to include flagged text.'
        )
        return

    pdf_bytes = build_pdf_bytes(package, exclude_unsafe=exclude_unsafe)
    st.download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name=_build_filename(topic, country, grade),
        mime="application/pdf",
        key=download_key,
    )
