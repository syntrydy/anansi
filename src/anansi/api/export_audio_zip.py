"""Build a ZIP archive of panel audio files from a serialized ``OutputPackage`` dict."""

from __future__ import annotations

import logging
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

logger = logging.getLogger(__name__)


def _audio_bytes(url: str) -> bytes | None:
    """Load audio bytes from an http(s) URL or local filesystem path."""
    u = (url or "").strip()
    if not u:
        return None
    if u.startswith("http://") or u.startswith("https://"):
        try:
            with urlopen(u, timeout=60) as resp:
                chunk = resp.read()
                return chunk if isinstance(chunk, bytes) else None
        except (URLError, OSError, ValueError, TypeError) as exc:
            logger.debug("Audio fetch failed for URL: %s (%s)", u, exc)
            return None
    path = Path(u)
    try:
        return path.read_bytes() if path.is_file() else None
    except OSError as exc:
        logger.debug("Audio read failed for path: %s (%s)", u, exc)
        return None


def _suffix_for_url(url: str) -> str:
    """Pick ``.mp3`` or a short extension from the URL/path tail."""
    path_part = (url or "").strip().split("?", maxsplit=1)[0]
    name = path_part.rsplit("/", maxsplit=1)[-1]
    ext = Path(name).suffix.lower()
    if (
        len(ext) >= 2
        and len(ext) <= 6
        and ext.startswith(".")
        and ext[1:].replace(".", "").isalnum()
    ):
        return ext
    return ".mp3"


def build_audio_zip_bytes(package: dict[str, Any]) -> bytes:
    """Zip all readable panel audio files as ``panel_{n}.<ext>``.

    Skips missing URLs, failed downloads, and empty payloads silently.
    Raises ``ValueError`` if no valid audio bytes were added.
    """
    panels: list[dict[str, Any]] = sorted(
        list(package.get("panels") or []),
        key=lambda p: int(p.get("panel_number") or 0),
    )
    buf = BytesIO()
    added = 0
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for panel in panels:
            url = str(panel.get("audio_url") or "").strip()
            if not url:
                continue
            blob = _audio_bytes(url)
            if not blob:
                continue
            pn = int(panel.get("panel_number") or added + 1)
            ext = _suffix_for_url(url)
            name = f"panel_{pn}{ext}"
            zf.writestr(name, blob)
            added += 1

    if added == 0:
        msg = "No downloadable audio files were found for this lesson."
        raise ValueError(msg)

    return buf.getvalue()
