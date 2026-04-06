"""Unit tests for ``build_audio_zip_bytes``."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from anansi.api.export_audio_zip import build_audio_zip_bytes


def test_build_audio_zip_from_local_files(tmp_path: Path) -> None:
    a = tmp_path / "one.mp3"
    b = tmp_path / "two.mp3"
    a.write_bytes(b"fake-audio-1")
    b.write_bytes(b"fake-audio-2")
    package = {
        "panels": [
            {
                "panel_number": 2,
                "audio_url": str(b),
            },
            {
                "panel_number": 1,
                "audio_url": str(a),
            },
        ],
    }
    raw = build_audio_zip_bytes(package)
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        names = sorted(zf.namelist())
        assert names == ["panel_1.mp3", "panel_2.mp3"]
        assert zf.read("panel_1.mp3") == b"fake-audio-1"
        assert zf.read("panel_2.mp3") == b"fake-audio-2"


def test_skips_missing_and_empty_urls(tmp_path: Path) -> None:
    good = tmp_path / "ok.mp3"
    good.write_bytes(b"x")
    package = {
        "panels": [
            {"panel_number": 1, "audio_url": ""},
            {"panel_number": 2, "audio_url": "https://invalid.invalid/nope.mp3"},
            {"panel_number": 3, "audio_url": str(good)},
        ],
    }
    raw = build_audio_zip_bytes(package)
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        assert zf.namelist() == ["panel_3.mp3"]


def test_no_valid_audio_raises() -> None:
    package = {"panels": [{"panel_number": 1, "audio_url": ""}]}
    with pytest.raises(ValueError, match="No downloadable audio"):
        build_audio_zip_bytes(package)
