# -*- coding: utf-8 -*-
from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Dict

import pytest


def _install_fake_pypandoc(monkeypatch: pytest.MonkeyPatch, target_module: Any) -> Dict[str, Any]:
    """
    Cài một phiên bản pypandoc giả vào module đích để:
    - Không thực sự gọi pandoc.
    - Ghi nhận tham số được truyền vào convert_file.
    """
    calls: Dict[str, Any] = {}

    fake = types.SimpleNamespace()

    def convert_file(source_file: str, to: str, format: str, outputfile: str, extra_args=None) -> None:  # type: ignore[override]
        calls["source_file"] = source_file
        calls["to"] = to
        calls["format"] = format
        calls["outputfile"] = outputfile
        calls["extra_args"] = extra_args or []

    fake.convert_file = convert_file  # type: ignore[attr-defined]
    monkeypatch.setattr(target_module, "pypandoc", fake, raising=False)
    return calls


@pytest.mark.asyncio
async def test_export_master_html_to_epub(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Phase 11: Helper HTML → EPUB phải:
    - Nhận master.html và novel_name.
    - Gọi pypandoc.convert_file(...) với format='html'.
    - Xuất file EPUB vào output_dir với tên {novel_name}.epub.
    """
    from src.output import html_exporter

    master_path = tmp_path / "MyNovel_master.html"
    master_path.write_text(
        "<!DOCTYPE html><html><head><title>Demo</title></head>"
        "<body><main id='nt-content'><section><h1>Chương 1</h1><p>Nội dung.</p></section></main></body></html>",
        encoding="utf-8",
    )

    calls = _install_fake_pypandoc(monkeypatch, html_exporter)

    novel_name = "MyNovel"
    output_dir = tmp_path / "out"

    epub_options: Dict[str, Any] = {
        "epub_title": "My Novel Title",
        "epub_author": "Author Name",
        "language": "vi",
    }

    epub_path = await html_exporter.export_master_html_to_epub(
        master_html_path=str(master_path),
        novel_name=novel_name,
        output_dir=str(output_dir),
        epub_options=epub_options,
    )

    # Đường dẫn trả về phải trỏ tới out/MyNovel.epub
    assert Path(epub_path) == output_dir / f"{novel_name}.epub"

    # Fake pypandoc phải được gọi đúng tham số
    assert calls["source_file"] == str(master_path)
    assert calls["to"] == "epub"
    assert calls["format"].startswith("html")
    assert calls["outputfile"] == epub_path
    assert "--metadata" in calls["extra_args"]


@pytest.mark.asyncio
async def test_ui_handler_option_4_no_master_returns_gracefully(tmp_path: Path) -> None:
    """
    Wire Phase 11: Khi chọn option 4 mà không có file master.html,
    UIHandler.handle_option_4_export_master_html phải trả về ([], txt_path)
    và không gọi callback export.
    """
    from unittest.mock import AsyncMock, MagicMock

    from src.translation.ui_handler import UIHandler

    config = {
        "progress": {"progress_dir": str(tmp_path)},
        "output": {},
    }
    # tmp_path rỗng → không có file {novel_name}_master.html
    handler = UIHandler(output_formatter=MagicMock(), novel_name="NoMaster", config=config)
    handler._export_master_html_to_epub = AsyncMock()

    chunks, out_path = await handler.handle_option_4_export_master_html(txt_path="/some/txt.txt")

    assert chunks == []
    assert out_path == "/some/txt.txt"
    handler._export_master_html_to_epub.assert_not_awaited()

