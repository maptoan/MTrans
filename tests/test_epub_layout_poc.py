import pytest
from bs4 import BeautifulSoup

from src.preprocessing.epub_layout_parser import (
    extract_text_map_from_html,
    reinject_translations_to_html,
)


class TestEpubLayoutPoc:
    def test_extract_text_map_simple_html(self) -> None:
        """HTML đơn giản: h1 + hai đoạn p → tạo TEXT_MAP và gán data-id ổn định."""
        html = """
        <html>
          <body>
            <h1>Tiêu đề chương</h1>
            <p>Đoạn thứ nhất.</p>
            <p>Đoạn thứ hai.</p>
          </body>
        </html>
        """

        chapter_id = "ch1"
        text_map, dom_html = extract_text_map_from_html(html, chapter_id)

        # 1) TEXT_MAP có đúng 3 bản ghi theo thứ tự
        assert len(text_map) == 3
        assert [entry["order"] for entry in text_map] == [0, 1, 2]

        # 2) Mỗi entry có text_id duy nhất và chapter_id đúng
        text_ids = [entry["text_id"] for entry in text_map]
        assert len(set(text_ids)) == 3
        assert all(entry["chapter_id"] == chapter_id for entry in text_map)

        # 3) Nội dung text khớp
        originals = [entry["original_text"] for entry in text_map]
        assert originals == ["Tiêu đề chương", "Đoạn thứ nhất.", "Đoạn thứ hai."]

        # 4) DOM sau khi xử lý có gán data-ntid cho đúng 3 block element
        soup = BeautifulSoup(dom_html, "html.parser")
        elems_with_id = soup.find_all(attrs={"data-ntid": True})
        assert len(elems_with_id) == 3

        dom_ids = [elem["data-ntid"] for elem in elems_with_id]
        # text_ids và dom_ids phải trùng thứ tự
        assert dom_ids == text_ids

    def test_reinject_translations_preserves_structure(self) -> None:
        """Re-inject bản dịch: thay text nhưng vẫn giữ cấu trúc h1/p."""
        html = """
        <html>
          <body>
            <h1>Tiêu đề chương</h1>
            <p>Đoạn thứ nhất.</p>
            <p>Đoạn thứ hai.</p>
          </body>
        </html>
        """

        chapter_id = "ch1"
        text_map, dom_html = extract_text_map_from_html(html, chapter_id)

        translations = {
            entry["text_id"]: f"DỊCH: {entry['original_text']}"
            for entry in text_map
        }

        translated_html = reinject_translations_to_html(dom_html, translations)
        soup = BeautifulSoup(translated_html, "html.parser")

        # Cấu trúc tag vẫn giữ nguyên (1 h1, 2 p)
        assert len(soup.find_all("h1")) == 1
        assert len(soup.find_all("p")) == 2

        # Nội dung đã được thay thế theo bản dịch
        texts = [elem.get_text(strip=True) for elem in soup.find_all(attrs={"data-ntid": True})]
        expected = [f"DỊCH: {entry['original_text']}" for entry in text_map]
        assert texts == expected

