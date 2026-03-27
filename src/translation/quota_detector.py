# -*- coding: utf-8 -*-
"""
QuotaDetector: Chuyên trách nhận diện các lỗi liên quan đến quota và rate limit.
Giúp tách biệt logic xử lý lỗi khỏi Translator.
"""

import logging
from typing import Optional

try:
    import google.api_core.exceptions
except ImportError:
    # Fallback if google-cloud-core is not installed
    class GoogleExceptionsFallback:
        class ResourceExhausted(Exception):
            pass
    google = type('obj', (object,), {'api_core': type('obj', (object,), {'exceptions': GoogleExceptionsFallback})})

logger = logging.getLogger("NovelTranslator")


class QuotaDetector:
    """
    Cung cấp các phương thức để nhận diện lỗi quota/rate limit từ API.
    """

    @staticmethod
    def is_quota_error(
        exception: Exception,
        error_type_name: str,
        error_msg: str,
    ) -> bool:
        """
        Kiểm tra xem một exception có phải là lỗi quota/rate limit hay không.
        Sử dụng logic fast-path và patterns matching.

        Args:
            exception: Đối tượng exception bắt được.
            error_type_name: Tên kiểu của exception (e.g., 'ResourceExhausted').
            error_msg: Thông điệp lỗi chi tiết.

        Returns:
            True nếu là lỗi quota, False nếu không phải.
        """
        error_msg_lower = error_msg.lower()

        # Fast path 1: Check type trực tiếp từ Google SDK
        if isinstance(exception, google.api_core.exceptions.ResourceExhausted):
            return True

        # Fast path 2: Check các mã lỗi phổ biến (429, RESOURCE_EXHAUSTED)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return True

        # Fast path 3: Check ClientError kèm mã 429 (thường gặp ở REST API)
        if "ClientError" in error_type_name and "429" in error_msg:
            return True

        # Slow path: Check các từ khóa trong message
        return (
            "resource_exhausted" in error_msg_lower
            or "quota" in error_msg_lower
            or "rate limit" in error_msg_lower
        )
