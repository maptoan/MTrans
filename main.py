#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
PHIÊN BẢN v1.8.stable - STABLE (Pre-Refactor Managers)
=================================================
Điểm khởi đầu của ứng dụng Novel Translator.

CẢI TIẾN v1.7.stable:
- Workflow mới với review và lựa chọn người dùng (1/2/3)
- Hybrid logic: lưu ngay (as_completed) + báo cáo batch
- Báo cáo tổng thời gian và chunk status chi tiết
- Fix lỗi chunks không được lưu vào progress
- Fix lỗi nhận diện sai số lượng chunk dịch bị xóa
- Fix lỗi option 3 không dịch lại chunks bị xóa
- Fix lỗi tên file chunk không khớp
- Menu lựa chọn ngắn gọn với số 1/2/3

LƯU Ý: Trước khi sửa đổi file này, hãy backup và đánh dấu phiên bản mới!
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import yaml

from src.utils.api_key_validator import validate_api_keys
from src.utils.custom_exceptions import ResourceExhaustedError
from src.utils.logger import setup_main_logger

# --- Constants & Menus ---

ACTIONS_MENU = """
════════════════════════════════════════════════════════════
  DANH MỤC HÀNH ĐỘNG / ACTIONS MENU
════════════════════════════════════════════════════════════
  1. Tiến hành dịch thuật (Start Translation)
  2. Tạo file metadata cho tác phẩm (Generate AI Metadata)
════════════════════════════════════════════════════════════
"""

DOC_TYPE_MENU = """
──────────────────────────────────────────────────
  CHỌN LOẠI TÀI LIỆU / SELECT DOCUMENT TYPE
──────────────────────────────────────────────────
  1. Tiểu thuyết (Novel)
  2. Tài liệu kỹ thuật (Technical Document)
  3. Tài liệu y khoa (Medical Document)
  4. Bài báo học thuật (Academic Paper)
  5. Sách hướng dẫn (Manual)
  6. Tài liệu chung (General)
  7. Phụ đề phim (Subtitle)
  8. Hợp đồng pháp lý (Legal)
  9. Tài chính, kinh tế (Economic)
──────────────────────────────────────────────────
"""

DOC_TYPE_MAP = {
    "1": "novel",
    "2": "technical_doc",
    "3": "medical",
    "4": "academic_paper",
    "5": "manual",
    "6": "general",
    "7": "subtitle",
    "8": "legal",
    "9": "economic",
}


