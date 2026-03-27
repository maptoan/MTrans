# -*- coding: utf-8 -*-
"""
Phase 12 – Integration test: pipeline TXT → finalize → TXT + master.html → option 4 export;
và pipeline EPUB layout → master.html → option 4 export.

TDD: Test viết trước; chỉ sửa code khi test yêu cầu.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.translation.translator import NovelTranslator
from src.translation.ui_handler import UIHandler


@pytest.mark.asyncio
class TestIntegrationMasterTxtPipeline:
    """Integration: TXT pipeline → finalize tạo TXT + master.html; option 4 export từ master."""

    async def test_finalize_produces_txt_and_master_html(self, tmp_path: Path) -> None:
        """
        Sau _finalize_translation (nhánh text-based, merge mock):
        - Có file TXT tổng (output_formatter.save được gọi và ghi file).
        - Có file {novel_name}_master.html trong progress_dir với nội dung hợp lệ (sections).
        """
        novel_path = tmp_path / "IntegrationNovel.txt"
        novel_path.write_text("placeholder", encoding="utf-8")

        out_dir = tmp_path / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        progress_dir = tmp_path / "progress"
        progress_dir.mkdir(parents=True, exist_ok=True)

        config: Dict[str, Any] = {
            "input": {"novel_path": str(novel_path)},
            "preprocessing": {"chunking": {"max_chunk_tokens": 1000}},
            "translation": {},
            "performance": {},
            "logging": {},
            "progress": {"progress_dir": str(progress_dir)},
            "output": {"output_path": str(out_dir)},
        }

        translator = NovelTranslator(config, valid_api_keys=[])
        flat_content = (
            "[H1]Chương 1[/H1]\n\nĐoạn một.\n\n"
            "[H1]Chương 2[/H1]\n\nĐoạn hai.\n"
        )
        all_chunks: List[Dict[str, Any]] = [
            {"global_id": 1, "chunk_id": 1},
            {"global_id": 2, "chunk_id": 2},
        ]

        async def fake_merge(_chunks: List[Dict]) -> str:
            return flat_content

        translator._merge_all_chunks = fake_merge

        txt_saved_path = out_dir / "IntegrationNovel.txt"

        def save_impl(content: str, name: str) -> str:
            out_dir.mkdir(parents=True, exist_ok=True)
            p = out_dir / f"{name}.txt"
            p.write_text(content, encoding="utf-8")
            return str(p)

        translator.output_formatter = MagicMock()
        translator.output_formatter.save = save_impl
        translator.output_formatter._normalize_paragraphs = lambda c: c  # Finalize dùng normalized cho TXT + master

        class DummyUI:
            async def generate_completion_report(
                self,
                _ac: List[Dict],
                _fc: List[Dict],
                _time: float,
                is_success: bool = True,
            ) -> None:
                pass

            async def show_user_options(
                self,
                all_chunks: List[Dict],
                failed_chunks: List[Dict],
                txt_path: str | None = None,
                retry_count: int = 0,
            ):
                return failed_chunks, txt_path or str(txt_saved_path)

        translator.ui_handler = DummyUI()

        result_chunks, output_path = await translator._finalize_translation(
            all_chunks, [], 1.0
        )

        assert result_chunks == []
        assert output_path is not None
        assert Path(output_path).exists(), "File TXT tổng phải tồn tại"

        master_path = progress_dir / "IntegrationNovel_master.html"
        assert master_path.exists(), "File master.html phải tồn tại sau finalize"
        master_content = master_path.read_text(encoding="utf-8")
        assert "id=\"nt-content\"" in master_content and "<section" in master_content
        assert master_content.count("<section") >= 2

    async def test_option_4_export_from_master_integration(self, tmp_path: Path) -> None:
        """
        Khi đã có master.html (sau finalize), option 4 phải gọi export với đúng đường dẫn
        và trả về kết quả từ ask_additional_formats.
        """
        progress_dir = tmp_path / "progress"
        progress_dir.mkdir(parents=True, exist_ok=True)
        master_path = progress_dir / "IntegrationNovel_master.html"
        master_path.write_text(
            "<!DOCTYPE html><html><body><main id='nt-content'>"
            "<section><h1>Chương 1</h1><p>Nội dung.</p></section></main></body></html>",
            encoding="utf-8",
        )

        config: Dict[str, Any] = {
            "progress": {"progress_dir": str(progress_dir)},
            "output": {},
        }
        handler = UIHandler(
            output_formatter=MagicMock(),
            novel_name="IntegrationNovel",
            config=config,
        )
        handler._export_master_html_to_epub = AsyncMock(
            return_value=str(tmp_path / "IntegrationNovel.epub")
        )
        handler._get_user_choice_with_timeout = lambda **kw: "0"

        chunks, out_path = await handler.handle_option_4_export_master_html(
            txt_path=str(tmp_path / "file.txt")
        )

        handler._export_master_html_to_epub.assert_awaited_once_with(str(master_path))
        assert chunks == []
        assert out_path is not None


@pytest.mark.asyncio
class TestIntegrationEpubLayoutPipeline:
    """Integration: EPUB layout → finalize tạo master.html; option 4 export dùng cùng file."""

    async def test_epub_layout_finalize_then_option_4_export_from_master(
        self, tmp_path: Path
    ) -> None:
        """
        Sau _finalize_translation (nhánh EPUB layout), master.html được lưu;
        option 4 phải gọi export với đúng đường dẫn master đó.
        """
        epub_path = tmp_path / "EpubLayout.epub"
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
        translator._epub_layout_state = {
            "text_map": [
                {"text_id": "c1-0000", "chapter_id": "c1", "order": 0, "original_text": "T1"},
            ],
            "chapters_html": {"c1": "<html><body><p>T1</p></body></html>"},
            "metadata": {"title": "EpubLayout"},
        }
        all_chunks: List[Dict[str, Any]] = [
            {"global_id": 1, "chunk_id": 1, "text_ids": ["c1-0000"], "text_delimiter": "\n[TX:{id}]\n"},
        ]

        class DummyProgress:
            completed_chunks = {"1": "Dịch T1\n[TX:c1-0000]\n"}

        translator.progress_manager = DummyProgress()

        class DummyUI:
            async def generate_completion_report(
                self,
                _ac: List[Dict],
                _fc: List[Dict],
                _time: float,
                is_success: bool = True,
            ) -> None:
                pass

            async def show_user_options(
                self,
                _ac: List[Dict],
                _fc: List[Dict],
                txt_path: str | None = None,
                retry_count: int = 0,
            ):
                raise AssertionError("EPUB layout flow không gọi show_user_options")

        translator.ui_handler = DummyUI()

        with patch(
            "src.preprocessing.translation_map_epub.build_translation_map_from_chunks",
            return_value={"c1-0000": "DỊCH MỚI"},
        ), patch(
            "src.output.epub_reinject.apply_translations_to_chapters",
            return_value={"c1": "<html><body><p>DỊCH MỚI</p></body></html>"},
        ), patch(
            "src.output.epub_reinject.build_html_master",
            return_value="<!DOCTYPE html><html><body><main id='nt-content'><section><h1>Chương 1</h1><p>DỊCH MỚI</p></section></main></body></html>",
        ), patch(
            "src.output.epub_reinject.write_epub_from_translated_chapters",
            return_value=str(tmp_path / "EpubLayout_translated.epub"),
        ):
            result_chunks, output_path = await translator._finalize_translation(
                all_chunks, [], 1.0
            )

        assert result_chunks == []  # Đã chuyển sang trả về failed_chunks (rỗng trong test này)
        assert output_path is not None
        assert output_path.endswith(".html")
        master_path = Path(output_path)
        assert master_path.exists()
        assert "nt-content" in master_path.read_text(encoding="utf-8")

        # Option 4: cùng progress_dir và novel_name → phải export được từ file master vừa tạo
        novel_name = "EpubLayout"
        expected_master = tmp_path / f"{novel_name}_master.html"
        assert expected_master == master_path, "Master phải nằm tại progress_dir/novel_name_master.html"

        handler = UIHandler(
            output_formatter=MagicMock(),
            novel_name=novel_name,
            config={"progress": {"progress_dir": str(tmp_path)}, "output": {}},
        )
        handler._export_master_html_to_epub = AsyncMock(
            return_value=str(tmp_path / "EpubLayout.epub")
        )
        handler._get_user_choice_with_timeout = lambda **kw: "0"

        chunks, out_path = await handler.handle_option_4_export_master_html(
            txt_path=str(tmp_path / "out.txt")
        )

        handler._export_master_html_to_epub.assert_awaited_once_with(str(expected_master))
        assert out_path is not None
