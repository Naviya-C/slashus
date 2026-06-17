import pymupdf
import os

def page_has_images(pdf_path: str, page_number: int) -> bool:
    """Quick check — does this page contain any embedded images?"""
    doc = pymupdf.open(pdf_path)
    has_img = len(doc[page_number].get_images(full=True)) > 0
    doc.close()
    return has_img


def extract_images_on_page(pdf_path: str, page_number: int, output_dir: str) -> list[dict]:
    doc = pymupdf.open(pdf_path)
    page = doc[page_number]
    image_list = page.get_images(full=True)
    extracted = []
    for img_index, img in enumerate(image_list):
        xref = img[0] # Get the image object id which asssign from pdf.
        base_image = doc.extract_image(xref) # returns the image bytes, means H,W, ext:png,svg,..., 
        ext = base_image["ext"] # Extracting the extenstion of image
        img_bytes = base_image["image"] # Actuall image
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