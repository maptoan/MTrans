"""Tests for v9.2.1 layout bug fixes: inline formatting, image-only, table nested structure."""
from __future__ import annotations

from typing import Dict

import pytest
from bs4 import BeautifulSoup

from src.preprocessing.epub_layout_parser import (
    extract_text_map_from_html,
    reinject_translations_to_html,
)
from src.output.epub_reinject import (
    apply_translations_to_chapters,
    build_html_master,
)


class TestImageOnlyPreservation:
    """Image-only elements should be tagged and preserved through reinject."""

    def test_extract_marks_image_only_elements(self) -> None:
        html = '<html><body><p><img src="cover.jpg"/></p><p>Hello world</p></body></html>'
        text_map, html_with_ids = extract_text_map_from_html(html, "ch1")

        img_entries = [e for e in text_map if e.get("is_image_only")]
        assert len(img_entries) == 1
        assert img_entries[0]["original_text"] == ""
        assert "cover.jpg" in img_entries[0]["original_inner_html"]

    def test_reinject_skips_image_only_elements(self) -> None:
        html = '<html><body><p data-ntid="ch1-0000" data-nt-image-only="true"><img src="cover.jpg"/></p><p data-ntid="ch1-0001">Hello</p></body></html>'
        translations = {"ch1-0001": "Xin chào"}

        result = reinject_translations_to_html(html, translations)
        soup = BeautifulSoup(result, "html.parser")

        # Image should be preserved
        imgs = soup.find_all("img")
        assert len(imgs) == 1
        assert imgs[0]["src"] == "cover.jpg"

        # Text should be translated
        p_translated = soup.find(attrs={"data-ntid": "ch1-0001"})
        assert p_translated.get_text(strip=True) == "Xin chào"

    def test_master_html_preserves_images(self) -> None:
        """build_html_master should include images from translated chapters."""
        chapter_html = '<html><body><p data-ntid="ch1-0000" data-nt-image-only="true"><img src="images/cover.jpg"/></p><h1 data-ntid="ch1-0001">Title</h1></body></html>'
        translations = {"ch1-0001": "Tiêu đề"}
        translated = reinject_translations_to_html(chapter_html, translations)

        master = build_html_master({"ch1.xhtml": translated}, title="Test")
        soup = BeautifulSoup(master, "html.parser")

        imgs = soup.find_all("img")
        assert len(imgs) >= 1
        # Master HTML flattens image paths to basename
        assert imgs[0]["src"] == "cover.jpg"


class TestInlineFormattingPreservation:
    """Inline tags (strong, em, a) should be preserved after reinject."""

    def test_plain_text_element_unchanged_behavior(self) -> None:
        """Simple text-only elements should still work as before."""
        html = '<p data-ntid="ch1-0000">Hello world</p>'
        translations = {"ch1-0000": "Xin chào thế giới"}

        result = reinject_translations_to_html(html, translations)
        soup = BeautifulSoup(result, "html.parser")

        p = soup.find("p")
        assert p.get_text(strip=True) == "Xin chào thế giới"

    def test_single_inline_wrapper_preserved(self) -> None:
        """<p><strong>text</strong></p> → <p><strong>translated</strong></p>"""
        html = '<p data-ntid="ch1-0000"><strong>Important text</strong></p>'
        translations = {"ch1-0000": "Văn bản quan trọng"}

        result = reinject_translations_to_html(html, translations)
        soup = BeautifulSoup(result, "html.parser")

        p = soup.find("p")
        strong = p.find("strong")
        assert strong is not None, "strong tag should be preserved"
        assert strong.get_text(strip=True) == "Văn bản quan trọng"

    def test_nested_inline_wrapper_preserved(self) -> None:
        """<p><em><strong>text</strong></em></p> → keeps outer wrapper at least."""
        html = '<p data-ntid="ch1-0000"><em>Emphasized text</em></p>'
        translations = {"ch1-0000": "Văn bản nhấn mạnh"}

        result = reinject_translations_to_html(html, translations)
        soup = BeautifulSoup(result, "html.parser")

        p = soup.find("p")
        em = p.find("em")
        assert em is not None, "em tag should be preserved"
        assert em.get_text(strip=True) == "Văn bản nhấn mạnh"

    def test_multiple_inline_children_fallback(self) -> None:
        """<p><em>part1</em> <strong>part2</strong></p> → fallback to plain text."""
        html = '<p data-ntid="ch1-0000"><em>First</em> <strong>Second</strong></p>'
        translations = {"ch1-0000": "Đầu tiên Thứ hai"}

        result = reinject_translations_to_html(html, translations)
        soup = BeautifulSoup(result, "html.parser")

        p = soup.find("p")
        assert p.get_text(strip=True) == "Đầu tiên Thứ hai"

    def test_image_inside_text_element_preserved(self) -> None:
        """<p>Text <img src="icon.png"/> more text</p> → img preserved after translated text."""
        # First extract to get proper IDs
        html = '<html><body><p>Some text <img src="icon.png"/> here</p></body></html>'
        text_map, html_with_ids = extract_text_map_from_html(html, "ch1")

        assert len(text_map) == 1
        assert text_map[0]["original_text"] == "Some text here"

        translations = {text_map[0]["text_id"]: "Một số văn bản ở đây"}
        result = reinject_translations_to_html(html_with_ids, translations)
        soup = BeautifulSoup(result, "html.parser")

        # Image should still be present
        imgs = soup.find_all("img")
        assert len(imgs) == 1
        assert imgs[0]["src"] == "icon.png"

        # Text should be translated
        p = soup.find("p")
        assert "Một số văn bản ở đây" in p.get_text()


