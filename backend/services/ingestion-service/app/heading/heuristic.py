from typing import Optional

def _heading_level(font_size: float, all_sizes: list[float]) -> Optional[int]:
    """
    This function identify the heading and pass values:
        1 -> H1(Title)
        2 -> H2(Sub-Title)
        3 -> H3(Sub-subtitle)
        None -> Paragraph
    """
    
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
    page_tables: list[dict]
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
        level = _heading_level(tb["font_size"], all_sizes)
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
