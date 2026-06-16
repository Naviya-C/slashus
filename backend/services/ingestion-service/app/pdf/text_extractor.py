import pymupdf

from sinhala.converter import SinhalaTextConverter

def get_page_text_blocks(
    pdf_path: str, 
    page_number: int, 
    converter: SinhalaTextConverter
    ) -> list[dict]:
    
    doc = pymupdf.open(pdf_path)
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