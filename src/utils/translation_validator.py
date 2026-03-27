# -*- coding: utf-8 -*-

"""
Translation Validator
=====================
Module kiểm tra tính toàn vẹn của bản dịch so với bản gốc.
Mục tiêu: Đảm bảo không bị mất nội dung quan trọng (hội thoại, đoạn văn) và cấu trúc câu hợp lệ.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NovelTranslator")


class TranslationValidator:
    """
    Validator kiểm tra chất lượng cấu trúc của bản dịch.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        # Ngưỡng cảnh báo chênh lệch số lượng trích dẫn (quote)
        self.quote_mismatch_threshold = 0.2  # 20%

    def validate(self, original_text: str, translated_text: str) -> Dict[str, Any]:
        """
        Thực hiện tất cả các kiểm tra validation.

        Returns:
            Dict kết quả: {'is_valid': bool, 'issues': List[str], 'score': float}
        """
        issues = []

        # 1. Kiểm tra tính toàn vẹn của câu (Sentence Integrity)
        if not self._check_sentence_integrity(translated_text):
            # [Relaxed] Downgrade logical error from Critical to Warning
            issues.append(
                "Cảnh báo: Bản dịch có thể kết thúc đột ngột (thiếu dấu câu kết thúc)."
            )
            # is_valid = False  <-- Bỏ comment này để cho phép pass

        # 2. Kiểm tra cân bằng hội thoại (Quote Balance)
        quote_issues = self._check_quote_balance(original_text, translated_text)
        if quote_issues:
            issues.extend(quote_issues)
            # Quote mismatch có thể chấp nhận được ở mức độ thấp, nhưng ở đây ta strict warning

        # 3. Kiểm tra độ dài/cấu trúc (Structure Ratio)
        # (Có thể thêm sau nếu cần)

        # 4. Kiểm tra paragraph spacing
        spacing_issues = self._check_paragraph_spacing(translated_text)
        if spacing_issues:
            issues.extend(spacing_issues)

        # 5. Kiểm tra dialogue formatting
        dialogue_issues = self._check_dialogue_formatting(translated_text)
        if dialogue_issues:
            issues.extend(dialogue_issues)

        # Determine strictness (Phase 2)
        # Formatting errors should be treated as critical to force retry/correction
        has_critical_error = False
        for issue in issues:
            # Check for critical keywords
            if "Lỗi formatting" in issue:
                has_critical_error = True
            # Check for dialogue warning (might be stylistic, but usually critical for novels)
            if "thiếu dấu ngoặc kép" in issue:
                has_critical_error = True

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "has_critical_error": has_critical_error,
        }

    def _check_sentence_integrity(self, text: str) -> bool:
        """
        Kiểm tra xem text có kết thúc bằng dấu câu hợp lệ không.
        Tránh trường hợp bị cắt giữa chừng (truncated).
        """
        if not text:
            return True  # Empty is valid contextually (maybe) but suspicious. Let's assume Valid for syntax.

        text = text.strip()
        if not text:
            return True

        # Các dấu kết câu hợp lệ: . ! ? " ” ' ’ > ) ] } —
        # Lưu ý: Đôi khi kết thúc bằng ngoặc đóng là hợp lệ.
        valid_endings = (
            ".",
            "!",
            "?",
            '"',
            "”",
            "’",
            "…",
            ">",
            ")",
            "]",
            "}",
            "—",
            "-",
        )

        return text.endswith(valid_endings)

    def _check_quote_balance(self, original: str, translated: str) -> List[str]:
        """
        So sánh số lượng dấu ngoặc kép giữa bản gốc và bản dịch.
        """
        issues = []

        # Đếm dấu ngoặc kép trong bản gốc (bao gồm cả CJK quotes)
        # CJK quotes: 「」『』“”
        # ASCII quotes: "

        orig_quotes = len(re.findall(r'["“”「」『』]', original))
        trans_quotes = len(
            re.findall(r'["“”]', translated)
        )  # Bản dịch tiếng Việt chủ yếu dùng " “”

        # Nếu bản gốc không có quote, không cần check
        if orig_quotes == 0:
            return []

        # Tính tỷ lệ chênh lệch
        # [FIX] Chỉ cảnh báo khi bản dịch CÓ ÍT HƠN bản gốc (có thể mất nội dung)
        # Cho phép bản dịch nhiều hơn (có thể do AI thêm emphasis hoặc nested quotes)
        if trans_quotes < orig_quotes:
            diff = orig_quotes - trans_quotes
            ratio = diff / orig_quotes

            if ratio > self.quote_mismatch_threshold:
                issues.append(
                    f"Cảnh báo chênh lệch hội thoại: Bản gốc có ~{orig_quotes} dấu trích dẫn, "
                    f"Bản dịch chỉ có {trans_quotes} (Thiếu {ratio:.0%})"
                )

        return issues

    def _check_paragraph_spacing(self, text: str) -> List[str]:
        """
        Kiểm tra khoảng cách giữa các đoạn văn (yêu cầu \n\n).
        """
        if not text:
            return []

        issues = []
        # Tỷ lệ dòng đơn so với đoạn văn
        # Nếu > 80% là dòng đơn (không có dòng trống ở giữa), có thể là lỗi formatting
        text.split("\n")
        paragraphs = text.split("\n\n")

        # Nếu văn bản dài (>1200 chars) mà chỉ có 1 paragraph -> Lỗi
        # [Relaxed for Lite models] Tăng từ 500 lên 1200 để tránh false positives
        if len(text) > 1200 and len(paragraphs) <= 1:
            issues.append(
                "Lỗi formatting: Văn bản dài nhưng thiếu dòng trống ngăn cách các đoạn văn."
            )
            return issues

        return issues

    def _check_dialogue_formatting(self, text: str) -> List[str]:
        """
        Kiểm tra định dạng hội thoại (yêu cầu dùng cặp dấu ngoặc kép " ").
        """
        if not text:
            return []

        issues = []

        # Các từ chỉ dẫn hội thoại phổ biến
        dialogue_verbs = [
            "nói:",
            "hỏi:",
            "đáp:",
            "bảo:",
            "kêu:",
            "thốt:",
            "cười:",
            "nghĩ:",
            "nói rằng",
            "hỏi rằng",
        ]
        lower_text = text.lower()

        # Kiểm tra xem có từ chỉ dẫn nhưng thiếu dấu ngoặc kép không
        likely_dialogue_count = 0
        quoted_dialogue_count = len(re.findall(r'["“”]', text)) / 2  # Mỗi cặp là 2 dấu

        for verb in dialogue_verbs:
            likely_dialogue_count += lower_text.count(verb)

        # Nếu có nhiều từ chỉ dẫn hội thoại (>3) nhưng rất ít dấu ngoặc kép (<10% so với verbs)
        if likely_dialogue_count > 3:
            if quoted_dialogue_count < likely_dialogue_count * 0.1:
                issues.append(
                    f'Cảnh báo formatting: Phát hiện {likely_dialogue_count} từ chỉ thoại nhưng thiếu dấu ngoặc kép ("{quoted_dialogue_count} cặp).'
                )

        return issues
