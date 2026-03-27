"""
Log filter module để loại bỏ các log gây nhiễu từ thư viện bên thứ ba.

Các chức năng chính:
- Lọc log từ Google API/GCP
- Lọc log từ urllib3, requests
- Lọc các system messages không cần thiết
"""

import logging
import re
from typing import List

logger = logging.getLogger("NovelTranslator")


class LogNoiseFilter(logging.Filter):
    """
    Filter để loại bỏ log gây nhiễu từ các thư viện bên thứ ba.

    Sử dụng regex patterns để phát hiện và loại bỏ các log messages
    không cần thiết từ Google API, GCP, urllib3, requests, etc.
    """

    def __init__(self) -> None:
        """
        Khởi tạo filter với các noise patterns đã compile.
        """
        super().__init__()

        # Các pattern gây nhiễu cần lọc
        self.noise_patterns: List[str] = [
            # Google API/GCP logs
            r"E0000.*alts_credentials\.cc.*ALTS.*GCP",
            r"alts_credentials\.cc.*ALTS.*untrusted",
            r"GCP.*untrusted.*ALTS",
            r"E0000.*00:00:.*alts_credentials\.cc.*ALTS.*ignored",
            # System logs không cần thiết
            r"DEBUG.*urllib3",
            r"DEBUG.*requests",
            r"DEBUG.*google",
            r"INFO.*google",
            r"WARNING.*urllib3",
            r"WARNING.*requests",
            # Other noise
            r"Using.*credentials",
            r"Loading.*credentials",
            r"Token.*refresh",
            r"API.*key.*validation",
            r"Authentication.*successful",
            r"Connection.*established",
            r"Request.*completed",
            # Verbose system messages
            r"Starting.*process",
            r"Process.*started",
            r"Initializing.*module",
            r"Module.*initialized",
        ]

        # Compile patterns để tăng tốc
        self.compiled_patterns: List[re.Pattern[str]] = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.noise_patterns
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Lọc log record dựa trên noise patterns.

        Args:
            record: LogRecord từ logging system

        Returns:
            False nếu log bị lọc (loại bỏ), True nếu giữ lại
        """
        message = record.getMessage()

        # Kiểm tra từng pattern
        for pattern in self.compiled_patterns:
            if pattern.search(message):
                return False  # Loại bỏ log này

        return True  # Giữ lại log này


def setup_clean_logging() -> logging.Logger:
    """
    Thiết lập logging sạch sẽ bằng cách áp dụng LogNoiseFilter.

    Áp dụng filter cho tất cả root handlers và tạo một logger mới
    với filter đã được cấu hình.

    Returns:
        Logger đã được cấu hình với noise filter

    Example:
        >>> clean_logger = setup_clean_logging()
        >>> clean_logger.info("This will be logged")
        >>> # Logs từ Google API sẽ bị lọc
    """
    # Tạo filter
    noise_filter = LogNoiseFilter()

    # Áp dụng filter cho tất cả handlers
    for handler in logging.root.handlers:
        handler.addFilter(noise_filter)

    # Tạo logger mới với filter
    clean_logger = logging.getLogger("clean_logger")
    clean_logger.addFilter(noise_filter)

    return clean_logger


