from __future__ import annotations

import re
from typing import Any, Dict, List

_HEADING_PATTERN = re.compile(r"^(?:#{1,6}\s+.+|(?:Chapter|Chương|第.+章).*)$", re.IGNORECASE)
_LIST_ITEM_PATTERN = re.compile(r"^(?:[-*+]\s+.+|\d+\.\s+.+)$")
_IMAGE_REF_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def _detect_block_type(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return "divider"
    if _HEADING_PATTERN.match(stripped):
        return "heading"
    if _LIST_ITEM_PATTERN.match(stripped):
        return "list_item"
    if "|" in stripped and stripped.count("|") >= 2:
        return "table_text"
    if _IMAGE_REF_PATTERN.search(stripped):
        return "image_ref"
    return "paragraph"


def build_structured_ir_from_text(text: str) -> List[Dict[str, Any]]:
    """Convert plain text to a lightweight semantic block IR."""
    blocks: List[Dict[str, Any]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        block_type = _detect_block_type(line)
        if block_type == "divider" and (not blocks or blocks[-1]["type"] == "divider"):
            continue
        blocks.append(
            {
                "id": f"b{index}",
                "type": block_type,
                "text": line.rstrip(),
                "metadata": {},
            }
        )
    return blocks


def ir_to_plain_text(blocks: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for block in blocks:
        lines.append((block.get("text") or "").rstrip())
    return "\n".join(lines).strip()


def build_structured_ir_from_text_map(text_map: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Map EPUB TEXT_MAP entries (from layout parser) to internal IR blocks.

    Use when tooling or future pipelines need semantic blocks aligned with text_id/chapter_id.
    Image-only nodes become image_ref with empty text (may be skipped by chunkers until enriched).
    """
    blocks: List[Dict[str, Any]] = []
    for entry in text_map:
        tid = str(entry.get("text_id") or "")
        chapter_id = entry.get("chapter_id")
        if entry.get("is_image_only"):
            blocks.append(
                {
                    "id": tid or f"img{len(blocks)}",
                    "type": "image_ref",
                    "text": "",
                    "metadata": {
                        "text_id": tid,
                        "chapter_id": chapter_id,
                        "is_image_only": True,
                    },
                }
            )
            continue
        txt = (entry.get("original_text") or "").strip()
        if not txt:
            continue
        blocks.append(
            {
                "id": tid or f"p{len(blocks)}",
                "type": "paragraph",
                "text": txt,
                "metadata": {"text_id": tid, "chapter_id": chapter_id},
            }
        )
    return blocks