def main_sync() -> Optional[Tuple[Dict[str, Any], List[str]]]:
    """Hàm bao bọc các tác vụ đồng bộ khởi tạo."""
    # Khởi tạo logger chính ngay lập tức
    from src.utils.logger import setup_main_logger

    logger_instance = setup_main_logger(logger_name="NovelTranslator")

    logger_instance.phase("KHỞI TẠO HỆ THỐNG")
    logger_instance.info("Đang tải cấu hình...")

    parser = argparse.ArgumentParser(description="Công cụ dịch tiểu thuyết song song bằng Gemini API.")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Đường dẫn đến tệp cấu hình YAML.")
    args, unknown = parser.parse_known_args()
    if unknown:
        logger_instance.debug(f"Bỏ qua các tham số không xác định: {unknown}")

    try:
        if not os.path.exists(args.config):
            raise FileNotFoundError(f"Không tìm thấy tệp cấu hình tại: {args.config}")
        with open(args.config, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        log_cfg = config.get("logging", {})
        logger_instance.setLevel(log_cfg.get("log_level", "INFO").upper())

        logger_instance.success("Đã tải cấu hình thành công.")

        all_keys = config.get("api_keys", [])
        if not all_keys or not any(k for k in all_keys if "YOUR_GOOGLE_API_KEY" not in k):
            raise ValueError("Chưa có API key nào được điền trong 'config.yaml'.")

        perform_validation = config.get("performance", {}).get("validate_api_keys_on_startup", True)
        use_optimized_workflow = config.get("performance", {}).get("use_optimized_key_workflow", True)
        valid_keys = []

        # Chỉ validate trong main.py nếu KHÔNG dùng optimized workflow
        # (Nếu dùng optimized workflow, sẽ test keys trong translator.py)
        if perform_validation and not use_optimized_workflow:
            logger_instance.check("Đang kiểm tra API key...")
            validation_results = validate_api_keys(all_keys, config)
            valid_keys = validation_results["valid_keys"]
        elif use_optimized_workflow:
            logger_instance.info("Sử dụng Smart Key Discovery (sẽ kiểm tra trong quá trình dịch).")
            valid_keys = [key for key in all_keys if key and "YOUR_GOOGLE_API_KEY" not in key]
        else:
            logger_instance.warning("Bỏ qua bước kiểm tra API key.")
            valid_keys = [key for key in all_keys if key and "YOUR_GOOGLE_API_KEY" not in key]
            logger_instance.info("Sử dụng toàn bộ key có sẵn.")

        if not valid_keys:
            raise ValueError("Không tìm thấy API key nào hợp lệ.")

        logger_instance.success(f"Sẵn sàng với {len(valid_keys)} API keys.")
        return config, valid_keys

    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        logger_instance.critical(f"Lỗi: {e}")
        sys.exit(1)
    except Exception as e:
        logger_instance.exception_detail("Lỗi khởi tạo không mong muốn", e)
        sys.exit(1)


async def main_async(config: Dict[str, Any], valid_keys: List[str]) -> None:
    """Hàm chính điều khiển luồng hoạt động dịch thuật (bất đồng bộ)."""
    # from src.output.formatter import OutputFormatter # Unused here
    from src.preprocessing.input_preprocessor import detect_and_preprocess_input
    from src.services.smart_key_distributor import SmartKeyDistributor
    from src.translation.initialization_service import InitializationService
    from src.translation.translator import NovelTranslator

    logger = logging.getLogger("NovelTranslator")
    app_start_time = datetime.now()

    # Key manager chung cho mọi quy trình dùng AI (metadata, preprocessing, translation)
    shared_key_manager = SmartKeyDistributor(
        api_keys=valid_keys, num_chunks=9999, config=config
    )

    # ---------------------------------------------------------
    # ACTION MENU (Translation vs Metadata Generation)
    # ---------------------------------------------------------
    # [MODIFIED] User requested to disable startup menu -> Default to "1" (Translation)
    # print(ACTIONS_MENU)
    # try:
    #     choice = await asyncio.to_thread(input, "\nNhập lựa chọn (1/2) [Mặc định: 1]: ")
    #     choice = choice.strip() or "1"
    # except (EOFError, KeyboardInterrupt):
    #     return

    choice = "1"
    logger.info("⏩ [TỰ ĐỘNG] Bỏ qua menu hành động -> Tiến hành Dịch thuật.")

    if choice == "2":
        # Sub-menu: Document Type Selection
        print(DOC_TYPE_MENU)

        try:
            doc_choice = await asyncio.to_thread(input, "\nNhập lựa chọn (1-9) [Mặc định: 1]: ")
            doc_choice = doc_choice.strip() or "1"
            document_type = DOC_TYPE_MAP.get(doc_choice, "novel")
        except (EOFError, KeyboardInterrupt):
            return

        logger.info(f"Loại tài liệu đã chọn: {document_type}")

        # Update config with selected document type
        if "metadata" not in config:
            config["metadata"] = {}
        config["metadata"]["document_type"] = document_type

        from src.preprocessing.metadata_generator import MetadataGenerator

        generator = MetadataGenerator(config, valid_keys, key_manager=shared_key_manager)

        should_generate = True
        if generator.check_existing_metadata():
            logger.warning(f"Metadata đã tồn tại trong thư mục {generator.base_metadata_dir}")
            try:
                sub_choice = await asyncio.to_thread(input, "\n[1] Sử dụng file cũ | [2] Tạo mới & Ghi đè: ")
                if sub_choice.strip() != "2":
                    should_generate = False
                    logger.info("Sử dụng metadata hiện có.")
            except (EOFError, KeyboardInterrupt):
                return

        if should_generate:
            # Clear config metadata paths to use auto-generated paths
            # This ensures program ignores manually specified paths in config
            if "input" in config:
                config["input"].pop("glossary_path", None)
                config["input"].pop("style_profile_path", None)
                config["input"].pop("character_relations_path", None)

            success = await generator.generate_all_metadata()
            if success:
                # Update config with newly generated metadata paths
                config["input"] = config.get("input", {})
                config["input"]["glossary_path"] = str(generator.glossary_path)
                config["input"]["style_profile_path"] = str(generator.style_path)
                config["input"]["character_relations_path"] = str(generator.relations_path)
                logger.info("Đã cập nhật đường dẫn metadata trong cấu hình.")

                try:
                    cont = await asyncio.to_thread(
                        input, "\n✅ Metadata đã được tạo. Tiến hành dịch? (y/n) [Mặc định: y]: "
                    )
                    if cont.strip().lower() == "n":
                        logger.info("Tác vụ hoàn tất. Đang thoát.")
                        return
                except (EOFError, KeyboardInterrupt):
                    return
            else:
                logger.error("Tạo Metadata thất bại.")
                return

    # Proceed with normal translation flow
    try:
        # OPTIMIZATION (Phase 4.2): Parallel Initialization
        # Khởi chạy việc khởi tạo tài nguyên chung (Keys, Models...) ở background
        # trong khi đang thực hiện Preprocessing (OCR, File detection...)
        logger.info("🚀 Bắt đầu khởi tạo nền...")
        init_service = InitializationService(config)
        shared_init_task = asyncio.create_task(
            init_service.initialize_shared_resources(valid_keys, existing_key_manager=shared_key_manager)
        )

        # PRE-PROCESS INPUT (OCR integration for scan PDFs)
        try:
            original_novel_path = config["input"]["novel_path"]
        except Exception:
            original_novel_path = None

        if original_novel_path:
            logger.info(f"📁 Tệp đầu vào: {original_novel_path}")
            try:
                # Chạy preprocessing trực tiếp (đã được chuyển thành async def)
                # giúp shared_init_task chạy song song. Truyền key_manager chung để AI cleanup/spell check dùng chung.
                processed_novel_path = await detect_and_preprocess_input(
                    novel_path=original_novel_path,
                    config=config,
                    key_manager=shared_key_manager,
                )

                # Cập nhật config để translator dùng processed path nếu có
                if processed_novel_path != original_novel_path:
                    logger.info(f"✅ Đã xử lý OCR, sử dụng tệp kết quả: {processed_novel_path}")
                    logger.info("📄 Tệp đã xử lý sẽ được dùng cho quy trình dịch thuật")
                else:
                    logger.info(f"📄 Sử dụng tệp gốc: {processed_novel_path}")
                config["input"]["novel_path"] = processed_novel_path
            except KeyboardInterrupt:
                # Nếu user cancel lúc nhập liệu hoặc OCR
                shared_init_task.cancel()
                raise
            except Exception as e:
                logger.error(f"Tiền xử lý đầu vào thất bại (tích hợp OCR): {e}")
                # Vẫn tiếp tục với đường dẫn gốc nếu có lỗi tiền xử lý
                if original_novel_path:
                    config["input"]["novel_path"] = original_novel_path
                    logger.warning(f"⚠️  Sử dụng tệp gốc: {original_novel_path}")

        # Đợi khởi tạo tài nguyên chung hoàn tất
        logger.info("⏳ Đang đợi khởi tạo tài nguyên chung...")
        try:
            shared_resources = await shared_init_task
        except Exception as e:
            logger.error(f"Thiết lập tài nguyên ban đầu thất bại: {e}")
            raise e

        logger.info(f"🚀 Khởi tạo NovelTranslator với tệp: {config['input']['novel_path']}")
        translator = NovelTranslator(config, valid_keys)

        # Inject pre-initialized resources
        await translator.setup_resources_async(shared_resources)

        while True:
            logger.translate("Bắt đầu chu kỳ dịch tiểu thuyết...")

            try:
                failed_chunks, docx_path = await translator.run_translation_cycle_with_review()
            except KeyboardInterrupt:
                logger.warning("\n⚠️ Đã nhận tín hiệu ngắt (Ctrl+C) trong quá trình dịch. Đang dừng...")
                # Flush progress nếu có thể
                try:
                    if hasattr(translator, "progress_manager"):
                        translator.progress_manager.flush_all()
                except Exception:
                    pass
                raise

            # CRITICAL: Chỉ báo thành công nếu không có failed chunks VÀ có đường dẫn output
            # (docx_path/master_path không None có nghĩa là merge/convert/layout-reinject thành công)
            if not failed_chunks and docx_path:
                logger.success("✅ 100% các phân đoạn đã được dịch thành công!")

                # Workflow mới đã xử lý tất cả (convert epub nếu cần)
                translation_end_time = datetime.now()
                total_duration = translation_end_time - app_start_time
                logger.success("🎉 QUÁ TRÌNH DỊCH THUẬT HOÀN TẤT!")
                logger.info(f"Tệp đầu vào: {config['input']['novel_path']}")
                logger.info(f"Tổng thời gian: {str(total_duration).split('.')[0]}")
            else:
                # Có failed chunks → báo lỗi và dừng
                logger.error("")
                logger.error("=" * 60)
                logger.error("❌ QUÁ TRÌNH DỊCH THUẬT KHÔNG HOÀN TẤT!")
                logger.error(f"Có {len(failed_chunks)} phân đoạn thất bại sau khi thử lại")
                logger.error("Vui lòng kiểm tra nhật ký (logs) và thử lại")
                logger.error("=" * 60)

            break

    except KeyboardInterrupt:
        # Re-raise để main handler xử lý
        raise
    except Exception as e:
        logger.critical(f"Lỗi không mong muốn trong quá trình dịch: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup: Đảm bảo tất cả async clients được đóng và tasks được cancel
        try:
            # 1. Cancel all pending tasks
            pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            if pending:
                logger.info(f"🛑 Đang dừng {len(pending)} tác vụ đang chạy...")
                for task in pending:
                    task.cancel()

                # Wait for cancellation to complete với timeout để tránh treo vô hạn
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*pending, return_exceptions=True),
                        timeout=30,
                    )
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Hủy tác vụ mất quá 30s, tiếp tục shutdown mà không chờ thêm.")

            # 2. Cleanup translator resources
            if "translator" in locals() and translator:
                if hasattr(translator, "gemini_service"):
                    try:
                        # Close gemini service if needed
                        pass
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Lỗi dọn dẹp (không nghiêm trọng): {e}")

        logger.info("👋 Kết thúc chương trình dịch thuật.")


