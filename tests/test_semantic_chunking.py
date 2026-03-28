from __future__ import annotations

from src.preprocessing.chunker import SmartChunker


def test_chunk_from_structured_ir_respects_max_effective_tokens() -> None:
    """Oversized sentences (no punctuation) must not produce chunks above hard limit."""
    config = {
        "preprocessing": {
            "chunking": {
                "max_chunk_tokens": 100,
                "safety_ratio": 1.0,
                "use_markers": False,
            }
        },
        "translation": {},
    }
    chunker = SmartChunker(config)
    chunker._count_tokens = lambda text: len(text)
    big = "a" * 500
    blocks = [{"type": "paragraph", "text": big}]
    chunks = chunker.chunk_from_structured_ir(blocks)
    assert chunks
    limit = chunker.max_effective_tokens
    for c in chunks:
        assert c["tokens"] <= limit, (
            f"chunk {c.get('global_id')} has {c['tokens']} > {limit}"
        )


def test_chunk_from_structured_ir_respects_heading_boundaries() -> None:
    config = {
        "preprocessing": {
            "chunking": {
                "max_chunk_tokens": 60,
                "safety_ratio": 1.0,
                "use_markers": False,
            }
        },
        "translation": {},
    }
    chunker = SmartChunker(config)
    chunker._count_tokens = lambda text: len(text)
    blocks = [
        {"type": "heading", "text": "Chapter 1"},
        {"type": "paragraph", "text": "A" * 20},
        {"type": "heading", "text": "Chapter 2"},
        {"type": "paragraph", "text": "B" * 20},
    ]
    chunks = chunker.chunk_from_structured_ir(blocks)
    assert len(chunks) >= 2
    assert "Chapter 1" in chunks[0]["text_original"]
