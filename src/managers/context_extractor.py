# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Module trích xuất ngữ cảnh từ chunk text để tối ưu hóa việc sử dụng character relations.
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger("NovelTranslator")

# Patterns để detect context
CONTEXT_PATTERNS = {
    "chapter": r"(?:chương|chapter|第.*章|第.*回)",
    "location": r"(?:tại|ở|trong|ngoài|trên|dưới|bên|giữa)",
    "time": r"(?:lúc|khi|sau|trước|đang|vừa|mới)",
    "emotion": r"(?:vui|buồn|tức|lo|sợ|ngạc nhiên|thích|ghét)",
    "formality": r"(?:trang trọng|thân mật|thoải mái|nghiêm túc)",
    "relationship": r"(?:sư phụ|đệ tử|bạn|anh|em|cha|mẹ|vợ|chồng)",
}

# Environment keywords
ENVIRONMENT_KEYWORDS = {
    "formal": ["đại điện", "triều đình", "họp", "nghi lễ", "cung đình"],
    "semi-formal": ["văn phòng", "họp mặt", "gặp gỡ", "thương lượng"],
    "informal": ["nhà riêng", "riêng tư", "bạn bè", "gia đình", "thân mật"],
    "combat": ["chiến đấu", "tranh đấu", "đấu võ", "chiến trường"],
    "public": ["nơi công cộng", "chợ", "đường phố", "quảng trường"],
}

# Context keywords
CONTEXT_KEYWORDS = {
    "romantic": [
        "yêu",
        "thương",
        "hôn",
        "ôm",
        "tay trong tay",
        "thân mật",
        "riêng tư",
        "tương lai",
        "cặp đôi",
    ],
    "business": ["làm ăn", "hợp tác", "thương lượng", "ký kết"],
    "family": ["gia đình", "cha mẹ", "anh em", "con cái"],
    "master_disciple": ["sư phụ", "đệ tử", "dạy", "học"],
    "conflict": ["tranh cãi", "cãi nhau", "tức giận", "thù hận"],
    "celebration": ["mừng", "chúc mừng", "tiệc", "lễ hội"],
}

# Confidence weights
CONFIDENCE_WEIGHTS = {
    "context": 0.4,
    "environment": 0.3,
    "chapter": 0.2,
    "keywords": 0.1,
}


