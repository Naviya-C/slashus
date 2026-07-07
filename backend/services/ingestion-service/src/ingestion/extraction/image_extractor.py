"""
extraction/image_extractor.py
=============================

PURPOSE
-------
Pull the raster images off a page and keep only the ones worth captioning. Each
survivor becomes ONE image chunk later:
    * bytes  -> stored in object storage (storage step, separate)
    * caption from a vision LLM -> the chunk content + what you embed (enrichment)
This module does the DETERMINISTIC half only: extract + filter. No LLM, no
storage, no chunk assembly.

WHY FILTER
----------
A page is full of raster junk that is not a "figure": logos, header/footer marks,
bullet glyphs, and horizontal rules (a rule is a wide image only 1-3 px tall).
Captioning those wastes LLM calls and adds noise chunks. So we drop images that
are too small in PIXELS (icons/bullets) or cover too little PAGE AREA (stray
marks). A thin rule fails the pixel-height gate; a bullet fails both.

WHAT IT RETURNS
---------------
ExtractedImage(data, ext, width, height, bbox, xref). One entry per distinct
image (xref); if the same image is placed several times we keep its largest
placement. Multi-column / repeated-placement figures are a later concern.

NOTE
----
Runs on DIGITAL pages (scanned pages go to OCR, not here). The bytes + bbox let a
later step store the image and ground the caption with nearby text.
"""

from __future__ import annotations
 
from dataclasses import dataclass


# ---- tunable filter thresholds (drop anything below these) ----
MIN_PIXEL_WIDTH = 50     # px: narrower than this -> icon / bullet / rule
MIN_PIXEL_HEIGHT = 50    # px: shorter than this  -> icon / bullet / rule
MIN_AREA_RATIO = 0.01    # fraction of page area: smaller -> stray mark


@dataclass
class ExtractedImage:
    """One raster image kept for captioning."""

    data: bytes                                      # raw image bytes
    ext: str                                         # 'png', 'jpeg', ...
    width: int                                       # pixel width
    height: int                                      # pixel height
    bbox: tuple[float, float, float, float]          # placement on the page
    xref: int                                        # PyMuPDF image id


def extract_images(
    page,
    *,
    min_width: int = MIN_PIXEL_WIDTH,
    min_height: int = MIN_PIXEL_HEIGHT,
    min_area_ratio: float = MIN_AREA_RATIO,
) -> list[ExtractedImage]:
    """Extract raster images from a page, dropping tiny/thin ones.

    Args:
        page: a PyMuPDF `fitz.Page`.
        min_width / min_height: pixel gates (reject icons, bullets, thin rules).
        min_area_ratio: minimum fraction of page area the image must cover.

    Returns:
        list[ExtractedImage] worth captioning.
    """
    doc = page.parent
    page_area = (page.rect.width * page.rect.height) or 1.0

    kept: list[ExtractedImage] = []
    seen: set[int] = set()

    for img in page.get_images(full=True):
        xref = img[0]
        if xref in seen:
            continue
        seen.add(xref)

        rects = page.get_image_rects(xref)
        if not rects:
            continue
        rect = max(rects, key=lambda r: abs(r))  # largest placement

        try:
            info = doc.extract_image(xref)
        except Exception:
            continue  # unreadable image -> skip, don't kill the page
        if not info or not info.get("image"):
            continue

        width, height = info["width"], info["height"]
        area_ratio = abs(rect) / page_area

        # filter: pixel gates catch icons/bullets/rules; area gate catches marks
        if width < min_width or height < min_height:
            continue
        if area_ratio < min_area_ratio:
            continue

        kept.append(
            ExtractedImage(
                data=info["image"],
                ext=info["ext"],
                width=width,
                height=height,
                bbox=tuple(rect),
                xref=xref,
            )
        )

    return kept