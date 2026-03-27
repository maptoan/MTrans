# -*- coding: utf-8 -*-

"""
Context Break Detector
======================
Phát hiện break trong context (chuyển chương/cảnh/chủ đề) để filter context không liên quan.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NovelTranslator")


class ContextBreakDetector:
    """
    Phát hiện break trong context (chuyển chương/cảnh/chủ đề).

    Attributes:
        patterns: List các regex patterns để detect breaks
        compiled_patterns: Compiled regex patterns (cached)
        enabled: Flag để enable/disable break detection
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo ContextBreakDetector.

        Args:
            config: Configuration dict với break_detection settings
        """
        self.config = config or {}
        break_config = self.config.get("break_detection", {})
        self.enabled = break_config.get("enabled", True)

        # Default patterns
        default_patterns = self._get_default_patterns()

        # Custom patterns từ config (nếu có)
        custom_patterns = break_config.get("patterns", [])

        # Combine patterns
        self.patterns = custom_patterns if custom_patterns else default_patterns

        # Compile patterns (cache để tối ưu performance)
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.patterns
        ]

        logger.debug(
            f"ContextBreakDetector initialized: enabled={self.enabled}, patterns={len(self.patterns)}"
        )

    def _get_default_patterns(self) -> List[str]:
        """Lấy default patterns cho break detection."""
        return [
            # Chapter breaks
            r"^(Chương|Chapter|第)\s*\d+",  # "Chương 1", "Chapter 1", "第1章"
            r"^第\d+章",  # "第1章"
            r"^CHAPTER\s+\d+",  # "CHAPTER 1"
            r"^CHƯƠNG\s+\d+",  # "CHƯƠNG 1"
            # Scene breaks (sẽ được check riêng)
            # Topic change markers (sẽ được check riêng)
        ]

    def detect(self, prev_chunk_text: str, current_chunk_text: str) -> bool:
        """
        Phát hiện break trong context.

        Args:
            prev_chunk_text: Text của chunk trước
            current_chunk_text: Text của chunk hiện tại

        Returns:
            True nếu phát hiện break, False nếu không
        """
        if not self.enabled:
            return False

        if not prev_chunk_text or not current_chunk_text:
            return False

        try:
            # Check chapter breaks ở đầu current chunk
            current_start = current_chunk_text.strip()[:200]  # First 200 chars

            for pattern in self.compiled_patterns:
                if pattern.search(current_start):
                    logger.debug(
                        f"[ContextBreak] Phát hiện chapter break: {pattern.pattern}"
                    )
                    return True

            # Check scene break (nhiều empty lines hoặc separators)
            if self._detect_scene_break(current_chunk_text):
                logger.debug("[ContextBreak] Phát hiện scene break")
                return True

            # Check topic change (keyword-based heuristic)
            if self._detect_topic_change(prev_chunk_text, current_chunk_text):
                logger.debug("[ContextBreak] Phát hiện topic change")
                return True

            return False

        except Exception as e:
            # Fallback: không detect break nếu có lỗi
            logger.warning(
                f"[ContextBreak] Lỗi khi detect break: {e}, fallback về no-break"
            )
            return False

    def _detect_scene_break(self, current_chunk_text: str) -> bool:
        """
        Phát hiện scene break (nhiều empty lines, separators).

        Args:
            current_chunk_text: Text của chunk hiện tại

        Returns:
            True nếu phát hiện scene break
        """
        # Check multiple empty lines (3+)
        if re.search(r"\n\s*\n\s*\n", current_chunk_text[:500]):
            return True

        # Check separators
        separator_patterns = [
            r"^[\s]*---[\s]*$",
            r"^[\s]*\*\*\*[\s]*$",
            r"^[\s]*===+[\s]*$",
        ]

        first_lines = current_chunk_text.split("\n")[:5]
        for line in first_lines:
            for pattern in separator_patterns:
                if re.match(pattern, line):
                    return True

        return False

    def _detect_topic_change(
        self, prev_chunk_text: str, current_chunk_text: str
    ) -> bool:
        """
        Phát hiện topic change (time/location markers).

        Args:
            prev_chunk_text: Text của chunk trước
            current_chunk_text: Text của chunk hiện tại

        Returns:
            True nếu phát hiện topic change
        """
        current_start = current_chunk_text.strip()[:200]
        prev_end = (
            prev_chunk_text[-200:] if len(prev_chunk_text) > 200 else prev_chunk_text
        )

        # Topic change markers
        topic_change_markers = [
            r"^(Ngày|Ngày hôm|Hôm|Sáng|Chiều|Tối|Đêm)",
            r"^(Tại|Ở|Trong|Ngoài|Trước|Sau)",
            r"^(Một|Hai|Ba|Bốn|Năm)\s+(ngày|tuần|tháng|năm)\s+(sau|trước)",
        ]

        for pattern_str in topic_change_markers:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(current_start):
                # Chỉ coi là break nếu prev chunk không có cùng marker
                if not pattern.search(prev_end):
                    return True

        return False
