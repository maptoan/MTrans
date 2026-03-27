# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("NovelTranslator")


class TranslationRefiner:
    """
    Handles post-translation refinement logic:
    - Metadata compliance check
    - Glossary auto-fix
    - CJK remaining detection
    """

    def __init__(self, config: Dict[str, Any], relation_manager: Any):
        self.config = config
        self.relation_manager = relation_manager

    def validate_metadata_compliance(
        self,
        translation: str,
        relevant_terms: List[Dict],
        active_characters: List[str],
        chunk_id: int,
    ) -> bool:
        """
        Validate xem AI có tuân thủ metadata guidelines không.
        """
        compliance_issues = []

        # 1. Kiểm tra glossary compliance
        for term in relevant_terms:
            cn_term = term.get("Original_Term_CN", "")
            pinyin_term = term.get("Original_Term_Pinyin", "")
            vi_term = term.get("Translated_Term_VI", "")

            if cn_term and cn_term != vi_term and cn_term in translation:
                compliance_issues.append(
                    f"Glossary term CN '{cn_term}' vẫn còn trong bản dịch (cần thay bằng '{vi_term}')"
                )
                logger.warning(
                    f"[Chunk {chunk_id}] Glossary violation - CN term '{cn_term}' chưa được dịch"
                )

            if pinyin_term and pinyin_term.lower() in translation.lower():
                compliance_issues.append(
                    f"Glossary term Pinyin '{pinyin_term}' vẫn còn trong bản dịch (cần thay bằng '{vi_term}')"
                )
                logger.warning(
                    f"[Chunk {chunk_id}] Glossary violation - Pinyin term '{pinyin_term}' chưa được dịch"
                )

        # 2. Kiểm tra character compliance
        if active_characters:
            for char in active_characters:
                pronoun_rules = self.relation_manager.get_pronoun_guidance(char, "")
                if pronoun_rules:
                    for rule in pronoun_rules:
                        expected_pronoun = rule.get("Pronoun_VN", "")
                        if (
                            expected_pronoun
                            and expected_pronoun.lower() not in translation.lower()
                        ):
                            compliance_issues.append(
                                f"Character '{char}' pronoun rule not followed: expected '{expected_pronoun}'"
                            )
                            logger.warning(
                                f"[Chunk {chunk_id}] Character compliance issue - '{char}' pronoun rule not followed"
                            )

        if compliance_issues:
            logger.warning(
                f"[Chunk {chunk_id}] Found {len(compliance_issues)} metadata compliance issues"
            )
            for issue in compliance_issues:
                logger.warning(f"  - {issue}")
        else:
            logger.debug(f"[Chunk {chunk_id}] Metadata compliance check passed")

        return len(compliance_issues) == 0

    def auto_fix_glossary(
        self, translation: str, relevant_terms: List[Dict]
    ) -> Tuple[str, int]:
        """
        Tự động sửa lỗi glossary bằng cách thay thế các term gốc/pinyin bị sót.
        """
        fixed_text = translation
        count = 0

        sorted_terms = sorted(
            relevant_terms,
            key=lambda x: len(x.get("Original_Term_Pinyin", ""))
            + len(x.get("Original_Term_CN", "")),
            reverse=True,
        )

        for term in sorted_terms:
            vi_term = term.get("Translated_Term_VI", "")
            if not vi_term:
                continue

            cn_term = term.get("Original_Term_CN")
            if cn_term and cn_term in fixed_text:
                fixed_text = fixed_text.replace(cn_term, vi_term)
                count += 1

            pinyin_term = term.get("Original_Term_Pinyin")
            if pinyin_term:
                pattern = re.compile(re.escape(pinyin_term), re.IGNORECASE)
                if pattern.search(fixed_text):
                    fixed_text = pattern.sub(vi_term, fixed_text)
                    count += 1

        return fixed_text, count

    def auto_fix_glossary_enhanced(
        self, text: str, terms: List[Dict], max_passes: int = 2
    ) -> Tuple[str, int]:
        """
        Multi-pass auto-fix to handle nested terms or terms that appear after a replacement.
        """
        if not text or not terms:
            return text, 0

        total_fixed = 0
        current_text = text
        
        for p in range(max_passes):
            new_text, count = self.auto_fix_glossary(current_text, terms)
            total_fixed += count
            if count == 0:
                break
            current_text = new_text
            
        if total_fixed > 0:
            logger.debug(f"Enhanced auto-fix: Đã thực hiện {total_fixed} thay thế qua {p+1} vòng.")
            
        return current_text, total_fixed

    def detect_cjk_remaining(self, text: str) -> List[str]:
        """
        Phát hiện các từ CJK (Trung, Nhật, Hàn) còn sót trong bản dịch.
        """
        if not text:
            return []

        cjk_pattern = re.compile(r"[一-鿿㐀-䶿豈-﫿]+")
        matches = cjk_pattern.findall(text)

        if not matches:
            return []

        unique_matches = sorted(list(set(matches)), key=len, reverse=True)
        return unique_matches

    def enforce_narrative_terms(self, text: str) -> str:
        """
        Chuẩn hóa đại từ trần thuật theo mapping từ RelationManager, bỏ qua vùng đối thoại.
        """
        mapping = self.relation_manager.get_narrative_terms_map()
        if not mapping or not text:
            return text

        # Xác định vùng đối thoại để bỏ qua thay thế
        dialogue_delims = (
            self.config.get("translation", {})
            .get("postprocessing", {})
            .get("dialog_quotations", ['"', "“”", "『』", "「」"])
        )
        # Tách đơn giản theo dòng; chỉ xử lý dòng không bắt đầu/khép bởi ngoặc thoại
        lines = text.split("\n")
        processed = []
        pronoun_set = {"anh", "cậu", "chàng", "cậu ấy", "y", "nàng", "hắn", "cô"}

        for ln in lines:
            ln_strip = ln.strip()
            is_dialogue = False
            for pair in dialogue_delims:
                if len(pair) == 1:
                    if (
                        ln_strip.startswith(pair)
                        and ln_strip.endswith(pair)
                        and len(ln_strip) > 1
                    ):
                        is_dialogue = True
                        break
                elif len(pair) == 2:
                    if ln_strip.startswith(pair[0]) and ln_strip.endswith(pair[1]):
                        is_dialogue = True
                        break
            if is_dialogue:
                processed.append(ln)
                continue

            # Với trần thuật: nếu có nhắc tới tên nhân vật, chuẩn hóa đại từ phổ biến
            lowered = ln
            for char_id, pron in mapping.items():
                if char_id and char_id in lowered:
                    for wrong in pronoun_set:
                        if wrong != pron:
                            lowered = re.sub(
                                rf"(?<![\w]){re.escape(wrong)}(?![\w])", pron, lowered
                            )
            processed.append(lowered)
        return "\n".join(processed)
