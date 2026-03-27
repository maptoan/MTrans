from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Tuple

from bs4 import BeautifulSoup
from ebooklib import epub

logger = logging.getLogger("NovelTranslator")


def extract_text_map_from_html(html: str, chapter_id: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Trích TEXT_MAP từ một đoạn HTML đơn giản và gán data-ntid cho từng block element.

    - Xử lý các block cơ bản: h1-h6, p, li, blockquote, div, td, th.
    - [v9.2.1] Lưu original_inner_html để reconstruct inline formatting khi re-inject.
    - [v9.2.1] Đánh dấu image-only elements (data-nt-image-only) để skip khi dịch.
    """
    soup = BeautifulSoup(html, "html.parser")

    block_tags = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "div", "td", "th"]
    elements = soup.find_all(block_tags)

    text_map: List[Dict[str, Any]] = []

    order = 0
    for elem in elements:
        text = elem.get_text(separator=" ", strip=True)
        has_img = bool(elem.find("img"))

        # [v9.2.1] Image-only element: has <img> but no meaningful text
        if not text and has_img:
            text_id = f"{chapter_id}-{order:04d}"
            elem["data-ntid"] = text_id
            elem["data-nt-image-only"] = "true"
            text_map.append(
                {
                    "text_id": text_id,
                    "chapter_id": chapter_id,
                    "order": order,
                    "original_text": "",
                    "original_inner_html": elem.decode_contents(),
                    "is_image_only": True,
                }
            )
            order += 1
            continue

        if not text:
            continue

        text_id = f"{chapter_id}-{order:04d}"

        # Gán id ổn định lên DOM để có thể re-inject sau này
        elem["data-ntid"] = text_id

        # [v9.2.1] Lưu inner HTML gốc (bao gồm inline tags) để reconstruct khi reinject
        inner_html = elem.decode_contents()

        text_map.append(
            {
                "text_id": text_id,
                "chapter_id": chapter_id,
                "order": order,
                "original_text": text,
                "original_inner_html": inner_html,
            }
        )
        order += 1

    return text_map, str(soup)


def reinject_translations_to_html(html_with_ids: str, translations: Dict[str, str]) -> str:
    """
    Nhận HTML đã có data-ntid và map text_id -> bản dịch, trả về HTML mới
    với nội dung đã được thay thế nhưng vẫn giữ nguyên cấu trúc thẻ.

    [v9.2.1] Bảo toàn inline formatting (strong, em, a, span) và image-only elements.
    """
    soup = BeautifulSoup(html_with_ids, "html.parser")

    for elem in soup.find_all(attrs={"data-ntid": True}):
        text_id = elem.get("data-ntid")
        if not text_id:
            continue

        # [v9.2.1] Skip image-only elements: giữ nguyên ảnh, không dịch
        if elem.get("data-nt-image-only") == "true":
            continue

        translated = translations.get(text_id)
        if translated is None:
            continue

        # [v9.2.1] Preserve inline structure using _replace_with_structure_preservation
        _replace_with_structure_preservation(elem, translated)

    return str(soup)


def _replace_with_structure_preservation(elem: Any, translated: str) -> None:
    """
    [v9.2.1] Thay nội dung text của element bằng bản dịch, bảo toàn inline structure.

    Strategy:
    1. Nếu element chỉ có text thuần (không child tags): replace trực tiếp.
    2. Nếu element có nested inline tags: reconstruct structure template với bản dịch.
    3. Luôn preserve <img> tags.
    """
    from bs4 import NavigableString, Tag

    # Thu thập images trước khi clear
    imgs = [img.extract() for img in elem.find_all("img")]

    # Kiểm tra xem element có inline child tags không
    child_tags = [c for c in elem.children if isinstance(c, Tag)]
    inline_tags = {"strong", "em", "b", "i", "a", "span", "sub", "sup", "u", "s", "small", "mark"}

    if not child_tags:
        # Trường hợp đơn giản: chỉ có text → replace trực tiếp
        elem.clear()
        elem.append(translated)
    elif elem.name in ["td", "th"]:
        # Table cell: reconstruct nested structure
        _reconstruct_table_cell(elem, translated, child_tags)
    elif all(c.name in inline_tags for c in child_tags):
        # Inline-only children (p chứa strong, em, etc.)
        # Giữ wrapper tag đầu tiên nếu có, thay text bên trong
        _reconstruct_inline(elem, translated, child_tags)
    else:
        # Cấu trúc phức tạp: fallback to plain text
        elem.clear()
        elem.append(translated)

    # Re-append preserved images
    for img in imgs:
        elem.append(img)


def _reconstruct_table_cell(cell: Any, translated: str, child_tags: List[Any]) -> None:
    """Reconstruct table cell content, wrapping translated text in the same nested structure."""
    from bs4 import BeautifulSoup as BS

    # Phân tích cấu trúc wrapper (ví dụ: <p><strong>text</strong></p>)
    # Chỉ xử lý cấu trúc đơn giản (1 level hoặc 2 level nesting)
    wrapper_chain = _extract_wrapper_chain(child_tags)

    cell.clear()

    if wrapper_chain:
        # Reconstruct: tạo nested tags từ chain rồi đặt translated text vào innermost
        temp = BS("<temp></temp>", "html.parser").find("temp")
        current = temp
        for tag_name, attrs in wrapper_chain:
            new_tag = temp.find_parent().new_tag(tag_name, **attrs) if temp.find_parent() else BS(f"<{tag_name}></{tag_name}>", "html.parser").find(tag_name)
            # Copy attributes
            for k, v in attrs.items():
                new_tag[k] = v
            current.append(new_tag)
            current = new_tag
        current.append(translated)

        for child in list(temp.children):
            cell.append(child)
    else:
        cell.append(translated)


def _reconstruct_inline(elem: Any, translated: str, child_tags: List[Any]) -> None:
    """Reconstruct inline formatting: keep the first significant wrapper tag."""
    from bs4 import BeautifulSoup as BS

    # Nếu chỉ có 1 child tag inline (ví dụ: <p><strong>text</strong></p>)
    # → wrap translated text trong cùng tag đó
    if len(child_tags) == 1:
        wrapper = child_tags[0]
        tag_name = wrapper.name
        attrs = dict(wrapper.attrs) if wrapper.attrs else {}
        elem.clear()
        new_wrapper = BS(f"<{tag_name}></{tag_name}>", "html.parser").find(tag_name)
        for k, v in attrs.items():
            new_wrapper[k] = v
        new_wrapper.append(translated)
        elem.append(new_wrapper)
    else:
        # Nhiều inline children (ví dụ: <p><em>part1</em> <strong>part2</strong></p>)
        # Fallback: thay plain text vì không thể map chính xác
        elem.clear()
        elem.append(translated)


def _extract_wrapper_chain(child_tags: List[Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Trích chuỗi wrapper tags từ child_tags. Chỉ xử lý single-child nesting.
    Ví dụ: [<p><strong>text</strong></p>] → [("p", {}), ("strong", {})]
    """
    from bs4 import Tag

    chain: List[Tuple[str, Dict[str, Any]]] = []

    if len(child_tags) != 1:
        return chain

    current = child_tags[0]
    max_depth = 5  # Safety limit
    depth = 0

    while isinstance(current, Tag) and depth < max_depth:
        attrs = dict(current.attrs) if current.attrs else {}
        # Remove data-ntid from attributes to avoid duplication
        attrs.pop("data-ntid", None)
        attrs.pop("data-nt-image-only", None)
        chain.append((current.name, attrs))

        # Đi sâu vào single child tag
        sub_tags = [c for c in current.children if isinstance(c, Tag)]
        if len(sub_tags) == 1:
            current = sub_tags[0]
            depth += 1
        else:
            break

    return chain



def parse_epub_with_layout(filepath: str) -> Dict[str, Any]:
    """
    Phase 1: Parser EPUB v2 cho chế độ preserve_layout (POC).

    - Đọc EPUB bằng ebooklib.
    - Duyệt spine theo đúng reading order.
    - Với mỗi spine item dạng HTML/XHTML:
      - Dùng extract_text_map_from_html để sinh TEXT_MAP + gán data-ntid.
      - Lưu HTML đã gán id vào chapters_html[chapter_id].
    - Trả về:
      - text_map: List[dict]
      - chapters_html: Dict[chapter_id, html_with_ids]
      - metadata cơ bản (giống parse_epub hiện tại, đơn giản hóa cho Phase 1).
    """
    book = epub.read_epub(filepath)

    metadata: Dict[str, Any] = {
        "format": "epub",
        "title": book.get_metadata("DC", "title"),
        "author": book.get_metadata("DC", "creator"),
        "language": book.get_metadata("DC", "language"),
        "publisher": book.get_metadata("DC", "publisher"),
        "size_bytes": os.path.getsize(filepath),
    }

    # Flatten lists nếu cần
    for key in ["title", "author", "language", "publisher"]:
        if isinstance(metadata[key], list):
            metadata[key] = metadata[key][0] if metadata[key] else None

    text_map: List[Dict[str, Any]] = []
    chapters_html: Dict[str, str] = {}

    # Dùng spine để đảm bảo thứ tự đọc
    for itemref, _linear in book.spine:
        item = book.get_item_with_id(itemref)
        if item is None:
            continue

        # Bỏ qua nav/toc mặc định để không trộn vào chapter nội dung
        name = item.get_name() or ""
        if name.endswith("nav.xhtml") or name.endswith("toc.xhtml"):
            continue

        # Chỉ xử lý tài liệu text (HTML/XHTML) – ebooklib không expose hằng ITEM_DOCUMENT
        media_type = getattr(item, "media_type", "") or ""
        if not media_type.startswith("application/xhtml+xml") and not media_type.startswith(
            "text/html"
        ):
            continue

        try:
            raw_html = item.get_content().decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.warning(f"Không thể decode spine item {item.get_name()}: {exc}")
            continue

        chapter_id = item.get_name() or itemref

        chapter_text_map, chapter_html_with_ids = extract_text_map_from_html(
            raw_html, chapter_id
        )

        if not chapter_text_map:
            continue

        # Cập nhật chapter_id cho mọi entry (đề phòng extract_text_map dùng id khác)
        for entry in chapter_text_map:
            entry["chapter_id"] = chapter_id

        text_map.extend(chapter_text_map)
        chapters_html[chapter_id] = chapter_html_with_ids

    return {
        "text_map": text_map,
        "chapters_html": chapters_html,
        "metadata": metadata,
    }


