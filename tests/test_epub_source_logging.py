# -*- coding: utf-8 -*-
"""
Test đề xuất 2: Config epub_source và log nguồn EPUB (TXT vs master.html).
RED: Test assert log chứa nguồn; GREEN: thêm log trong UIHandler.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.translation.ui_handler import UIHandler


@pytest.mark.asyncio
async def test_option_1_logs_epub_source_txt(caplog: pytest.LogCaptureFixture) -> None:
    """Khi convert từ TXT (option 1), log phải ghi rõ nguồn là TXT."""
    config: Dict[str, Any] = {"output": {}, "progress": {}}
    handler = UIHandler(output_formatter=MagicMock(), novel_name="Test", config=config)
    handler._convert_to_epub = AsyncMock(return_value="/out/Test.epub")
    handler._convert_to_docx = AsyncMock(return_value=None)
    handler._convert_to_pdf = AsyncMock(return_value=None)
    handler._get_user_choice_with_timeout = lambda **kw: "0"

    with caplog.at_level(logging.INFO, logger="NovelTranslator"):
        await handler.handle_option_1(all_chunks=[], txt_path="/some/Test.txt")

    assert "EPUB source: TXT" in caplog.text


@pytest.mark.asyncio
async def test_option_4_logs_epub_source_master_html(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Khi export từ master.html (option 4), log phải ghi rõ nguồn là master.html."""
    master = tmp_path / "Novel_master.html"
    master.write_text("<html></html>", encoding="utf-8")
    config: Dict[str, Any] = {
        "progress": {"progress_dir": str(tmp_path)},
        "output": {},
    }
    handler = UIHandler(output_formatter=MagicMock(), novel_name="Novel", config=config)
    handler._export_master_html_to_epub = AsyncMock(return_value="/out/Novel.epub")
    handler._convert_to_docx = AsyncMock(return_value=None)
    handler._convert_to_pdf = AsyncMock(return_value=None)
    handler._get_user_choice_with_timeout = lambda **kw: "0"

    with caplog.at_level(logging.INFO, logger="NovelTranslator"):
        await handler.handle_option_4_export_master_html(txt_path="/some/txt.txt")

    assert "EPUB source: master.html" in caplog.text


@pytest.mark.asyncio
async def test_option_4_no_master_suggests_txt_option(caplog: pytest.LogCaptureFixture) -> None:
    """Khi không có master.html nhưng có txt_path, log phải gợi ý dùng option 1 hoặc 2."""
    config: Dict[str, Any] = {"progress": {"progress_dir": "/nonexistent"}, "output": {}}
    handler = UIHandler(output_formatter=MagicMock(), novel_name="X", config=config)

    with caplog.at_level(logging.INFO, logger="NovelTranslator"):
        await handler.handle_option_4_export_master_html(txt_path="/some/file.txt")

    assert "option 1" in caplog.text or "option 2" in caplog.text
