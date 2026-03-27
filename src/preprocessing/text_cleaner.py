# -*- coding: utf-8 -*-
from __future__ import annotations

"""
(PHIÊN BẢN NÂNG CẤP) Module làm sạch và chuẩn hóa văn bản với nhiều tính năng nâng cao.
"""

import logging
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")

# Patterns cho các loại noise phổ biến
PAGE_NUMBER_PATTERN = re.compile(
    r"^\s*(?:第)?\s*\d+\s*(?:页|頁|Page|page|P\.?)?\s*$", re.MULTILINE
)
HEADER_FOOTER_PATTERN = re.compile(
    r"^(?:Chapter|第.*章|.*目录|Table of Contents).*$", re.MULTILINE | re.IGNORECASE
)
URL_PATTERN = re.compile(r"https?://[^\s]+")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

# Normalize Whitespace Patterns
MULTIPLE_SPACES_PATTERN = re.compile(r"[ \t]+")
MULTIPLE_NEWLINES_PATTERN = re.compile(r"\n{3,}")
SPACE_BEFORE_NEWLINE_PATTERN = re.compile(r" +\n(?!\n)")

# Punctuation Patterns
CJK_PUNCTUATION_SPACING_PATTERN = re.compile(r"\s+([，。！？；：、）】」』》])")
CJK_OPEN_QUOTE_SPACING_PATTERN = re.compile(r"([（【「『《])\s+")
LATIN_PUNCTUATION_SPACING_PATTERN = re.compile(r"([.!?,;:])([A-Za-z])")

# Chapter Detection Patterns (for preservation)
CHAPTER_MARKER_PATTERNS = [
    r"^(第\s*[零一二三四五六七八九十百千0-9]+\s*[章回节卷篇部])[：:\s]*(.*?)$",
    r"^(Chapter\s+\d+)[:\s]*(.*?)$",
    r"^(Chương\s+\d+)[:\s]*(.*?)$",
]
STRONG_PUNCTUATION_PATTERN = re.compile(r'[.!?,:;。，！？”“"\-]')
HAS_DIGIT_PATTERN = re.compile(r"\d+")
STARTS_WITH_DAI_PATTERN = re.compile(r"^第")


