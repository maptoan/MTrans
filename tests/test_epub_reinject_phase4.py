from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
from bs4 import BeautifulSoup
from ebooklib import epub

from src.output.epub_reinject import (
    apply_translations_to_chapters,
    build_html_master,
    write_epub_from_translated_chapters,
)
from src.preprocessing.epub_layout_parser import extract_text_map_from_html


class TestEpubReinjectPhase4:
    def test_apply_translations_single_chapter(self) -> None:
        """
        Một chương: apply_translations_to_chapters phải thay text theo map, giữ nguyên cấu trúc.
        """
        html = """
        <html>
          <body>
            <h1>Chapter One</h1>
            <p>First paragraph.</p>
            <p>Second paragraph.</p>
          </body>
        </html>
        """

        chapter_id = "ch1.xhtml"
        text_map, html_with_ids = extract_text_map_from_html(html, chapter_id)

        chapters_html: Dict[str, str] = {chapter_id: html_with_ids}

        translations = {
            entry["text_id"]: f"TR-{entry['original_text']}"
            for entry in text_map
        }

        translated_chapters = apply_translations_to_chapters(chapters_html, translations)

        assert set(translated_chapters.keys()) == {chapter_id}
        translated_html = translated_chapters[chapter_id]

        soup = BeautifulSoup(translated_html, "html.parser")

        # Cấu trúc h1 + 2 p vẫn giữ nguyên
        assert len(soup.find_all("h1")) == 1
        assert len(soup.find_all("p")) == 2

        # Nội dung là bản dịch tương ứng
        texts = [elem.get_text(strip=True) for elem in soup.find_all(attrs={"data-ntid": True})]
        expected = [f"TR-{entry['original_text']}" for entry in text_map]
        assert texts == expected

    def test_build_html_master_multiple_chapters(self) -> None:
        """
        2 chương: build_html_master phải tạo 1 HTML tổng chứa cả hai section,
        mỗi section có nội dung dịch đúng chương của nó.
        """
        html1 = """
        <html><body><h1>C1</h1><p>A</p></body></html>
        """
        html2 = """
        <html><body><h1>C2</h1><p>B</p></body></html>
        """

        tm1, h1_ids = extract_text_map_from_html(html1, "c1")
        tm2, h2_ids = extract_text_map_from_html(html2, "c2")

        chapters_html: Dict[str, str] = {"c1": h1_ids, "c2": h2_ids}

        translations = {
            **{e["text_id"]: f"TX1-{e['original_text']}" for e in tm1},
            **{e["text_id"]: f"TX2-{e['original_text']}" for e in tm2},
        }

        translated_chapters = apply_translations_to_chapters(chapters_html, translations)

        master = build_html_master(translated_chapters, title="Master Title")
        soup = BeautifulSoup(master, "html.parser")

        # Có title đúng
        assert soup.title.string == "Master Title"

        # Có 2 section chương
        sections = soup.find_all("section")
        assert len(sections) == 2

        section_texts: List[str] = [sec.get_text(strip=True) for sec in sections]

        # Mỗi section chứa text theo bản dịch riêng của chương
        assert any("TX1-C1" in t and "TX1-A" in t for t in section_texts)
        assert any("TX2-C2" in t and "TX2-B" in t for t in section_texts)

    def test_write_epub_from_translated_chapters(self, tmp_path: Path) -> None:
        """
        Tạo EPUB 1 chương, gọi write_epub_from_translated_chapters với HTML dịch,
        đọc lại EPUB ra và kiểm tra nội dung chương là bản dịch.
        """
        # 1. Tạo EPUB gốc (1 chương)
        book = epub.EpubBook()
        book.set_identifier("orig-123")
        book.set_title("Original")
        book.set_language("en")
        c1 = epub.EpubHtml(title="Ch1", file_name="ch1.xhtml", lang="en")
        c1.set_content("<html><body><h1>Chapter One</h1><p>Hello.</p></body></html>")
        book.add_item(c1)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", c1]
        orig_path = tmp_path / "orig.epub"
        epub.write_epub(str(orig_path), book)

        # 2. Xuất EPUB với chương đã "dịch"
        translated_html = "<html><body><h1>Chương Một</h1><p>Xin chào.</p></body></html>"
        out_path = tmp_path / "out.epub"
        result = write_epub_from_translated_chapters(
            str(orig_path),
            translated_chapters={"ch1.xhtml": translated_html},
            output_epub_path=str(out_path),
        )
        assert result == str(out_path)
        assert out_path.exists()

        # 3. Đọc EPUB ra, kiểm tra chương chứa nội dung đã dịch
        out_book = epub.read_epub(str(out_path))
        for item in out_book.get_items():
            if getattr(item, "get_name", None) and item.get_name() == "ch1.xhtml":
                content = item.get_content().decode("utf-8", errors="replace")
                assert "Chương Một" in content
                assert "Xin chào" in content
                assert "Chapter One" not in content
                break
        else:
            pytest.fail("Không tìm thấy ch1.xhtml trong EPUB ra")

