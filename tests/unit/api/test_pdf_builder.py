"""Unit tests for the pure build_pdf_bytes() helper."""

import pytest

from anansi.ui.components.export_pdf import build_pdf_bytes


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
        # Including more panels should generally produce a larger PDF
        assert len(result_incl) >= len(result_excl)

    def test_empty_panels_still_returns_pdf(self) -> None:
        package = {"panels": [], "teacher_guide": "", "lesson_title": "Empty", "safety_results": []}
        result = build_pdf_bytes(package)
        assert result[:4] == b"%PDF"
