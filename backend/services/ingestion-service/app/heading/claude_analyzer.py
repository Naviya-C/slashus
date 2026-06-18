import re
import json

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

