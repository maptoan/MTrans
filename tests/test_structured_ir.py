from __future__ import annotations

from src.preprocessing.structured_ir import (
    build_structured_ir_from_text,
    build_structured_ir_from_text_map,
    ir_to_plain_text,
)


def test_build_structured_ir_detects_heading_and_list() -> None:
    text = "# Chapter 1\n\n- item one\n\nNormal paragraph."
    blocks = build_structured_ir_from_text(text)
    assert blocks[0]["type"] == "heading"
    assert any(block["type"] == "list_item" for block in blocks)
    assert any(block["type"] == "paragraph" for block in blocks)


def test_ir_to_plain_text_roundtrip_contains_content() -> None:
    text = "Chapter 1\n\nSome text here.\n\nAnother paragraph."
    blocks = build_structured_ir_from_text(text)
    rebuilt = ir_to_plain_text(blocks)
    assert "Some text here." in rebuilt
    assert "Another paragraph." in rebuilt


def test_build_structured_ir_from_text_map_paragraph_and_image() -> None:
    tm = [
        {
            "text_id": "c1-0000",
            "chapter_id": "c1",
            "order": 0,
            "original_text": "Hello world",
            "original_inner_html": "Hello world",
        },
        {
            "text_id": "c1-0001",
            "chapter_id": "c1",
            "order": 1,
            "original_text": "",
            "original_inner_html": "<img src=\"x.png\" />",
            "is_image_only": True,
        },
    ]
    blocks = build_structured_ir_from_text_map(tm)
    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["text"] == "Hello world"
    assert blocks[1]["type"] == "image_ref"
    assert blocks[1]["metadata"].get("is_image_only") is True
