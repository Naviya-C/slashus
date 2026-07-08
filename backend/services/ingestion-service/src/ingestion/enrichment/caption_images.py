"""
enrichment/caption_images.py
============================

PURPOSE
-------
The enrichment STAGE for images. Given the ExtractedImage objects from
image_extractor, attach a caption to each by calling the ImageCaptioner port.
The caption is BOTH the image chunk's content and its embed text.

FAILURE ISOLATION
-----------------
A vision LLM call can fail (network, quota, safety block, unreadable image). One
bad image must not kill the ingest, so a failed caption falls back to a
deterministic placeholder ("Image (WxH) on the page."). The pipeline moves on.

CACHING (later)
---------------
Captions are expensive and are pure functions of the image bytes, so cache by a
hash of the bytes (utils/caching.py) -- a reused textbook figure then costs one
call, not thousands. Left as a wrap point.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.ingestion.extraction.image_extractor import ExtractedImage


# map PyMuPDF ext -> mime type Gemini expects
_MIME = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "bmp": "image/bmp",
}


@dataclass
class CaptionedImage:
    """An image plus its caption. caption = chunk content AND embed text."""

    image: ExtractedImage
    caption: str


def _mime_for(ext: str) -> str:
    return _MIME.get(ext.lower(), "image/png")


def _fallback(image: ExtractedImage) -> str:
    return f"Image ({image.width}x{image.height}) on the page."


def caption_images(
    images: list[ExtractedImage],
    captioner,
    context: str = "",
) -> list[CaptionedImage]:
    """Attach a caption to each image via the captioner port.

    Args:
        images: from image_extractor.extract_images.
        captioner: an ImageCaptioner (real Gemini adapter, or a fake).
        context: optional grounding text (nearby caption + section title).

    Returns:
        list[CaptionedImage] in the same order.
    """
    out: list[CaptionedImage] = []
    for image in images:
        try:
            caption = captioner.caption(image.data, _mime_for(image.ext), context=context).strip()
            if not caption:
                caption = _fallback(image)
        except Exception:
            caption = _fallback(image)  # isolate failure, keep going
        out.append(CaptionedImage(image=image, caption=caption))
    return out