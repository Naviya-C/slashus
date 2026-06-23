from uuid import uuid4

def chunking(document):
    pdf_name = document["document"].get("source_file", "")
    all_blocks = document.get("blocks", [])

    chunks = []

    for block in all_blocks:
        text = block.get("content", "")

        if len(text) < 20:
            continue

        metadata = block.get("metadata", {})

        chunks.append(
            {
                "id": str(uuid4()),
                "text": text,
                "metadata": {
                    "title": metadata.get("title"),
                    "subtitle": metadata.get("subtitle"),
                    "sub_subtitles": metadata.get("sub_subtitles"),
                    "page_number": metadata.get("page_number"),
                    "block_type": block.get("block_type"),
                    "source_file": pdf_name,
                },
            }
        )

    return chunks