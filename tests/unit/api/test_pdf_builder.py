"""Unit tests for the pure build_pdf_bytes() helper."""

from io import BytesIO

import pytest
from PIL import Image

from anansi.ui.components.export_pdf import (
    _is_webp_payload,
    _prepare_image_bytes_for_pdf,
    build_pdf_bytes,
    build_pdf_bytes_async,
)


def _make_panel(n: int, safe: bool = True) -> dict:
    return {
        "panel_number": n,
        "panel_id": f"p{n}",
        "title": f"Panel {n}",
        "caption": f"Caption {n}",
        "dialogue": f"Dialogue {n}",
        "narration": f"Narration {n}",
        "image_url": "",
        "audio_url": "",
        "audio_error": None,
        "safe": safe,
        "safety_reason": None if safe else "Contains inappropriate content",
    }


@pytest.fixture()
def minimal_package() -> dict:
    return {
        "panels": [_make_panel(1), _make_panel(2)],
        "teacher_guide": "Remember to pause between panels.",
        "lesson_title": "The Water Cycle",
        "safety_results": [],
    }


def test_prepare_image_converts_webp_to_png() -> None:
    """Replicate often serves WebP; PDF path must normalize to PNG for FPDF."""
    buf = BytesIO()
    try:
        Image.new("RGB", (8, 8), (10, 90, 200)).save(buf, format="WEBP")
    except OSError:
        pytest.skip("WebP encode not available in this Pillow build")
    webp = buf.getvalue()
    assert _is_webp_payload(webp)
    png = _prepare_image_bytes_for_pdf(webp, "https://replicate.delivery/x/out.webp")
    assert png is not None
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


class TestBuildPdfBytes:
    def test_returns_bytes(self, minimal_package: dict) -> None:
        result = build_pdf_bytes(minimal_package)
        assert isinstance(result, bytes)

    def test_pdf_header_magic(self, minimal_package: dict) -> None:
        result = build_pdf_bytes(minimal_package)
        assert result[:4] == b"%PDF"

    def test_non_empty_output(self, minimal_package: dict) -> None:
        result = build_pdf_bytes(minimal_package)
        assert len(result) > 1024  # a real PDF is at least 1 KB

    def test_exclude_unsafe_omits_flagged_panels(self) -> None:
        package = {
            "panels": [_make_panel(1, safe=True), _make_panel(2, safe=False)],
            "teacher_guide": "",
            "lesson_title": "Test",
            "safety_results": [],
        }
        # exclude_unsafe=True → only panel 1 included; result is still a valid PDF
        result = build_pdf_bytes(package, exclude_unsafe=True)
        assert result[:4] == b"%PDF"

    def test_include_unsafe_includes_all_panels(self) -> None:
        package = {
            "panels": [_make_panel(1, safe=True), _make_panel(2, safe=False)],
            "teacher_guide": "",
            "lesson_title": "Test",
            "safety_results": [],
        }
        result_excl = build_pdf_bytes(package, exclude_unsafe=True)
        result_incl = build_pdf_bytes(package, exclude_unsafe=False)
        assert result_excl[:4] == b"%PDF"
        assert result_incl[:4] == b"%PDF"

    def test_empty_panels_still_returns_pdf(self) -> None:
        package = {"panels": [], "teacher_guide": "", "lesson_title": "Empty", "safety_results": []}
        result = build_pdf_bytes(package)
        assert result[:4] == b"%PDF"

    async def test_build_pdf_bytes_async_returns_valid_pdf(
        self, minimal_package: dict
    ) -> None:
        """Async API is safe to await from FastAPI (no nested ``asyncio.run``)."""
        result = await build_pdf_bytes_async(minimal_package)
        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_teacher_guide_smart_punctuation_does_not_crash(self, minimal_package: dict) -> None:
        """FPDF page streams are latin-1; guide bodies must be normalized."""
        minimal_package["teacher_guide"] = (
            "## Notes\n"
            "Use an em dash\u2014like this\u2014for emphasis.\n"
            "Also \u2018smart\u2019 quotes and ellipsis\u2026\n"
        )
        result = build_pdf_bytes(minimal_package)
        assert result[:4] == b"%PDF"
        assert len(result) > 1024

    def test_teacher_guide_markdown_headings_lists_quotes(self, minimal_package: dict) -> None:
        """H1–H6, bullets, ordered items, and blockquotes render without error."""
        minimal_package["teacher_guide"] = (
            "# Unit overview\n"
            "Intro paragraph.\n\n"
            "## Vocabulary\n"
            "- term one\n"
            "- term two\n\n"
            "### Deep dive\n"
            "1. First step\n"
            "2. Second step\n\n"
            "> Teacher tip: pause here.\n"
        )
        result = build_pdf_bytes(minimal_package)
        assert result[:4] == b"%PDF"
        assert len(result) > 1024
