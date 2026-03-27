# -*- coding: utf-8 -*-

"""
Format Normalizer - Thống nhất format giữa các chunks dịch

Module này phân tích format của các chunks đã dịch và thống nhất format
để tránh tình trạng mỗi chunk format khác nhau (ví dụ: có chunk dùng [H1]
cho tiêu đề chương, có chunk lại dùng cho đề mục nhỏ).
"""

import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")


class FormatNormalizer:
    """
    Lớp thống nhất format giữa các chunks dịch.

    Chức năng:
    1. Phân tích format của chunks đã dịch
    2. Xác định format pattern phổ biến nhất
    3. Normalize format của tất cả chunks theo pattern đó
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.format_rules = self._load_format_rules()

        # [v8.2] Unified Terminology Configuration
        self.preferred_chapter_term = self.config.get("output", {}).get("preferred_chapter_term")
        self.preferred_volume_term = self.config.get("output", {}).get("preferred_volume_term")

        # Define regex patterns locally (Synced with formatter.py)
        self.VIETNAMESE_NUMBER_MAP = {
            "không": 0,
            "một": 1,
            "nhất": 1,
            "hai": 2,
            "nhị": 2,
            "ba": 3,
            "tam": 3,
            "bốn": 4,
            "tư": 4,
            "tứ": 4,
            "năm": 5,
            "ngũ": 5,
            "sáu": 6,
            "lục": 6,
            "bảy": 7,
            "thất": 7,
            "tám": 8,
            "bát": 8,
            "chín": 9,
            "cửu": 9,
            "mười": 10,
            "thập": 10,
        }
        KEYWORDS_PATTERN = r"(?:Chương|Hồi|Quyển|Tập|Phần|Q|C)"
        NUMBERS_PATTERN = r"\d+|" + "|".join(self.VIETNAMESE_NUMBER_MAP.keys())
        self.UNIFIED_TITLE_PATTERN = re.compile(
            rf"^\s*(?:{KEYWORDS_PATTERN}\s+)?({KEYWORDS_PATTERN})[\s:.\-]*\s*(?:thứ\s+)?({NUMBERS_PATTERN})\s*[:.\-]*\s*(.*)$",
            re.IGNORECASE,
        )

    def _standardize_title_format(self, line: str) -> str:
        """
        Chuẩn hóa một dòng văn bản nếu nó là một tiêu đề (Logic synced with formatter.py)
        """

        def replacer(match) -> str:
            original_keyword = match.group(1)
            if not original_keyword:
                return match.group(0)

            original_keyword = original_keyword.title()
            number_str = match.group(2).lower() if match.group(2) else ""
            title_part = match.group(3).strip() if match.group(3) else ""

            # Unified Terminology
            keyword = original_keyword
            if self.preferred_chapter_term and original_keyword in ["Chương", "Hồi"]:
                keyword = self.preferred_chapter_term
            elif self.preferred_volume_term and original_keyword in ["Quyển", "Tập"]:
                keyword = self.preferred_volume_term

            digit = None
            try:
                digit = int(number_str)
            except ValueError:
                digit = self.VIETNAMESE_NUMBER_MAP.get(number_str)

            if digit is None:
                return match.group(0)

            clean_title = re.sub(r"^[:.\-\s]+", "", title_part).strip()
            if clean_title:
                clean_title = clean_title.title()
                return f"{keyword} {digit}: {clean_title}"
            return f"{keyword} {digit}"

        return self.UNIFIED_TITLE_PATTERN.sub(replacer, line)

    def _load_format_rules(self) -> Dict[str, Any]:
        """
        Load format rules từ config hoặc dùng default.

        Returns:
            Dict chứa format rules
        """
        default_rules = {
            "heading_patterns": {
                "chapter": [
                    # Chinese patterns
                    r"^第?\s*\d+\s*章[：:]?\s*",  # 第1章, 第一章, 1章
                    r"^第\s*\d+\s*回[：:]?\s*",  # 第1回 (Hồi)
                    r"^第\s*\d+\s*卷[：:]?\s*",  # 第1卷 (Quyển/Volume)
                    r"^第\s*\d+\s*部[：:]?\s*",  # 第1部 (Phần/Part)
                    r"^第\s*\d+\s*集[：:]?\s*",  # 第1集 (Tập)
                    # English patterns
                    r"^[Cc]hapter\s+\d+[：:]?\s*",  # Chapter 1
                    r"^[Pp]art\s+\d+[：:]?\s*",  # Part 1
                    r"^[Pp]art\s+[IVXLCDM]+[：:]?\s*",  # Part IV (Roman)
                    r"^[Vv]olume\s+\d+[：:]?\s*",  # Volume 1
                    r"^[Bb]ook\s+\d+[：:]?\s*",  # Book 1
                    r"^[Ee]pisode\s+\d+[：:]?\s*",  # Episode 1
                    # Vietnamese patterns (Enhanced v8.2 - Synced with formatter.py)
                    r"^(?:Chương|Hồi|Quyển|Tập)\s+(?:thứ\s+)?(\d+|[A-Za-zÀ-ỹ]+)\s*[:\-.]?\s*",
                    r"^Chương\s+(\d+|[A-Za-zÀ-ỹ]+)\s*[:\-.]?\s*",
                    r"^Hồi\s+(\d+|[A-Za-zÀ-ỹ]+)\s*[:\-.]?\s*",
                    r"^Tập\s+(\d+|[A-Za-zÀ-ỹ]+)\s*[:\-.]?\s*",
                    r"^Quyển\s+(\d+|[A-Za-zÀ-ỹ]+)\s*[:\-.]?\s*",
                    r"^Phần\s+(\d+|[A-Za-zÀ-ỹ]+)\s*[:\-.]?\s*",
                    r"^Phần\s+[IVXLCDM]+[：:]?\s*",
                ],
                "section": [
                    r"^第?\s*\d+[\.、]\s*\d+[：:]?\s*",  # 1.1, 1、1
                    r"^[Ss]ection\s+\d+[：:]?\s*",  # Section 1
                    r"^[Mm]ục\s+\d+[：:]?\s*",  # Mục 1
                    r"^[Tt]iết\s+\d+[：:]?\s*",  # Tiết 1
                ],
                "subsection": [
                    r"^第?\s*\d+[\.、]\s*\d+[\.、]\s*\d+[：:]?\s*",  # 1.1.1
                    r"^[Ss]ubsection\s+\d+[：:]?\s*",  # Subsection 1
                    r"^[Tt]iểu\s+[Mm]ục\s+\d+[：:]?\s*",  # Tiểu mục 1
                ],
            },
            "heading_levels": {
                "chapter": "H1",
                "section": "H2",
                "subsection": "H3",
            },
            "min_heading_length": 3,  # Độ dài tối thiểu của heading
            "max_heading_length": 100,  # Độ dài tối đa của heading
        }

        # Merge với config nếu có
        config_rules = self.config.get("format_normalizer", {})
        default_rules.update(config_rules)

        return default_rules

    def analyze_format_patterns(self, chunks: List[str]) -> Dict[str, Any]:
        """
        Phân tích format patterns từ các chunks đã dịch.

        Args:
            chunks: List các chunks đã dịch

        Returns:
            Dict chứa format patterns:
            {
                'heading_formats': {
                    'H1': [list of patterns],
                    'H2': [list of patterns],
                    'H3': [list of patterns],
                },
                'most_common_format': {
                    'H1': 'pattern',
                    'H2': 'pattern',
                    'H3': 'pattern',
                },
                'format_consistency': float,  # 0-1, 1 = hoàn toàn thống nhất
            }
        """
        heading_formats = {
            "H1": [],
            "H2": [],
            "H3": [],
        }

        # Phân tích từng chunk
        for chunk in chunks:
            if not chunk or not chunk.strip():
                continue

            # Tìm tất cả headings trong chunk
            headings = self._extract_headings(chunk)

            for heading_level, heading_text in headings:
                if heading_level in heading_formats:
                    heading_formats[heading_level].append(heading_text)

        # Xác định format phổ biến nhất
        most_common_format = {}
        format_consistency = {}

        for level in ["H1", "H2", "H3"]:
            if heading_formats[level]:
                # Đếm frequency của mỗi pattern
                pattern_counter = Counter(heading_formats[level])
                most_common = pattern_counter.most_common(1)[0]
                most_common_format[level] = most_common[0]

                # Tính consistency (tỷ lệ chunks dùng format phổ biến nhất)
                total = len(heading_formats[level])
                consistency = most_common[1] / total if total > 0 else 0.0
                format_consistency[level] = consistency
            else:
                most_common_format[level] = None
                format_consistency[level] = 1.0  # Không có heading = consistent

        # Tính overall consistency
        overall_consistency = sum(format_consistency.values()) / len(format_consistency)

        return {
            "heading_formats": heading_formats,
            "most_common_format": most_common_format,
            "format_consistency": {
                "H1": format_consistency.get("H1", 1.0),
                "H2": format_consistency.get("H2", 1.0),
                "H3": format_consistency.get("H3", 1.0),
                "overall": overall_consistency,
            },
        }

    def _extract_headings(self, text: str) -> List[Tuple[str, str]]:
        """
        Trích xuất headings từ text.

        Args:
            text: Text cần phân tích

        Returns:
            List of (level, heading_text) tuples
        """
        headings = []

        # Pattern cho [H1]...[/H1], [H2]...[/H2], [H3]...[/H3]
        patterns = {
            "H1": re.compile(r"\[H1\](.*?)\[/H1\]", re.DOTALL),
            "H2": re.compile(r"\[H2\](.*?)\[/H2\]", re.DOTALL),
            "H3": re.compile(r"\[H3\](.*?)\[/H3\]", re.DOTALL),
        }

        for level, pattern in patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                heading_text = match.strip()
                if heading_text:
                    headings.append((level, heading_text))

        return headings

    def normalize_chunk_format(
        self,
        chunk: str,
        format_patterns: Dict[str, Any],
        reference_chunk: Optional[str] = None,
    ) -> str:
        """
        Normalize format của một chunk theo format patterns.

        Args:
            chunk: Chunk cần normalize
            format_patterns: Format patterns từ analyze_format_patterns()
            reference_chunk: Chunk tham chiếu (optional)

        Returns:
            Chunk đã được normalize
        """
        if not chunk or not chunk.strip():
            return chunk

        normalized = chunk

        # Normalize headings
        normalized = self._normalize_headings(normalized, format_patterns.get("most_common_format", {}))

        return normalized

    def _normalize_headings(self, text: str, most_common_format: Dict[str, Optional[str]]) -> str:
        """
        Normalize headings trong text.

        Logic:
        1. Xác định loại heading (chapter/section/subsection) dựa trên pattern
        2. Áp dụng format level phù hợp (H1/H2/H3)
        3. Đảm bảo format nhất quán (Nội dung bên trong heading)
        """
        normalized = text

        # Tìm tất cả headings hiện có
        heading_pattern = re.compile(r"\[(H[123])\](.*?)\[/H[123]\]", re.DOTALL)

        def replace_heading(match):
            current_level = match.group(1)
            heading_text = match.group(2).strip()

            # Xác định loại heading dựa trên nội dung
            heading_type = self._classify_heading(heading_text)

            # Xác định level phù hợp
            target_level = self.format_rules["heading_levels"].get(heading_type, current_level)

            # [Task Fix] Normalize content inside heading
            final_text = heading_text
            if heading_type in ["chapter", "section"]:
                # Apply standardization (e.g., "Chương 1" -> "Hồi 1" if preferred)
                normalized_text = self._standardize_title_format(heading_text)
                if normalized_text != heading_text:
                    final_text = normalized_text

            # Nếu có format phổ biến nhất, dùng format đó (chỉ áp dụng level tag)
            if heading_type in most_common_format:
                return f"[{target_level}]{final_text}[/{target_level}]"

            # Nếu không có format phổ biến, dùng level mặc định
            if current_level != target_level:
                return f"[{target_level}]{final_text}[/{target_level}]"

            # Mặc định: cập nhật nội dung (nếu có thay đổi) và giữ nguyên level
            return f"[{current_level}]{final_text}[/{current_level}]"

        normalized = heading_pattern.sub(replace_heading, normalized)

        return normalized

    def _classify_heading(self, heading_text: str) -> str:
        """
        Phân loại heading dựa trên nội dung.

        Returns:
            'chapter', 'section', 'subsection', hoặc 'unknown'
        """
        heading_text = heading_text.strip()

        # Check patterns
        for heading_type, patterns in self.format_rules["heading_patterns"].items():
            for pattern in patterns:
                if re.match(pattern, heading_text, re.IGNORECASE):
                    return heading_type

        # Heuristic: Nếu heading ngắn và không có dấu chấm → có thể là chapter
        if len(heading_text) <= 50 and "." not in heading_text:
            # Check common chapter keywords
            chapter_keywords = ["章", "chapter", "chương", "回"]
            if any(keyword in heading_text.lower() for keyword in chapter_keywords):
                return "chapter"

        # Heuristic: Nếu có số thứ tự dạng 1.1, 1.2 → section
        if re.match(r"^\d+\.\d+", heading_text):
            return "section"

        # Heuristic: Nếu có số thứ tự dạng 1.1.1 → subsection
        if re.match(r"^\d+\.\d+\.\d+", heading_text):
            return "subsection"

        # Fallback: Short headings without numbering → subsection (H3)
        # Prevents them from being treated as H1 and polluting TOC
        if len(heading_text) < 80:
            return "subsection"

        return "unknown"

    def normalize_all_chunks(self, chunks: List[str], analyze_first_n: int = 10) -> Tuple[List[str], Dict[str, Any]]:
        """
        Normalize format của tất cả chunks.

        Args:
            chunks: List các chunks cần normalize
            analyze_first_n: Số chunks đầu tiên để phân tích format (default: 10)

        Returns:
            Tuple (normalized_chunks, analysis_report)
        """
        if not chunks:
            return [], {}

        # Phân tích format từ các chunks đầu tiên
        chunks_to_analyze = chunks[:analyze_first_n]
        format_patterns = self.analyze_format_patterns(chunks_to_analyze)

        logger.info(
            f"📊 Format analysis: "
            f"H1 consistency: {format_patterns['format_consistency']['H1']:.2%}, "
            f"H2 consistency: {format_patterns['format_consistency']['H2']:.2%}, "
            f"H3 consistency: {format_patterns['format_consistency']['H3']:.2%}, "
            f"Overall: {format_patterns['format_consistency']['overall']:.2%}"
        )

        # Normalize tất cả chunks
        normalized_chunks = []
        for i, chunk in enumerate(chunks):
            normalized = self.normalize_chunk_format(
                chunk, format_patterns, reference_chunk=chunks[0] if chunks else None
            )
            normalized_chunks.append(normalized)

        # Tạo report
        analysis_report = {
            "total_chunks": len(chunks),
            "analyzed_chunks": len(chunks_to_analyze),
            "format_patterns": format_patterns,
            "normalized_count": sum(1 for i, (orig, norm) in enumerate(zip(chunks, normalized_chunks)) if orig != norm),
        }

        logger.info(f"✅ Normalized {analysis_report['normalized_count']}/{len(chunks)} chunks")

        return normalized_chunks, analysis_report
