import os
import sys

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import sys

from src.utils.logger import SystemNoiseFilter, setup_main_logger


def test_enhanced_logging():
    # Setup logger
    logger = setup_main_logger(logger_name="TestLogger", log_dir="logs_test")
    logger.setLevel(logging.DEBUG)

    print("--- Testing Enhanced Logging Features ---\n")

    # Test Phase
    logger.phase("KHỞI TẠO", "Bắt đầu")

    # Test Normal Levels
    logger.info("Đây là log INFO bình thường")
    logger.success("Đây là log SUCCESS (✨)")
    logger.warning("Đây là cảnh báo (⚠️)")

    # Test Progress
    logger.phase("TIẾN TRÌNH DỊCH")
    for i in range(1, 4):
        logger.progress(i, 3, f"Đang xử lý chunk {i}", duration=0.5 * i)

    # Test Context-aware logging
    logger.phase("NGỮ CẢNH (CONTEXT)")
    with logger.context("Worker-1"):
        logger.info("Worker 1 bắt đầu làm việc")
        with logger.context("Chunk-101"):
            logger.start("Bắt đầu dịch chunk 101")
            logger.debug("Dữ liệu trung gian...")
            logger.success("Hoàn thành chunk 101")
        logger.info("Worker 1 nghỉ ngơi")

    logger.phase("KẾT THÚC", "Thành công")
    logger.end("Hệ thống dừng.")


def test_system_noise_filter_hides_afc_logs():
    """
    Đảm bảo SystemNoiseFilter ẩn được các log kiểu:
    "[INFO] AFC is enabled with max remote calls: 10."
    """
    noise_filter = SystemNoiseFilter()

    # Log AFC spam cần bị loại bỏ
    afc_record = logging.LogRecord(
        name="google.genai.afc",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="AFC is enabled with max remote calls: 10.",
        args=(),
        exc_info=None,
    )
    assert noise_filter.filter(afc_record) is False

    # Log bình thường vẫn phải được giữ lại
    normal_record = logging.LogRecord(
        name="NovelTranslator",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="Dịch chunk 1/10 thành công",
        args=(),
        exc_info=None,
    )
    assert noise_filter.filter(normal_record) is True

if __name__ == "__main__":
    test_enhanced_logging()
