"""
Printable comic-book PDF from ``OutputPackage`` (React ``PanelCard`` order).

Cover: full-width–preferred ``storyboard_image_url`` hero, lesson title, optional
``topic``, grade, lesson date, Anansi Teacher Tool branding. Teacher guide:
``teacher_guide`` Markdown (headings, lists, vocabulary / comprehension / plan).
Comic: async prefetch ``panels[].image_url`` (3 attempts); WebP → PNG/JPEG-safe
bytes for FPDF. Panels without a reachable, loadable image are **omitted** from
the comic (logged); no placeholders or empty image slots. ``audio_url`` ignored.
Teacher guide stays full text on its own pages. Print-ready layout: image above
caption / dialogue / narration; panel order preserved for included panels.
"""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
from io import BytesIO
from datetime import date
from pathlib import Path
from typing import Any, cast

import httpx
import streamlit as st
from fpdf import FPDF

logger = logging.getLogger(__name__)

# Remote lesson images (FLUX / SD) may return 404/empty until generation finishes.
# Async prefetch + retries runs before any FPDF render call so bytes exist on disk.
_PDF_HTTP_TIMEOUT_SEC = 45.0
_PDF_FETCH_RETRIES = 3
_PDF_FETCH_RETRY_DELAY_SEC = 2.0
_PDF_HTTP_USER_AGENT = "AnansiLessonPDF/1.0"
# Transient HTTP statuses worth waiting on (asset pipeline still writing).
_PDF_RETRY_STATUS = frozenset({404, 408, 429, 500, 502, 503, 504})

# ── Layout (mm) ────────────────────────────────────────────────────────────
_PAGE_H = 297.0
_PAGE_W = 210.0
_MARGIN = 10.0
_GAP = 5.0
_USABLE_W = _PAGE_W - (2 * _MARGIN)
_GRID_Y0 = 20.0
_FOOTER_RESERVE = 16.0

# Effective DPI for mm sizing (panels / guide). Higher = sharper print.
_PRINT_DPI = 300.0
# Landscape panel aspect (w/h): own full-width row (matches wide “full bleed” cards).
_WIDE_PANEL_ASPECT_MIN = 1.22

_BRAND = (158, 61, 0)
_BRAND_DARK = (53, 16, 0)
_BRAND_LIGHT = (224, 192, 178)
_TEXT = (26, 28, 28)
_TEXT_MUTED = (89, 66, 56)
_WHITE = (255, 255, 255)

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


