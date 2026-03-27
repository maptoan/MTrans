# -*- coding: utf-8 -*-

"""
UI Handler
==========
[Phase 8B] Manages user interaction and menu handling.

Extracted from NovelTranslator to reduce translator.py size.

Responsibilities:
- Display user option menus
- Handle user input with timeouts
- Coordinate format conversion choices
- Manage retry workflows

PHIÊN BẢN: v8.0+
"""

import asyncio
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")


class UIHandler:
    """
    [Phase 8B] Manages user interaction and menu handling.

    Uses threading for input with timeout support.
    Delegates conversion operations to translator instance.
    """

    def __init__(
        self,
        output_formatter: Any,
        novel_name: str,
        config: Dict[str, Any],
    ):
        """
        Initialize UIHandler.

        Args:
            output_formatter: OutputFormatter instance for saving files.
            novel_name: Name of the novel being translated.
            config: Configuration dictionary.
        """
        self.output_formatter = output_formatter
        self.novel_name = novel_name
        self.config = config

        # Callbacks to translator methods (set via set_callbacks)
        self._convert_to_epub: Optional[Callable] = None
        self._convert_to_docx: Optional[Callable] = None
        self._convert_to_pdf: Optional[Callable] = None
        self._merge_all_chunks: Optional[Callable] = None
        self._translate_all_chunks: Optional[Callable] = None
        self._find_deleted_chunks: Optional[Callable] = None
        self._progress_manager: Optional[Any] = None
        self._export_master_html_to_epub: Optional[Callable] = None

    def set_callbacks(
        self,
        convert_to_epub: Callable,
        convert_to_docx: Callable,
        convert_to_pdf: Callable,
        merge_all_chunks: Callable,
        translate_all_chunks: Callable,
        find_deleted_chunks: Callable,
        progress_manager: Any,
        *,
        export_master_html_to_epub: Optional[Callable] = None,
    ) -> None:
        """Set callback functions that delegate to translator methods."""
        self._convert_to_epub = convert_to_epub
        self._convert_to_docx = convert_to_docx
        self._convert_to_pdf = convert_to_pdf
        self._merge_all_chunks = merge_all_chunks
        self._translate_all_chunks = translate_all_chunks
        self._find_deleted_chunks = find_deleted_chunks
        self._progress_manager = progress_manager
        self._export_master_html_to_epub = export_master_html_to_epub

    def log_batch_summary(self, batch_results: List[Dict], error_handler: Any = None):
        """Tạo báo cáo tóm tắt cho một batch."""
        if not batch_results:
            return

        success_count = sum(1 for r in batch_results if r and r.get("status") == "success")
        failed_count = sum(1 for r in batch_results if r and r.get("status") == "failed")
        total_count = len(batch_results)

        if failed_count > 0:
            logger.warning(f"\U0001f4e6 Batch: {success_count}/{total_count} THÀNH CÔNG | {failed_count} THẤT BẠI")
            for result in batch_results:
                if result and result.get("status") == "failed":
                    chunk_id = result.get("chunk_id", "?")
                    err = result.get("error", "Error")
                    if error_handler and hasattr(error_handler, "_simplify_error_msg"):
                        err = error_handler._simplify_error_msg(str(err))
                    logger.error(f"   - Chunk {chunk_id}: {err}")
        else:
            logger.debug(f"\U0001f4e6 Batch: {total_count} THÀNH CÔNG")

    async def generate_completion_report(
        self,
        all_chunks: List[Dict],
        failed_chunks: List[Dict],
        translation_time: float,
        is_success: bool = True,
    ):
        """
        Tạo báo cáo hoàn thành dịch thuật.

        Args:
            all_chunks: Tất cả chunks
            failed_chunks: Chunks thất bại
            translation_time: Thời gian dịch (giây)
            is_success: True nếu thành công hoàn toàn, False nếu có lỗi
        """
        completed_chunks = self._progress_manager.get_completed_chunks_count()
        total_chunks = len(all_chunks)
        success_rate = (completed_chunks / total_chunks * 100) if total_chunks > 0 else 0

        hours = int(translation_time // 3600)
        minutes = int((translation_time % 3600) // 60)
        seconds = int(translation_time % 60)

        if hours > 0:
            time_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"

        logger.info("=" * 60)
        if failed_chunks is None:
            failed_chunks = []
        missing_count = total_chunks - completed_chunks

        if is_success and len(failed_chunks) == 0 and missing_count == 0 and completed_chunks == total_chunks:
            logger.info("\U0001f389 HOÀN THÀNH DỊCH THUẬT - 100% thành công")
        else:
            if missing_count > 0:
                logger.error(
                    f"\u274c KHÔNG HOÀN TẤT - {missing_count} chunks thiếu/thất bại ({100 - success_rate:.0f}%)"
                )
            else:
                logger.error(
                    f"\u274c KHÔNG HOÀN TẤT - {len(failed_chunks)} chunks thất bại ({100 - success_rate:.0f}%)"
                )
        logger.info(
            f"\u23f1\ufe0f  Thời gian: {time_str} | \U0001f4ca Tổng: {total_chunks} | \u2705 Hoàn thành: {completed_chunks} | \u274c Thất bại: {len(failed_chunks)} | \U0001f4c8 Tỷ lệ: {success_rate:.0f}%"
        )

        if failed_chunks:
            failed_chunk_ids = [c.get("chunk_id") for c in failed_chunks if c.get("chunk_id")]
            failed_ids_str = str(failed_chunk_ids[:5])
            if len(failed_chunk_ids) > 5:
                failed_ids_str += f", ... (+{len(failed_chunk_ids) - 5} more)"
            logger.error(f"\U0001f4cb Chunks thất bại: {failed_ids_str}")
            import logging as _logging

            if logger.isEnabledFor(_logging.DEBUG):
                for i, chunk_id in enumerate(failed_chunk_ids, 1):
                    logger.debug(f"  {i}. Chunk {chunk_id}")

        logger.info("=" * 60)

    def _get_user_choice_with_timeout(
        self,
        prompt: str,
        timeout_seconds: int = 300,
        default_choice: str = "1",
        timeout_message: str = "Timeout, using default choice...",
    ) -> str:
        """
        Get user input with timeout support.

        Args:
            prompt: Input prompt to display.
            timeout_seconds: Timeout in seconds.
            default_choice: Default choice if timeout.
            timeout_message: Message to display on timeout.

        Returns:
            User choice or default on timeout.
        """
        user_choice = None
        user_choice_lock = threading.Lock()
        user_choice_done = threading.Event()

        def _auto_timer():
            nonlocal user_choice
            time.sleep(timeout_seconds)
            with user_choice_lock:
                if user_choice is None:
                    logger.info(f"\n⏰ {timeout_message}")
                    user_choice = default_choice
                    user_choice_done.set()

        def _input_thread():
            nonlocal user_choice
            try:
                choice = input(prompt).strip()
                with user_choice_lock:
                    if user_choice is None:
                        user_choice = choice
                        user_choice_done.set()
            except (KeyboardInterrupt, EOFError):
                with user_choice_lock:
                    if user_choice is None:
                        user_choice = "0"
                        user_choice_done.set()
            except Exception as e:
                logger.error(f"Lỗi nhập liệu: {e}")
                with user_choice_lock:
                    if user_choice is None:
                        user_choice = "0"
                        user_choice_done.set()

        # Start timer and input threads
        timer_thread = threading.Thread(target=_auto_timer, daemon=True)
        input_thread = threading.Thread(target=_input_thread, daemon=True)
        timer_thread.start()
        input_thread.start()

        # Wait for choice
        user_choice_done.wait()

        with user_choice_lock:
            return user_choice

    async def show_user_options(
        self,
        all_chunks: List[Dict],
        failed_chunks: List[Dict],
        txt_path: Optional[str] = None,
        retry_count: int = 0,
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Display option menu for user after translation.

        Auto-selects option 1 after 5 minutes if no interaction.
        """
        logger.info("📋 WORKFLOW REVIEW VÀ LỰA CHỌN")
        logger.info("=" * 50)
        logger.info("✅ Đã dịch hết các phân đoạn!")
        logger.info("📁 Các file phân đoạn dịch được lưu trong: data/progress/")
        if txt_path:
            logger.info(f"📄 File txt tổng đã được tạo: {txt_path}")
        logger.info("")
        logger.info("🔍 Hãy review file txt tổng và chọn một trong các option sau:")
        logger.info("")
        logger.info("1.   Convert file txt sang epub ngay")
        logger.info("2.   Chờ review và xác nhận trước khi convert sang epub")
        logger.info("3.   Dịch lại các phân đoạn bị xóa trong quá trình review")
        logger.info("4.   Export EPUB từ master.html (nếu có)")
        logger.info("0.   Thoát chương trình")
        logger.info("")
        logger.info("⏰ Tự động convert sang epub sau 60 phút nếu không có tương tác...")

        choice = self._get_user_choice_with_timeout(
            prompt="Nhập lựa chọn của bạn (1/2/3/4/0): ",
            timeout_seconds=3600,
            default_choice="1",
            timeout_message="Không có tương tác sau 60 phút, tự động convert sang epub...",
        )

        # Handle choice
        if choice == "1":
            return await self.handle_option_1(all_chunks, txt_path)
        elif choice == "2":
            return await self.handle_option_2(all_chunks, txt_path)
        elif choice == "3":
            return await self.handle_option_3(all_chunks, retry_count, txt_path)
        elif choice == "4":
            return await self.handle_option_4_export_master_html(txt_path)
        elif choice == "0":
            logger.info("👋 Thoát chương trình.")
            return [], txt_path
        else:
            logger.warning("❌ Lựa chọn không hợp lệ, tự động chọn option 1...")
            return await self.handle_option_1(all_chunks, txt_path)

    async def handle_option_1(
        self, all_chunks: List[Dict], txt_path: Optional[str] = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """Option 1: Convert txt to epub immediately."""
        if not txt_path:
            logger.error("❌ File txt không tồn tại!")
            return [], None

        logger.info("📤 EPUB source: TXT")
        logger.info("🔄 Đang convert sang epub...")
        try:
            epub_path = await self._convert_to_epub(txt_path)
            logger.info(f"✅ Đã convert thành công sang epub: {epub_path}")
            return await self.ask_additional_formats(epub_path, txt_path)
        except Exception as e:
            logger.error(f"❌ Lỗi convert sang epub: {e}")
            return [], txt_path

    async def handle_option_2(
        self, all_chunks: List[Dict], txt_path: Optional[str] = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """Option 2: Wait for review before converting."""
        if not txt_path:
            logger.error("❌ File txt không tồn tại!")
            return [], None

        logger.info("")
        logger.info("📖 File txt tổng đã được tạo!")
        logger.info(f"📄 Đường dẫn: {txt_path}")
        logger.info("🔍 Hãy review file này và xác nhận khi sẵn sàng convert sang epub.")
        logger.info("⏰ Tự động convert sau 60 phút nếu không có tương tác...")

        choice = self._get_user_choice_with_timeout(
            prompt="Bạn có muốn convert sang epub không? (y/n): ",
            timeout_seconds=3600,
            default_choice="auto",
            timeout_message="Không có tương tác sau 60 phút, tự động convert sang epub...",
        )

        if choice in ["auto", "y", "yes", "có"]:
            logger.info("📤 EPUB source: TXT")
            logger.info("🔄 Đang convert sang epub...")
            try:
                epub_path = await self._convert_to_epub(txt_path)
                logger.info(f"✅ Đã convert thành công sang epub: {epub_path}")
                return await self.ask_additional_formats(epub_path, txt_path)
            except Exception as e:
                logger.error(f"❌ Lỗi convert sang epub: {e}")
                return [], txt_path
        elif choice in ["n", "no", "không"]:
            logger.info("👋 Không convert sang epub. File txt đã được lưu.")
            return [], txt_path
        else:
            logger.info("\n👋 Thoát chương trình.")
            return [], txt_path

    async def handle_option_3(
        self,
        all_chunks: List[Dict],
        retry_count: int = 0,
        txt_path: Optional[str] = None,
    ) -> Tuple[List[Dict], Optional[str]]:
        """Option 3: Retranslate deleted chunks."""
        if retry_count > 3:
            logger.error(f"⚠️ Quá nhiều lần dịch lại (>{retry_count})! Dừng lại để tránh lặp vô hạn.")
            logger.info("💡 Gợi ý: Kiểm tra lại files chunk trong data/progress/")
            return [], None

        logger.info("🔍 Đang kiểm tra các chunks bị xóa...")
        deleted_chunks = self._find_deleted_chunks(all_chunks)

        if not deleted_chunks:
            logger.info("✅ Không có chunk nào bị xóa!")
            logger.info("🔄 Quay lại menu lựa chọn...")
            return await self.show_user_options(all_chunks, [], txt_path, retry_count)

        # Log summary
        deleted_ids = [c["global_id"] for c in deleted_chunks]
        deleted_ids_str = str(deleted_ids[:5])
        if len(deleted_ids) > 5:
            deleted_ids_str += f", ... (+{len(deleted_ids) - 5} more)"
        logger.info(f"📋 Tìm thấy {len(deleted_chunks)} chunks bị xóa: {deleted_ids_str}")

        logger.info("")
        logger.info("🔄 Tự động tiến hành dịch lại các chunks bị xóa...")

        # Remove deleted chunks from completed to force retranslation
        for chunk in deleted_chunks:
            chunk_id = chunk["global_id"]
            chunk_id_str = str(chunk_id)
            if chunk_id_str in self._progress_manager.completed_chunks:
                del self._progress_manager.completed_chunks[chunk_id_str]

        failed_chunks = await self._translate_all_chunks(deleted_chunks)
        logger.info("✅ Hoàn thành dịch lại!")

        # Merge TXT after retranslation
        logger.info("")
        logger.info("🔄 Đang ghép lại file txt tổng sau khi dịch lại...")
        full_content = await self._merge_all_chunks(all_chunks)
        if full_content:
            new_txt_path = self.output_formatter.save(full_content, self.novel_name)
            logger.info(f"✅ Đã cập nhật file txt tổng: {new_txt_path}")
            txt_path = new_txt_path
        else:
            logger.warning("⚠️ Không thể ghép lại chunks, giữ nguyên file txt cũ.")

        logger.info("🔄 Quay lại menu lựa chọn...")
        return await self.show_user_options(all_chunks, failed_chunks, txt_path, retry_count + 1)

    async def handle_option_4_export_master_html(
        self, txt_path: Optional[str] = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Option 4: Export EPUB từ file master.html (nếu có).
        Đường dẫn master: progress_dir / {novel_name}_master.html (do Phase 8 / EPUB layout tạo).
        """
        progress_dir = self.config.get("progress", {}).get("progress_dir", "data/progress")
        master_path = os.path.join(progress_dir, f"{self.novel_name}_master.html")
        if not os.path.isfile(master_path):
            logger.warning("⚠️ Không tìm thấy file master.html (chưa có hoặc pipeline chưa tạo).")
            logger.info(f"   Đường dẫn kiểm tra: {master_path}")
            if txt_path:
                logger.info("   💡 Bạn có thể dùng option 1 hoặc 2 để convert từ file TXT sang EPUB.")
            return [], txt_path

        if not self._export_master_html_to_epub:
            logger.warning("⚠️ Tính năng export từ master.html chưa được cấu hình.")
            return [], txt_path

        logger.info("📤 EPUB source: master.html")
        logger.info("🔄 Đang export EPUB từ master.html...")
        try:
            epub_path = await self._export_master_html_to_epub(master_path)
            if epub_path:
                logger.info(f"✅ Đã export thành công EPUB từ master.html: {epub_path}")
                return await self.ask_additional_formats(epub_path, txt_path or "")
            return [], txt_path
        except Exception as e:
            logger.error(f"❌ Lỗi export từ master.html: {e}")
            return [], txt_path

    async def ask_additional_formats(self, epub_path: str, txt_path: str) -> Tuple[List[Dict], Optional[str]]:
        """Ask user about additional format conversions (DOCX/PDF)."""
        logger.info("")
        logger.info("📋 Bạn có muốn convert thêm sang các định dạng khác không?")
        logger.info("   1. Convert sang DOCX")
        logger.info("   2. Convert sang PDF")
        logger.info("   3. Convert cả DOCX và PDF")
        logger.info("   0. Không, chỉ giữ EPUB")
        logger.info("")
        logger.info("⏰ Tự động bỏ qua sau 60 phút nếu không có tương tác...")

        choice = self._get_user_choice_with_timeout(
            prompt="Nhập lựa chọn (1/2/3/0): ",
            timeout_seconds=3600,
            default_choice="0",
            timeout_message="Không có tương tác sau 60 phút, bỏ qua convert thêm...",
        )

        if choice == "1":
            docx_path = await self._convert_to_docx(txt_path)
            if docx_path:
                logger.info(f"✅ Đã convert thành công sang DOCX: {docx_path}")
            return [], epub_path
        elif choice == "2":
            pdf_path = await self._convert_to_pdf(txt_path)
            if pdf_path:
                logger.info(f"✅ Đã convert thành công sang PDF: {pdf_path}")
            return [], epub_path
        elif choice == "3":
            logger.info("🔄 Đang convert cả DOCX và PDF song song...")
            docx_task = asyncio.create_task(self._convert_to_docx(txt_path))
            pdf_task = asyncio.create_task(self._convert_to_pdf(txt_path))

            docx_path, pdf_path = await asyncio.gather(docx_task, pdf_task, return_exceptions=True)

            if isinstance(docx_path, Exception):
                logger.error(f"❌ Lỗi convert sang DOCX: {docx_path}")
            elif docx_path:
                logger.info(f"✅ Đã convert thành công sang DOCX: {docx_path}")

            if isinstance(pdf_path, Exception):
                logger.error(f"❌ Lỗi convert sang PDF: {pdf_path}")
            elif pdf_path:
                logger.info(f"✅ Đã convert thành công sang PDF: {pdf_path}")

            return [], epub_path
        else:
            logger.info("👋 Không convert thêm. File EPUB đã được lưu.")
            return [], epub_path