class AdvancedTextCleaner:
    """
    Text cleaner nâng cao với nhiều tính năng xử lý văn bản.
    """

    # Special Unicode categories to remove
    CONTROL_CHARS = [
        "\u200b",  # Zero-width space
        "\u200c",  # Zero-width non-joiner
        "\u200d",  # Zero-width joiner
        "\ufeff",  # Zero-width no-break space (BOM)
        "\u2060",  # Word joiner
        "\u00ad",  # Soft hyphen
    ]

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.cleaning_config = (self.config.get("preprocessing") or {}).get(
            "cleaning"
        ) or {}
        # Phase 1.3: Advanced whitespace normalization config
        translation_config = self.config.get("translation", {})
        self.advanced_whitespace = translation_config.get(
            "advanced_whitespace_normalization", True
        )

        self.stats = {
            "original_length": 0,
            "cleaned_length": 0,
            "removed_chars": 0,
            "normalized_spaces": 0,
            "removed_pages": 0,
            "removed_urls": 0,
        }

    def remove_bom(self, text: str) -> str:
        """Loại bỏ BOM (Byte Order Mark)."""
        if text.startswith("\ufeff"):
            text = text[1:]
            logger.debug("Đã loại bỏ BOM")
        return text

    def remove_zero_width_chars(self, text: str) -> str:
        """Loại bỏ các ký tự zero-width và invisible."""
        original_len = len(text)
        for char in self.CONTROL_CHARS:
            text = text.replace(char, "")

        removed = original_len - len(text)
        if removed > 0:
            self.stats["removed_chars"] += removed
            logger.debug(f"Đã loại bỏ {removed} ký tự invisible")

        return text

    def normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode về dạng NFC (Canonical Decomposition, followed by Canonical Composition).
        Đảm bảo các ký tự được biểu diễn nhất quán.
        """
        # NFC là form phổ biến nhất, tốt cho CJK
        return unicodedata.normalize("NFC", text)

    def remove_page_numbers(self, text: str) -> str:
        """Loại bỏ số trang."""
        lines = text.split("\n")
        cleaned_lines = []
        removed_count = 0

        for line in lines:
            # Kiểm tra nếu line chỉ chứa số trang
            if PAGE_NUMBER_PATTERN.match(line.strip()):
                removed_count += 1
                continue
            cleaned_lines.append(line)

        if removed_count > 0:
            self.stats["removed_pages"] += removed_count
            logger.debug(f"Đã loại bỏ {removed_count} dòng số trang")

        return "\n".join(cleaned_lines)

    def remove_urls_and_emails(self, text: str) -> str:
        """Loại bỏ URLs và emails (thường là noise trong ebooks)."""
        # Remove URLs
        url_count = len(URL_PATTERN.findall(text))
        text = URL_PATTERN.sub("", text)

        # Remove emails
        email_count = len(EMAIL_PATTERN.findall(text))
        text = EMAIL_PATTERN.sub("", text)

        if url_count + email_count > 0:
            self.stats["removed_urls"] += url_count + email_count
            logger.debug(f"Đã loại bỏ {url_count} URLs và {email_count} emails")

        return text

    def normalize_whitespace(self, text: str) -> str:
        """
        Chuẩn hóa khoảng trắng:
        - Thay thế nhiều spaces/tabs thành 1 space
        - Loại bỏ trailing spaces
        - Giảm nhiều newlines thành tối đa 2
        """
        # Replace multiple spaces/tabs with single space
        text = MULTIPLE_SPACES_PATTERN.sub(" ", text)

        # Strip spaces from each line
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(lines)

        # Reduce multiple newlines to max 2
        original_newlines = text.count("\n\n\n")
        text = MULTIPLE_NEWLINES_PATTERN.sub("\n\n", text)

        if original_newlines > 0:
            self.stats["normalized_spaces"] += original_newlines

        return text.strip()

    def normalize_whitespace_advanced(self, text: str) -> str:
        """
        Phase 1.3: Advanced whitespace normalization để tiết kiệm tokens.

        Features:
        - Remove redundant line breaks (3+ consecutive → 2)
        - Remove spaces before line breaks
        - Preserve paragraph breaks (double newlines)

        Args:
            text: Text cần normalize

        Returns:
            Normalized text
        """
        # Remove redundant line breaks (3+ consecutive → 2)
        # Giữ paragraph breaks (double newlines) nhưng loại bỏ 3+ newlines
        text = MULTIPLE_NEWLINES_PATTERN.sub("\n\n", text)

        # Remove spaces before line breaks (trừ khi là paragraph break)
        # Pattern: space(s) + single newline → single newline
        # Giữ: space(s) + double newline → double newline (paragraph break)
        text = SPACE_BEFORE_NEWLINE_PATTERN.sub("\n", text)

        # Normalize multiple spaces/tabs (giữ lại từ normalize_whitespace)
        text = MULTIPLE_SPACES_PATTERN.sub(" ", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def fix_punctuation_spacing(self, text: str) -> str:
        """
        Sửa spacing xung quanh dấu câu.
        Đặc biệt quan trọng cho văn bản CJK.
        """
        # Loại bỏ spaces trước dấu câu CJK
        text = CJK_PUNCTUATION_SPACING_PATTERN.sub(r"\1", text)

        # Loại bỏ spaces sau dấu mở ngoặc CJK
        text = CJK_OPEN_QUOTE_SPACING_PATTERN.sub(r"\1", text)

        # Đảm bảo có space sau dấu câu Latin (nếu theo sau là chữ)
        text = LATIN_PUNCTUATION_SPACING_PATTERN.sub(r"\1 \2", text)

        return text

    def remove_duplicate_lines(self, text: str) -> str:
        """Loại bỏ các dòng trùng lặp liên tiếp (thường là lỗi OCR/parsing)."""
        lines = text.split("\n")
        cleaned_lines = []
        prev_line = None
        removed_count = 0

        for line in lines:
            stripped = line.strip()
            if stripped and stripped == prev_line:
                removed_count += 1
                continue
            cleaned_lines.append(line)
            prev_line = stripped

        if removed_count > 0:
            logger.debug(f"Đã loại bỏ {removed_count} dòng trùng lặp")

        return "\n".join(cleaned_lines)

    def preserve_chapter_markers(self, text: str) -> Tuple[str, List[Dict]]:
        """
        Detect và preserve chapter markers để chunker có thể tôn trọng boundaries.
        Returns: (cleaned_text, chapter_markers)
        """
        # Cho phép bật/tắt qua config
        if not self.cleaning_config.get("enable_chapter_marker_detection", True):
            return text, []

        max_markers = int(self.cleaning_config.get("max_chapter_markers", 2000) or 2000)
        chapter_markers = []

        lines = text.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Ràng buộc bổ sung để tránh false positive ồ ạt
            if not stripped or len(stripped) > 120:
                continue
            # Tối đa 2 dấu câu mạnh trong dòng tiêu đề
            if len(STRONG_PUNCTUATION_PATTERN.findall(stripped)) > 2:
                continue

            for pattern in CHAPTER_MARKER_PATTERNS:
                match = re.match(pattern, stripped, re.IGNORECASE)
                if match:
                    # Yêu cầu có số rõ ràng (Ả Rập hoặc đã match mẫu 第...章/...)
                    if not HAS_DIGIT_PATTERN.search(
                        stripped
                    ) and not STARTS_WITH_DAI_PATTERN.search(stripped):
                        break
                    chapter_markers.append(
                        {
                            "line_number": i,
                            "title": stripped,
                            "position": len("\n".join(lines[:i])),
                        }
                    )
                    break
            if len(chapter_markers) >= max_markers:
                logger.warning(
                    f"Số chapter markers đạt trần {max_markers}, dừng phát hiện để đảm bảo hiệu năng."
                )
                break

        if chapter_markers:
            logger.info(f"Phát hiện {len(chapter_markers)} chapter markers")

        return text, chapter_markers

    def clean(self, text: str) -> Dict:
        """
        Main cleaning pipeline.
        Returns dict với cleaned text và metadata.
        """
        if not text or not isinstance(text, str):
            raise ValueError("Input text phải là string không rỗng")

        self.stats["original_length"] = len(text)
        logger.info("Bắt đầu làm sạch văn bản...")

        # Pipeline steps
        text = self.remove_bom(text)
        text = self.remove_zero_width_chars(text)
        text = self.normalize_unicode(text)
        text = self.remove_urls_and_emails(text)
        text = self.remove_page_numbers(text)

        # Phase 1.3: Advanced whitespace normalization nếu enabled
        if self.advanced_whitespace:
            text = self.normalize_whitespace_advanced(text)
        else:
            text = self.normalize_whitespace(text)

        text = self.fix_punctuation_spacing(text)
        text = self.remove_duplicate_lines(text)

        # Preserve chapter markers
        text, chapter_markers = self.preserve_chapter_markers(text)

        self.stats["cleaned_length"] = len(text)

        # Log summary
        reduction = self.stats["original_length"] - self.stats["cleaned_length"]
        reduction_pct = (
            (reduction / self.stats["original_length"] * 100)
            if self.stats["original_length"] > 0
            else 0
        )

        logger.info("Hoàn thành làm sạch văn bản:")
        logger.info(f"  - Độ dài gốc: {self.stats['original_length']:,} ký tự")
        logger.info(f"  - Độ dài sau: {self.stats['cleaned_length']:,} ký tự")
        logger.info(f"  - Đã giảm: {reduction:,} ký tự ({reduction_pct:.1f}%)")

        return {
            "text": text,
            "chapter_markers": chapter_markers,
            "stats": self.stats.copy(),
        }


# Backward compatible function
def clean_text(text: str, config: Optional[Dict] = None) -> str:
    """
    Backward compatible wrapper cho code cũ.

    Args:
        text: Text cần clean
        config: Optional config dict (để enable advanced whitespace normalization)

    Returns:
        Cleaned text
    """
    cleaner = AdvancedTextCleaner(config)
    result = cleaner.clean(text)
    return result["text"]
