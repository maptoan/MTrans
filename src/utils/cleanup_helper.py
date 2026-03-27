# -*- coding: utf-8 -*-

"""
Cleanup Helper: Sentence-level và Word-level cleanup cho bản dịch.

Các chức năng chính:
- Extract và phân tích câu chứa CJK characters
- Phân loại complexity của câu (simple/complex)
- Tìm câu gốc tương ứng với câu dịch
- Smart word replacement với spacing tự động
- Cleanup spacing dư thừa
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")


@dataclass
class SentenceInfo:
    """
    Thông tin về một câu chứa CJK characters.

    Attributes:
        sentence: Nội dung câu
        cjk_terms: Danh sách các từ CJK có trong câu (unique)
        start_pos: Vị trí bắt đầu của câu trong văn bản gốc
        end_pos: Vị trí kết thúc của câu trong văn bản gốc
        complexity: Độ phức tạp ('simple' hoặc 'complex')
    """

    sentence: str
    cjk_terms: List[str]
    start_pos: int
    end_pos: int
    complexity: str  # 'simple' hoặc 'complex'


class SentenceExtractor:
    """
    Utility class để extract và phân tích câu chứa CJK characters.

    Cung cấp các phương thức để:
    - Tách văn bản thành các câu với position tracking
    - Tìm các câu chứa CJK và phân loại complexity
    - Tìm câu gốc tương ứng với câu dịch dựa trên CJK terms
    """

    # Regex patterns
    SENTENCE_DELIMITERS: re.Pattern[str] = re.compile(r"[.!?。！？]+")
    CJK_PATTERN: re.Pattern[str] = re.compile(
        r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+"
    )

    # Thresholds cho complexity classification
    COMPLEX_THRESHOLD_CJK_COUNT: int = 3  # >= 3 từ CJK = phức tạp
    COMPLEX_THRESHOLD_LENGTH: int = 100  # >= 100 ký tự = phức tạp

    @staticmethod
    def split_into_sentences(text: str) -> List[Tuple[str, int, int]]:
        """
        Tách văn bản thành các câu với position tracking.

        Sử dụng các dấu câu: . ! ? 。 ！ ？ để phân tách câu.
        Mỗi câu được trả về kèm vị trí bắt đầu và kết thúc trong văn bản gốc.

        Args:
            text: Văn bản cần tách thành câu

        Returns:
            List các tuple (sentence, start_pos, end_pos)

        Example:
            >>> sentences = SentenceExtractor.split_into_sentences("Hello. World!")
            >>> # Returns: [("Hello.", 0, 6), (" World!", 6, 13)]
        """
        sentences: List[Tuple[str, int, int]] = []
        last_end = 0

        for match in SentenceExtractor.SENTENCE_DELIMITERS.finditer(text):
            # Lấy câu từ vị trí cuối câu trước đến dấu câu hiện tại
            start = last_end
            end = match.end()
            sentence = text[start:end].strip()

            if sentence:
                sentences.append((sentence, start, end))

            last_end = end

        # Câu cuối cùng (nếu không kết thúc bằng dấu câu)
        if last_end < len(text):
            sentence = text[last_end:].strip()
            if sentence:
                sentences.append((sentence, last_end, len(text)))

        return sentences

    @staticmethod
    def find_sentences_with_cjk(text: str) -> List[SentenceInfo]:
        """
        Tìm tất cả các câu có chứa ký tự CJK và phân loại complexity.

        Phân loại complexity dựa trên:
        - Số lượng từ CJK unique: >= 3 = complex
        - Độ dài câu: >= 100 ký tự = complex

        Args:
            text: Văn bản cần phân tích

        Returns:
            List các SentenceInfo objects chứa thông tin về các câu có CJK

        Example:
            >>> text = "Hello 你好 world. 这是一个复杂的句子。"
            >>> results = SentenceExtractor.find_sentences_with_cjk(text)
            >>> # Returns list of SentenceInfo objects
        """
        sentences = SentenceExtractor.split_into_sentences(text)
        results: List[SentenceInfo] = []

        for sentence, start_pos, end_pos in sentences:
            # Tìm CJK trong câu
            cjk_terms = SentenceExtractor.CJK_PATTERN.findall(sentence)

            if cjk_terms:
                unique_cjk = list(set(cjk_terms))

                # Classify complexity
                is_complex = (
                    len(unique_cjk) >= SentenceExtractor.COMPLEX_THRESHOLD_CJK_COUNT
                    or len(sentence) >= SentenceExtractor.COMPLEX_THRESHOLD_LENGTH
                )

                results.append(
                    SentenceInfo(
                        sentence=sentence,
                        cjk_terms=unique_cjk,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        complexity="complex" if is_complex else "simple",
                    )
                )

        return results

    @staticmethod
    def find_original_sentence(
        translated_sentence: str, original_text: str, cjk_terms: List[str]
    ) -> Optional[str]:
        """
        Tìm câu gốc tiếng Trung tương ứng với câu dịch.

        Strategy: Match dựa trên CJK terms có trong câu dịch.
        Tính điểm match dựa trên tỷ lệ CJK terms xuất hiện trong câu gốc.
        Chỉ trả về câu gốc nếu match score >= 50%.

        Args:
            translated_sentence: Câu đã dịch (có CJK sót) - không sử dụng trong logic hiện tại
            original_text: Văn bản gốc tiếng Trung
            cjk_terms: List các từ CJK trong câu dịch (dùng để match)

        Returns:
            Câu gốc tiếng Trung nếu tìm thấy match >= 50%, None nếu không

        Example:
            >>> original = "这是一个测试。"
            >>> cjk_terms = ["测试"]
            >>> sentence = SentenceExtractor.find_original_sentence("", original, cjk_terms)
            >>> # Returns: "这是一个测试。"
        """
        if not cjk_terms or not original_text:
            return None

        original_sentences = SentenceExtractor.split_into_sentences(original_text)

        best_match: Optional[str] = None
        best_score = 0.0

        for orig_sent, _, _ in original_sentences:
            # Tính điểm match dựa trên số CJK terms xuất hiện
            match_count = sum(1 for cjk in cjk_terms if cjk in orig_sent)
            score = match_count / len(cjk_terms) if cjk_terms else 0.0

            if score > best_score:
                best_score = score
                best_match = orig_sent

        # Chỉ return nếu match >= 50%
        if best_score >= 0.5:
            return best_match

        return None


class CleanupHelper:
    """
    Helper class cho cả sentence-level và word-level cleanup.

    Cung cấp các phương thức để:
    - Thay thế từ CJK bằng bản dịch với smart spacing
    - Cleanup spacing dư thừa trong văn bản
    """

    @staticmethod
    def smart_word_replacement(text: str, cjk_term: str, viet_translation: str) -> str:
        """
        Thay thế từ CJK bằng bản dịch với smart spacing.

        Xử lý 4 trường hợp:
        1. CJK giữa 2 chữ Latin/Vietnamese → thêm space cả 2 bên
        2. CJK sau chữ Latin/Vietnamese → thêm space trước
        3. CJK trước chữ Latin/Vietnamese → thêm space sau
        4. CJK đơn độc → thay thế trực tiếp không thêm space

        Args:
            text: Văn bản cần replace
            cjk_term: Từ CJK gốc cần thay thế
            viet_translation: Bản dịch tiếng Việt để thay thế

        Returns:
            Văn bản đã được thay thế với spacing hợp lý

        Example:
            >>> text = "Hello你好world"
            >>> result = CleanupHelper.smart_word_replacement(text, "你好", "xin chào")
            >>> # Returns: "Hello xin chào world"
        """
        escaped_cjk = re.escape(cjk_term)

        # Pattern 1: CJK giữa 2 chữ Latin/Vietnamese
        pattern_between = rf"(?<=[a-zA-ZÀ-ỹ])({escaped_cjk})(?=[a-zA-ZÀ-ỹ])"
        text = re.sub(pattern_between, f" {viet_translation} ", text)

        # Pattern 2: CJK sau chữ Latin/Vietnamese
        pattern_after = rf"(?<=[a-zA-ZÀ-ỹ])({escaped_cjk})"
        text = re.sub(pattern_after, f" {viet_translation}", text)

        # Pattern 3: CJK trước chữ Latin/Vietnamese
        pattern_before = rf"({escaped_cjk})(?=[a-zA-ZÀ-ỹ])"
        text = re.sub(pattern_before, f"{viet_translation} ", text)

        # Pattern 4: CJK đơn độc
        pattern_alone = rf"(?<![a-zA-ZÀ-ỹ])({escaped_cjk})(?![a-zA-ZÀ-ỹ])"
        text = re.sub(pattern_alone, viet_translation, text)

        return text

    @staticmethod
    def cleanup_spacing(text: str) -> str:
        """
        Dọn dẹp spacing dư thừa trong văn bản.

        Thực hiện các cleanup:
        - Loại bỏ multiple spaces (2+ spaces → 1 space)
        - Loại bỏ space trước dấu câu
        - Loại bỏ space sau mở ngoặc và trước đóng ngoặc
        - Loại bỏ space sau/before quotes

        Args:
            text: Văn bản cần dọn spacing

        Returns:
            Văn bản đã được cleanup spacing

        Example:
            >>> text = "Hello  ,  world  (  test  )  "
            >>> result = CleanupHelper.cleanup_spacing(text)
            >>> # Returns: "Hello, world (test)"
        """
        # Loại bỏ multiple spaces
        text = re.sub(r"  +", " ", text)

        # Loại bỏ space trước dấu câu
        text = re.sub(r" +([,\.。!?;:！？，])", r"\1", text)

        # Loại bỏ space sau mở ngoặc và trước đóng ngoặc
        text = re.sub(r"\(\s+", "(", text)
        text = re.sub(r"\s+\)", ")", text)
        text = re.sub(r'"\s+', '"', text)
        text = re.sub(r'\s+"', '"', text)

        return text

    @staticmethod
    def strip_ntid_markers(text: str) -> str:
        """
        Loại bỏ các marker [TX:chapter-order] khỏi văn bản.
        
        Regex match: [TX: followed by anything up to the next ]
        """
        if not text:
            return text
        # Pattern: [TX:chapter_id-order]
        pattern = r"\[TX:[^\]]+\]"
        return re.sub(pattern, "", text)
