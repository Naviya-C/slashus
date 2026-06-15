"""
Sinhala Textbook PDF Ingestion Pipeline
========================================
Converts a PDF into a structured JSON tree of blocks.
Each block is one of: paragraph | table | image
Each block carries hierarchical metadata:
  title, subtitle, sub_subtitles, page_number, block_index, etc.

Strategy:
  1. Detect legacy Sinhala font encoding (FM Abhaya, FM Malithi, etc.)
  2. Auto-convert legacy ASCII-mapped Sinhala → Unicode via Pandukabhaya
  3. Use PyMuPDF for layout-aware text extraction with font sizes
  4. Use pdfplumber for table detection
  5. Use PyMuPDF for image extraction
  6. Claude Vision (Anthropic API) — called ONLY on pages that have images
     Pages with no images: font-size heuristics handle heading detection
  7. Assemble the final JSON tree

Anthropic API is lazy-imported — only loaded when a page has images.
No API key needed if your PDF has no images.
"""

import fitz
import pdfplumber
import json
import base64
import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from pandukabhaya import Converter as PandukabhayaConverter


# ──────────────────────────────────────────────────────────────────
# Legacy font detection
# ──────────────────────────────────────────────────────────────────

LEGACY_FONT_PATTERNS = [
    r"fm[\.\-_]?abhaya",
    r"fm[\.\-_]?malithi",
    r"fm[\.\-_]?gemunu",
    r"fm[\.\-_]?bindumathi",
    r"fm[\.\-_]?yazida",
    r"fm[\.\-_]?gangani",
    r"fm[\.\-_]?champa",
    r"fm[\.\-_]?suwaya",
    r"fm[\.\-_]?sunil",
    r"fm[\.\-_]?ridi",
    r"fm[\.\-_]?paras",
    r"fm[\.\-_]?nirmali",
    r"fm[\.\-_]?kaputa",
    r"fm[\.\-_]?arjuna",
    r"wijeya",
    r"dinamina",
    r"iskoola[\.\-_]?pota",
]

FONT_TO_MAPPING: dict[str, str] = {
    "fm_abhaya":     "fm_abhaya",
    "fm_malithi":    "fm_abhaya",
    "fm_gemunu":     "fm_abhaya",
    "fm_bindumathi": "fm_abhaya",
    "wijeya":        "fm_abhaya",
    "dinamina":      "fm_abhaya",
}


def _normalise_font_name(name: str) -> str:
    return name.lower().replace(" ", ".").replace("-", ".").replace("_", ".")


def detect_legacy_font(pdf_path: str) -> tuple[bool, str]:
    doc = fitz.open(pdf_path)
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_name = _normalise_font_name(span.get("font", ""))
                    for pat in LEGACY_FONT_PATTERNS:
                        if re.search(pat, font_name):
                            doc.close()
                            return True, _resolve_mapping(font_name)
    doc.close()
    return False, ""


def _resolve_mapping(normalised_font_name: str) -> str:
    for key in FONT_TO_MAPPING:
        if key.replace("_", ".") in normalised_font_name:
            return FONT_TO_MAPPING[key]
    return "fm_abhaya"


def has_sinhala_unicode(text: str) -> bool:
    return bool(re.search(r"[\u0d80-\u0dff]", text))


def looks_like_legacy_ascii_sinhala(text: str) -> bool:
    if has_sinhala_unicode(text):
        return False
    stripped = text.strip()
    if not stripped:
        return False
    special = len(re.findall(r'[%\$\#\@\!\*\+\=\^\&\;\:\,\<\>\?\/\\\|\~\`\'\"]', stripped))
    return (special / len(stripped)) > 0.08


# ──────────────────────────────────────────────────────────────────
# Text converter
# ──────────────────────────────────────────────────────────────────

class SinhalaTextConverter:
    def __init__(self, is_legacy: bool, mapping: str = "fm_abhaya"):
        self.is_legacy = is_legacy
        self.mapping = mapping
        self._converter: Optional[PandukabhayaConverter] = None
        if is_legacy:
            try:
                self._converter = PandukabhayaConverter(mapping)
                print(f"  🔤 Legacy font detected → Pandukabhaya loaded (mapping: {mapping})")
            except FileNotFoundError:
                print(f"  ⚠ Mapping '{mapping}' not found. Falling back to fm_abhaya.")
                self._converter = PandukabhayaConverter("fm_abhaya")

    def convert(self, text: str) -> str:
        if self._converter is not None:
            return self._converter.convert(text)
        if looks_like_legacy_ascii_sinhala(text):
            return PandukabhayaConverter("fm_abhaya").convert(text)
        return text


