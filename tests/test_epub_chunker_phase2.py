from __future__ import annotations

from typing import Any, Dict, List

import pytest

from src.preprocessing.chunker_epub import build_chunks_from_text_map


class TestEpubChunkerPhase2:
    def test_build_single_chunk_from_text_map(self) -> None:
        """
        TEXT_MAP ngắn, max_tokens lớn → gộp thành 1 chunk với đủ text_ids và delimiter [TX:id].
        """
        text_map: List[Dict[str, Any]] = [
            {"text_id": "ch1-0000", "chapter_id": "ch1.xhtml", "order": 0, "original_text": "Heading"},
            {"text_id": "ch1-0001", "chapter_id": "ch1.xhtml", "order": 1, "original_text": "Para 1."},
            {"text_id": "ch1-0002", "chapter_id": "ch1.xhtml", "order": 2, "original_text": "Para 2."},
        ]

        chunks = build_chunks_from_text_map(text_map, max_tokens=1000)

        assert len(chunks) == 1
        chunk = chunks[0]

        # text_ids giữ đúng thứ tự
        assert chunk["text_ids"] == ["ch1-0000", "ch1-0001", "ch1-0002"]
        # delimiter đúng format
        assert chunk["text_delimiter"] == "\n[TX:{id}]\n"

        text_original = chunk["text_original"]
        # Mỗi đoạn text phải xuất hiện cùng với marker riêng
        for entry in text_map:
            marker = f"[TX:{entry['text_id']}]"
            assert entry["original_text"] in text_original
            assert marker in text_original

        # Có tokens > 0
        assert isinstance(chunk["tokens"], int)
        assert chunk["tokens"] > 0

    def test_split_into_multiple_chunks_by_max_tokens(self) -> None:
        """
        max_tokens nhỏ → TEXT_MAP phải được chia thành nhiều chunks, vẫn giữ thứ tự text_ids.
        """
        # Mỗi đoạn ~10 ký tự → với token_counter đơn giản (len), max_tokens=25 sẽ tạo 2 chunks
        text_map: List[Dict[str, Any]] = [
            {"text_id": "t0", "chapter_id": "ch1.xhtml", "order": 0, "original_text": "AAAAA AAAAA"},
            {"text_id": "t1", "chapter_id": "ch1.xhtml", "order": 1, "original_text": "BBBBB BBBBB"},
            {"text_id": "t2", "chapter_id": "ch1.xhtml", "order": 2, "original_text": "CCCCC CCCCC"},
        ]

        def simple_counter(text: str) -> int:
            return len(text)

        chunks = build_chunks_from_text_map(text_map, max_tokens=25, token_counter=simple_counter)

        # Với 3 đoạn ~11 ký tự, max 25 → 2 đoạn đầu vào chunk 1, đoạn cuối vào chunk 2
        assert len(chunks) == 2

        ids_chunk1 = chunks[0]["text_ids"]
        ids_chunk2 = chunks[1]["text_ids"]

        assert ids_chunk1 == ["t0", "t1"]
        assert ids_chunk2 == ["t2"]

        # Tổng số text_ids vẫn đúng, không mất đoạn
        all_ids = ids_chunk1 + ids_chunk2
        assert all_ids == ["t0", "t1", "t2"]

