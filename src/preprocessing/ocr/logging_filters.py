# -*- coding: utf-8 -*-
"""
Logging filters for OCR module.
Extracted from ocr_reader.py to improve code organization.

This module contains:
- NoisyMessageFilter: Filter to suppress noisy stderr/stdout messages from Google libraries
- GoogleLogFilter: Logging filter to suppress Google/gRPC/absl log messages
- _suppress_google_logs: Function to configure log suppression
"""
from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, TextIO

# Module-level flag to track stderr filter state
_stderr_filter_active = False
_stdout_filter_active = False


class NoisyMessageFilter:
    """Filter để chặn các messages gây nhiễu được in trực tiếp ra stderr/stdout."""

    def __init__(self, original_stream: "TextIO"):
        self.original_stream = original_stream
        # Buffer để xử lý multi-line messages
        self.buffer = ""
        # Patterns gây nhiễu (tất cả lowercase để so sánh)
        # Bao gồm cả partial matches để catch variations
        self.noisy_patterns = [
            "e0000",  # gRPC error prefix
            "alts_credentials",
            "alts creds",
            "alts creds ignored",
            "alts creds ignored. not running on gcp",
            "absl::initializelog",
            "not running on gcp",
            "untrusted alts",
            "untrusted alts is not enabled",
            "written to stderr",
            "all log messages before",
            "all log messages before absl",
            "alts_credentials.cc",  # File path pattern
            "alts_credentials.cc:93",  # File path with line number
            "warning: all log messages",  # Warning prefix
        ]

    def write(self, text: str) -> None:
        if not text:
            return

        # Thêm vào buffer để xử lý multi-line messages
        self.buffer += text

        # Kiểm tra buffer có chứa noisy patterns không (case-insensitive)
        buffer_lower = self.buffer.lower()

        # Kiểm tra nhanh trước khi split (tối ưu hơn)
        is_noisy = False

        # Check toàn bộ buffer trước (faster)
        for pattern in self.noisy_patterns:
            if pattern in buffer_lower:
                is_noisy = True
                break

        # Nếu chưa detect, check từng dòng chi tiết
        if not is_noisy:
            lines = self.buffer.split("\n")
            for line in lines:
                line_lower = line.lower().strip()
                # Check các pattern cụ thể
                if any(pattern in line_lower for pattern in self.noisy_patterns):
                    is_noisy = True
                    break
                # Check pattern E0000 ở đầu dòng
                if line_lower.startswith("e0000"):
                    is_noisy = True
                    break
                # Check "WARNING:" prefix với absl messages
                if line_lower.startswith("warning:") and (
                    "absl" in line_lower or "stderr" in line_lower
                ):
                    is_noisy = True
                    break

        # Nếu không noisy, ghi ra stream
        if not is_noisy:
            self.original_stream.write(text)
        # Nếu noisy, không ghi gì cả (suppress hoàn toàn)

        # Reset buffer sau mỗi newline hoặc khi buffer quá dài
        if "\n" in text:
            # Giữ lại phần sau newline cuối cùng để check tiếp (cho multi-line messages)
            parts = self.buffer.rsplit("\n", 1)
            self.buffer = parts[-1] if len(parts) > 1 else ""

        if len(self.buffer) > 2000:  # Reset nếu buffer quá dài
            self.buffer = ""

    def flush(self) -> None:
        self.original_stream.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.original_stream, name)


class GoogleLogFilter(logging.Filter):
    """Filter để loại bỏ các log messages gây nhiễu từ Google libraries."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        msg_lower = msg.lower()

        # Loại bỏ các messages về absl::InitializeLog
        if "absl::initializelog" in msg_lower or "absl::InitializeLog" in msg:
            return False

        # Loại bỏ các messages về ALTS creds (nhiều pattern khác nhau)
        if any(
            pattern in msg
            for pattern in [
                "ALTS creds",
                "alts_credentials",
                "alts creds ignored",
                "not running on gcp",
                "untrusted alts is not enabled",
            ]
        ):
            return False

        # Loại bỏ các messages từ absl logger
        if record.name.startswith("absl.") or "absl" in record.name.lower():
            return False

        # Loại bỏ messages có pattern E0000 từ gRPC/absl
        if msg.startswith("E0000") and ("alts" in msg_lower or "cred" in msg_lower):
            return False

        return True


def _suppress_google_logs() -> None:
    """
    Suppress logging từ Google libraries (gRPC, absl, etc.)
    Bao gồm cả việc filter stderr trực tiếp.
    """
    global _stderr_filter_active, _stdout_filter_active

    # Set environment variables
    os.environ["GRPC_VERBOSITY"] = "ERROR"
    os.environ["GLOG_minloglevel"] = "2"
    os.environ["GRPC_PYTHON_LOG_LEVEL"] = "ERROR"
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

    # Suppress absl logging nếu có
    try:
        import absl.logging

        absl.logging.set_verbosity(absl.logging.ERROR)
        # Disable absl handler
        for handler in absl.logging._absl_logger.handlers:
            handler.setLevel(logging.ERROR)
    except Exception:
        pass

    # Filter stderr và stdout để chặn messages in trực tiếp
    try:
        # Kiểm tra nếu đã là NoisyMessageFilter rồi thì không cần apply lại
        if not isinstance(sys.stderr, NoisyMessageFilter):
            original_stderr = (
                sys.stderr
                if not isinstance(sys.stderr, NoisyMessageFilter)
                else sys.stderr.original_stream
            )
            sys.stderr = NoisyMessageFilter(original_stderr)
            _stderr_filter_active = True
    except Exception:
        pass

    try:
        if not isinstance(sys.stdout, NoisyMessageFilter):
            original_stdout = (
                sys.stdout
                if not isinstance(sys.stdout, NoisyMessageFilter)
                else sys.stdout.original_stream
            )
            sys.stdout = NoisyMessageFilter(original_stdout)
            _stdout_filter_active = True
    except Exception:
        pass

    # Apply filter cho root logger và các loggers cụ thể
    google_filter = GoogleLogFilter()
    root_logger = logging.getLogger()
    root_logger.addFilter(google_filter)

    # Suppress logging từ các Google libraries
    for lib_name in [
        "google",
        "grpc",
        "absl",
        "google.generativeai",
        "google.api_core",
        "google.auth",
        "grpc._cython",
    ]:
        lib_logger = logging.getLogger(lib_name)
        lib_logger.setLevel(logging.ERROR)
        lib_logger.propagate = False
        lib_logger.addFilter(google_filter)
