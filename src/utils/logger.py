# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Module Logger chuyên dụng với đầy đủ tính năng.

Các chức năng chính:
- Log rotation tự động (time-based hoặc size-based)
- Cleanup handlers an toàn
- Performance monitoring
- Exception tracking với traceback đầy đủ
- Flexible configuration (console/file levels riêng biệt)
- Icon-based logging để dễ đọc
- Colored logging (nếu colorlog được cài đặt)
"""

import contextvars
import io
import logging
import os
import sys
import time
import traceback
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Any, Dict, Generator, List, Optional, Type, Union

# Các icon để làm cho log trực quan hơn
LOG_ICONS: Dict[str, str] = {
    "INFO": "✓",
    "SUCCESS": "✨",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🔥",
    "DEBUG": "🐞",
    "START": "🚀",
    "END": "🏁",
    "CHECK": "🔍",
    "SAVE": "💾",
    "LOAD": "📥",
    "TRANSLATE": "🌐",
    "PROMPT": "📝",
    "TIMER": "⏱️",
    "MEMORY": "💭",
    "PROGRESS": "📊",
    "PHASE": "💠",
}

# ContextVar for async-safe context logging
# Default value is an empty list
_context_stack = contextvars.ContextVar("logging_context_stack", default=[])


def get_current_context() -> str:
    """Lấy context hiện tại của task/thread."""
    stack = _context_stack.get()

    if not stack:
        return ""

    # Format: [Item1][Item2]
    return "".join(f"[{item}]" for item in stack)


@contextmanager
def log_context(context_id: Union[str, int], *args) -> Generator[None, None, None]:
    """
    Context manager để tự động thêm prefix vào log.
    Async-safe (sử dụng contextvars).

    Example:
        with log_context("Worker-1"):
            logger.info("Starting...") # Log: [Worker-1] Starting...
    """
    if not isinstance(context_id, (str, int)) and args:
        # Probable call: logger.context(actual_id) -> log_context(logger, actual_id)
        context_id = args[0]

    # Get current stack (immutable list copy required for async safety)
    current_stack = _context_stack.get()

    # Create new stack with appended item
    new_stack = current_stack + [str(context_id)]

    # Set context var and get token to reset later
    token = _context_stack.set(new_stack)

    try:
        yield
    finally:
        # Reset to previous state (removes the added item)
        _context_stack.reset(token)


FormatterBase: Type[logging.Formatter] = logging.Formatter
colorlog_imported: bool = False

try:
    from colorlog import ColoredFormatter

    FormatterBase = ColoredFormatter  # type: ignore
    colorlog_imported = True
except ImportError:
    pass


class IconFormatter(FormatterBase):  # type: ignore
    """
    Formatter tùy chỉnh để thêm icon và format log đẹp hơn.

    Tự động thêm icon dựa trên log level hoặc custom icon từ extra['icon_override'].
    Hỗ trợ cả ColoredFormatter (nếu colorlog được cài đặt) và Formatter thông thường.
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = "%",
        **kwargs: Any,
    ) -> None:
        """
        Khởi tạo IconFormatter.

        Args:
            fmt: Format string cho log message
            datefmt: Format string cho date/time
            style: Style cho format string ('%', '{', hoặc '$')
            **kwargs: Additional arguments cho Formatter/ColoredFormatter
        """
        if not colorlog_imported:
            kwargs.pop("log_colors", None)
            kwargs.pop("reset", None)
        super().__init__(fmt, datefmt, style, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record với icon.

        Args:
            record: LogRecord từ logging system

        Returns:
            Formatted log message string
        """
        record.icon = LOG_ICONS.get(record.levelname, "•")
        if hasattr(record, "icon_override"):
            record.icon = record.icon_override

        # Thêm context tự động nếu có
        context = get_current_context()
        if context:
            record.msg = f"{context} {record.msg}"

        return super().format(record)


class PerformanceFilter(logging.Filter):
    """
    Filter để theo dõi performance - chỉ log WARNING nếu quá chậm.

    Nếu log record có attribute 'duration_ms' và vượt quá threshold,
    sẽ nâng log level lên WARNING để cảnh báo.
    """

    def __init__(self, threshold_ms: float = 1000.0) -> None:
        """
        Khởi tạo PerformanceFilter.

        Args:
            threshold_ms: Ngưỡng thời gian (milliseconds) để nâng lên WARNING
        """
        super().__init__()
        self.threshold_ms: float = threshold_ms

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record dựa trên performance.

        Args:
            record: LogRecord từ logging system

        Returns:
            True nếu log được giữ lại, False nếu bị lọc
        """
        if hasattr(record, "duration_ms"):
            if record.duration_ms > self.threshold_ms:
                record.levelno = logging.WARNING
                record.levelname = "WARNING"
            return True
        return True


class SystemNoiseFilter(logging.Filter):
    """
    Filter để loại bỏ các log hệ thống không hữu ích cho người dùng cuối.

    Ví dụ: spam từ Adaptive Flow Control (AFC) của SDK:
    "[INFO] AFC is enabled with max remote calls: 10."
    """

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        # Ẩn các thông báo AFC không mang giá trị cho user
        if "AFC is enabled with max remote calls" in message:
            return False

        return True


class StdoutNoiseFilter:
    """
    Wrapper cho sys.stdout để chặn một số dòng log rác in trực tiếp (không đi qua logging).

    Hiện tại dùng để chặn:
    "[INFO] AFC is enabled with max remote calls: 10."
    từ Adaptive Flow Control của SDK.
    """

    def __init__(self, original):
        self._original = original
        self._afc_filter_enabled = True

    def write(self, s: str) -> int:  # type: ignore[override]
        if "AFC is enabled with max remote calls" in s:
            # Nuốt log rác, giả vờ đã ghi đủ độ dài để tránh lỗi caller
            return len(s)
        return self._original.write(s)

    def flush(self) -> None:  # type: ignore[override]
        return self._original.flush()

    def isatty(self) -> bool:  # type: ignore[override]
        return getattr(self._original, "isatty", lambda: False)()

    def fileno(self):  # type: ignore[override]
        return getattr(self._original, "fileno", lambda: -1)()


class StderrNoiseFilter:
    """
    Wrapper tương tự cho sys.stderr để chặn log rác in trực tiếp ra stderr.
    """

    def __init__(self, original):
        self._original = original

    def write(self, s: str) -> int:  # type: ignore[override]
        if "AFC is enabled with max remote calls" in s:
            return len(s)
        return self._original.write(s)

    def flush(self) -> None:  # type: ignore[override]
        return self._original.flush()

    def isatty(self) -> bool:  # type: ignore[override]
        return getattr(self._original, "isatty", lambda: False)()

    def fileno(self):  # type: ignore[override]
        return getattr(self._original, "fileno", lambda: -1)()


@contextmanager
def suppress_library_logging(*library_names: str) -> Generator[None, None, None]:
    """
    Context manager tổng quát để chặn log từ nhiều thư viện.

    Tạm thời set log level của các thư viện lên CRITICAL để chặn log,
    sau đó khôi phục lại level ban đầu.

    Args:
        *library_names: Tên các thư viện cần chặn log (ví dụ: 'grpc', 'httpx')

    Yields:
        None

    Example:
        >>> with suppress_library_logging('grpc', 'httpx', 'urllib3'):
        ...     # Code của bạn - logs từ các thư viện này sẽ bị chặn
        ...     pass
    """
    loggers: List[logging.Logger] = [logging.getLogger(name) for name in library_names]
    original_levels: List[int] = [logger.level for logger in loggers]

    try:
        for logger in loggers:
            logger.setLevel(logging.CRITICAL)
        yield
    finally:
        for logger, level in zip(loggers, original_levels):
            logger.setLevel(level)


def setup_main_logger(
    logger_name: str = "NovelTranslator",
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    console_level: Optional[int] = None,
    file_level: Optional[int] = None,
    max_file_size_mb: int = 20,
    backup_count: int = 10,
    enable_rotation: bool = True,
    rotation_when: str = "midnight",  # 'midnight', 'h', 'd', 'w0'-'w6'
    enable_performance_tracking: bool = False,
) -> logging.Logger:
    """
    Thiết lập logger với cấu hình toàn diện.

    Args:
        logger_name: Tên logger (mặc định "NovelTranslator")
        log_dir: Thư mục chứa log files
        log_level: Mức log chung
        console_level: Mức log riêng cho console (None = dùng log_level)
        file_level: Mức log riêng cho file (None = dùng log_level)
        max_file_size_mb: Kích thước tối đa file log (MB) trước khi rotate
        backup_count: Số lượng file backup giữ lại
        enable_rotation: Bật log rotation theo thời gian
        rotation_when: Chu kỳ rotation ('midnight', 'h', 'd')
        enable_performance_tracking: Bật theo dõi performance

    Returns:
        Logger đã được cấu hình
    """
    logger = logging.getLogger(logger_name)

    # Cleanup handlers cũ nếu đã tồn tại
    if logger.hasHandlers():
        for handler in logger.handlers[:]:
            try:
                # Tránh đóng standard streams
                if isinstance(handler, logging.StreamHandler):
                    if handler.stream in (sys.stdout, sys.stderr):
                        handler.flush()
                        logger.removeHandler(handler)
                        continue
                handler.close()
                logger.removeHandler(handler)
            except Exception:
                logger.removeHandler(handler)

    logger.setLevel(log_level)

    # Xác định level riêng cho mỗi handler
    _console_level = console_level if console_level is not None else log_level
    _file_level = file_level if file_level is not None else log_level

    # ===== CONSOLE HANDLER =====
    # On Windows, use UTF-8 encoding to support emojis and Chinese characters
    if sys.platform == "win32":
        try:
            # Safer than wrapping in TextIOWrapper which might close the stream
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, io.UnsupportedOperation):
            pass

    # Áp dụng Stdout/StderrNoiseFilter một lần để chặn log rác in trực tiếp
    try:
        if not isinstance(sys.stdout, StdoutNoiseFilter):
            sys.stdout = StdoutNoiseFilter(sys.stdout)  # type: ignore[assignment]
        if not isinstance(sys.stderr, StderrNoiseFilter):
            sys.stderr = StderrNoiseFilter(sys.stderr)  # type: ignore[assignment]
    except Exception:
        # Không chặn nếu môi trường không cho phép override stdout
        pass

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_console_level)

    color_format = " %(log_color)s%(asctime)s - %(icon)s %(message)s%(reset)s"
    basic_format = " %(asctime)s - %(icon)s %(message)s"

    if colorlog_imported:
        console_formatter = IconFormatter(
            color_format,
            datefmt="%H:%M:%S",
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "white",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
    else:
        console_formatter = IconFormatter(basic_format, datefmt="%H:%M:%S")

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # ===== FILE HANDLER với ROTATION =====
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"{logger_name}.log"
    log_path = os.path.join(log_dir, log_filename)

    if enable_rotation:
        # Sử dụng TimedRotatingFileHandler để rotate theo thời gian
        file_handler = TimedRotatingFileHandler(
            log_path,
            when=rotation_when,
            interval=1,
            backupCount=backup_count,
            encoding="utf-8",
        )
    else:
        # Sử dụng RotatingFileHandler để rotate theo kích thước
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )

    file_handler.setLevel(_file_level)

    file_format = "%(asctime)s - %(levelname)-8s - %(name)s:%(lineno)d - %(message)s"
    file_formatter = logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_formatter)

    # ===== NOISE FILTERS =====
    # Ẩn một số log hệ thống không hữu ích (như AFC spam) trên cả console, file và root logger.
    system_noise_filter = SystemNoiseFilter()
    console_handler.addFilter(system_noise_filter)
    file_handler.addFilter(system_noise_filter)

    # Đồng thời áp dụng cho root logger để chặn các log từ thư viện ngoài
    root_logger = logging.getLogger()
    root_logger.addFilter(system_noise_filter)
    for handler in root_logger.handlers:
        handler.addFilter(system_noise_filter)

    # Thêm performance filter nếu được bật
    if enable_performance_tracking:
        file_handler.addFilter(PerformanceFilter())

    logger.addHandler(file_handler)
    logger.propagate = False  # Prevent duplicate logs from root logger

    # ===== EXTERNAL LIBRARY LOGGING (SUPPRESS NOISE) =====
    # [v7.6] Suppress repetitive INFO logs from Google GenAI SDK
    logging.getLogger("google.genai").setLevel(logging.WARNING)
    logging.getLogger("google.ai").setLevel(logging.WARNING)
    # Suppress HTTP request logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    # Suppress gRPC logs
    logging.getLogger("grpc").setLevel(logging.ERROR)

    return logger


