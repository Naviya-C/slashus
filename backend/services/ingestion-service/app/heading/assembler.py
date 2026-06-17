from models.block import Block
from models.metadata import BlockMetadata
from models.assemble import Assemble

def assemble_blocks(context: Assemble) -> list[Block]:
    ctx = context.page_analysis.get("page_heading_context", {})
    if ctx.get("title"):
        context.heading_context["title"] = ctx["title"]
    if ctx.get("subtitle"):
        context.heading_context["subtitle"] = ctx["subtitle"]
    if ctx.get("sub_subtitles"):
        context.heading_context["sub_subtitles"] = ctx["sub_subtitles"]

    blocks_out: list[Block] = []

    for raw_block in context.page_analysis.get("blocks", []):
        btype = raw_block.get("block_type", "paragraph")

        # Headings update context but are not stored as blocks
        if btype == "heading":
            level = raw_block.get("heading_level")
            text = raw_block.get("text", "").strip()
            if level == 1:
                context.heading_context.update({"title": text, "subtitle": None, "sub_subtitles": []})
            elif level == 2:
                context.heading_context.update({"subtitle": text, "sub_subtitles": []})
            elif level == 3 and text:
                if text not in context.heading_context["sub_subtitles"]:
                    context.heading_context["sub_subtitles"].append(text)
            continue

        meta = BlockMetadata(
            title = context.heading_context.get("title"),
            subtitle = context.heading_context.get("subtitle"),
            sub_subtitles=list(context.heading_context.get("sub_subtitles", [])),
            page_number = context.page_number + 1,
            block_index = context.block_counter[0],
            block_type = btype,
            font_size_hint = raw_block.get("font_size_hint"),
            encoding_converted = context.encoding_converted,
        )

        if btype == "table":
            tbl_idx = raw_block.get("table_index_on_page", 0)
            content = context.page_tables[tbl_idx] if tbl_idx < len(context.page_tables) else {"rows": []}
        elif btype == "image":
            img_idx = raw_block.get("image_index_on_page", 0)
            content = context.page_images[img_idx] if img_idx < len(context.page_images) else {"filename": "unknown"}
            content["content_summary"] = raw_block.get("content_summary", "")
        else:
            content = raw_block.get("text", raw_block.get("content_summary", ""))

        blocks_out.append(Block(block_type=btype, content=content, metadata=meta))
        context.block_counter[0] += 1

    return blocks_out