class ContextExtractor:
    """
    Trích xuất ngữ cảnh từ chunk text để tối ưu hóa character relations.
    """

    def __init__(self) -> None:
        pass

    def extract_context_from_chunk(
        self, chunk_text: str, chunk_id: str = ""
    ) -> Dict[str, Any]:
        """
        Trích xuất ngữ cảnh từ chunk text.

        Args:
            chunk_text: Nội dung chunk
            chunk_id: ID của chunk (có thể chứa thông tin chapter)

        Returns:
            Dict chứa context và environment
        """
        context_info = {
            "context": "",
            "environment": "",
            "chapter": "",
            "detected_keywords": [],
            "confidence": 0.0,
        }

        # Extract chapter info từ chunk_id hoặc text
        chapter = self._extract_chapter_info(chunk_text, chunk_id)
        if chapter:
            context_info["chapter"] = chapter

        # Extract environment
        environment = self._extract_environment(chunk_text)
        if environment:
            context_info["environment"] = environment

        # Extract context
        context = self._extract_context(chunk_text)
        if context:
            context_info["context"] = context

        # Extract keywords
        keywords = self._extract_keywords(chunk_text)
        if keywords:
            context_info["detected_keywords"] = keywords

        # Calculate confidence
        context_info["confidence"] = self._calculate_confidence(context_info)

        return context_info

    def _extract_chapter_info(self, text: str, chunk_id: str) -> str:
        """Trích xuất thông tin chapter."""
        # Từ chunk_id
        if "chapter" in chunk_id.lower() or "chương" in chunk_id.lower():
            match = re.search(r"(?:chapter|chương)\s*(\d+)", chunk_id, re.IGNORECASE)
            if match:
                return f"Chapter {match.group(1)}"

        # Từ text content
        chapter_patterns = [r"(?:chương|chapter)\s*(\d+)", r"第(\d+)章", r"第(\d+)回"]

        for pattern in chapter_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"Chapter {match.group(1)}"

        return ""

    def _extract_environment(self, text: str) -> str:
        """Trích xuất environment từ text."""
        text_lower = text.lower()

        # Tìm environment keywords
        for env_type, keywords in ENVIRONMENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return env_type

        # Fallback: dựa vào context patterns
        if re.search(CONTEXT_PATTERNS["location"], text_lower):
            return "semi-formal"

        return "informal"  # Default

    def _extract_context(self, text: str) -> str:
        """Trích xuất context từ text."""
        text_lower = text.lower()

        # Tìm context keywords
        for context_type, keywords in CONTEXT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return context_type

        # Fallback: dựa vào patterns
        if re.search(CONTEXT_PATTERNS["emotion"], text_lower):
            return "emotional"

        return "general"  # Default

    def _extract_keywords(self, text: str) -> List[str]:
        """Trích xuất keywords từ text."""
        keywords = []
        text_lower = text.lower()

        # Tìm tất cả keywords
        for category, keyword_list in CONTEXT_KEYWORDS.items():
            for keyword in keyword_list:
                if keyword in text_lower:
                    keywords.append(keyword)

        for category, keyword_list in ENVIRONMENT_KEYWORDS.items():
            for keyword in keyword_list:
                if keyword in text_lower:
                    keywords.append(keyword)

        return keywords

    def _calculate_confidence(self, context_info: Dict[str, Any]) -> float:
        """Tính confidence score cho context extraction."""
        score = 0.0

        # Base score using constant weights
        if context_info["context"]:
            score += CONFIDENCE_WEIGHTS["context"]
        if context_info["environment"]:
            score += CONFIDENCE_WEIGHTS["environment"]
        if context_info["chapter"]:
            score += CONFIDENCE_WEIGHTS["chapter"]
        if context_info["detected_keywords"]:
            score += CONFIDENCE_WEIGHTS["keywords"]

        return min(score, 1.0)

    def suggest_context_for_chunk(
        self, chunk_text: str, chunk_id: str = ""
    ) -> Dict[str, Any]:
        """
        Suggest context cho chunk dựa trên content analysis.

        Returns:
            Dict với suggested context và environment
        """
        context_info = self.extract_context_from_chunk(chunk_text, chunk_id)

        # Suggest based on analysis
        suggestions = {
            "suggested_context": context_info["context"] or "general",
            "suggested_environment": context_info["environment"] or "informal",
            "confidence": context_info["confidence"],
            "reasoning": self._generate_reasoning(context_info),
        }

        return suggestions

    def _generate_reasoning(self, context_info: Dict[str, Any]) -> str:
        """Generate reasoning cho context suggestions."""
        reasons = []

        if context_info["context"]:
            reasons.append(f"Detected context: {context_info['context']}")

        if context_info["environment"]:
            reasons.append(f"Detected environment: {context_info['environment']}")

        if context_info["detected_keywords"]:
            reasons.append(
                f"Keywords: {', '.join(context_info['detected_keywords'][:3])}"
            )

        if context_info["chapter"]:
            reasons.append(f"Chapter: {context_info['chapter']}")

        return "; ".join(reasons) if reasons else "No specific context detected"

    def get_context_templates(self) -> Dict[str, List[str]]:
        """Trả về context templates để user có thể tham khảo."""
        return {
            "contexts": list(CONTEXT_KEYWORDS.keys()),
            "environments": list(ENVIRONMENT_KEYWORDS.keys()),
            "patterns": list(CONTEXT_PATTERNS.keys()),
        }
