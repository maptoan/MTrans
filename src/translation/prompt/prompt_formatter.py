# -*- coding: utf-8 -*-
from __future__ import annotations

"""
PromptFormatter - Format và assembly logic cho prompts.

Extracted from PromptBuilder to improve modularity and maintainability.
"""

from typing import Dict, List


class PromptFormatter:
    """
    Xử lý formatting và assembly của prompt components.
    """

    def __init__(self, use_markers: bool = True):
        self.use_markers = use_markers

    def format_glossary_for_prompt(self, glossary_terms: List[Dict]) -> str:
        """
        Format glossary terms for use in prompts.
        """
        if not glossary_terms:
            return "(No specific glossary terms for this chunk)"

        lines = []
        for term in glossary_terms:
            # Ưu tiên hiển thị cả CN và Pinyin nếu có để AI dễ nhận diện
            orig_cn = term.get("Original_Term_CN", "")
            orig_pinyin = term.get("Original_Term_Pinyin", "")
            tgt = term.get("Translated_Term_VI", "")
            note = term.get("Note", "")

            # Label
            src_label = orig_cn
            if orig_pinyin:
                if src_label:
                    src_label += f" ({orig_pinyin})"
                else:
                    src_label = orig_pinyin

            if src_label and tgt:
                line = f"- {src_label} -> {tgt}"
                if note:
                    line += f" [Note: {note}]"
                lines.append(line)

        return "\n".join(lines)

    def build_summary_section(self, contains_potential_title: bool) -> str:
        """
        Tạo summary section ngắn gọn ở đầu prompt để AI nắm tổng quan.
        """
        summary_parts = ["[TÓM TẮT YÊU CẦU]"]

        if self.use_markers:
            summary_parts.append("→ Giữ nguyên markers [CHUNK:ID:START/END]")

        summary_parts.append("→ Dịch chính xác theo glossary và quy tắc xưng hô")
        summary_parts.append("→ Giữ nguyên paragraph breaks như bản gốc")

        if contains_potential_title:
            summary_parts.append(
                "→ Tiêu đề chương: [H1]...[/H1], Tiêu đề mục: [H2]...[/H2]"
            )

        summary_parts.append("→ Văn phong tự nhiên, nhịp điệu tốt, không lặp từ")
        summary_parts.append("→ Đọc lại như độc giả trước khi trả về")

        return "\n".join(summary_parts)

    def build_cjk_guardrail(self) -> str:
        """
        CJK guardrail rút gọn.
        """
        return """[RÀO CHẮN CJK]
→ Mọi ký tự CJK (汉/かな/한글) PHẢI được dịch sang tiếng Việt
→ Nếu phát hiện còn CJK → Tự sửa câu/đoạn đó ngay
→ Đầu ra chỉ gồm tiếng Việt thuần"""

    def build_glossary_section_compact(self, glossary_section: str) -> str:
        """
        Glossary section rút gọn - Tăng cường tính bắt buộc.
        """
        return f"""⚠️ [THUẬT NGỮ BẮT BUỘC - VI PHẠM SẼ BỊ TỪ CHỐI] ⚠️

{glossary_section}

🔴 QUY TẮC NGHIÊM NGẶT:
1. PHẢI dịch CHÍNH XÁC theo bảng - KHÔNG được thay đổi.
2. PHẢI dùng âm Hán-Việt, KHÔNG dùng pinyin.

❌ SAI: "Cui Xiao Xuan", "Xie Huang", "Jing"
✓ ĐÚNG: "Thôi Tiểu Huyền", "Tà Hoàng", "Kinh Thành" """
