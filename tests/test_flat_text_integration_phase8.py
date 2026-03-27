# -*- coding: utf-8 -*-
"""
Integration test Phase 8: finalize text-based/scan-based tạo *_master.html từ flat text.

TDD: Test viết trước, assert rằng sau _finalize_translation (nhánh không EPUB layout)
có file {novel_name}_master.html trong progress_dir và nội dung có main#nt-content,
section với h1 data-role="chapter-title".
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from src.translation.translator import NovelTranslator


@pytest.mark.asyncio
class TestFlatTextFinalizePhase8:
    """Integration: finalize (text-based) gọi build_html_master_from_flat_text và lưu *_master.html."""

    async def test_finalize_translation_creates_master_html_from_flat_text(self, tmp_path: Path) -> None:
        """
        Khi KHÔNG có _epub_layout_state (text-based/scan-based), sau merge và lưu TXT,
        _finalize_translation phải:
        - Gọi build_html_master_from_flat_text(full_content, novel_name)
        - Lưu file {novel_name}_master.html vào progress_dir
        - Nội dung HTML có main#nt-content và ít nhất một <section> với <h1 data-role="chapter-title">.
        """
        novel_path = tmp_path / "Phase8Novel.txt"
        novel_path.write_text("placeholder", encoding="utf-8")

        config: Dict[str, Any] = {
            "input": {"novel_path": str(novel_path)},
            "preprocessing": {"chunking": {"max_chunk_tokens": 1000}},
            "translation": {},
            "performance": {},
            "logging": {},
            "progress": {"progress_dir": str(tmp_path)},
        }

        translator = NovelTranslator(config, valid_api_keys=[])
        # Đảm bảo không đi nhánh EPUB layout
        assert getattr(translator, "_epub_layout_state", None) is None

        flat_content = (
            "[H1]Chương 1: Mở đầu[/H1]\n\n"
            "Đoạn đầu tiên.\n\n"
            "[H1]Chương 2[/H1]\n\n"
            "Đoạn chương hai.\n"
        )

        all_chunks: List[Dict[str, Any]] = [
            {"global_id": 1, "chunk_id": 1},
            {"global_id": 2, "chunk_id": 2},
        ]
        failed_chunks: List[Dict[str, Any]] = []
        translation_time = 5.0

        # Mock _merge_all_chunks để trả về full_content có marker [H1]
        async def fake_merge(_chunks: List[Dict]) -> str:
            return flat_content

        translator._merge_all_chunks = fake_merge

        # Mock output_formatter: save trả đường dẫn; _normalize_paragraphs trả nội dung (finalize dùng normalized cho cả TXT và master)
        saved_txt = tmp_path / "Phase8Novel.txt"
        translator.output_formatter = MagicMock()
        translator.output_formatter.save = lambda content, name: str(tmp_path / f"{name}.txt")
        translator.output_formatter._normalize_paragraphs = lambda c: c  # Nội dung test đã có [H1]

        # Mock UI: chỉ cần báo cáo và trả về (all_chunks, txt_path)
        class DummyUI:
            async def generate_completion_report(
                self,
                _all_chunks: List[Dict[str, Any]],
                _failed_chunks: List[Dict[str, Any]],
                _translation_time: float,
                is_success: bool = True,
            ) -> None:
                pass

            async def show_user_options(
                self,
                all_chunks: List[Dict[str, Any]],
                _failed_chunks: List[Dict[str, Any]],
                txt_path: str | None = None,
                retry_count: int = 0,
            ):
                return all_chunks, txt_path or str(saved_txt)

        translator.ui_handler = DummyUI()

        result_chunks, output_path = await translator._finalize_translation(
            all_chunks, failed_chunks, translation_time
        )

        assert result_chunks == all_chunks
        assert output_path is not None

        # Phase 8: phải có file *_master.html trong progress_dir
        master_path = tmp_path / "Phase8Novel_master.html"
        assert master_path.exists(), f"Thiếu file {master_path} sau finalize (text-based)"

        content = master_path.read_text(encoding="utf-8")
        assert "main" in content and "id=\"nt-content\"" in content, "HTML phải có main#nt-content"
        assert "data-role=\"chapter-title\"" in content, "Phải có ít nhất một h1 data-role=chapter-title"
        assert "<section" in content, "Phải có ít nhất một section"
        assert "Chương 1" in content and "Chương 2" in content, "Nội dung chương phải có trong HTML"