def patch_logger(logger: Optional[logging.Logger] = None) -> None:
    """
    Patch logging.Logger class (hoặc instance cụ thể) với các method tiện ích.

    Args:
        logger: Nếu được cung cấp, chỉ patch instance này.
                Nếu None, patch class logging.Logger (ảnh hưởng tất cả loggers).
    """
    target = logger if logger is not None else logging.Logger

    # Define all custom methods as class-compatible functions
    def _log_with_icon(self, level, icon_key, msg, *args, **kwargs):
        extra = kwargs.get("extra", {})
        extra["icon_override"] = LOG_ICONS.get(icon_key, "•")
        kwargs["extra"] = extra
        self.log(level, msg, *args, **kwargs)

    def _success(self, msg, *args, **kwargs):
        _log_with_icon(self, logging.INFO, "SUCCESS", msg, *args, **kwargs)

    def _start(self, msg, *args, **kwargs):
        _log_with_icon(self, logging.INFO, "START", msg, *args, **kwargs)

    def _end(self, msg, *args, **kwargs):
        _log_with_icon(self, logging.INFO, "END", msg, *args, **kwargs)

    def _check(self, msg, *args, **kwargs):
        _log_with_icon(self, logging.INFO, "CHECK", msg, *args, **kwargs)

    def _save(self, msg, *args, **kwargs):
        _log_with_icon(self, logging.INFO, "SAVE", msg, *args, **kwargs)

    def _load(self, msg, *args, **kwargs):
        _log_with_icon(self, logging.INFO, "LOAD", msg, *args, **kwargs)

    def _translate(self, msg, *args, **kwargs):
        _log_with_icon(self, logging.INFO, "TRANSLATE", msg, *args, **kwargs)

    def _prompt(self, msg, *args, **kwargs):
        _log_with_icon(self, logging.DEBUG, "PROMPT", msg, *args, **kwargs)

    def _timer(self, msg, *args, **kwargs):
        _log_with_icon(self, logging.INFO, "TIMER", msg, *args, **kwargs)

    def _memory(self, msg, *args, **kwargs):
        _log_with_icon(self, logging.DEBUG, "MEMORY", msg, *args, **kwargs)

    def _perf(
        self,
        operation: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        msg = f"{operation} hoàn thành trong {duration_ms:.2f}ms"
        if details:
            msg += f" | {details}"
        _log_with_icon(self, logging.INFO, "TIMER", msg)

    def _progress(
        self, current: int, total: int, msg: str, duration: Optional[float] = None
    ):
        """Log tiến độ dạng: [Tiến độ] [10/50] Message (2.5s)"""
        time_str = f" ({duration:.2f}s)" if duration is not None else ""
        full_msg = f"[Tiến độ] [{current}/{total}] {msg}{time_str}"
        _log_with_icon(self, logging.INFO, "PROGRESS", full_msg)

    def _phase(self, name: str, status: str = "Bắt đầu"):
        """Log phân đoạn công việc."""
        _log_with_icon(self, logging.INFO, "PHASE", f"═══ {name.upper()}: {status} ═══")

    def _exception_detail(
        self, msg: str, exc: Optional[Exception] = None, **kwargs: Any
    ) -> None:
        extra = kwargs.get("extra", {})
        extra["icon_override"] = LOG_ICONS["ERROR"]
        kwargs["extra"] = extra

        if exc:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            full_msg = f"{msg}\n{tb}"
        else:
            full_msg = f"{msg}\n{traceback.format_exc()}"

        self.error(full_msg, **kwargs)

    def _perf(
        self,
        operation: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        extra: Dict[str, Any] = {
            "icon_override": LOG_ICONS["TIMER"],
            "duration_ms": duration_ms,
        }

        msg = f"{operation} hoàn thành trong {duration_ms:.2f}ms"
        if details:
            msg += f" | {details}"

        self.info(msg, extra=extra)

    # Apply patches to class or instance
    target.success = _success
    target.start = _start
    target.end = _end
    target.check = _check
    target.save = _save
    target.load = _load
    target.translate = _translate
    target.prompt = _prompt
    target.timer = _timer
    target.memory = _memory
    target.exception_detail = _exception_detail
    target.perf = _perf
    target.progress = _progress
    target.phase = _phase
    target.context = log_context

    # Also ensure propagate is False by default for our loggers if needed
    if not isinstance(target, type):
        target.propagate = False

    return target


@contextmanager
def log_performance_context(
    logger: logging.Logger, operation: str
) -> Generator[None, None, None]:
    """
    Context manager để tự động đo và log performance.

    Tự động đo thời gian thực thi của code block và log kết quả.

    Args:
        logger: Logger instance để log performance
        operation: Tên operation đang được đo

    Yields:
        None

    Example:
        >>> with log_performance_context(logger, "Dịch chunk"):
        ...     # Code của bạn
        ...     translate_chunk(chunk)
        # Sẽ tự động log: "Dịch chunk hoàn thành trong 123.45ms"
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.perf(operation, duration_ms)  # type: ignore


# Alias cho suppress_grpc_logging để tương thích ngược
@contextmanager
def suppress_grpc_logging() -> Generator[None, None, None]:
    """
    Context manager để chặn log từ gRPC library.

    Tương thích ngược với code cũ. Sử dụng suppress_library_logging('grpc').

    Yields:
        None

    Example:
        >>> with suppress_grpc_logging():
        ...     # Code sử dụng gRPC - logs sẽ bị chặn
        ...     pass
    """
    with suppress_library_logging("grpc"):
        yield


# Tự động patch khi import module này
patch_logger()
