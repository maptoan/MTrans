from __future__ import annotations

from typing import Any, Dict, List

import pytest

from src.preprocessing.translation_map_epub import build_translation_map_from_chunks


class TestEpubTranslationMapPhase3:
    def test_build_translation_map_single_chunk_with_markers(self) -> None:
        """
        Một chunk với 3 text_ids, bản dịch giữ nguyên marker [TX:id] → map text_id -> đoạn dịch tương ứng.
        """
        chunks: List[Dict[str, Any]] = [
            {
                "global_id": 1,
                "text_ids": ["t0", "t1", "t2"],
                "text_delimiter": "\n[TX:{id}]\n",
            }
        ]

        translated_by_chunk: Dict[int, str] = {
            1: "Dịch A\n[TX:t0]\nDịch B\n[TX:t1]\nDịch C\n[TX:t2]\n"
        }

        result = build_translation_map_from_chunks(chunks, translated_by_chunk)

        assert result == {
            "t0": "Dịch A",
            "t1": "Dịch B",
            "t2": "Dịch C",
        }

    def test_build_translation_map_multiple_chunks_order_preserved(self) -> None:
        """
        Nhiều chunks, mỗi chunk có 1-2 text_ids, đảm bảo:
        - Tổng số text_id không mất.
        - Mỗi text_id map đúng đoạn dịch.
        """
        chunks: List[Dict[str, Any]] = [
            {
                "global_id": 1,
                "text_ids": ["a0", "a1"],
                "text_delimiter": "\n[TX:{id}]\n",
            },
            {
                "global_id": 2,
                "text_ids": ["b0"],
                "text_delimiter": "\n[TX:{id}]\n",
            },
        ]

        translated_by_chunk: Dict[int, str] = {
            1: "Dịch A0\n[TX:a0]\nDịch A1\n[TX:a1]\n",
            2: "Dịch B0\n[TX:b0]\n",
        }

        result = build_translation_map_from_chunks(chunks, translated_by_chunk)

        assert result == {
            "a0": "Dịch A0",
            "a1": "Dịch A1",
            "b0": "Dịch B0",
        }

