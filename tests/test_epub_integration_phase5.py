from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.translation.translator import NovelTranslator


@pytest.mark.asyncio
class TestEpubIntegrationPhase5:
    async def test_prepare_translation_uses_epub_layout_when_enabled(self, tmp_path: Path) -> None:
        """
        Khi input là EPUB và preserve_layout=true, _prepare_translation phải:
        - Gọi parse_epub_with_layout
        - Gọi build_chunks_from_text_map
        - Lưu _epub_layout_state
        - Trả về all_chunks do chunker_epub trả về
        """
        # Tạo file EPUB giả (chỉ cần path kết thúc .epub)
        epub_path = tmp_path / "dummy.epub"
        epub_path.write_text("dummy", encoding="utf-8")

        config: Dict[str, Any] = {
            "input": {"novel_path": str(epub_path)},
            "preprocessing": {
                "epub": {"preserve_layout": True},
                "chunking": {"max_chunk_tokens": 1000},
            },
            "translation": {},
            "performance": {},
            "logging": {},
            "progress": {},
        }

        translator = NovelTranslator(config, valid_api_keys=[])

        fake_text_map = [
            {"text_id": "c1-0000", "chapter_id": "c1", "order": 0, "original_text": "T1"},
        ]
        fake_chapters_html = {"c1": "<html><body><p>T1</p></body></html>"}
        fake_metadata = {"title": "Dummy"}

        fake_chunks = [
            {
                "global_id": 1,
                "text_original": "T1\n[TX:c1-0000]\n",
                "text": "T1\n[TX:c1-0000]\n",
                "tokens": 10,
                "text_ids": ["c1-0000"],
                "text_delimiter": "\n[TX:{id}]\n",
            }
        ]

        with patch(
            "src.preprocessing.epub_layout_parser.parse_epub_with_layout",
            return_value={
                "text_map": fake_text_map,
                "chapters_html": fake_chapters_html,
                "metadata": fake_metadata,
            },
        ) as mock_parse, patch(
            "src.preprocessing.chunker_epub.build_chunks_from_text_map",
            return_value=fake_chunks,
        ) as mock_chunker, patch(
            "src.preprocessing.file_parser.parse_file"
        ) as mock_parse_file:
            # Đảm bảo nhánh txt cũ không bị gọi trong mode preserve_layout
            all_chunks, cleaned_text = await translator._prepare_translation()

        # Không dùng parse_file trong nhánh preserve_layout
        mock_parse_file.assert_not_called()
        mock_parse.assert_called_once()
        mock_chunker.assert_called_once_with(fake_text_map, 1000, token_counter=None)

        assert all_chunks == fake_chunks
        assert cleaned_text is None

        # _epub_layout_state phải được lưu trên translator
        state = getattr(translator, "_epub_layout_state", None)
        assert state is not None
        assert state["text_map"] == fake_text_map
        assert state["chapters_html"] == fake_chapters_html
        assert state["metadata"] == fake_metadata

    async def test_finalize_translation_uses_epub_layout_flow(self, tmp_path: Path) -> None:
        """
        Khi _epub_layout_state tồn tại, _finalize_translation phải:
        - Không ghép TXT theo luồng cũ
        - Gọi build_translation_map_from_chunks
        - Gọi apply_translations_to_chapters và build_html_master
        - Trả về (all_chunks, path_html_master)
        """
        epub_path = tmp_path / "dummy.epub"
        epub_path.write_text("dummy", encoding="utf-8")

        config: Dict[str, Any] = {
            "input": {"novel_path": str(epub_path)},
            "preprocessing": {
                "epub": {"preserve_layout": True},
                "chunking": {"max_chunk_tokens": 1000},
            },
            "translation": {},
            "performance": {},
            "logging": {},
            "progress": {"progress_dir": str(tmp_path)},
        }

        translator = NovelTranslator(config, valid_api_keys=[])

        # Giả lập state EPUB layout đã có sẵn sau _prepare_translation
        translator._epub_layout_state = {
            "text_map": [
                {"text_id": "c1-0000", "chapter_id": "c1", "order": 0, "original_text": "T1"},
            ],
            "chapters_html": {"c1": "<html><body><p>T1</p></body></html>"},
            "metadata": {"title": "Dummy"},
        }

        # all_chunks giả: 1 chunk đã dịch
        all_chunks: List[Dict[str, Any]] = [
            {
                "global_id": 1,
                "chunk_id": 1,
                "text_ids": ["c1-0000"],
                "text_delimiter": "\n[TX:{id}]\n",
            }
        ]
        failed_chunks: List[Dict[str, Any]] = []
        translation_time = 12.3

        # progress_manager giả: có completed_chunks cho global_id=1
        class DummyProgress:
            def __init__(self) -> None:
                self.completed_chunks = {"1": "Dịch T1\n[TX:c1-0000]\n"}

        translator.progress_manager = DummyProgress()

        # ui_handler giả: chỉ cần generate_completion_report (async)
        class DummyUI:
            def __init__(self) -> None:
                self.called = False

            async def generate_completion_report(
                self, all_chunks: List[Dict[str, Any]], failed_chunks: List[Dict[str, Any]], translation_time: float, is_success: bool
            ) -> None:
                self.called = True

            async def show_user_options(
                self,
                all_chunks: List[Dict[str, Any]],
                failed_chunks: List[Dict[str, Any]],
                txt_path: str | None = None,
                retry_count: int = 0,
            ):
                # Không được gọi trong nhánh EPUB layout
                raise AssertionError("show_user_options should not be called in EPUB layout flow")

        translator.ui_handler = DummyUI()

        # Patch các helper Phase 3–4 và writer EPUB (tránh đọc file dummy.epub không phải zip)
        with patch(
            "src.preprocessing.translation_map_epub.build_translation_map_from_chunks",
            return_value={"c1-0000": "DỊCH MỚI"},
        ) as mock_build_map, patch(
            "src.output.epub_reinject.apply_translations_to_chapters",
            return_value={"c1": "<html><body><p>DỊCH MỚI</p></body></html>"},
        ) as mock_apply, patch(
            "src.output.epub_reinject.build_html_master",
            return_value="<html><body><p>MASTER</p></body></html>",
        ) as mock_master, patch(
            "src.output.epub_reinject.write_epub_from_translated_chapters",
            return_value=str(epub_path).replace(".epub", "_translated.epub"),
        ):
            result_chunks, output_path = await translator._finalize_translation(
                all_chunks, failed_chunks, translation_time
            )

        # Đảm bảo đã gọi báo cáo hoàn thành
        assert translator.ui_handler.called is True

        # Đảm bảo các helper đã được gọi với tham số hợp lý
        mock_build_map.assert_called_once()
        mock_apply.assert_called_once()
        mock_master.assert_called_once()

        # failed_chunks được trả về, trong trường hợp này là rỗng (mock)
        assert result_chunks == failed_chunks
        # output_path là đường dẫn tới file HTML master đã được lưu
        assert output_path is not None
        assert output_path.endswith(".html")

        # File HTML master thực sự tồn tại và có nội dung mock
        master_path = Path(output_path)
        assert master_path.exists()
        content = master_path.read_text(encoding="utf-8")
        assert "<p>MASTER</p>" in content

