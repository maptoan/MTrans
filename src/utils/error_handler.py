#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Centralized Error Handler
=========================
Centralized error handling với classification, recovery strategy, và metrics tracking.

PHIÊN BẢN: v2.0+
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("NovelTranslator")


class ErrorType(Enum):
    """Error types được classify."""

    INVALID_KEY = "invalid_key"
    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    GENERATION_ERROR = "generation_error"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"
    CONTENT_BLOCKED = "content_blocked"
    VALIDATION_ERROR = "validation_error"
    FILE_ERROR = "file_error"
    CACHE_NOT_FOUND = "cache_not_found"


# --- Constants ---

CLASSIFICATION_PATTERNS = {
    ErrorType.INVALID_KEY: [
        "invalid api key",
        "api key not found",
        "authentication failed",
        "unauthorized",
        "401",
    ],
    ErrorType.QUOTA_EXCEEDED: [
        "quota exceeded",
        "quota limit",
        "resource exhausted",
        "429",
        "rate limit exceeded",
    ],
    ErrorType.RATE_LIMIT: [
        "rate limit",
        "too many requests",
        "429",
        "throttled",
    ],
    ErrorType.NETWORK_ERROR: [
        "network error",
        "connection error",
        "timeout",
        "connection refused",
        "dns",
    ],
    ErrorType.TIMEOUT: [
        "timeout",
        "timed out",
        "deadline exceeded",
    ],
    ErrorType.GENERATION_ERROR: [
        "generation error",
        "content generation failed",
        "model error",
    ],
    ErrorType.SERVER_ERROR: [
        "server error",
        "internal server error",
        "500",
        "502",
        "503",
    ],
    ErrorType.CONTENT_BLOCKED: [
        "content blocked",
        "safety",
        "harmful content",
    ],
    ErrorType.CACHE_NOT_FOUND: [
        "404",
        "not found",
        "cache",
        "expired",
    ],
}

DEFAULT_RECOVERY_STRATEGIES = {
    ErrorType.INVALID_KEY: {
        "should_retry": False,
        "cooldown_time": 0,
        "max_retries": 0,
        "fallback_action": "get_new_key",
    },
    ErrorType.QUOTA_EXCEEDED: {
        "should_retry": True,
        "cooldown_time": 3600,
        "max_retries": 3,
        "fallback_action": "get_new_key",
    },
    ErrorType.RATE_LIMIT: {
        "should_retry": True,
        "cooldown_time": 300,
        "max_retries": 5,
        "fallback_action": "get_new_key",
    },
    ErrorType.NETWORK_ERROR: {
        "should_retry": True,
        "cooldown_time": 2,
        "max_retries": 3,
        "fallback_action": None,
    },
    ErrorType.TIMEOUT: {
        "should_retry": True,
        "cooldown_time": 2,
        "max_retries": 3,
        "fallback_action": None,
    },
    ErrorType.GENERATION_ERROR: {
        "should_retry": True,
        "cooldown_time": 300,
        "max_retries": 2,
        "fallback_action": "use_pro_model",
    },
    ErrorType.SERVER_ERROR: {
        "should_retry": True,
        "cooldown_time": 5,
        "max_retries": 3,
        "fallback_action": None,
    },
    ErrorType.CONTENT_BLOCKED: {
        "should_retry": False,
        "cooldown_time": 0,
        "max_retries": 0,
        "fallback_action": "skip_chunk",
    },
    ErrorType.CACHE_NOT_FOUND: {
        "should_retry": True,
        "cooldown_time": 5,
        "max_retries": 2,
        "fallback_action": "recreate_cache",
    },
    ErrorType.UNKNOWN: {
        "should_retry": True,
        "cooldown_time": 60,
        "max_retries": 2,
        "fallback_action": None,
    },
}


@dataclass
class ErrorContext:
    """Context information cho error."""

    chunk_id: Optional[int] = None
    api_key: Optional[str] = None
    worker_id: Optional[int] = None
    model: Optional[str] = None
    retry_count: int = 0
    timestamp: float = field(default_factory=time.time)
    additional_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorMetrics:
    """Metrics cho error tracking."""

    total_errors: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    errors_by_key: Dict[str, int] = field(default_factory=dict)
    recovery_success: int = 0
    recovery_failure: int = 0
    last_error_time: Optional[float] = None