# ──────────────────────────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────────────────────────

@dataclass
class BlockMetadata:
    title: Optional[str] = None
    subtitle: Optional[str] = None
    sub_subtitles: list[str] = field(default_factory=list)
    page_number: int = 0
    block_index: int = 0
    block_type: str = "paragraph"
    font_size_hint: Optional[float] = None
    encoding_converted: bool = False


@dataclass
class Block:
    block_type: str
    content: str | list | dict
    metadata: BlockMetadata


# ──────────────────────────────────────────────────────────────────
# PDF extraction helpers
# ──────────────────────────────────────────────────────────────────

def page_has_images(pdf_path: str, page_number: int) -> bool:
    """Quick check — does this page contain any embedded images?"""
    doc = fitz.open(pdf_path)
    has_img = len(doc[page_number].get_images(full=True)) > 0
    doc.close()
    return has_img


def pdf_page_to_base64_image(pdf_path: str, page_number: int, dpi: int = 150) -> str:
    """Rasterise a page to JPEG base64 (only called when page has images)."""
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("jpeg")
    doc.close()
    return base64.b64encode(img_bytes).decode("utf-8")


def get_page_text_blocks(
    pdf_path: str,
    page_number: int,
    converter: SinhalaTextConverter,
) -> list[dict]:
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    blocks = page.get_text("dict")["blocks"]
    doc.close()

    text_blocks = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        lines_text = []
        max_font_size = 0.0
        was_converted = False
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                raw = span.get("text", "")
                converted = converter.convert(raw)
                if converted != raw:
                    was_converted = True
                lines_text.append(converted)
                fs = span.get("size", 0.0)
                if fs > max_font_size:
                    max_font_size = fs
        full_text = " ".join(lines_text).strip()
        if full_text:
            text_blocks.append({
                "text": full_text,
                "font_size": round(max_font_size, 1),
                "bbox": block.get("bbox"),
                "block_no": block.get("number"),
                "encoding_converted": was_converted,
            })
    return text_blocks


def extract_tables_on_page(
    pdf_path: str,
    page_number: int,
    converter: SinhalaTextConverter,
) -> list[dict]:
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number]
        raw_tables = page.extract_tables()
        for i, tbl in enumerate(raw_tables):
            cleaned = [
                [converter.convert(cell or "") for cell in row]
                for row in tbl
            ]
            tables.append({
                "table_index_on_page": i,
                "rows": cleaned,
                "num_rows": len(cleaned),
                "num_cols": len(cleaned[0]) if cleaned else 0,
            })
    return tables


def extract_images_on_page(
    pdf_path: str,
    page_number: int,
    output_dir: str,
) -> list[dict]:
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    image_list = page.get_images(full=True)
    extracted = []
    for img_index, img in enumerate(image_list):
        xref = img[0]
        base_image = doc.extract_image(xref)
        ext = base_image["ext"]
        img_bytes = base_image["image"]
        filename = f"page{page_number + 1}_img{img_index + 1}.{ext}"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(img_bytes)
        extracted.append({
            "filename": filename,
            "filepath": filepath,
            "width": base_image.get("width"),
            "height": base_image.get("height"),
            "colorspace": base_image.get("colorspace"),
            "size_bytes": len(img_bytes),
        })
    doc.close()
    return extracted


# ──────────────────────────────────────────────────────────────────
# Heading detection — two modes
# ──────────────────────────────────────────────────────────────────

# ── Mode A: heuristic (no API) — used for text/table-only pages ──