def _strip_markdown_inline(text: str) -> str:
    """Remove inline markdown for plain PDF text paths."""
    text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text)
    text = re.sub(r"\*{2}(.+?)\*{2}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"_{2}(.+?)_{2}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text


def _strip_markdown(text: str) -> str:
    """Convert markdown blocks to readable plain text."""
    text = re.sub(r"^#{1,6}\s+(.+)$", r"\1", text, flags=re.MULTILINE)
    text = _strip_markdown_inline(text)
    text = re.sub(r"^[ \t]*[-*+]\s+", "- ", text, flags=re.MULTILINE)
    text = re.sub(r"^[ \t]*(\d+)\.\s+", r"\1. ", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean(text: str) -> str:
    """Sanitise user-visible text to latin-1."""
    return _to_latin1(_strip_markdown(text))


def _format_panel_text_field(value: Any) -> str:
    """
    Normalize caption / dialogue / narration for PDF (never dump raw list repr).

    Lists from structured outputs are joined as separate lines; other types
    stringify without JSON-style brackets in the common case.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            if isinstance(item, str):
                t = item.strip()
                if t:
                    lines.append(t)
            elif item is not None:
                t = str(item).strip()
                if t:
                    lines.append(t)
        return "\n".join(lines)
    return str(value).strip()


def _image_bytes_from_path(path: Path) -> bytes | None:
    try:
        return path.read_bytes() if path.is_file() else None
    except OSError:
        return None


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xD9:
            break
        if 0xD0 <= marker <= 0xD7 or marker in (0x01,):
            i += 2
            continue
        seg_len = int.from_bytes(data[i + 2 : i + 4], "big")
        if seg_len < 2 or i + 2 + seg_len > len(data):
            break
        if marker in (0xC0, 0xC1, 0xC2):
            h = int.from_bytes(data[i + 5 : i + 7], "big")
            w = int.from_bytes(data[i + 7 : i + 9], "big")
            return w, h
        i += 2 + seg_len
    return None


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w = int.from_bytes(data[16:20], "big")
    h = int.from_bytes(data[20:24], "big")
    return w, h


def _verify_image_bytes(data: bytes) -> bool:
    """True if payload looks like a supported raster (PNG, JPEG, GIF)."""
    if len(data) < 8:
        return False
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:2] == b"\xff\xd8":
        return True
    return len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a")


def _is_webp_payload(data: bytes) -> bool:
    """RIFF container with WEBP tag (Replicate often returns ``.webp``)."""
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def _prepare_image_bytes_for_pdf(data: bytes, hint: str) -> bytes | None:
    """
    Normalize rasters for FPDF: WebP and other Pillow formats → PNG.

    Replicate ``replicate.delivery`` URLs often serve WebP; fpdf + our old
    verifier rejected them. Returns PNG bytes or original PNG/JPEG/GIF bytes.
    """
    if len(data) < 8:
        return None
    if _verify_image_bytes(data) and not _is_webp_payload(data):
        return data
    try:
        from PIL import Image

        work = cast(Any, Image.open(BytesIO(data)))
        if work.mode in ("RGBA", "LA"):
            rgb = Image.new("RGB", work.size, (255, 255, 255))
            rgb.paste(work, mask=work.split()[-1])
            work = rgb
        elif work.mode == "P":
            if "transparency" in work.info:
                tmp_rgba = work.convert("RGBA")
                rgb = Image.new("RGB", tmp_rgba.size, (255, 255, 255))
                rgb.paste(tmp_rgba, mask=tmp_rgba.split()[3])
                work = rgb
            else:
                work = work.convert("RGB")
        elif work.mode != "RGB":
            work = work.convert("RGB")
        out = BytesIO()
        work.save(out, format="PNG", optimize=False)
        png = out.getvalue()
        return png if _verify_image_bytes(png) else None
    except OSError as exc:
        logger.debug("PDF PIL decode failed hint=%s err=%s", hint[:80], exc)
        return None


def _pil_raster_dimensions(data: bytes) -> tuple[int, int] | None:
    try:
        from PIL import Image

        with Image.open(BytesIO(data)) as im:
            w, h = im.size
            if w > 0 and h > 0:
                return w, h
    except OSError:
        pass
    return None


def _verify_image_file_path(path_str: str) -> bool:
    blob = _image_bytes_from_path(Path(path_str))
    if blob is None:
        return False
    if _verify_image_bytes(blob):
        return True
    return _prepare_image_bytes_for_pdf(blob, path_str) is not None


def _guess_image_suffix(url: str, data: bytes) -> str:
    lower = (url or "").split("?", 1)[0].lower()
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        if lower.endswith(ext):
            if ext == ".jpeg":
                return ".jpg"
            if ext == ".webp":
                return ".png"
            return ext
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if len(data) >= 2 and data[:2] == b"\xff\xd8":
        return ".jpg"
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if _is_webp_payload(data):
        return ".png"
    return ".png"


def _px_to_mm_for_print(
    px_w: int,
    px_h: int,
    max_w_mm: float,
    max_h_mm: float,
    *,
    dpi: float | None = None,
) -> tuple[float, float]:
    """Scale bitmap dimensions to mm; allow upscaling to fill the print slot."""
    if px_w <= 0 or px_h <= 0:
        return max_w_mm, 0.0
    d = dpi if dpi is not None else _PRINT_DPI
    w_mm = px_w * 25.4 / d
    h_mm = px_h * 25.4 / d
    scale = min(max_w_mm / w_mm, max_h_mm / h_mm)
    return w_mm * scale, h_mm * scale


def _image_fit_mm(
    path: Path,
    max_w_mm: float,
    max_h_mm: float,
    *,
    dpi: float | None = None,
) -> tuple[float, float] | None:
    blob = _image_bytes_from_path(path)
    if not blob:
        return None
    dims = (
        _png_dimensions(blob)
        or _jpeg_dimensions(blob)
        or _pil_raster_dimensions(blob)
    )
    if not dims:
        return None
    return _px_to_mm_for_print(dims[0], dims[1], max_w_mm, max_h_mm, dpi=dpi)


def _cover_hero_dimensions_mm(
    path: Path,
    max_w_mm: float,
    max_h_mm: float,
) -> tuple[float, float]:
    """
    Full-width–preferred hero (``storyboard_image_url``).

    Uses intrinsic aspect ratio: span ``max_w_mm`` when height allows, else cap
    height and shrink width—same idea as CSS ``width:100%`` + ``max-height``
    with ``object-fit: contain``.
    """
    blob = _image_bytes_from_path(path)
    if not blob:
        return max_w_mm, min(52.0, max_h_mm)
    dims = (
        _png_dimensions(blob)
        or _jpeg_dimensions(blob)
        or _pil_raster_dimensions(blob)
    )
    if not dims or dims[0] <= 0 or dims[1] <= 0:
        return max_w_mm, min(52.0, max_h_mm)
    pw, ph = dims
    iw = max_w_mm
    ih = iw * float(ph) / float(pw)
    if ih > max_h_mm:
        ih = max_h_mm
        iw = ih * float(pw) / float(ph)
    return (iw, ih)


def _resolve_local_image_path(path_or_url: str) -> str | None:
    """Map a non-HTTP reference to an existing local file path, or None."""
    raw = (path_or_url or "").strip()
    if not raw or raw.startswith("http://") or raw.startswith("https://"):
        return None
    local = Path(raw).expanduser()
    try:
        local = local.resolve()
    except OSError:
        logger.warning("PDF image local path resolve failed: %s", raw[:120])
        return None
    if local.is_file():
        return str(local)
    logger.warning("PDF image missing: %s", raw[:120])
    return None


def _write_bytes_to_temp_file(data: bytes, url: str) -> str:
    suffix = _guess_image_suffix(url, data)
    tmp = tempfile.NamedTemporaryFile(
        prefix="anansi_pdf_img_",
        suffix=suffix,
        delete=False,
    )
    try:
        tmp.write(data)
        tmp.flush()
    finally:
        tmp.close()
    return tmp.name


def _register_downloaded_path(
    url: str,
    path: str,
    *,
    shared_image_cache: dict[str, str] | None,
    owned_paths: list[str],
) -> None:
    """Track temp file lifetime: session cache owns paths; else delete after PDF build."""
    if shared_image_cache is not None:
        shared_image_cache[url] = path
    else:
        owned_paths.append(path)


async def _download_image_url_with_retries(
    client: httpx.AsyncClient,
    url: str,
) -> bytes | None:
    """
    Fetch remote image bytes; retry while the CDN may still be propagating.

    Async I/O keeps the event loop free so many panel URLs prefetch in parallel.
    """
    last_log: str | None = None
    for attempt in range(_PDF_FETCH_RETRIES):
        try:
            resp = await client.get(
                url,
                headers={"User-Agent": _PDF_HTTP_USER_AGENT},
                timeout=_PDF_HTTP_TIMEOUT_SEC,
                follow_redirects=True,
            )
            if resp.status_code in _PDF_RETRY_STATUS and attempt + 1 < _PDF_FETCH_RETRIES:
                last_log = f"status={resp.status_code}"
                await asyncio.sleep(_PDF_FETCH_RETRY_DELAY_SEC)
                continue
            resp.raise_for_status()
            data = resp.content
            if not data and attempt + 1 < _PDF_FETCH_RETRIES:
                last_log = "empty body"
                await asyncio.sleep(_PDF_FETCH_RETRY_DELAY_SEC)
                continue
            if not data:
                logger.warning("PDF image download empty body url=%s", url[:120])
                return None
            prepared = await asyncio.to_thread(
                _prepare_image_bytes_for_pdf, data, url
            )
            if prepared is None:
                last_log = "webp_or_decode_failed"
                if attempt + 1 < _PDF_FETCH_RETRIES:
                    logger.warning(
                        "PDF image normalize failed (retry) url=%s attempt=%s",
                        url[:120],
                        attempt + 1,
                    )
                    await asyncio.sleep(_PDF_FETCH_RETRY_DELAY_SEC)
                    continue
                logger.error(
                    "PDF image prefetch failed url=%s after_attempts=%s",
                    url[:120],
                    _PDF_FETCH_RETRIES,
                )
                return None
            return prepared
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code in _PDF_RETRY_STATUS and attempt + 1 < _PDF_FETCH_RETRIES:
                last_log = f"HTTPStatusError {code}"
                await asyncio.sleep(_PDF_FETCH_RETRY_DELAY_SEC)
                continue
            logger.warning(
                "PDF image download failed url=%s err=%s", url[:120], exc
            )
            return None
        except (httpx.RequestError, OSError) as exc:
            if attempt + 1 < _PDF_FETCH_RETRIES:
                last_log = str(exc)
                await asyncio.sleep(_PDF_FETCH_RETRY_DELAY_SEC)
                continue
            logger.warning("PDF image download failed url=%s err=%s", url[:120], exc)
            return None
    if last_log:
        logger.warning(
            "PDF image download gave up url=%s last=%s", url[:120], last_log
        )
    return None


async def _ensure_image_path_async(
    url: str,
    client: httpx.AsyncClient,
    *,
    shared_image_cache: dict[str, str] | None,
    owned_paths: list[str],
) -> str | None:
    """
    Resolve one asset URL to a readable filesystem path.

    Runs concurrently via gather(); each task is independent I/O-bound work.
    """
    raw = (url or "").strip()
    if not raw:
        return None

    if shared_image_cache is not None:
        cached = shared_image_cache.get(raw)
        if cached and Path(cached).is_file():
            suf = Path(cached).suffix.lower()
            head = await asyncio.to_thread(lambda: Path(cached).read_bytes()[:12])
            if suf != ".webp" and not _is_webp_payload(head):
                return cached

    local = await asyncio.to_thread(_resolve_local_image_path, raw)
    if local:

        def _materialize_local_disk(local_path: str) -> tuple[str | None, bool]:
            """
            Return ``(path, ephemeral_temp)``.

            WebP and other decodes are written as PNG temp files FPDF can embed.
            """
            p = Path(local_path)
            try:
                blob = p.read_bytes()
            except OSError:
                return None, False
            prepared = _prepare_image_bytes_for_pdf(blob, local_path)
            if prepared is None:
                logger.error(
                    "PDF local image unreadable or unsupported path=%s",
                    local_path[:100],
                )
                return None, False
            if (
                prepared == blob
                and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif")
            ):
                return str(p.resolve()), False
            tmp_path = _write_bytes_to_temp_file(prepared, local_path)
            return tmp_path, True

        path_local, ephemeral = await asyncio.to_thread(
            _materialize_local_disk, local
        )
        if path_local is None:
            return None
        if ephemeral:
            _register_downloaded_path(
                raw,
                path_local,
                shared_image_cache=shared_image_cache,
                owned_paths=owned_paths,
            )
        elif shared_image_cache is not None:
            shared_image_cache[raw] = path_local
        logger.info("PDF prefetch local ok path=%s", path_local[:100])
        return path_local

    if not (raw.startswith("http://") or raw.startswith("https://")):
        return None

    data = await _download_image_url_with_retries(client, raw)
    if not data:
        logger.error(
            "PDF image prefetch failed url=%s after_attempts=%s (no bytes)",
            raw[:120],
            _PDF_FETCH_RETRIES,
        )
        return None

    path = await asyncio.to_thread(_write_bytes_to_temp_file, data, raw)
    _register_downloaded_path(
        raw, path, shared_image_cache=shared_image_cache, owned_paths=owned_paths
    )
    logger.info("PDF prefetch remote stored path=%s url=%s", path[-32:], raw[:80])
    return path


def _raster_path_loadable_for_pdf(path_str: str) -> bool:
    """Confirm on-disk file is a raster Pillow can read (matches FPDF embed expectations)."""
    try:
        from PIL import Image

        with Image.open(path_str) as im:
            im.load()
        return True
    except OSError:
        return False


def _panel_ready_for_comic_pdf(
    panel: dict[str, Any],
    resolved: dict[str, str | None],
) -> bool:
    """
    Safe panel with ``image_url`` resolved to a non-empty, loadable local file.

    Panels that fail are omitted from the comic (no frame without art).
    """
    if not panel.get("safe", True):
        return False
    url = str(panel.get("image_url") or "").strip()
    if not url:
        return False
    path = resolved.get(url)
    if not path or not Path(path).is_file():
        return False
    if not _raster_path_loadable_for_pdf(path):
        logger.error(
            "PDF panel image not loadable panel_number=%s path=%s",
            panel.get("panel_number", "?"),
            path[:100],
        )
        return False
    return True


def _collect_prefetch_urls(
    package: dict[str, Any],
    include_panels: list[dict[str, Any]],
) -> list[str]:
    """Unique URLs in stable order: storyboard first, then panel images (audio ignored)."""
    ordered: list[str] = []
    seen: set[str] = set()
    story = str(package.get("storyboard_image_url") or "").strip()
    if story and story not in seen:
        seen.add(story)
        ordered.append(story)
    for panel in include_panels:
        if not panel.get("safe", True):
            continue
        u = str(panel.get("image_url") or "").strip()
        if u and u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


async def prefetch_lesson_pdf_assets_async(
    package: dict[str, Any],
    include_panels: list[dict[str, Any]],
    *,
    client: httpx.AsyncClient | None = None,
    shared_image_cache: dict[str, str] | None = None,
) -> tuple[dict[str, str | None], list[str]]:
    """
    Download or resolve every image before PDF layout.

    Parallel ``gather`` minimizes wall-clock latency; FPDF stays synchronous later.
    """
    urls = _collect_prefetch_urls(package, include_panels)
    owned_paths: list[str] = []
    if not urls:
        return {}, owned_paths

    close_client = client is None
    ac = client or httpx.AsyncClient()

    try:
        # asyncio.gather schedules all GETs together instead of serial await chains.
        paths = await asyncio.gather(
            *[
                _ensure_image_path_async(
                    u,
                    ac,
                    shared_image_cache=shared_image_cache,
                    owned_paths=owned_paths,
                )
                for u in urls
            ]
        )
    finally:
        if close_client:
            await ac.aclose()

    resolved: dict[str, str | None] = dict(zip(urls, paths, strict=True))
    n_ok = sum(1 for p in paths if p)
    n_fail = len(paths) - n_ok
    logger.info(
        "PDF prefetch complete urls=%s resolved_ok=%s unresolved=%s",
        len(urls),
        n_ok,
        n_fail,
    )
    return resolved, owned_paths


def _log_prefetch_image_outcomes(
    package: dict[str, Any],
    include: list[dict[str, Any]],
    resolved: dict[str, str | None],
) -> int:
    """
    Observability: storyboard + each safe panel image URL success/failure.

    Returns the number of safe panels that had a non-empty ``image_url`` but no
    verified local file after prefetch (image permanently unavailable).
    """
    missing_panel_images = 0
    story = str(package.get("storyboard_image_url") or "").strip()
    if story:
        path = resolved.get(story)
        if path and Path(path).is_file():
            logger.info("PDF prefetch storyboard_image ok url=%s", story[:100])
        else:
            logger.warning("PDF prefetch storyboard_image failed url=%s", story[:100])

    for p in include:
        pn = p.get("panel_number", "?")
        url = str(p.get("image_url") or "").strip()
        if not url:
            logger.debug("PDF prefetch panel_image absent panel_number=%s", pn)
            continue
        if not p.get("safe", True):
            logger.info(
                "PDF prefetch panel_image skipped_unsafe panel_number=%s", pn
            )
            continue
        path = resolved.get(url)
        if path and Path(path).is_file():
            logger.info(
                "PDF prefetch panel_image ok panel_number=%s url=%s",
                pn,
                url[:90],
            )
        else:
            missing_panel_images += 1
            logger.warning(
                "PDF prefetch panel_image failed panel_number=%s url=%s",
                pn,
                url[:90],
            )
    return missing_panel_images


def _text_multicell_limited(
    pdf: FPDF,
    x: float,
    y: float,
    w: float,
    y_max: float,
    font_style: str,
    size: float,
    color: tuple[int, int, int],
    text: str,
    line_h: float,
) -> float:
    if not text.strip() or y >= y_max:
        return y
    pdf.set_xy(x, y)
    pdf.set_font("Helvetica", font_style, size)
    pdf.set_text_color(*color)
    pdf.multi_cell(w, line_h, text[:1200])
    end_y = float(pdf.get_y())
    if end_y > y_max:
        pdf.set_y(y_max)
        return y_max
    return end_y


def _render_teacher_guide_from_markdown(pdf: _TeachingComicPDF, raw: str) -> None:
    """
    Walk teacher guide Markdown line-wise: headings (#–######), lists, quotes, paragraphs.

    Latin-1 safety is applied at emit time for FPDF compatibility.
    """
    text = (raw or "").strip()
    if not text:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*_TEXT_MUTED)
        pdf.multi_cell(0, 5.5, _clean("No teacher guide was generated for this lesson."))
        pdf.set_text_color(*_TEXT)
        return

    para_buf: list[str] = []

    def flush_para() -> None:
        if not para_buf:
            return
        blob = "\n".join(para_buf).strip()
        if blob:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_TEXT)
            pdf.multi_cell(0, 5.5, _clean(blob))
        para_buf.clear()

    heading_sizes = {1: 14, 2: 13, 3: 12, 4: 11, 5: 10, 6: 10}

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            flush_para()
            pdf.ln(2)
            pdf.set_x(_MARGIN)
            continue
        if re.match(r"^[-*_]{3,}\s*$", stripped):
            flush_para()
            pdf.ln(1)
            pdf.set_x(_MARGIN)
            continue
        hm = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if hm:
            flush_para()
            level = len(hm.group(1))
            title = _to_latin1(_strip_markdown_inline(hm.group(2).strip()))
            size = heading_sizes[min(level, 6)]
            pdf.set_font("Helvetica", "B", size)
            pdf.set_text_color(*_BRAND if level <= 2 else _TEXT)
            pdf.multi_cell(0, 6.2 if level <= 2 else 5.4, title)
            pdf.set_text_color(*_TEXT)
            pdf.ln(1)
            pdf.set_x(_MARGIN)
            continue
        if re.match(r"^[-*+]\s+", stripped):
            flush_para()
            rest = re.sub(r"^[-*+]\s+", "", stripped)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_TEXT)
            pdf.set_x(_MARGIN + 4)
            pdf.multi_cell(0, 4.5, _clean("- " + rest))
            pdf.set_x(_MARGIN)
            continue
        nm = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if nm:
            flush_para()
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_TEXT)
            pdf.set_x(_MARGIN + 4)
            pdf.multi_cell(0, 4.5, _clean(f"{nm.group(1)}. {nm.group(2)}"))
            pdf.set_x(_MARGIN)
            continue
        if stripped.startswith(">"):
            flush_para()
            body = _to_latin1(_strip_markdown_inline(stripped.lstrip(">").strip()))
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(*_TEXT_MUTED)
            pdf.set_x(_MARGIN + 3)
            pdf.multi_cell(0, 4.5, body)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_TEXT)
            pdf.set_x(_MARGIN)
            continue
        para_buf.append(stripped)
    flush_para()


def _render_dialogue_block(
    pdf: FPDF,
    x: float,
    y: float,
    w: float,
    y_max: float,
    dialogue: str,
) -> float:
    """Render dialogue; bold speaker name when line matches ``Name: speech``."""
    cy = y
    for line in dialogue.split("\n"):
        line = line.strip()
        if not line or cy >= y_max:
            break
        m = re.match(r"^([^:]{1,48}):\s*(.+)$", line)
        pdf.set_xy(x, cy)
        if m:
            speaker = _clean(m.group(1).strip())
            speech = _clean(m.group(2).strip())
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(*_TEXT)
            sw = pdf.get_string_width(speaker + ": ")
            pdf.cell(sw, 3.2, speaker + ": ", ln=0)
            pdf.set_font("Helvetica", "", 7)
            pdf.multi_cell(w - sw, 3.2, speech)
        else:
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*_TEXT)
            pdf.multi_cell(w, 3.2, _clean(line))
        cy = float(pdf.get_y()) + 0.5
        if cy > y_max:
            pdf.set_y(y_max)
            return y_max
    return cy


class _TeachingComicPDF(FPDF):  # type: ignore[misc]
    """A4 PDF: no top banner on cover/guide; banner from comic pages; dated footer."""

    def __init__(self, footer_date: str) -> None:
        super().__init__()
        self._footer_date = footer_date

    def header(self) -> None:
        if self.page_no() <= 2:
            return
        self.set_fill_color(*_BRAND)
        self.rect(0, 0, 210, 7, "F")
        self.set_fill_color(*_BRAND_LIGHT)
        self.rect(0, 7, 210, 0.6, "F")
        self.set_xy(15, 1.8)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_WHITE)
        self.cell(0, 4, "Anansi Teaching Comic", ln=False)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_draw_color(*_BRAND_LIGHT)
        self.set_line_width(0.3)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(1)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_TEXT_MUTED)
        self.cell(0, 4, f"Page {self.page_no()}", align="C", ln=True)
        self.set_font("Helvetica", "", 7)
        self.cell(
            0,
            4,
            f"Anansi Teacher Tool  |  {self._footer_date}",
            align="C",
            ln=False,
        )


def _build_filename(topic: str, country: str, grade: str | int) -> str:
    parts: list[str] = []
    if topic:
        slug = topic.strip().lower().replace(" ", "_")
        slug = "".join(c for c in slug if c.isalnum() or c == "_")[:30]
        parts.append(slug)
    if country:
        parts.append(country.strip().lower().replace(" ", "_"))
    if grade:
        parts.append(f"grade{grade}")
    return ("_".join(parts) or "lesson_comic") + ".pdf"


def _render_cover_page(
    pdf: _TeachingComicPDF,
    package: dict[str, Any],
    resolved_assets: dict[str, str | None],
    today: date,
) -> None:
    """
    Page 1: hero storyboard (print-ready), then title stack and lesson metadata.

    Mirrors the app’s emphasis on the storyboard as the visual lead.
    """
    pdf.set_auto_page_break(False)
    pdf.set_fill_color(*_WHITE)
    pdf.rect(0, 0, _PAGE_W, _PAGE_H, "F")

    lesson_title = _clean(
        str(package.get("lesson_title") or package.get("title") or "Lesson")
    )
    topic_raw = str(package.get("topic") or "").strip()
    topic_line = _clean(topic_raw) if topic_raw else ""
    grade_val = package.get("grade")
    grade_line = ""
    if grade_val is not None and str(grade_val).strip():
        grade_line = _clean(f"Grade {grade_val}")

    date_str = today.strftime("%B %d, %Y")
    x0 = _MARGIN
    w = _USABLE_W
    y = _MARGIN + 4.0

    story = str(package.get("storyboard_image_url") or "").strip()
    img_path: str | None = resolved_assets.get(story) if story else None
    if img_path and Path(img_path).is_file():
        hero_max_w = w
        hero_max_h = 100.0
        iw, ih = _cover_hero_dimensions_mm(Path(img_path), hero_max_w, hero_max_h)
        ix = x0 + (w - iw) / 2
        try:
            pdf.image(img_path, x=ix, y=y, w=iw, h=ih)
            y += ih + 10.0
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            logger.warning("PDF cover storyboard embed failed: %s", exc)
            y += 4.0
    elif story:
        logger.info("PDF cover: storyboard URL present but asset not loaded; hero omitted")

    pdf.set_xy(x0, y)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*_TEXT)
    pdf.multi_cell(w, 10, "Anansi Teaching Comic", align="C")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 17)
    pdf.multi_cell(w, 8, "Teaching Story", align="C")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*_TEXT)
    pdf.multi_cell(w, 7, lesson_title, align="C")
    pdf.ln(1)

    if topic_line and topic_line.casefold() != lesson_title.casefold():
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(*_TEXT_MUTED)
        pdf.multi_cell(w, 5.5, topic_line, align="C")
        pdf.ln(1)
        pdf.set_text_color(*_TEXT)

    if grade_line:
        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(w, 5.5, grade_line, align="C")
        pdf.ln(1)

    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(*_TEXT_MUTED)
    pdf.multi_cell(w, 6, f"Lesson date: {date_str}", align="C")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*_BRAND)
    pdf.multi_cell(w, 5, "Anansi Teacher Tool", align="C")


def _render_teacher_guide_page(pdf: _TeachingComicPDF, package: dict[str, Any]) -> None:
    """Teacher guide: starts on page 2; headings and body flow with pagination."""
    pdf.set_auto_page_break(True, margin=24)
    pdf.set_fill_color(*_WHITE)
    pdf.rect(0, 0, _PAGE_W, _PAGE_H, "F")

    pdf.set_xy(_MARGIN, 18)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*_BRAND)
    pdf.cell(0, 8, "Teacher Guide", ln=True)
    pdf.ln(2)

    raw_guide = str(package.get("teacher_guide", "") or "")
    _render_teacher_guide_from_markdown(pdf, raw_guide)
    pdf.set_auto_page_break(False)


def _panel_image_aspect_ratio(path_str: str) -> float | None:
    blob = _image_bytes_from_path(Path(path_str))
    if not blob:
        return None
    dims = (
        _png_dimensions(blob)
        or _jpeg_dimensions(blob)
        or _pil_raster_dimensions(blob)
    )
    if not dims:
        return None
    w, h = dims
    return float(w) / float(h) if h else None


def _panel_is_wide_for_layout(
    panel: dict[str, Any],
    resolved_assets: dict[str, str | None],
) -> bool:
    """Landscape thumbnails get a full-width row (React-style wide card)."""
    if not panel.get("safe", True):
        return False
    src = str(panel.get("image_url") or "").strip()
    if not src:
        return False
    path = resolved_assets.get(src)
    if not path or not Path(path).is_file():
        return False
    ar = _panel_image_aspect_ratio(path)
    return ar is not None and ar >= _WIDE_PANEL_ASPECT_MIN


def _comic_row_placements(
    include: list[dict[str, Any]],
    resolved_assets: dict[str, str | None],
) -> list[tuple[list[int], bool]]:
    """
    Rows of panel indices: wide panels occupy a full-width row; narrow pack 2-up.
    """
    rows: list[tuple[list[int], bool]] = []
    pending_narrow: list[int] = []
    for i, p in enumerate(include):
        if _panel_is_wide_for_layout(p, resolved_assets):
            if pending_narrow:
                rows.append((pending_narrow, False))
                pending_narrow = []
            rows.append(([i], True))
        else:
            pending_narrow.append(i)
            if len(pending_narrow) == 2:
                rows.append((pending_narrow, False))
                pending_narrow = []
    if pending_narrow:
        rows.append((pending_narrow, False))
    return rows


def _row_height_mm(is_wide_row: bool) -> float:
    return 128.0 if is_wide_row else 106.0


def _draw_panel_in_cell(
    pdf: _TeachingComicPDF,
    panel: dict[str, Any],
    x: float,
    y: float,
    cell_w: float,
    cell_h: float,
    resolved_assets: dict[str, str | None],
    page_no: int,
    *,
    img_slot_max_h: float,
) -> None:
    """
    Panel card aligned with ``PanelCard.tsx``: image first, then meta,
    labeled caption / dialogue / narration. Audio omitted entirely.
    """
    inner = 1.8
    ix = x + inner
    iy = y + inner
    iw = max(cell_w - 2 * inner, 16.0)
    cell_bottom = y + cell_h - inner

    pdf.set_draw_color(*_BRAND_DARK)
    pdf.set_line_width(0.35)
    pdf.rect(x, y, cell_w, cell_h, style="D")

    blocked = not panel.get("safe", True)
    pn = panel.get("panel_number", "?")
    ptitle = _format_panel_text_field(panel.get("title"))
    caption = _clean(_format_panel_text_field(panel.get("caption")))
    dialogue = _clean(_format_panel_text_field(panel.get("dialogue")))
    narration = _clean(_format_panel_text_field(panel.get("narration")))

    logger.info("PDF panel render start panel_number=%s pdf_page=%s", pn, page_no)

    src = str(panel.get("image_url") or "")
    img_h = 0.0
    if blocked:
        logger.debug("PDF panel image skipped blocked panel_number=%s", pn)
    elif src.strip():
        path = resolved_assets.get(src)
        if path and Path(path).is_file():
            fit = _image_fit_mm(Path(path), iw, img_slot_max_h)
            disp_w, disp_h = iw, img_slot_max_h
            if fit:
                disp_w, disp_h = fit[0], fit[1]
            try:
                pdf.image(path, x=ix, y=iy, w=disp_w, h=disp_h)
                img_h = disp_h
            except (OSError, ValueError, TypeError, RuntimeError) as exc:
                logger.warning(
                    "PDF panel FPDF embed failed panel=%s page=%s err=%s",
                    pn,
                    page_no,
                    exc,
                )
        else:
            logger.error(
                "PDF panel image path missing (should not happen after filter) "
                "panel_number=%s",
                pn,
            )

    cy = iy + img_h + (3.5 if img_h > 0 else 1.0)
    y_max = cell_bottom

    pdf.set_xy(ix, cy)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*_TEXT)
    meta_line = _clean(f"Panel {pn}")
    if ptitle:
        meta_line = f"{meta_line}  --  {_clean(ptitle)}"
    pdf.multi_cell(iw, 3.5, meta_line)
    cy = float(pdf.get_y()) + 1.2

    def emit_label(lbl: str) -> None:
        nonlocal cy
        pdf.set_xy(ix, cy)
        pdf.set_font("Helvetica", "B", 5.5)
        pdf.set_text_color(*_TEXT_MUTED)
        pdf.cell(iw, 2.0, lbl, ln=1)
        cy = float(pdf.get_y()) + 0.5

    if caption and cy < y_max:
        emit_label("CAPTION")
        cy = _text_multicell_limited(
            pdf, ix, cy, iw, y_max, "B", 7.5, _TEXT, caption, 3.4
        )
        cy += 1.0
    if dialogue and cy < y_max:
        emit_label("DIALOGUE")
        cy = _render_dialogue_block(pdf, ix, cy, iw, y_max, dialogue)
        cy += 1.0
    if narration and cy < y_max:
        emit_label("NARRATION")
        _text_multicell_limited(
            pdf, ix, cy, iw, y_max, "I", 6.5, _TEXT_MUTED, narration, 3.2
        )

    logger.info("PDF panel render end panel_number=%s pdf_page=%s", pn, page_no)


def _render_comic_rows(
    pdf: _TeachingComicPDF,
    include: list[dict[str, Any]],
    resolved_assets: dict[str, str | None],
) -> None:
    """Flow comic rows with page breaks."""
    rows = _comic_row_placements(include, resolved_assets)
    y_cur = _GRID_Y0
    page_bottom = _PAGE_H - _FOOTER_RESERVE - _MARGIN
    half_w = (_USABLE_W - _GAP) / 2.0

    for indices, is_wide in rows:
        rh = _row_height_mm(is_wide)
        img_cap = min(70.0, rh * 0.5) if is_wide else min(54.0, rh * 0.48)

        if y_cur + rh > page_bottom:
            pdf.add_page()
            logger.info("PDF compose: comic page pdf_page=%s", pdf.page_no())
            y_cur = _GRID_Y0

        if len(indices) == 1 and is_wide:
            _draw_panel_in_cell(
                pdf,
                include[indices[0]],
                _MARGIN,
                y_cur,
                _USABLE_W,
                rh,
                resolved_assets,
                pdf.page_no(),
                img_slot_max_h=img_cap,
            )
        elif len(indices) == 2:
            _draw_panel_in_cell(
                pdf,
                include[indices[0]],
                _MARGIN,
                y_cur,
                half_w,
                rh,
                resolved_assets,
                pdf.page_no(),
                img_slot_max_h=img_cap,
            )
            _draw_panel_in_cell(
                pdf,
                include[indices[1]],
                _MARGIN + half_w + _GAP,
                y_cur,
                half_w,
                rh,
                resolved_assets,
                pdf.page_no(),
                img_slot_max_h=img_cap,
            )
        else:
            _draw_panel_in_cell(
                pdf,
                include[indices[0]],
                _MARGIN,
                y_cur,
                half_w,
                rh,
                resolved_assets,
                pdf.page_no(),
                img_slot_max_h=img_cap,
            )
        y_cur += rh + _GAP


def _compose_pdf_sync(
    package: dict[str, Any],
    include: list[dict[str, Any]],
    resolved_assets: dict[str, str | None],
    *,
    prefetch_missing_panel_images: int = 0,
    panels_omitted_no_image: int = 0,
) -> bytes:
    """FPDF is synchronous; run only after async prefetch has filled ``resolved_assets``."""
    today = date.today()
    date_str = today.strftime("%B %d, %Y")

    pdf = _TeachingComicPDF(footer_date=date_str)
    pdf.set_margins(_MARGIN, 16, _MARGIN)
    pdf.set_auto_page_break(False)

    logger.info("PDF compose: cover page")
    pdf.add_page()
    _render_cover_page(pdf, package, resolved_assets, today)

    logger.info("PDF compose: teacher guide section")
    pdf.add_page()
    _render_teacher_guide_page(pdf, package)

    if not include:
        logger.info("PDF compose: no comic panels after filters")
        out: str | bytes = pdf.output(dest="S")
        return out.encode("latin-1") if isinstance(out, str) else out

    logger.info(
        "PDF compose: prefetch_missing_panel_images=%s panels_omitted_no_image=%s",
        prefetch_missing_panel_images,
        panels_omitted_no_image,
    )

    pdf.add_page()
    logger.info("PDF compose: first comic page pdf_page=%s", pdf.page_no())
    _render_comic_rows(pdf, include, resolved_assets)

    logger.info(
        "PDF compose: comic_panels_drawn=%s prefetch_missing_urls=%s omitted=%s",
        len(include),
        prefetch_missing_panel_images,
        panels_omitted_no_image,
    )
    out = pdf.output(dest="S")
    return out.encode("latin-1") if isinstance(out, str) else out


async def build_pdf_bytes_async(
    package: dict[str, Any],
    *,
    exclude_unsafe: bool = True,
    shared_image_cache: dict[str, str] | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> bytes:
    """
    Async entry: prefetch images in parallel, then build the PDF.

    Audio URLs are never read. Pass ``shared_image_cache`` (e.g. Streamlit session)
    to reuse temp files across multiple exports in the same session.
    """
    panels: list[dict[str, Any]] = list(package.get("panels") or [])
    include = [p for p in panels if not (exclude_unsafe and not p.get("safe", True))]
    skipped = len(panels) - len(include)
    if skipped:
        logger.info("PDF: skipped %s unsafe panel(s)", skipped)

    # Await ensures every HTTP URL is tried (with retries) before layout starts.
    resolved_assets, owned_paths = await prefetch_lesson_pdf_assets_async(
        package,
        include,
        client=http_client,
        shared_image_cache=shared_image_cache,
    )
    missing_imgs = _log_prefetch_image_outcomes(package, include, resolved_assets)

    include_comic: list[dict[str, Any]] = []
    for p in include:
        if _panel_ready_for_comic_pdf(p, resolved_assets):
            include_comic.append(p)
        elif p.get("safe", True) and str(p.get("image_url") or "").strip():
            logger.error(
                "PDF skipping panel_number=%s (image unreachable or corrupt after "
                "prefetch) url=%s",
                p.get("panel_number", "?"),
                str(p.get("image_url") or "")[:120],
            )
        elif p.get("safe", True):
            logger.warning(
                "PDF skipping panel_number=%s (no image_url)",
                p.get("panel_number", "?"),
            )

    omitted = len(include) - len(include_comic)
    if omitted:
        logger.warning(
            "PDF comic: omitted %s panel(s) without usable images (order preserved "
            "for remaining)",
            omitted,
        )

    try:
        return _compose_pdf_sync(
            package,
            include_comic,
            resolved_assets,
            prefetch_missing_panel_images=missing_imgs,
            panels_omitted_no_image=omitted,
        )
    finally:
        if shared_image_cache is None:
            for pth in owned_paths:
                try:
                    Path(pth).unlink(missing_ok=True)
                except OSError:
                    pass


def build_pdf_bytes(
    package: dict[str, Any],
    *,
    exclude_unsafe: bool = True,
    shared_image_cache: dict[str, str] | None = None,
) -> bytes:
    """
    Sync wrapper for Streamlit and scripts (spawns a fresh event loop).

    Prefer ``await build_pdf_bytes_async`` inside FastAPI handlers.
    """
    return asyncio.run(
        build_pdf_bytes_async(
            package,
            exclude_unsafe=exclude_unsafe,
            shared_image_cache=shared_image_cache,
        )
    )


def export_pdf(
    package: dict[str, Any] | None,
    *,
    exclude_unsafe: bool = True,
    download_key: str = "pdf_download",
    topic: str = "",
    country: str = "",
    grade: str | int = "",
    shared_image_cache: dict[str, str] | None = None,
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

    pdf_bytes = build_pdf_bytes(
        package,
        exclude_unsafe=exclude_unsafe,
        shared_image_cache=shared_image_cache,
    )
    st.download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name=_build_filename(topic, country, grade),
        mime="application/pdf",
        key=download_key,
    )
