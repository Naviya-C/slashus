from pathlib import Path

import os
import pymupdf
import json
import anthropic 


from app.pdf.font_detector import detect_legacy_font
from app.pdf.image_extractor import page_has_images, extract_images_on_page
from app.pdf.text_extractor import get_page_text_blocks
from app.pdf.table_extractor import extract_tables_on_page
from app.pdf.page_renderer import pdf_page_to_base64_image
from app.pdf.check_box_overlap import intersects

from app.sinhala.converter import SinhalaTextConverter

from app.heading.heuristic import classify_page_heuristic
from app.heading.assembler import assemble_blocks
from app.heading.claude_analyzer import analyse_page_with_claude

from app.models.text_extract import PageContext
from app.models.assemble import Assemble
from app.models.block import Block
from app.models.processPDF import ProcessPDF

from app.rag.chunking.chunker import chunking
from app.rag.embedding.embedder import embed_texts
from app.rag.vectorDB.vector_store import (
    create_collection,
    create_payload_indexes,
    upload_chunks,
)


def process_pdf(context: ProcessPDF) -> dict:
    """
    Full ingestion pipeline.

    context Args:
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
    
    # ── Paths extracting ──────────────────────────────────-----
    pdf_path = str(Path(context.pdf_path).resolve())
    pdf_name = Path(pdf_path).stem
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    image_output_dir = str(Path(context.image_output_dir).resolve())
    if image_output_dir is None:
        image_output_dir = str(Path(context.output_json_path).parent / f"extracted_images{pdf_name}")
        os.makedirs(image_output_dir, exist_ok = True)

    # ── Legacy font detection ──────────────────────────────────
    if context.force_legacy_mapping:
        is_legacy, mapping = True, context.force_legacy_mapping
        print(f"🔤 Forced legacy mapping: {mapping}")
    else:
        print("🔍 Scanning fonts for legacy Sinhala encoding...")
        is_legacy, mapping = detect_legacy_font(pdf_path)
        if is_legacy:
            print(f"✅ Legacy font detected → mapping: {mapping}")
        else:
            print("✅ Unicode font — no conversion needed")

    converter = SinhalaTextConverter(is_legacy, mapping)

    # ── Page range ────────────────────────────────────────────
    """
    This is for temporary until system able to pass first few pages(e.g: table of content) 
    """
    
    
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    # Clamp to valid range
    start_page = max(0, context.start_page)
    ep = min(context.end_page if context.end_page is not None else total_pages, total_pages)

    print(f"\n📄 {Path(pdf_path).name}")
    print(f"   Total pages : {total_pages}")
    print(f"   Processing  : pages {start_page + 1} → {ep}")

    # ── Anthropic client — only start if any page has images ──
    _anthropic_client = None

    def get_client():
        nonlocal _anthropic_client
        if _anthropic_client is None:
            import anthropic as _anthropic
            key = context.api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise ValueError(
                    "This PDF contains images. Set ANTHROPIC_API_KEY or pass --api-key "
                )
            _anthropic_client = _anthropic.Anthropic(api_key = key)
            print("🤖 Anthropic client initialised (page has images)")
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
        
        context_block = PageContext(
            pdf_path,
            page_idx,
            converter
        )

        text_blocks = get_page_text_blocks(context_block)
        page_tables = extract_tables_on_page(context_block)
        page_images = extract_images_on_page(pdf_path, page_idx, image_output_dir)
        
        """
        text_blocks and page_table both extract table different way, detect the tables inside the textblock and remove from text_blocks
        cause page_tables already extract it.
        Avoid the redundent table extraction.
        """
        
        # Calculate font sizes once
        all_sizes = [
            tb["font_size"]
            for tb in text_blocks
            if tb["font_size"] > 0
        ]

        max_font_size = max(all_sizes) if all_sizes else 0

        filtered_blocks = []

        for block in text_blocks:

            # Never remove large text blocks
            if block["font_size"] >= max_font_size * 0.8:
                filtered_blocks.append(block)
                continue

            inside_table = False

            for table in page_tables:
                if intersects(block["bbox"], table["bbox"]):
                    inside_table = True
                    break

            if not inside_table:
                filtered_blocks.append(block)

        text_blocks = filtered_blocks
        
        ### ==============Debug================ ###
        """
        for tb in text_blocks:
            print(
                f"FONT={tb['font_size']} "
                f"TEXT={tb['text'][:100]}"
            )
        """
        # ========================================

        if has_img:
            # ── Pages WITH images─────────────
            page_image_b64 = pdf_page_to_base64_image(pdf_path, page_idx)
            try:
                page_analysis = analyse_page_with_claude(
                    get_client(), page_image_b64, text_blocks, page_idx
                )
                api_calls += 1
            except Exception as e:
                print(f"\n     ⚠ Claude error: {e} — falling back to heuristic")
                page_analysis = classify_page_heuristic(text_blocks, page_tables)
        else:
            # ── Pages with NO images → heuristic only, zero API cost ──
            
            page_analysis = classify_page_heuristic(text_blocks, page_tables)
            
        context_page_block = Assemble(
            page_analysis,
            page_tables,
            page_images,
            page_idx,
            block_counter,
            heading_context,
            encoding_converted = is_legacy
        )

        page_blocks = assemble_blocks(context_page_block)
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
    
    # ======= Chunking ==============================
    
    print("\n📦 Creating chunks...")
    chunks = chunking(document)
    print(f"   Chunks: {len(chunks)}")
    
    print("🧠 Generating embeddings...")
    
    
    # =================== Embedding ================================

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    vectors = embed_texts(texts)

    print(f"Embeddings: {len(vectors)}")
    
    
    # ========= Create Qdrant Collection =============================
    
    print("🗄️ Preparing Qdrant collection...")

    create_collection()
    create_payload_indexes()
    
    # =============== Uploading Chunks to Qdrant ======================
    
    print("⬆️ Uploading vectors...")

    upload_chunks(
        chunks,
        vectors,
    )

    print("✅ Upload complete")
    
    # ================= Finish uploading ==============================
    
    print(f"\n✅ Done")
    print(f"   Blocks   : {len(all_blocks)}")
    print(f"   Chunks   : {len(chunks)}")
    print(f"   Vectors  : {len(vectors)}")
    print(f"   API calls: {api_calls}")

    return {
        "source_file": Path(pdf_path).name,
        "blocks_extracted": len(all_blocks),
        "chunks_created": len(chunks),
        "vectors_uploaded": len(vectors),
    }

    """
    with open(context.output_json_path, "w", encoding="utf-8") as f:
    json.dump(document, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done → {context.output_json_path}")
    print(f"   Blocks extracted : {len(all_blocks)}")
    print(f"   API calls made   : {api_calls}  "
          f"({'only on image pages' if api_calls else 'none — no images found'})")
    return document
    """



if __name__ == "__main__":
    
    context = ProcessPDF(
        "/home/naviya-c/Downloads/grade-10-sinhala.pdf",
        "/home/naviya-c/Downloads/output.json",
        "/home/naviya-c/Downloads" ,
        start_page = 10,
        end_page = 15,
    )
    
    process_pdf(context) 
    