def _heuristic_heading_level(font_size: float, all_sizes: list[float]) -> Optional[int]:
    if not all_sizes:
        return None
    body = sorted(all_sizes)[len(all_sizes) // 2]
    if font_size >= body * 1.6:
        return 1
    elif font_size >= body * 1.3:
        return 2
    elif font_size >= body * 1.1:
        return 3
    return None


def classify_page_heuristic(
    text_blocks: list[dict],
    page_tables: list[dict],
    page_images: list[dict],   # will always be empty in this path
) -> dict:
    """Font-size based classification. No API call. Used when page has no images."""
    all_sizes = [tb["font_size"] for tb in text_blocks if tb["font_size"] > 0]
    heading_ctx: dict = {"title": None, "subtitle": None, "sub_subtitles": []}
    blocks_out = []

    for i in range(len(page_tables)):
        blocks_out.append({
            "block_type": "table",
            "table_index_on_page": i,
            "font_size_hint": None,
        })

    for tb in text_blocks:
        level = _heuristic_heading_level(tb["font_size"], all_sizes)
        if level is not None:
            text = tb["text"].strip()
            if level == 1:
                heading_ctx.update({"title": text, "subtitle": None, "sub_subtitles": []})
            elif level == 2:
                heading_ctx.update({"subtitle": text, "sub_subtitles": []})
            elif level == 3 and text not in heading_ctx["sub_subtitles"]:
                heading_ctx["sub_subtitles"].append(text)
            blocks_out.append({
                "block_type": "heading",
                "text": tb["text"],
                "heading_level": level,
                "font_size_hint": tb["font_size"],
            })
        else:
            blocks_out.append({
                "block_type": "paragraph",
                "text": tb["text"],
                "font_size_hint": tb["font_size"],
            })

    return {"page_heading_context": heading_ctx, "blocks": blocks_out}


# ── Mode B: Claude Vision — used only when page has images ────────

SYSTEM_PROMPT = """You are an expert document structure analyser specialising in Sinhala educational textbooks.
Analyse the page image and the extracted text blocks, then return a structured JSON.
Text blocks are already converted to Unicode Sinhala.

Return ONLY valid JSON — no markdown fences, no explanation.

Output schema:
{
  "page_heading_context": {
    "title": "<H1 heading or null>",
    "subtitle": "<H2 heading or null>",
    "sub_subtitles": ["<H3+ headings>"]
  },
  "blocks": [
    {
      "block_type": "paragraph" | "table" | "image" | "heading",
      "text": "<Sinhala text for paragraph/heading blocks>",
      "content_summary": "<one-line English summary>",
      "heading_level": 1 | 2 | 3 | null,
      "font_size_hint": <number or null>,
      "table_index_on_page": <0-based int or null>,
      "image_index_on_page": <0-based int or null>
    }
  ]
}

Rules:
- Detect headings by font size, bold style, position, and Sinhala numbering.
- For images/diagrams set block_type "image" and image_index_on_page.
- Preserve all Sinhala text exactly as-is in the "text" field.
- Maintain top-to-bottom reading order.
"""


def analyse_page_with_claude(
    client,          # anthropic.Anthropic — passed in, not imported here
    page_image_b64: str,
    text_blocks: list[dict],
    page_number: int,
) -> dict:
    """Call Claude Vision. Only invoked when page_has_images() is True."""
    text_blocks_json = json.dumps(text_blocks, ensure_ascii=False, indent=2)
    user_message = (
        f"Page number: {page_number + 1}\n\n"
        f"Extracted text blocks:\n{text_blocks_json}\n\n"
        "Return the structured JSON."
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": page_image_b64,
                    },
                },
                {"type": "text", "text": user_message},
            ],
        }],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"```$", "", raw).strip()
    return json.loads(raw)


# ──────────────────────────────────────────────────────────────────
# Block assembler (shared by both modes)
# ──────────────────────────────────────────────────────────────────

