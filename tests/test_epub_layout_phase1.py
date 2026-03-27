from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pytest
from bs4 import BeautifulSoup
from ebooklib import epub

from src.preprocessing.epub_layout_parser import parse_epub_with_layout


@pytest.mark.asyncio
class TestEpubLayoutPhase1:
    async def test_parse_epub_with_layout_single_chapter(self, tmp_path: Path) -> None:
        """
        Tạo 1 EPUB đơn giản (1 chương) và kiểm tra:
        - parse_epub_with_layout trả về text_map không rỗng
        - chapters_html có đúng 1 chương, đã gán data-ntid
        - original_text trong text_map khớp với nội dung HTML gốc
        """
        # 1. Tạo EPUB giả
        book = epub.EpubBook()
        book.set_identifier("id123")
        book.set_title("Test Book")
        book.set_language("en")

        chapter_html = """
        <html>
          <body>
            <h1>Chapter One</h1>
            <p>First paragraph.</p>
            <p>Second paragraph.</p>
          </body>
        </html>
        """
        c1 = epub.EpubHtml(title="Chapter 1", file_name="ch1.xhtml", lang="en")
        c1.set_content(chapter_html)

        book.add_item(c1)
        book.spine = ["nav", c1]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub_path = tmp_path / "test_book.epub"
        epub.write_epub(str(epub_path), book)

        # 2. Gọi parser mới
        result = parse_epub_with_layout(str(epub_path))

        text_map: List[Dict] = result["text_map"]
        chapters_html: Dict[str, str] = result["chapters_html"]

        # 3. Kiểm tra text_map có ít nhất 3 entry (h1 + 2 đoạn p)
        assert len(text_map) >= 3
        chapter_ids = {entry["chapter_id"] for entry in text_map}
        assert len(chapter_ids) == 1
        chapter_id = next(iter(chapter_ids))

        # 4. chapters_html có đúng 1 key và khớp với chapter_id
        assert set(chapters_html.keys()) == {chapter_id}
        chapter_html_with_ids = chapters_html[chapter_id]

        soup = BeautifulSoup(chapter_html_with_ids, "html.parser")
        elems_with_id = soup.find_all(attrs={"data-ntid": True})

        # Ít nhất 3 phần tử có data-ntid (h1 + 2 p)
        assert len(elems_with_id) >= 3

        # 5. original_text trong text_map phải nằm trong các text node sau khi gán id
        extracted_texts = [elem.get_text(strip=True) for elem in elems_with_id]
        for entry in text_map:
            assert entry["original_text"] in extracted_texts