_shutdown_requested = False
_shutdown_first_signal_time: Optional[datetime] = None


def _signal_handler(signum, frame):
    """
    Handle SIGINT (Ctrl+C) và SIGTERM signals.

    Lần đầu: kích hoạt shutdown an toàn (raise KeyboardInterrupt).
    Lần thứ hai: force exit ngay lập tức để tránh treo nếu cleanup bị kẹt.
    """
    import os as _os  # tránh shadow os global

    global _shutdown_requested, _shutdown_first_signal_time
    logger = logging.getLogger("NovelTranslator")

    if _shutdown_requested:
        logger.warning("⚠️ Đã nhận Ctrl+C lần thứ hai → Thoát ngay lập tức.")
        _os._exit(130)

    _shutdown_requested = True
    _shutdown_first_signal_time = datetime.now()
    logger.warning("\n⚠️ Đã nhận tín hiệu ngắt (Ctrl+C). Đang dừng chương trình...")
    raise KeyboardInterrupt("Chương trình bị hủy bởi người dùng (Ctrl+C)")


if __name__ == "__main__":
    # Register signal handlers để handle Ctrl+C đúng cách
    try:
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except (ValueError, OSError) as e:
        # Signal handlers chỉ hoạt động trong main thread
        logger = logging.getLogger("NovelTranslator")
        logger.debug(f"Không thể đăng ký signal handlers: {e}")

    try:
        result = main_sync()
        if result:
            config, valid_keys = result
            asyncio.run(main_async(config, valid_keys))
    except KeyboardInterrupt:
        logger = logging.getLogger("NovelTranslator")
        logger.warning("\n⚠️ Chương trình đã bị hủy bởi người dùng (Ctrl+C).")
        logger.info("Đang lưu tiến độ hiện tại...")
        sys.exit(130)
    except ResourceExhaustedError as e:
        logger = logging.getLogger("NovelTranslator")
        logger.error(f"\n❌ {e}")
        logger.info("💡 Gợi ý: Hãy chờ một lát rồi thử lại, hoặc thêm API Key mới vào config.yaml.")
        sys.exit(1)
    except Exception as e:
        logger = logging.getLogger("NovelTranslator")
        logger.critical(f"❌ Lỗi nghiêm trọng không mong muốn: {e}")
        logger.debug("Chi tiết lỗi:", exc_info=True)
        print(f"\n❌ CHƯƠNG TRÌNH GẶP LỖI: {e}")
        print("Vui lòng kiểm tra tệp log để biết thêm chi tiết.")
        sys.exit(1)