class CentralizedErrorHandler:
    """
    Centralized error handler với classification, recovery strategy, và metrics.

    Features:
    - Error classification
    - Recovery strategy determination
    - Structured logging với context
    - Error metrics tracking
    - Fail-safe mechanism
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo CentralizedErrorHandler.

        Args:
            config: Configuration dict với error handling settings
        """
        self.config = config or {}
        error_config = self.config.get("error_handling", {})

        self.enabled = error_config.get("enabled", True)
        self.track_metrics = error_config.get("track_metrics", True)
        self.log_errors = error_config.get("log_errors", True)

        # Error metrics
        self.metrics = ErrorMetrics()

        # Recovery strategies (configurable)
        self.recovery_strategies = error_config.get("recovery_strategies", {})

        # Error classification patterns
        self.classification_patterns = CLASSIFICATION_PATTERNS

        logger.debug(f"CentralizedErrorHandler initialized: enabled={self.enabled}")

    def _init_classification_patterns(self):
        """Deprecated: Patterns now loaded from constants."""
        pass

    def classify_error(self, error: Exception, error_message: Optional[str] = None) -> ErrorType:
        """
        Classify error type từ exception và error message.

        Args:
            error: Exception object
            error_message: Optional error message string

        Returns:
            ErrorType enum
        """
        if not self.enabled:
            return ErrorType.UNKNOWN

        # Get error message
        if error_message is None:
            error_message = str(error).lower()
        else:
            error_message = error_message.lower()

        # Check classification patterns
        for error_type, patterns in self.classification_patterns.items():
            for pattern in patterns:
                if pattern in error_message:
                    return error_type

        # Check exception type
        error_type_name = type(error).__name__.lower()
        for error_type, patterns in self.classification_patterns.items():
            for pattern in patterns:
                if pattern in error_type_name:
                    return error_type

        return ErrorType.UNKNOWN

    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        error_message: Optional[str] = None,
        recovery_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Handle error với classification, logging, và recovery.

        Args:
            error: Exception object
            context: ErrorContext với thông tin context
            error_message: Optional error message string
            recovery_callback: Optional recovery callback function

        Returns:
            Dict với error information và recovery strategy
        """
        try:
            # Classify error
            error_type = self.classify_error(error, error_message)

            # Update metrics
            if self.track_metrics:
                self._update_metrics(error_type, context)

            # Log error với context
            if self.log_errors:
                self._log_error(error, error_type, context, error_message)

            # Determine recovery strategy
            recovery_strategy = self._determine_recovery_strategy(error_type, context)

            # Attempt recovery nếu có callback
            recovery_result = None
            if recovery_callback and recovery_strategy.get("should_retry", False):
                try:
                    recovery_result = recovery_callback()
                    if recovery_result:
                        if self.track_metrics:
                            self.metrics.recovery_success += 1
                    else:
                        if self.track_metrics:
                            self.metrics.recovery_failure += 1
                except Exception as recovery_error:
                    logger.error(f"Recovery callback failed: {recovery_error}", exc_info=True)
                    if self.track_metrics:
                        self.metrics.recovery_failure += 1

            return {
                "error_type": error_type.value,
                "error_message": error_message or str(error),
                "context": {
                    "chunk_id": context.chunk_id,
                    "api_key": context.api_key[:8] + "..." if context.api_key else None,
                    "worker_id": context.worker_id,
                    "model": context.model,
                    "retry_count": context.retry_count,
                },
                "recovery_strategy": recovery_strategy,
                "recovery_result": recovery_result,
                "timestamp": context.timestamp,
            }

        except Exception as handler_error:
            # Fail-safe: Nếu error handler fail, log và return basic info
            logger.critical(f"Error handler failed: {handler_error}", exc_info=True)
            return {
                "error_type": "unknown",
                "error_message": str(error),
                "context": {},
                "recovery_strategy": {"should_retry": False},
                "recovery_result": None,
                "timestamp": time.time(),
                "handler_error": str(handler_error),
            }

    def _update_metrics(self, error_type: ErrorType, context: ErrorContext):
        """Update error metrics."""
        self.metrics.total_errors += 1
        self.metrics.last_error_time = time.time()

        # Update by type
        error_type_str = error_type.value
        self.metrics.errors_by_type[error_type_str] = self.metrics.errors_by_type.get(error_type_str, 0) + 1

        # Update by key (nếu có)
        if context.api_key:
            key_prefix = context.api_key[:8] + "..."
            self.metrics.errors_by_key[key_prefix] = self.metrics.errors_by_key.get(key_prefix, 0) + 1

    def _log_error(
        self,
        error: Exception,
        error_type: ErrorType,
        context: ErrorContext,
        error_message: Optional[str],
    ):
        """Log error với structured format."""
        log_data = {
            "error_type": error_type.value,
            "error_class": type(error).__name__,
            "error_message": error_message or str(error),
            "chunk_id": context.chunk_id,
            "worker_id": context.worker_id,
            "model": context.model,
            "retry_count": context.retry_count,
            "timestamp": datetime.fromtimestamp(context.timestamp).isoformat(),
        }

        # Log level based on error type
        simplified_msg = self._simplify_error_msg(log_data.get("error_message", ""))
        log_data_simple = log_data.copy()
        log_data_simple["error_message"] = simplified_msg

        if error_type in [ErrorType.INVALID_KEY, ErrorType.QUOTA_EXCEEDED]:
            logger.warning(f"⚠️ Lỗi: {simplified_msg} | Loại: {error_type.value} | Phân đoạn: {context.chunk_id}")
            logger.debug(f"Full error context: {log_data}")
        elif error_type == ErrorType.CONTENT_BLOCKED:
            logger.warning(f"🛡️ Nội dung bị chặn: Phân đoạn {context.chunk_id} | Model: {context.model}")
        else:
            logger.error(f"❌ Lỗi: {simplified_msg} | Loại: {error_type.value}", exc_info=False)
            logger.debug(f"Full error context: {log_data}")

    def _simplify_error_msg(self, msg: str) -> str:
        """Rút gọn error message dài dòng của Gemini API."""
        if not msg:
            return "Lỗi không xác định"

        # Nếu là chuỗi JSON lớn từ Gemini
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            # Tìm thời gian retry nếu có
            import re

            retry_match = re.search(r"retry in ([\d\.]+s)", msg)
            retry_after = retry_match.group(1) if retry_match else "không xác định"
            return f"Hết hạn mức (429 RESOURCE_EXHAUSTED). Thử lại sau {retry_after}."

        if "SAFETY" in msg or "blocked" in msg.lower():
            return "Nội dung bị chặn do quy tắc an toàn."

        if "DEADLINE_EXCEEDED" in msg or "timeout" in msg.lower():
            return "Hết thời gian chờ (Timeout)."

        # Truncate nếu quá dài
        if len(msg) > 150:
            return msg[:147] + "..."

        return msg

    def _determine_recovery_strategy(self, error_type: ErrorType, context: ErrorContext) -> Dict[str, Any]:
        """
        Determine recovery strategy dựa trên error type và context.

        Returns:
            Dict với recovery strategy information
        """
        # Default fallback strategy if not found
        default_strategy = {
            "should_retry": False,
            "cooldown_time": 0,
            "max_retries": 0,
            "fallback_action": None,
        }

        # Get custom strategy từ config (nếu có)
        strategy_key = error_type.value
        if strategy_key in self.recovery_strategies:
            custom_strategy = self.recovery_strategies[strategy_key]
            # Merge with default structure
            merged = default_strategy.copy()
            merged.update(custom_strategy)
            return merged

        # Use module-level default strategies
        if error_type in DEFAULT_RECOVERY_STRATEGIES:
            return DEFAULT_RECOVERY_STRATEGIES[error_type]

        # Fallback for completely unknown errors
        return {
            "should_retry": True,
            "cooldown_time": 60,  # 1 minute
            "max_retries": 2,
            "fallback_action": None,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get error metrics summary.

        Returns:
            Dict với error metrics
        """
        return {
            "total_errors": self.metrics.total_errors,
            "errors_by_type": dict(self.metrics.errors_by_type),
            "errors_by_key": dict(self.metrics.errors_by_key),
            "recovery_success": self.metrics.recovery_success,
            "recovery_failure": self.metrics.recovery_failure,
            "recovery_success_rate": (
                self.metrics.recovery_success / max(1, self.metrics.recovery_success + self.metrics.recovery_failure)
            )
            if self.track_metrics
            else 0,
            "last_error_time": (
                datetime.fromtimestamp(self.metrics.last_error_time).isoformat()
                if self.metrics.last_error_time
                else None
            ),
        }

    def reset_metrics(self):
        """Reset error metrics."""
        self.metrics = ErrorMetrics()
        logger.debug("Error metrics reset")