class TestTableNestedStructure:
    """Table cell nested structure (td/th with p, strong, span) should be preserved."""

    def test_simple_table_cell(self) -> None:
        """<td>plain text</td> → <td>translated</td>"""
        html = '<td data-ntid="ch1-0000">Plain cell</td>'
        translations = {"ch1-0000": "Ô đơn giản"}

        result = reinject_translations_to_html(html, translations)
        soup = BeautifulSoup(result, "html.parser")

        td = soup.find("td")
        assert td.get_text(strip=True) == "Ô đơn giản"

    def test_table_cell_with_bold_wrapper(self) -> None:
        """<td><strong>Header</strong></td> → <td><strong>translated</strong></td>"""
        # Use extract to do proper setup
        html = '<html><body><table><tr><td><strong>Header Text</strong></td></tr></table></body></html>'
        text_map, html_with_ids = extract_text_map_from_html(html, "ch1")

        assert len(text_map) >= 1
        td_entry = text_map[0]
        assert td_entry["original_text"] == "Header Text"

        translations = {td_entry["text_id"]: "Văn Bản Tiêu Đề"}
        result = reinject_translations_to_html(html_with_ids, translations)
        soup = BeautifulSoup(result, "html.parser")

        td = soup.find("td")
        strong = td.find("strong")
        assert strong is not None, "strong tag inside td should be preserved"
        assert strong.get_text(strip=True) == "Văn Bản Tiêu Đề"

    def test_table_cell_with_p_strong_nesting(self) -> None:
        """<td><p><strong>text</strong></p></td> → nested structure preserved."""
        html = '<html><body><table><tr><td><p><strong>Deep nested</strong></p></td></tr></table></body></html>'
        text_map, html_with_ids = extract_text_map_from_html(html, "ch1")

        # td gets data-ntid; p inside would also get one — find the td entry
        td_entries = [e for e in text_map if "Deep nested" in e["original_text"]]
        assert len(td_entries) >= 1

        # Use the first (td) entry
        td_entry = td_entries[0]
        translations = {e["text_id"]: f"TR-{e['original_text']}" for e in text_map}
        result = reinject_translations_to_html(html_with_ids, translations)
        soup = BeautifulSoup(result, "html.parser")

        td = soup.find("td")
        assert td is not None
        # Verify the translated text is present
        assert "TR-Deep nested" in td.get_text()

    def test_table_cell_attributes_preserved(self) -> None:
        """td attributes (style, colspan) must be preserved (v9.2 achievement)."""
        html = '<html><body><table><tr><td style="background:#FFC" colspan="2"><strong>Styled</strong></td></tr></table></body></html>'
        text_map, html_with_ids = extract_text_map_from_html(html, "ch1")

        translations = {e["text_id"]: "Có phong cách" for e in text_map}
        result = reinject_translations_to_html(html_with_ids, translations)
        soup = BeautifulSoup(result, "html.parser")

        td = soup.find("td")
        assert td is not None
        assert td.get("style") == "background:#FFC"
        assert td.get("colspan") == "2"
        assert "Có phong cách" in td.get_text()


class TestExtractTextMapInnerHTML:
    """extract_text_map_from_html should capture original_inner_html."""

    def test_plain_text_inner_html(self) -> None:
        html = '<html><body><p>Simple text</p></body></html>'
        text_map, _ = extract_text_map_from_html(html, "ch1")

        assert len(text_map) == 1
        assert text_map[0]["original_inner_html"] == "Simple text"

    def test_inline_formatting_inner_html(self) -> None:
        html = '<html><body><p><strong>Bold</strong> and <em>italic</em></p></body></html>'
        text_map, _ = extract_text_map_from_html(html, "ch1")

        assert len(text_map) == 1
        inner = text_map[0]["original_inner_html"]
        assert "<strong>" in inner
        assert "<em>" in inner

    def test_image_only_inner_html(self) -> None:
        html = '<html><body><div><img src="photo.jpg" alt="Photo"/></div></body></html>'
        text_map, _ = extract_text_map_from_html(html, "ch1")

        img_entries = [e for e in text_map if e.get("is_image_only")]
        assert len(img_entries) == 1
        assert "photo.jpg" in img_entries[0]["original_inner_html"]
