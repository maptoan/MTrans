from __future__ import annotations

"""
Bộ phân loại lỗi tập trung cho API Gemini.

Mục tiêu:
- Chuyển các exception đa dạng từ SDK/thư viện về một tập error_type nội bộ ổn định.
- error_type sẽ được SmartKeyDistributor và Translator sử dụng để quyết định cooldown, thay key, hoặc đánh dấu key hỏng.

Các error_type nội bộ:
- 'quota_exceeded'
- 'rate_limit'
- 'invalid_key'
- 'timeout'
- 'generation_blocked'
- 'server_error'
- 'unknown'
"""

from typing import Tuple


def classify_error(exc: Exception) -> str:
    """
    Phân loại lỗi thành một trong các error_type nội bộ.

    Args:
        exc: Exception bắt được khi gọi API.

    Returns:
        error_type: chuỗi thuộc một trong các giá trị:
            'quota_exceeded', 'rate_limit', 'invalid_key',
            'timeout', 'generation_blocked', 'server_error', 'unknown'
    """
    error_type_name = type(exc).__name__
    message = str(exc) or ""
    msg_lower = message.lower()
    type_lower = error_type_name.lower()

    # 1. QuotaExceeded / ResourceExhausted / 429 quota
    if (
        "resource_exhausted" in msg_lower
        or "quota" in msg_lower
        or "quota" in type_lower
        or "429 resource_exhausted" in msg_lower
    ):
        return "quota_exceeded"

    # 2. Rate limit (khác quota: quá nhiều request ngắn hạn)
    if "rate_limit" in msg_lower or "too many requests" in msg_lower:
        return "rate_limit"

    # 3. Invalid API key / auth
    if (
        "api key" in msg_lower
        and ("not valid" in msg_lower or "invalid" in msg_lower)
    ) or "invalid_api_key" in msg_lower:
        return "invalid_key"
    if any(code in msg_lower for code in (" 401", "401 ", " 403", "403 ")):
        return "invalid_key"

    # 4. Timeout / Deadline
    if "timeout" in type_lower or "timeout" in msg_lower or "deadline" in msg_lower:
        return "timeout"

    # 5. Safety / blocked nội dung
    if "safety" in msg_lower or "blocked" in msg_lower:
        return "generation_blocked"

    # 6. Server error 5xx
    if message.startswith("5") or "internal" in msg_lower or "server error" in msg_lower:
        return "server_error"

    # 7. Fallback: unknown
    return "unknown"


def classify_error_with_message(exc: Exception) -> Tuple[str, str]:
    """
    Helper trả về (error_type, full_message) để tiện log và truyền tiếp.
    """
    return classify_error(exc), str(exc) or ""

