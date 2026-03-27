# -*- coding: utf-8 -*-

"""
Context Selector
================
Chọn context chunks tốt nhất dựa trên proximity weighting và relevance scoring.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")

logger = logging.getLogger("NovelTranslator")


class ContextSelector:
    """
    Chọn context chunks tốt nhất để hiển thị.

    Attributes:
        proximity_weight: Weight cho proximity (0.0-1.0)
        relevance_weight: Weight cho relevance (0.0-1.0)
        max_display: Số lượng chunks tối đa để hiển thị
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo ContextSelector.

        Args:
            config: Configuration dict với selection settings
        """
        self.config = config or {}
        selection_config = self.config.get("selection", {})

        self.proximity_weight = selection_config.get("proximity_weight", 0.6)
        self.relevance_weight = selection_config.get("relevance_weight", 0.4)
        self.max_display = selection_config.get("max_display", 2)

        # Normalize weights
        total_weight = self.proximity_weight + self.relevance_weight
        if total_weight > 0:
            self.proximity_weight /= total_weight
            self.relevance_weight /= total_weight

        logger.debug(
            f"ContextSelector initialized: "
            f"proximity_weight={self.proximity_weight:.2f}, "
            f"relevance_weight={self.relevance_weight:.2f}, "
            f"max_display={self.max_display}"
        )

    def select_best(
        self,
        context_candidates: List[
            Tuple[str, str, int]
        ],  # (original, translated, distance)
        current_chunk_text: Optional[str] = None,
    ) -> List[Tuple[str, str]]:
        """
        Chọn context chunks tốt nhất để hiển thị.

        Args:
            context_candidates: List of (original_text, translated_text, distance_from_current)
            current_chunk_text: Text của chunk hiện tại (để tính relevance, optional)

        Returns:
            List of (original_text, translated_text) - top N chunks
        """
        if not context_candidates:
            return []

        # Calculate weights cho mỗi candidate
        weighted_candidates = []
        for orig, trans, distance in context_candidates:
            # Proximity weight: 1.0 for distance=1, 0.5 for distance=2, etc.
            proximity_score = 1.0 / distance if distance > 0 else 1.0

            # Relevance weight (nếu có current_chunk_text)
            relevance_score = 1.0  # Default: no relevance scoring
            if current_chunk_text:
                relevance_score = self._calculate_relevance(orig, current_chunk_text)

            # Combined weight
            total_weight = (
                proximity_score * self.proximity_weight
                + relevance_score * self.relevance_weight
            )

            weighted_candidates.append((orig, trans, total_weight))

        # Select top N (Phase 2: Optimize với heap nếu cần, nhưng với k nhỏ thì sort đơn giản hơn)
        # Với k thường < 5, sort O(k log k) đủ nhanh
        weighted_candidates.sort(key=lambda x: x[2], reverse=True)
        return [
            (orig, trans) for orig, trans, _ in weighted_candidates[: self.max_display]
        ]

    def _calculate_relevance(self, context_text: str, current_text: str) -> float:
        """
        Tính relevance score giữa context và current chunk (keyword overlap).

        Args:
            context_text: Text của context chunk
            current_text: Text của chunk hiện tại

        Returns:
            Relevance score (0.0-1.0)
        """
        if not context_text or not current_text:
            return 0.0

        try:
            # Simple keyword overlap (không cần TF-IDF)
            # Split thành words (đơn giản, không cần tokenization phức tạp)
            context_words = set(context_text.lower().split())
            current_words = set(current_text.lower().split())

            # Remove common stop words (đơn giản)
            stop_words = {
                "và",
                "của",
                "với",
                "trong",
                "cho",
                "từ",
                "đến",
                "the",
                "a",
                "an",
                "of",
                "in",
                "on",
                "at",
                "to",
                "for",
            }
            context_words = context_words - stop_words
            current_words = current_words - stop_words

            # Calculate overlap
            common_words = context_words & current_words
            total_unique_words = context_words | current_words

            if not total_unique_words:
                return 0.0

            relevance = len(common_words) / len(total_unique_words)
            return min(relevance, 1.0)

        except Exception as e:
            logger.warning(
                f"[ContextSelector] Lỗi khi tính relevance: {e}, fallback về 1.0"
            )
            return 1.0  # Fallback: assume relevant
