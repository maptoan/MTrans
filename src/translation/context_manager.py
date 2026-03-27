# -*- coding: utf-8 -*-
"""
ContextManager: Quản lý và điều phối ngữ cảnh (context) cho quá trình dịch thuật.
Hợp nhất logic từ ContextBreakDetector và ContextSelector.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .context_break_detector import ContextBreakDetector
from .context_selector import ContextSelector

logger = logging.getLogger("NovelTranslator")


class ContextManager:
    """
    Quản lý việc lấy ngữ cảnh (context chunks) cho một chunk cụ thể.
    Hỗ trợ Adaptive Context Window, Break Detection, và Caching.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.translation_config = config.get("translation", {})
        
        # Thành phần hỗ trợ
        self.context_break_detector = ContextBreakDetector(config)
        self.context_selector = ContextSelector(config)
        
        # Caching logic
        self._cache: Dict[str, Tuple[List[str], List[str]]] = {}
        self._cache_max_size = config.get("performance", {}).get("context_cache_max_size", 100)

    def get_context_chunks(
        self,
        chunk_index: int,
        all_chunks: List[Dict[str, Any]],
        translated_chunks_map: Dict[str, str],
    ) -> Tuple[List[str], List[str]]:
        """
        Lấy context chunks (original và translated) cho một chunk index cụ thể.
        
        Args:
            chunk_index: Index của chunk hiện tại trong danh sách all_chunks.
            all_chunks: Danh sách tất cả các chunks của tài liệu.
            translated_chunks_map: Map chứa bản dịch của các chunks đã hoàn thành.

        Returns:
            Tuple (original_context_chunks, translated_context_chunks)
        """
        # 1. Kiểm tra Cache
        cache_key = f"{chunk_index}_{len(translated_chunks_map)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 2. Xác định Window Size (Adaptive)
        current_chunk_text = all_chunks[chunk_index]["text"]
        context_window = self._calculate_adaptive_window(current_chunk_text)

        # 3. Thu thập ứng viên ngữ cảnh (Context Candidates)
        start_index = max(0, chunk_index - context_window)
        context_candidates = []  # List of (original, translated, distance)

        for j in range(start_index, chunk_index):
            prev_chunk = all_chunks[j]
            prev_chunk_id_str = str(prev_chunk["global_id"])
            prev_chunk_text = prev_chunk["text"]

            # Smart Fallback: Ưu tiên bản dịch, nếu chưa có thì TRẢ VỀ None
            # [PHASE 13] ANTI-BLEEDING: Tuyệt đối không dùng bản gốc làm fallback cho bản dịch
            if prev_chunk_id_str in translated_chunks_map:
                translated_text = translated_chunks_map[prev_chunk_id_str]
            else:
                translated_text = None

            distance = chunk_index - j

            # Break Detection
            if self.context_break_detector.detect(prev_chunk_text, current_chunk_text):
                # Nếu phát hiện break, reset toàn bộ context trước đó và bắt đầu lại từ đây
                context_candidates = []
                logger.debug(
                    f"[ContextManager] Break detected at chunk {j} -> {chunk_index}. Resetting context."
                )
                continue

            context_candidates.append((prev_chunk_text, translated_text, distance))

        # 4. Lựa chọn ngữ cảnh tốt nhất (Ranking)
        selected_context = self.context_selector.select_best(
            context_candidates, current_chunk_text=current_chunk_text
        )

        # 5. Unpack kết quả
        original_context_chunks = []
        translated_context_chunks = []
        for orig, trans in selected_context:
            original_context_chunks.append(orig)
            translated_context_chunks.append(trans)

        result = (original_context_chunks, translated_context_chunks)

        # 6. Cập nhật Cache (với logic eviction đơn giản)
        self._update_cache(cache_key, result)

        return result

    def _calculate_adaptive_window(self, text: str) -> int:
        """Tính toán window size dựa trên độ phức tạp của text."""
        base_window = self.translation_config.get("context_window_size", 1)
        adaptive_enabled = self.translation_config.get("adaptive_context_window", True)

        if not adaptive_enabled:
            return base_window

        # Heuristic complexity estimation
        length = len(text)
        has_dialogue = '"' in text or '“' in text or '«' in text
        has_paragraphs = "\n\n" in text

        complexity_score = 0
        if length > 5000: complexity_score += 2
        elif length > 3000: complexity_score += 1
        if has_dialogue: complexity_score += 1
        if has_paragraphs: complexity_score += 1

        if complexity_score < 2:
            return 1
        elif complexity_score < 4:
            return 2
        else:
            return 3

    def _update_cache(self, key: str, value: Any) -> None:
        """Lưu vào cache và thực hiện dọn dẹp nếu vượt giới hạn."""
        if len(self._cache) >= self._cache_max_size:
            # Simple FIFO eviction (remove oldest 10%)
            keys_to_remove = list(self._cache.keys())[: self._cache_max_size // 10]
            for k in keys_to_remove:
                del self._cache[k]
            logger.debug(f"[ContextManager] Cache evicted {len(keys_to_remove)} entries.")
            
        self._cache[key] = value

    def clear_cache(self) -> None:
        """Xóa sạch cache ngữ cảnh."""
        self._cache.clear()
        logger.debug("[ContextManager] Cache cleared.")
