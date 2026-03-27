# -*- coding: utf-8 -*-

"""
Error Formatter - Format exceptions ngắn gọn và dễ đọc.

Module này cung cấp các utility functions để format exceptions
một cách ngắn gọn, đảm bảo log dễ đọc và đủ thông tin để debug.
"""

import re
import traceback
from typing import Any, Dict, Optional


def format_exception_short(exception: Exception, context: Optional[str] = None, max_traceback_lines: int = 3) -> str:
    """
    Format exception ngắn gọn với thông tin cần thiết.

    Args:
        exception: Exception object
        context: Optional context string (e.g., "Chunk 123", "API call")
        max_traceback_lines: Số dòng traceback tối đa (mặc định: 3)

    Returns:
        Formatted error message string
    """
    error_type = type(exception).__name__
    error_msg = str(exception)

    # Rút gọn error message nếu quá dài
    if len(error_msg) > 200:
        error_msg = error_msg[:200] + "..."

    # Build message
    parts = []
    if context:
        parts.append(f"[{context}]")
    parts.append(f"{error_type}: {error_msg}")

    # KHÔNG thêm traceback vào short message (chỉ log ở DEBUG level)
    # Traceback sẽ được log riêng ở DEBUG level nếu cần

    return " | ".join(parts)


def format_api_error(exception: Exception, context: Optional[str] = None) -> str:
    """
    Format API error (Google GenAI) ngắn gọn với thông tin quan trọng.

    Args:
        exception: Exception object
        context: Optional context string

    Returns:
        Formatted error message string
    """
    error_type = type(exception).__name__
    error_msg = str(exception)

    # Extract thông tin quan trọng từ error message
    status_code = None
    quota_info = None
    retry_delay = None

    # Tìm status code (429, 401, 403, etc.)
    status_match = re.search(r"\b(\d{3})\b", error_msg)
    if status_match:
        status_code = status_match.group(1)

    # Tìm error code từ exception attributes
    if hasattr(exception, "status_code"):
        status_code = str(exception.status_code)
    if hasattr(exception, "code"):
        str(exception.code)

    # Tìm quota info
    if "quota" in error_msg.lower() or "429" in error_msg:
        quota_match = re.search(r"limit:\s*(\d+)", error_msg, re.IGNORECASE)
        if quota_match:
            quota_info = quota_match.group(1)

    # Tìm retry delay
    retry_match = re.search(r"retry.*?(\d+\.?\d*)\s*s", error_msg, re.IGNORECASE)
    if retry_match:
        retry_delay = retry_match.group(1)

    # Build message ngắn gọn
    parts = []
    if context:
        parts.append(f"[{context}]")

    # Error type và status code
    if status_code:
        parts.append(f"{error_type} ({status_code})")
    else:
        parts.append(error_type)

    # Error message (rút gọn)
    msg_short = error_msg
    if "RESOURCE_EXHAUSTED" in msg_short or "429" in msg_short:
        msg_short = "Hết hạn mức tài nguyên (429)."
    elif "SAFETY" in msg_short or "blocked" in msg_short.lower():
        msg_short = "Nội dung bị chặn do quy tắc an toàn."
    elif len(msg_short) > 150:
        # Tìm câu đầu tiên hoặc cắt ở 150 ký tự
        first_sentence = msg_short.split(".")[0]
        if len(first_sentence) < 150:
            msg_short = first_sentence + "..."
        else:
            msg_short = msg_short[:150] + "..."
    parts.append(msg_short)

    # Thông tin bổ sung (quota, retry delay)
    extras = []
    if quota_info:
        extras.append(f"Giới hạn Quota: {quota_info}")
    if retry_delay:
        extras.append(f"Thử lại sau: {retry_delay}s")
    if extras:
        parts.append(" | ".join(extras))

    return " | ".join(parts)


def format_exception_for_logging(
    exception: Exception,
    context: Optional[str] = None,
    include_traceback: bool = False,
    max_traceback_lines: int = 3,
) -> Dict[str, Any]:
    """
    Format exception cho logging với cả short và full version.

    Args:
        exception: Exception object
        context: Optional context string
        include_traceback: Có include full traceback không (cho debug)
        max_traceback_lines: Số dòng traceback tối đa cho short version

    Returns:
        Dictionary với:
            - short: Short formatted message (cho console)
            - full: Full formatted message (cho file log nếu cần)
            - type: Error type name
            - message: Error message
    """
    error_type = type(exception).__name__
    error_msg = str(exception)

    # Short version (cho console) - KHÔNG có traceback
    if (
        "genai" in error_type.lower()
        or "api" in error_type.lower()
        or "429" in error_msg
        or "503" in error_msg
        or "quota" in error_msg.lower()
        or "unavailable" in error_msg.lower()
    ):
        short_msg = format_api_error(exception, context)
    else:
        # Rút gọn error message
        msg_short = error_msg[:150] + "..." if len(error_msg) > 150 else error_msg
        if context:
            short_msg = f"[{context}] {error_type}: {msg_short}"
        else:
            short_msg = f"{error_type}: {msg_short}"

    # Full version (cho file log) - chỉ có traceback nếu include_traceback=True
    full_msg = short_msg
    if include_traceback:
        full_tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        full_msg = f"{short_msg}\n\nFull traceback:\n{full_tb}"
    else:
        # Mặc định: chỉ thêm traceback ngắn gọn (3 dòng cuối) ở DEBUG level
        tb_lines = traceback.format_exception(type(exception), exception, exception.__traceback__)
        if tb_lines and len(tb_lines) > 1:
            # Lấy 3 dòng cuối cùng
            relevant_lines = tb_lines[-3:]
            tb_short = "".join(relevant_lines).strip()
            if tb_short:
                full_msg = f"{short_msg}\n\nTraceback (last 3 lines):\n{tb_short}"

    return {
        "short": short_msg,
        "full": full_msg,
        "type": error_type,
        "message": error_msg,
    }
