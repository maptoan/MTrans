# -*- coding: utf-8 -*-
"""
Module tối ưu hóa token bằng cách "nén" văn bản và dữ liệu (Minification).
Mục tiêu: Giảm số lượng token gửi lên Gemini mà không làm mất thông tin ngữ nghĩa quan trọng.
"""

import re
from typing import Any, Dict, List


class TokenOptimizer:
    """
    Cung cấp các phương thức để minification text, context, và metadata.
    """

    @staticmethod
    def minify_text(text: str) -> str:
        """
        Chuẩn hóa khoảng trắng cơ bản:
        - Xóa khoảng trắng đầu/cuối.
        - Thay thế nhiều khoảng trắng liên tiếp bằng 1 khoảng trắng.
        - Thay thế nhiều dòng trống liên tiếp bằng 1 dòng trống (`\n`).
        """
        if not text:
            return ""

        # Thay thế mọi whitespace sequence (space, tab) thành 1 space, nhưng giữ newline
        # Bước 1: Strip
        text = text.strip()

        # Bước 2: Collapse spaces (trừ newline)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]

        # Bước 3: Join lại, loại bỏ các dòng trống dư thừa (>1 dòng trống liên tiếp)
        result = []
        empty_line_count = 0

        for line in lines:
            if not line:
                if empty_line_count < 1:
                    result.append(line)
                    empty_line_count += 1
            else:
                result.append(line)
                empty_line_count = 0

        return "\n".join(result)

    @staticmethod
    def minify_context_chunk(text: str) -> str:
        """
        Nén Context Chunk mạnh hơn:
        - Xóa toàn bộ dòng trống (gộp paragraph).
        - Xóa các ký tự trang trí Markdown không cần thiết cho ngữ nghĩa (như **bold**, *italic* nếu chỉ để nhấn mạnh).
        - Tuy nhiên, để an toàn cho prompt, ta sẽ giữ lại cấu trúc câu.
        - Format: [Đoạn 1] [Đoạn 2]...
        """
        if not text:
            return ""

        # 1. Normalization cơ bản
        text = text.strip()

        # 2. Xóa markdown bold/italic (**text** -> text)
        # Lưu ý: Regex này đơn giản, có thể sót trường hợp phức tạp lồng nhau
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)

        # 3. Gộp dòng: Thay thế newline bằng space (biến context thành 1 block text dày đặc)
        # HOẶC giữ lại dấu hiệu tách đoạn tối thiểu ' | ' hoặc '\n' đơn
        # Ở đây chọn '\n' đơn để model dễ phân biệt, nhưng xóa dòng trống kép
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        return "\n".join(lines)

    @staticmethod
    def compact_list(items: List[str], separator: str = " | ") -> str:
        """
        Nén danh sách thành một chuỗi duy nhất, ngăn cách bởi separator.
        Ví dụ: ['A', 'B'] -> "A | B"
        """
        if not items:
            return ""
        return separator.join(
            [str(item).strip() for item in items if str(item).strip()]
        )

    @staticmethod
    def compact_dict(
        data: Dict[str, Any], pair_separator: str = ":", item_separator: str = "; "
    ) -> str:
        """
        Nén dictionary thành chuỗi.
        Ví dụ: {'Name': 'A', 'Age': 20} -> "Name:A; Age:20"
        """
        if not data:
            return ""

        parts = []
        for key, val in data.items():
            k = str(key).strip()
            v = str(val).strip()
            if k and v:
                parts.append(f"{k}{pair_separator}{v}")

        return item_separator.join(parts)

    @staticmethod
    def compact_glossary_terms(terms: List[Dict[str, Any]]) -> str:
        """
        Nén danh sách thuật ngữ glossary thành format siêu gọn.
        Format: "Original(Pinyin)->Translated[Notes]; ..."
        """
        if not terms:
            return ""

        compact_items = []
        for term in terms:
            original = (
                term.get("Original_Term_CN")
                or term.get("Original_Term_Pinyin")
                or term.get("Original_Term_EN")
                or ""
            ).strip()
            pinyin = (term.get("Original_Term_Pinyin") or "").strip()
            translated = (
                term.get("Translated_Term_VI")
                or term.get("Translated_Term_EN")
                or term.get("Translated")
                or ""
            ).strip()
            notes = (term.get("Notes") or "").strip()

            if original and translated:
                item_str = f"{original}"
                if pinyin and pinyin != original:
                    item_str += f"({pinyin})"
                item_str += f"->{translated}"
                if notes:
                    item_str += f"[{notes}]"

                compact_items.append(item_str)

        return "; ".join(compact_items)

    @staticmethod
    def optimize_prompt_section(title: str, content: str) -> str:
        """
        Tạo một section trong prompt nhưng xóa khoảng trắng thừa của tiêu đề và nội dung.
        """
        return f"{title.strip()}\n{TokenOptimizer.minify_text(content)}"