def assemble_blocks(
    page_analysis: dict,
    page_tables: list[dict],
    page_images: list[dict],
    page_number: int,
    block_counter: list[int],
    heading_context: dict,
    encoding_converted: bool,
) -> list[Block]:
    ctx = page_analysis.get("page_heading_context", {})
    if ctx.get("title"):
        heading_context["title"] = ctx["title"]
    if ctx.get("subtitle"):
        heading_context["subtitle"] = ctx["subtitle"]
    if ctx.get("sub_subtitles"):
        heading_context["sub_subtitles"] = ctx["sub_subtitles"]

    blocks_out: list[Block] = []

    for raw_block in page_analysis.get("blocks", []):
        btype = raw_block.get("block_type", "paragraph")

        # Headings update context but are not stored as blocks
        if btype == "heading":
            level = raw_block.get("heading_level")
            text = raw_block.get("text", "").strip()
            if level == 1:
                heading_context.update({"title": text, "subtitle": None, "sub_subtitles": []})
            elif level == 2:
                heading_context.update({"subtitle": text, "sub_subtitles": []})
            elif level == 3 and text:
                if text not in heading_context["sub_subtitles"]:
                    heading_context["sub_subtitles"].append(text)
            continue

        meta = BlockMetadata(
            title=heading_context.get("title"),
            subtitle=heading_context.get("subtitle"),
            sub_subtitles=list(heading_context.get("sub_subtitles", [])),
            page_number=page_number + 1,
            block_index=block_counter[0],
            block_type=btype,
            font_size_hint=raw_block.get("font_size_hint"),
            encoding_converted=encoding_converted,
        )

        if btype == "table":
            tbl_idx = raw_block.get("table_index_on_page", 0)
            content = page_tables[tbl_idx] if tbl_idx < len(page_tables) else {"rows": []}
        elif btype == "image":
            img_idx = raw_block.get("image_index_on_page", 0)
            content = page_images[img_idx] if img_idx < len(page_images) else {"filename": "unknown"}
            content["content_summary"] = raw_block.get("content_summary", "")
        else:
            content = raw_block.get("text", raw_block.get("content_summary", ""))

        blocks_out.append(Block(block_type=btype, content=content, metadata=meta))
        block_counter[0] += 1

    return blocks_out


# ──────────────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────────────

