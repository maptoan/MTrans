# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.translation.translator import NovelTranslator


@pytest.mark.asyncio
class TestBatchQAPhase10:
    async def test_run_batch_qa_applies_fixes_to_chunks(self, tmp_path) -> None:
        """
        Phase 10: _run_batch_qa_pass phải:
        - Lấy được api_key từ key_manager.
        - Gọi batch_qa_processor.process_batch với batch_qa_issues.
        - Áp dụng các sửa đổi trả về vào field 'translation' của all_chunks.
        """
        novel_path = tmp_path / "dummy.txt"
        novel_path.write_text("dummy", encoding="utf-8")

        config: Dict[str, Any] = {
            "input": {"novel_path": str(novel_path)},
            "translation": {
                "qa_editor": {
                    "max_batch_size": 50,
                }
            },
            "preprocessing": {"chunking": {"max_chunk_tokens": 1000}},
            "performance": {},
            "logging": {},
            "progress": {},
        }

        translator = NovelTranslator(config, valid_api_keys=[])

        # Giả lập key_manager + batch_qa_processor
        translator.key_manager = MagicMock()
        translator.key_manager.get_available_key.return_value = "test-key"

        fake_results: Dict[int, List[Dict[str, str]]] = {
            1: [
                {"old": "CJK đoạn 1", "new": "Đoạn 1 đã sửa"},
                {"old": "CJK đoạn 2", "new": "Đoạn 2 đã sửa"},
            ]
        }

        translator.batch_qa_processor = MagicMock()
        translator.batch_qa_processor.process_batch = AsyncMock(return_value=fake_results)

        # all_chunks trước batch: chứa cả 2 đoạn cần sửa trong cùng một chuỗi
        all_chunks: List[Dict[str, Any]] = [
            {
                "chunk_id": 1,
                "translation": "Trước đó... CJK đoạn 1 ... còn đây là CJK đoạn 2.",
            },
            {
                "chunk_id": 2,
                "translation": "Chunk khác, không có gì cần sửa.",
            },
        ]

        # Thu thập 2 issues cho cùng chunk_id=1 (Batch QA đã gom sẵn)
        translator.batch_qa_issues = [
            {"chunk_id": 1, "sentence_idx": 0},
            {"chunk_id": 1, "sentence_idx": 1},
        ]

        await translator._run_batch_qa_pass(all_chunks)

        # Đảm bảo process_batch được gọi đúng 1 lần với batch hiện có
        translator.batch_qa_processor.process_batch.assert_awaited_once()

        # Chunk 1 phải được áp dụng cả 2 sửa đổi
        updated_chunk1 = next(c for c in all_chunks if c["chunk_id"] == 1)
        assert "Đoạn 1 đã sửa" in updated_chunk1["translation"]
        assert "Đoạn 2 đã sửa" in updated_chunk1["translation"]

        # Chunk 2 không bị ảnh hưởng
        updated_chunk2 = next(c for c in all_chunks if c["chunk_id"] == 2)
        assert updated_chunk2["translation"] == "Chunk khác, không có gì cần sửa."

    async def test_run_batch_qa_no_key_skips_processing(self, tmp_path) -> None:
        """
        Khi không lấy được API key, _run_batch_qa_pass phải:
        - Không gọi batch_qa_processor.process_batch.
        - Không thay đổi nội dung all_chunks.
        """
        novel_path = tmp_path / "dummy.txt"
        novel_path.write_text("dummy", encoding="utf-8")

        config: Dict[str, Any] = {
            "input": {"novel_path": str(novel_path)},
            "translation": {},
            "preprocessing": {"chunking": {"max_chunk_tokens": 1000}},
            "performance": {},
            "logging": {},
            "progress": {},
        }

        translator = NovelTranslator(config, valid_api_keys=[])
        translator.key_manager = MagicMock()
        translator.key_manager.get_available_key.return_value = None

        translator.batch_qa_processor = MagicMock()
        translator.batch_qa_processor.process_batch = AsyncMock(return_value={})

        all_chunks: List[Dict[str, Any]] = [
            {
                "chunk_id": 1,
                "translation": "Nội dung gốc không đổi.",
            }
        ]
        translator.batch_qa_issues = [{"chunk_id": 1, "sentence_idx": 0}]

        await translator._run_batch_qa_pass(all_chunks)

        # Không có key → không được gọi process_batch
        translator.batch_qa_processor.process_batch.assert_not_awaited()
        assert all_chunks[0]["translation"] == "Nội dung gốc không đổi."

