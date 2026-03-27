# -*- coding: utf-8 -*-
"""
Menu Handler for OCR Completion.
Handles user interaction after OCR processing completes.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("NovelTranslator")


def _show_completion_menu(
    cleanup_failed: int, spell_check_failed: int, output_path: str = None
) -> str:
    """
    Hiển thị menu lựa chọn sau khi OCR hoàn tất.
    
    Args:
        cleanup_failed: Số chunks AI Cleanup thất bại
        spell_check_failed: Số chunks AI Spell Check thất bại
        output_path: Đường dẫn file output (không sử dụng hiện tại)
        
    Returns:
        str: 'retry', 'save', hoặc 'exit'
    """
    has_failures = cleanup_failed > 0 or spell_check_failed > 0
    user_choice = None
    user_choice_lock = threading.Lock()
    user_choice_done = threading.Event()
    input_available = threading.Event()
    input_line = None
    input_lock = threading.Lock()

    def _auto_save_timer():
        nonlocal user_choice
        time.sleep(600)  # 10 phút = 600 giây
        with user_choice_lock:
            if user_choice is None:
                logger.info("\nTu dong luu file sau 10 phut...")
                user_choice = "save"
                user_choice_done.set()
                input_available.set()  # Đánh thức thread đọc input nếu đang chờ

    def _read_input_thread():
        """Thread đọc input từ stdin"""
        nonlocal input_line
        try:
            # Đọc input trong thread riêng để không block main thread
            line = input("\nNhap lua chon: ").strip()
            with input_lock:
                input_line = line
                input_available.set()
        except (EOFError, KeyboardInterrupt):
            with input_lock:
                input_line = "1"  # Mặc định save
                input_available.set()
        except Exception:
            with input_lock:
                input_line = None
                input_available.set()

    auto_save_thread = threading.Thread(target=_auto_save_timer, daemon=True)
    auto_save_thread.start()

    if not has_failures:
        # Không có lỗi, chỉ có option save/exit
        logger.info("\n" + "=" * 80)
        logger.info("OCR hoan tat khong co loi!")
        logger.info("=" * 80)
        logger.info("Lua chon:")
        logger.info("  1. Luu file (tu dong luu sau 10 phut neu khong chon)")
        logger.info("  2. Thoat khong luu")
        logger.info("=" * 80)

        while not user_choice_done.is_set():
            try:
                # Khởi động thread đọc input
                input_thread = threading.Thread(target=_read_input_thread, daemon=True)
                input_thread.start()

                # Đợi input hoặc auto-save (kiểm tra mỗi 0.5 giây)
                while not user_choice_done.is_set() and not input_available.is_set():
                    time.sleep(0.5)

                # Kiểm tra xem có input hay auto-save đã trigger
                if user_choice_done.is_set():
                    break  # Auto-save đã trigger

                # Có input, xử lý
                with input_lock:
                    choice = input_line
                    input_line = None
                    input_available.clear()

                if choice:
                    with user_choice_lock:
                        if choice == "1":
                            user_choice = "save"
                            user_choice_done.set()
                            break
                        elif choice == "2":
                            user_choice = "exit"
                            user_choice_done.set()
                            break
                        else:
                            logger.warning(
                                "Lua chon khong hop le. Vui long nhap 1 hoac 2."
                            )
            except (EOFError, KeyboardInterrupt):
                with user_choice_lock:
                    user_choice = "save"
                    user_choice_done.set()
                break
    else:
        # Có lỗi, hiển thị đầy đủ 3 options
        logger.info("\n" + "=" * 80)
        logger.info("OCR hoan tat voi mot so loi:")
        if cleanup_failed > 0:
            logger.info(f"  - AI Cleanup: {cleanup_failed} chunks failed")
        if spell_check_failed > 0:
            logger.info(f"  - AI Spell Check: {spell_check_failed} chunks failed")
        logger.info("=" * 80)
        logger.info("Lua chon:")
        logger.info("  1. Retry cac chunk failed")
        logger.info("  2. Luu file (tu dong luu sau 10 phut neu khong chon)")
        logger.info("  3. Thoat khong luu")
        logger.info("=" * 80)

        while not user_choice_done.is_set():
            try:
                # Khởi động thread đọc input
                input_thread = threading.Thread(target=_read_input_thread, daemon=True)
                input_thread.start()

                # Đợi input hoặc auto-save (kiểm tra mỗi 0.5 giây)
                while not user_choice_done.is_set() and not input_available.is_set():
                    time.sleep(0.5)

                # Kiểm tra xem có input hay auto-save đã trigger
                if user_choice_done.is_set():
                    break  # Auto-save đã trigger

                # Có input, xử lý
                with input_lock:
                    choice = input_line
                    input_line = None
                    input_available.clear()

                if choice:
                    with user_choice_lock:
                        if choice == "1":
                            user_choice = "retry"
                            user_choice_done.set()
                            break
                        elif choice == "2":
                            user_choice = "save"
                            user_choice_done.set()
                            break
                        elif choice == "3":
                            user_choice = "exit"
                            user_choice_done.set()
                            break
                        else:
                            logger.warning(
                                "Lua chon khong hop le. Vui long nhap 1, 2 hoac 3."
                            )
            except (EOFError, KeyboardInterrupt):
                with user_choice_lock:
                    user_choice = "save"
                    user_choice_done.set()
                break

    # Đợi user chọn hoặc auto-save (nếu chưa có)
    if not user_choice_done.is_set():
        user_choice_done.wait()
    return user_choice if user_choice else "save"
