# -*- coding: utf-8 -*-
"""
ResultHandler: Kiểm tra tính hợp lệ của kết quả dịch và ghi nhận token usage.
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("NovelTranslator")


class ResultHandler:
    """
    Chịu trách nhiệm xác thực phản hồi từ AI và cập nhật các chỉ số sử dụng.
    """

    def __init__(self, metrics_collector: Any):
        self.metrics_collector = metrics_collector

    def validate_translation_result(
        self, chunk_id: int, main_result: Optional[Dict[str, Any]], text_to_translate: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Xác thực kết quả dịch thuật từ API.

        Returns:
            Tuple[is_valid, translation, error_message]
        """
        try:
            if not main_result:
                return False, None, f"main_result is None or empty for chunk {chunk_id}"

            if "translation" not in main_result:
                return (
                    False,
                    None,
                    f"main_result missing 'translation' key for chunk {chunk_id}. Available keys: {list(main_result.keys())}",
                )

            translation = main_result["translation"]

            if not translation:
                return False, None, f"translation is None or empty for chunk {chunk_id}"

            if not isinstance(translation, str):
                return False, None, f"translation is not a string for chunk {chunk_id}"

            if not translation.strip():
                return (
                    False,
                    None,
                    f"translation is whitespace-only for chunk {chunk_id}",
                )

            return True, translation, None

        except Exception as e:
            return False, None, f"Validation error for chunk {chunk_id}: {str(e)}"

    def record_token_usage(self, chunk_id: int, main_result: Dict[str, Any]) -> None:
        """
        Ghi nhận mức độ tiêu thụ token từ phản hồi của API vào MetricsCollector.
        """
        usage = main_result.get("usage")
        if not usage:
            return

        # Trích xuất các chỉ số từ thuộc tính (getattr hỗ trợ cả object lẫn dict)
        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        cached_tokens = getattr(usage, "cached_content_token_count", 0) or 0
        total_tokens = getattr(usage, "total_token_count", 0) or 0

        if cached_tokens > 0:
            logger.debug(
                f"💰 [Chunk {chunk_id}] Cache Hit! {cached_tokens}/{prompt_tokens} tokens saved."
            )

        # Ghi nhận vào metrics collector
        if self.metrics_collector:
            try:
                self.metrics_collector.record_token_usage(
                    chunk_id=chunk_id,
                    prompt_tokens=prompt_tokens,
                    cached_tokens=cached_tokens,
                    total_tokens=total_tokens,
                    model_name=main_result.get("model_used"),
                )
            except Exception as e:
                logger.debug(f"Failed to record token usage: {e}")
