# -*- coding: utf-8 -*-
"""
Translation Exceptions
======================
Định nghĩa hệ thống ngoại lệ (exceptions) cho module translation.
Giúp chuẩn hóa việc xử lý lỗi và cung cấp thông tin debug chính xác hơn.
"""

class TranslationError(Exception):
    """Base exception class for all translation-related errors."""
    def __init__(self, message: str, context: str = None):
        self.message = message
        self.context = context
        super().__init__(self.message)

class ResourceExhaustedError(TranslationError):
    """Raised when all API keys or quota are exhausted."""
    def __init__(self, message: str = "All API keys or quota exhausted", context: str = None):
        super().__init__(message, context)

class ContentBlockedError(TranslationError):
    """Raised when Gemini API blocks content due to safety filters."""
    def __init__(self, block_reason: str, context: str = None):
        self.block_reason = block_reason
        message = f"Content blocked by safety filters. Reason: {block_reason}"
        super().__init__(message, context)

class APIError(TranslationError):
    """Raised when there's a general API failure (e.g., 500 Internal Server Error)."""
    def __init__(self, message: str, status_code: int = None, context: str = None):
        self.status_code = status_code
        super().__init__(message, context)

class ConfigurationError(TranslationError):
    """Raised when there's an error in translation configuration (e.g., missing model)."""
    def __init__(self, message: str, context: str = None):
        super().__init__(message, context)

class ValidationError(TranslationError):
    """Raised when the translation output fails validation checks."""
    def __init__(self, message: str, chunk_id: int = None, context: str = None):
        self.chunk_id = chunk_id
        super().__init__(message, context)
