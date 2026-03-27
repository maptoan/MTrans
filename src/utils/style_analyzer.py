# -*- coding: utf-8 -*-

"""
Style Analyzer
==============
Phân tích văn phong từ context chunks để duy trì sự nhất quán.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NovelTranslator")


class StyleAnalyzer:
    """
    Phân tích văn phong từ context chunks.

    Attributes:
        include_tone: Có phân tích tone không
        include_register: Có phân tích register không
        include_dialogue_ratio: Có tính dialogue ratio không
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo StyleAnalyzer.

        Args:
            config: Configuration dict với style_analysis settings
        """
        self.config = config or {}
        style_config = self.config.get("style_analysis", {})

        self.enabled = style_config.get("enabled", True)
        self.include_tone = style_config.get("include_tone", True)
        self.include_register = style_config.get("include_register", True)
        self.include_dialogue_ratio = style_config.get("include_dialogue_ratio", False)

        # Formal markers (từ điển)
        self.formal_markers = [
            "xin",
            "kính",
            "thưa",
            "quý",
            "vị",
            "ngài",
            "đức",
            "bệ hạ",
            "kính thưa",
            "thưa quý",
            "kính gửi",
        ]

        # Informal markers (từ điển)
        self.informal_markers = [
            "mày",
            "tao",
            "tớ",
            "cậu",
            "bạn",
            "mình",
            "chúng mình",
            "ông",
            "bà",
            "anh",
            "chị",
            "em",  # Có thể formal hoặc informal tùy context
        ]

        # Complex words (formal register)
        self.complex_words = [
            "nhưng",
            "tuy nhiên",
            "do đó",
            "vì vậy",
            "mặc dù",
            "bởi vì",
            "tuy vậy",
            "song",
            "thế nhưng",
            "vì thế",
        ]

        # Dialogue markers
        self.dialogue_markers = ['"', "'", "nói", "hỏi", "đáp", "thưa", "kêu", "gọi"]

        logger.debug(
            f"StyleAnalyzer initialized: enabled={self.enabled}, "
            f"tone={self.include_tone}, register={self.include_register}"
        )

    def analyze(self, translated_context_chunks: List[str]) -> Dict[str, Any]:
        """
        Phân tích văn phong từ context chunks.

        Args:
            translated_context_chunks: List các chunk đã dịch

        Returns:
            Dict với các metrics: pace, avg_length, tone, register, etc.
        """
        if not self.enabled or not translated_context_chunks:
            return {}

        try:
            # Lấy 2 chunks gần nhất để analyze
            recent_chunks = translated_context_chunks[-2:]
            combined_text = " ".join(recent_chunks)

            # Basic analysis (pace, sentence length)
            basic_analysis = self._analyze_basic_style(combined_text)

            result = basic_analysis.copy()

            # Tone analysis (nếu enabled)
            if self.include_tone:
                tone = self._detect_tone(combined_text)
                if tone:
                    result["tone"] = tone

            # Register analysis (nếu enabled)
            if self.include_register:
                register = self._detect_register(combined_text)
                if register:
                    result["register"] = register

            # Dialogue ratio (nếu enabled)
            if self.include_dialogue_ratio:
                dialogue_ratio = self._calculate_dialogue_ratio(
                    combined_text, recent_chunks
                )
                if dialogue_ratio is not None:
                    result["dialogue_ratio"] = dialogue_ratio

            return result

        except Exception as e:
            logger.warning(
                f"[StyleAnalyzer] Lỗi khi analyze style: {e}, fallback về basic analysis"
            )
            # Fallback về basic analysis
            if translated_context_chunks:
                recent_chunks = translated_context_chunks[-2:]
                combined_text = " ".join(recent_chunks)
                return self._analyze_basic_style(combined_text)
            return {}

    def _analyze_basic_style(self, combined_text: str) -> Dict[str, Any]:
        """
        Phân tích style cơ bản (pace, sentence length).

        Args:
            combined_text: Combined text từ context chunks

        Returns:
            Dict với pace, avg_length, sentence_count
        """
        sentences = [s.strip() for s in re.split(r"[.!?]+", combined_text) if s.strip()]
        if not sentences:
            return {}

        total_words = sum(len(s.split()) for s in sentences)
        avg_sentence_length = total_words / len(sentences) if sentences else 0

        # Pace classification
        if avg_sentence_length < 15:
            pace = "nhanh"
        elif avg_sentence_length < 25:
            pace = "trung bình"
        else:
            pace = "chậm"

        return {
            "pace": pace,
            "avg_length": round(avg_sentence_length, 1),
            "sentence_count": len(sentences),
        }

    def _detect_tone(self, text: str) -> Optional[str]:
        """
        Phát hiện tone (trang trọng/thân mật/trung tính).

        Args:
            text: Text để analyze

        Returns:
            Tone: "trang trọng", "thân mật", hoặc "trung tính"
        """
        text_lower = text.lower()

        # Count formal và informal markers
        formal_count = sum(1 for marker in self.formal_markers if marker in text_lower)
        informal_count = sum(
            1 for marker in self.informal_markers if marker in text_lower
        )

        # Determine tone
        if formal_count > informal_count and formal_count > 0:
            return "trang trọng"
        elif informal_count > formal_count and informal_count > 0:
            return "thân mật"
        else:
            return "trung tính"

    def _detect_register(self, text: str) -> Optional[str]:
        """
        Phát hiện register (formal/informal).

        Args:
            text: Text để analyze

        Returns:
            Register: "formal" hoặc "informal"
        """
        text_lower = text.lower()

        # Count complex words (formal register indicator)
        complex_count = sum(1 for word in self.complex_words if word in text_lower)

        # Simple heuristic: nếu có nhiều complex words → formal
        if complex_count > 2:
            return "formal"
        else:
            return "informal"

    def _calculate_dialogue_ratio(
        self, combined_text: str, chunks: List[str]
    ) -> Optional[float]:
        """
        Tính tỷ lệ dialogue vs narrative.

        Args:
            combined_text: Combined text
            chunks: List các chunks

        Returns:
            Dialogue ratio (0.0-1.0) hoặc None nếu không tính được
        """
        if not chunks:
            return None

        text_lower = combined_text.lower()

        # Count dialogue markers
        dialogue_count = sum(
            1 for marker in self.dialogue_markers if marker in text_lower
        )

        # Count sentences
        sentences = [s.strip() for s in re.split(r"[.!?]+", combined_text) if s.strip()]
        total_sentences = len(sentences) if sentences else 1

        # Calculate ratio
        ratio = dialogue_count / total_sentences if total_sentences > 0 else 0.0
        return round(min(ratio, 1.0), 2)
