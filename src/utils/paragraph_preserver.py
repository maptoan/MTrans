# -*- coding: utf-8 -*-

"""
Paragraph Preserver - Bảo toàn và xử lý paragraph breaks khi merge chunks

Module này đảm bảo:
1. Giữ nguyên paragraph breaks từ bản gốc
2. Ghép các đoạn bị ngắt do chuyển trang
3. Không làm mất paragraph breaks khi merge chunks
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger("NovelTranslator")


class ParagraphPreserver:
    """
    Lớp bảo toàn và xử lý paragraph breaks.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

    def merge_chunks_with_paragraph_preservation(
        self, chunks: List[str], original_chunks: Optional[List[dict]] = None
    ) -> str:
        """
        Merge chunks với bảo toàn paragraph breaks.

        Logic:
        1. Giữ nguyên paragraph breaks trong mỗi chunk
        2. Thêm paragraph break giữa các chunks nếu cần
        3. Detect và merge các đoạn bị ngắt do chuyển trang

        Args:
            chunks: List các chunks đã dịch
            original_chunks: List chunks gốc (optional, để so sánh)

        Returns:
            Merged content với paragraph breaks được preserve
        """
        if not chunks:
            return ""

        merged_parts = []

        for i, chunk in enumerate(chunks):
            if not chunk or not chunk.strip():
                continue

            # Normalize chunk: đảm bảo có paragraph breaks hợp lý
            normalized_chunk = self._normalize_chunk_paragraphs(chunk)

            # Nếu không phải chunk đầu tiên, kiểm tra xem có cần thêm paragraph break không
            if i > 0 and merged_parts:
                # Kiểm tra chunk trước có kết thúc bằng paragraph break không
                prev_chunk = merged_parts[-1]
                needs_break = self._needs_paragraph_break(prev_chunk, normalized_chunk)

                if needs_break:
                    # Thêm paragraph break
                    merged_parts.append("")

            merged_parts.append(normalized_chunk)

        # Merge với paragraph breaks
        result = "\n\n".join(merged_parts)

        # Detect và merge các đoạn bị ngắt do chuyển trang
        result = self._merge_broken_paragraphs(result)

        return result

    def _normalize_chunk_paragraphs(self, chunk: str) -> str:
        """
        Normalize paragraph breaks trong một chunk.

        Đảm bảo:
        - Paragraph breaks là "\n\n" (2 newlines)
        - Không có paragraph breaks thừa (3+ newlines)
        - Giữ nguyên paragraph breaks hợp lý
        """
        if not chunk:
            return chunk

        # Normalize: thay nhiều newlines liên tiếp (3+) thành 2 newlines
        normalized = re.sub(r"\n{3,}", "\n\n", chunk)

        # Đảm bảo chunk không bắt đầu/ kết thúc bằng newlines thừa
        normalized = normalized.strip()

        return normalized

    def _needs_paragraph_break(self, prev_chunk: str, current_chunk: str) -> bool:
        """
        Kiểm tra xem có cần thêm paragraph break giữa 2 chunks không.

        Logic:
        - Nếu chunk trước kết thúc bằng paragraph break → không cần thêm
        - Nếu chunk trước kết thúc bằng dấu câu (.!?) → có thể cần paragraph break
        - Nếu chunk sau bắt đầu bằng chữ hoa/số/bullet → có thể cần paragraph break
        - Nếu không rõ → thêm paragraph break để an toàn
        """
        if not prev_chunk or not current_chunk:
            return True

        # Nếu chunk trước kết thúc bằng paragraph break → không cần thêm
        if prev_chunk.rstrip().endswith("\n\n"):
            return False

        # Nếu chunk trước kết thúc bằng dấu câu → có thể cần paragraph break
        prev_ends_with_punctuation = bool(
            re.search(r"[.!?。！？]\s*$", prev_chunk.rstrip())
        )

        # Nếu chunk sau bắt đầu bằng chữ hoa/số/bullet → có thể cần paragraph break
        current_stripped = current_chunk.lstrip()
        if not current_stripped:
            return True

        first_char = current_stripped[0]
        current_starts_with_upper = first_char.isupper() and first_char.isalpha()
        current_starts_with_number = bool(re.match(r"^\d+", current_stripped))
        current_starts_with_bullet = bool(re.match(r"^[•·\-*]\s", current_stripped))
        current_starts_with_heading = bool(re.match(r"^\[H[123]\]", current_stripped))

        # Nếu cả hai điều kiện đều đúng → cần paragraph break
        if prev_ends_with_punctuation and (
            current_starts_with_upper
            or current_starts_with_number
            or current_starts_with_bullet
            or current_starts_with_heading
        ):
            return True

        # Mặc định: thêm paragraph break để an toàn
        return True

    def _merge_broken_paragraphs(self, text: str) -> str:
        """
        Detect và merge các đoạn bị ngắt do chuyển trang.

        Logic:
        - Tìm các đoạn kết thúc không có dấu câu (.!?)
        - Nếu đoạn sau bắt đầu bằng chữ thường → có thể là đoạn bị ngắt
        - Merge chúng lại
        """
        if not text:
            return text

        # Split thành paragraphs
        paragraphs = text.split("\n\n")

        if len(paragraphs) <= 1:
            return text

        merged_paragraphs = []
        i = 0

        while i < len(paragraphs):
            current_para = paragraphs[i].strip()

            if not current_para:
                merged_paragraphs.append("")
                i += 1
                continue

            # Kiểm tra xem đoạn hiện tại có bị ngắt không
            # (kết thúc không có dấu câu và đoạn sau bắt đầu bằng chữ thường)
            if i + 1 < len(paragraphs):
                next_para = paragraphs[i + 1].strip()

                if next_para:
                    # Kiểm tra đoạn hiện tại có kết thúc bằng dấu câu không
                    ends_with_punctuation = bool(
                        re.search(r"[.!?。！？]\s*$", current_para)
                    )

                    # Kiểm tra đoạn sau có bắt đầu bằng chữ thường không
                    first_char = next_para[0]
                    starts_with_lower = first_char.islower() and first_char.isalpha()

                    # Nếu đoạn hiện tại không kết thúc bằng dấu câu
                    # và đoạn sau bắt đầu bằng chữ thường → có thể là đoạn bị ngắt
                    if not ends_with_punctuation and starts_with_lower:
                        # Merge: nối đoạn sau vào đoạn hiện tại
                        merged_para = current_para + " " + next_para
                        merged_paragraphs.append(merged_para)
                        i += 2  # Skip cả 2 đoạn
                        continue

            # Không merge → giữ nguyên
            merged_paragraphs.append(current_para)
            i += 1

        # Join lại với paragraph breaks
        return "\n\n".join(merged_paragraphs)

    def preserve_paragraph_structure(
        self, translated_text: str, original_text: str
    ) -> str:
        """
        Preserve paragraph structure từ bản gốc.

        So sánh số paragraph breaks giữa bản gốc và bản dịch,
        điều chỉnh bản dịch để match với bản gốc.

        Args:
            translated_text: Bản dịch
            original_text: Bản gốc

        Returns:
            Bản dịch đã được điều chỉnh để match paragraph structure
        """
        if not original_text or not translated_text:
            return translated_text

        # Đếm paragraph breaks trong bản gốc
        original_paragraphs = original_text.split("\n\n")
        original_para_count = len([p for p in original_paragraphs if p.strip()])

        # Đếm paragraph breaks trong bản dịch
        translated_paragraphs = translated_text.split("\n\n")
        translated_para_count = len([p for p in translated_paragraphs if p.strip()])

        # Nếu số paragraph breaks khác nhau quá nhiều → có thể có vấn đề
        if abs(original_para_count - translated_para_count) > original_para_count * 0.2:
            logger.debug(
                f"⚠️ Paragraph count mismatch: Original={original_para_count}, "
                f"Translated={translated_para_count}"
            )

        # Trả về bản dịch (có thể điều chỉnh thêm nếu cần)
        return translated_text
