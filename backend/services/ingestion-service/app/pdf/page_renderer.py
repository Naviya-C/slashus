import pymupdf, base64

def pdf_page_to_base64_image(pdf_path: str, page_number: int, dpi: int = 150) -> str:
    """Rasterise a page to JPEG base64 (only called when page has images).
        UseCase:
            1) PDF pages has scanned.
            2) If PDF contains redable images, e.g:- Diagrams and others.
            
        LLM like Claude can't directly read those, Therefore should need to :
                                    PDF Page
                                       ↓
                            Render page as image
                                       ↓
                            Convert image to Base64
                                       ↓
                            Send to Claude Vision
                                       ↓
                            Get structured analysis
    """
    doc = pymupdf.open(pdf_path)
    page = doc[page_number]
    mat = pymupdf.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("jpeg")
    doc.close()
    return base64.b64encode(img_bytes).decode("utf-8")