def process_pdf(
    pdf_path: str,
    output_json_path: str,
    image_output_dir: Optional[str] = None,
    start_page: int = 0,
    end_page: Optional[int] = None,
    api_key: Optional[str] = None,
    force_legacy_mapping: Optional[str] = None,
) -> dict:
    """
    Full ingestion pipeline.

    Args:
        pdf_path:             Path to input PDF.
        output_json_path:     Where to write the output JSON.
        image_output_dir:     Directory for extracted images.
        start_page:           0-based start page index (default 0).
        end_page:             0-based exclusive end page (default: all pages).
                              e.g. start_page=0, end_page=5 → pages 1–5 only.
        api_key:              Anthropic API key (or ANTHROPIC_API_KEY env var).
                              Only needed if the PDF contains images.
        force_legacy_mapping: Override font auto-detection (e.g. 'fm_abhaya').
    """
    pdf_path = str(Path(pdf_path).resolve())
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if image_output_dir is None:
        image_output_dir = str(Path(output_json_path).parent / "extracted_images")
    os.makedirs(image_output_dir, exist_ok=True)

    # ── Legacy font detection ──────────────────────────────────
    if force_legacy_mapping:
        is_legacy, mapping = True, force_legacy_mapping
        print(f"  🔤 Forced legacy mapping: {mapping}")
    else:
        print("  🔍 Scanning fonts for legacy Sinhala encoding...")
        is_legacy, mapping = detect_legacy_font(pdf_path)
        if is_legacy:
            print(f"  ✅ Legacy font detected → mapping: {mapping}")
        else:
            print("  ✅ Unicode font — no conversion needed")

    converter = SinhalaTextConverter(is_legacy, mapping)

    # ── Page range ────────────────────────────────────────────
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    # Clamp to valid range
    start_page = max(0, start_page)
    ep = min(end_page if end_page is not None else total_pages, total_pages)

    print(f"\n📄 {Path(pdf_path).name}")
    print(f"   Total pages : {total_pages}")
    print(f"   Processing  : pages {start_page + 1} → {ep}")

    # ── Lazy Anthropic client — only created if any page has images ──
    _anthropic_client = None

    def get_client():
        nonlocal _anthropic_client
        if _anthropic_client is None:
            import anthropic as _anthropic
            key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise ValueError(
                    "This PDF contains images. Set ANTHROPIC_API_KEY or pass --api-key "
                    "so Claude Vision can describe them."
                )
            _anthropic_client = _anthropic.Anthropic(api_key=key)
            print("  🤖 Anthropic client initialised (page has images)")
        return _anthropic_client

    # ── Per-page processing ───────────────────────────────────
    all_blocks: list[Block] = []
    block_counter = [0]
    heading_context: dict = {"title": None, "subtitle": None, "sub_subtitles": []}
    api_calls = 0

    for page_idx in range(start_page, ep):
        has_img = page_has_images(pdf_path, page_idx)
        mode = "claude-vision" if has_img else "heuristic"
        print(f"  ▶ Page {page_idx + 1}/{ep}  [{mode}]", end=" ... ", flush=True)

        text_blocks = get_page_text_blocks(pdf_path, page_idx, converter)
        page_tables = extract_tables_on_page(pdf_path, page_idx, converter)
        page_images = extract_images_on_page(pdf_path, page_idx, image_output_dir)

        if has_img:
            # ── Pages WITH images → Claude Vision ─────────────
            page_image_b64 = pdf_page_to_base64_image(pdf_path, page_idx)
            try:
                page_analysis = analyse_page_with_claude(
                    get_client(), page_image_b64, text_blocks, page_idx
                )
                api_calls += 1
            except Exception as e:
                print(f"\n     ⚠ Claude error: {e} — falling back to heuristic")
                page_analysis = classify_page_heuristic(text_blocks, page_tables, page_images)
        else:
            # ── Pages with NO images → heuristic only, zero API cost ──
            page_analysis = classify_page_heuristic(text_blocks, page_tables, page_images)

        page_blocks = assemble_blocks(
            page_analysis, page_tables, page_images,
            page_idx, block_counter, heading_context,
            encoding_converted=is_legacy,
        )
        all_blocks.extend(page_blocks)
        print(f"✓  ({len(page_blocks)} blocks)")

    # ── Final document ────────────────────────────────────────
    document = {
        "document": {
            "source_file":     Path(pdf_path).name,
            "total_pages":     total_pages,
            "processed_pages": ep - start_page,
            "page_range":      f"{start_page + 1}–{ep}",
            "total_blocks":    len(all_blocks),
            "api_calls_made":  api_calls,
            "encoding": {
                "legacy_font_detected": is_legacy,
                "pandukabhaya_mapping": mapping if is_legacy else None,
            },
        },
        "blocks": [
            {
                "block_index": b.metadata.block_index,
                "block_type":  b.block_type,
                "content":     b.content,
                "metadata": {
                    "title":              b.metadata.title,
                    "subtitle":           b.metadata.subtitle,
                    "sub_subtitles":      b.metadata.sub_subtitles,
                    "page_number":        b.metadata.page_number,
                    "font_size_hint":     b.metadata.font_size_hint,
                    "encoding_converted": b.metadata.encoding_converted,
                },
            }
            for b in all_blocks
        ],
    }

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done → {output_json_path}")
    print(f"   Blocks extracted : {len(all_blocks)}")
    print(f"   API calls made   : {api_calls}  "
          f"({'only on image pages' if api_calls else 'none — no images found'})")
    return document


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sinhala Textbook PDF → JSON Block Tree"
    )
    parser.add_argument("pdf", help="Path to input PDF")
    parser.add_argument("-o", "--output", default=None,
                        help="Output JSON path (default: <pdf>_blocks.json)")
    parser.add_argument("--images-dir", default=None,
                        help="Directory to save extracted images")
    parser.add_argument("--start-page", type=int, default=1,
                        help="First page to process, 1-based (default: 1)")
    parser.add_argument("--end-page", type=int, default=None,
                        help="Last page to process, 1-based inclusive (default: all)")
    parser.add_argument("--api-key", default=None,
                        help="Anthropic API key — only needed if PDF has images")
    parser.add_argument("--legacy-mapping", default=None,
                        help="Force Pandukabhaya mapping e.g. fm_abhaya")
    args = parser.parse_args()

    # Convert 1-based CLI args to 0-based internal indices
    start_0 = args.start_page - 1
    end_0   = args.end_page if args.end_page is None else args.end_page  # end is exclusive internally

    output = args.output or str(Path(args.pdf).with_suffix("")) + "_blocks.json"
    process_pdf(
        pdf_path=args.pdf,
        output_json_path=output,
        image_output_dir=args.images_dir,
        start_page=start_0,
        end_page=end_0,
        api_key=args.api_key,
        force_legacy_mapping=args.legacy_mapping,
    )
