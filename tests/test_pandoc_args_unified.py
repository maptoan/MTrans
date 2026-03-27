# -*- coding: utf-8 -*-
"""
Test đề xuất 1: Pandoc args thống nhất giữa TXT→EPUB và master.html→EPUB.
RED: Viết test trước; GREEN: refactor dùng helper chung.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from src.output.formatter import OutputFormatter, build_epub_pandoc_args


def test_pandoc_args_equivalent_between_formatter_and_html_exporter(tmp_path: Path) -> None:
    """
    Với cùng novel_name và epub_options, OutputFormatter._build_pandoc_args
    và build_epub_pandoc_args (helper dùng chung cho html_exporter) phải sinh ra
    danh sách extra_args giống nhau.
    """
    novel_name = "TestNovel"
    epub_options: Dict[str, Any] = {
        "epub_title": "Tiêu đề EPUB",
        "epub_author": "Tác giả",
        "language": "vi",
    }

    formatter = OutputFormatter(config={})
    formatter_args = formatter._build_pandoc_args(novel_name, epub_options)
    helper_args = build_epub_pandoc_args(novel_name, epub_options)

    assert formatter_args == helper_args
    assert "--metadata" in formatter_args
    assert "title=Tiêu đề EPUB" in formatter_args
    assert "author=Tác giả" in formatter_args
    assert "lang=vi" in formatter_args


def test_pandoc_args_with_optional_cover_and_css(tmp_path: Path) -> None:
    """
    Khi có cover_image_path và css_path trỏ tới file tồn tại,
    cả hai builder phải đều thêm --epub-cover-image và --css.
    """
    cover = tmp_path / "cover.png"
    cover.write_bytes(b"fake")
    css = tmp_path / "style.css"
    css.write_text("body{}", encoding="utf-8")

    novel_name = "Novel"
    epub_options: Dict[str, Any] = {
        "epub_title": "T",
        "epub_author": "A",
        "language": "vi",
        "cover_image_path": str(cover),
        "css_path": str(css),
    }

    formatter = OutputFormatter(config={})
    formatter_args = formatter._build_pandoc_args(novel_name, epub_options)
    helper_args = build_epub_pandoc_args(novel_name, epub_options)

    assert formatter_args == helper_args
    assert "--epub-cover-image" in formatter_args
    assert "--css" in formatter_args
