# -*- coding: utf-8 -*-
"""
AI Table Recovery: Dùng Gemini (ưu tiên 2.5 Flash, fallback 2.5 Pro) để phục hồi bảng từ PDF.

Module này sử dụng Gemini API để:
- OCR và detect tables từ PDF pages (images)
- Reconstruct tables với đầy đủ rows, columns, headers
- Output tables dưới dạng CSV và Markdown
- Hỗ trợ batch processing và retry logic

Sử dụng GenAI Adapter để hỗ trợ cả SDK mới và SDK cũ.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, List, Optional, Tuple

from ..services.genai_adapter import GenAIClient, create_client

_WORKER_ID_TABLE_RECOVERY = 995

logger = logging.getLogger("NovelTranslator")

try:
    import fitz  # PyMuPDF, để render trang thành ảnh
except ImportError:
    fitz = None


PROMPT_TABLE_RECOVERY = (
    "You are a table reconstruction assistant. Input: scanned or text-based PDF pages (images/text).\n"
    "Task:\n"
    "1) OCR any text (if needed) and detect all tables on each page.\n"
    "2) Reconstruct each table faithfully (rows, columns, headers). Preserve logical groupings.\n"
    "3) Output tables in two formats:\n"
    "   - Markdown tables (for human review)\n"
    "   - CSV (comma-separated, RFC4180, quote cells with commas or quotes)\n"
    "4) For each table include: page number, table index, and if inferred: header rows count.\n"
    "5) Avoid narrative text; only tables. If no table on a page, say NO_TABLE.\n\n"
    "Constraints:\n"
    "- Ensure each row has consistent number of columns (pad empty cells if needed).\n"
    "- Escape internal quotes by doubling them. Line breaks inside cells -> space.\n"
    "- For merged cells (rowspan/colspan), flatten into repeated values or empty placeholders; keep columns consistent.\n"
    "- If table is too wide, split into sub-tables with suffixes (_a, _b).\n\n"
    "Return format per table:\n"
    "PAGE: <n>\nTABLE: <k>\nMARKDOWN:\n<markdown table>\nCSV:\n<csv block>\n"
)


class AITableRecovery:
    """
    AI Table Recovery sử dụng Gemini API để phục hồi tables từ PDF.

    Hỗ trợ:
    - Flash model (nhanh, rẻ) và Pro model (chính xác hơn)
    - Batch processing để xử lý nhiều pages
    - Retry logic với model fallback
    """

    def __init__(
        self,
        api_keys: List[str],
        model_flash: str = "gemini-2.5-flash",
        model_pro: str = "gemini-2.5-pro",
        timeout_seconds: int = 240,
        max_retries: int = 2,
        use_flash_first: bool = True,
        use_new_sdk: bool = True,
        key_manager: Any = None,
    ) -> None:
        """
        Khởi tạo AI Table Recovery.

        Args:
            api_keys: Danh sách API keys để sử dụng (khi không có key_manager)
            model_flash: Tên Flash model (mặc định: "gemini-2.5-flash")
            model_pro: Tên Pro model (mặc định: "gemini-2.5-pro")
            timeout_seconds: Timeout cho mỗi request (mặc định: 240)
            max_retries: Số lần retry tối đa (mặc định: 2)
            use_flash_first: True để ưu tiên Flash, False để ưu tiên Pro
            use_new_sdk: True để dùng SDK mới, False để dùng SDK cũ
            key_manager: Nếu có thì dùng chung get_available_key/return_key với quy trình chính.
        """
        self.api_keys: List[str] = api_keys or []
        self.key_manager: Any = key_manager
        self.model_flash: str = model_flash
        self.model_pro: str = model_pro
        self.timeout_seconds: int = int(timeout_seconds)
        self.max_retries: int = int(max_retries)
        self.use_flash_first: bool = bool(use_flash_first)
        self.use_new_sdk: bool = use_new_sdk
        self._key_index: int = 0

    def _client_and_model_from_key(
        self, api_key: str, prefer_flash: bool
    ) -> Optional[Tuple[GenAIClient, str]]:
        """Tạo (client, model_name) từ một key cho trước."""
        model_name = self.model_flash if prefer_flash else self.model_pro
        try:
            client = create_client(api_key=api_key, use_new_sdk=self.use_new_sdk)
            return (client, model_name)
        except Exception as e:
            logger.debug(f"Khởi tạo client với model {model_name} lỗi: {e}")
            return None

    def _rotate_key_and_client(
        self, prefer_flash: bool
    ) -> Optional[Tuple[GenAIClient, str]]:
        """
        Rotate API key và tạo client với model phù hợp (dùng khi không có key_manager).
        """
        if not self.api_keys:
            return None

        api_key = self.api_keys[self._key_index % len(self.api_keys)]
        self._key_index += 1

        return self._client_and_model_from_key(api_key, prefer_flash)

    def _render_pages_to_images(
        self, pdf_path: str, pages: Optional[List[int]], zoom: float = 2.0
    ) -> List[Tuple[int, bytes]]:
        """
        Render các trang PDF thành PNG bytes.

        Args:
            pdf_path: Đường dẫn file PDF
            pages: Optional list các page numbers cần render (None = tất cả)
            zoom: Zoom factor cho rendering (mặc định: 2.0)

        Returns:
            List các (page_num, image_bytes)
        """
        results: List[Tuple[int, bytes]] = []
        if fitz is None:
            logger.warning("PyMuPDF không khả dụng, không thể render ảnh để AI xử lý.")
            return results
        try:
            doc = fitz.open(pdf_path)
            total = doc.page_count
            if pages:
                pages_to_use = [p for p in pages if 1 <= p <= total]
            else:
                pages_to_use = list(range(1, total + 1))
            for pno in pages_to_use:
                try:
                    page = doc.load_page(pno - 1)
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    img_bytes = pix.tobytes("png")
                    results.append((pno, img_bytes))
                except Exception as e:
                    logger.debug(f"Render trang {pno} lỗi: {e}", exc_info=True)
            doc.close()
        except Exception as e:
            logger.warning(f"Không thể mở PDF để render: {e}", exc_info=True)
        return results

    def _call_model_with_images(
        self,
        client_and_model: Optional[Tuple[GenAIClient, str]],
        images: List[Tuple[int, bytes]],
    ) -> Optional[str]:
        """
        Gọi model với images để recover tables.

        Args:
            client_and_model: Tuple (client, model_name) hoặc None
            images: List các (page_num, image_bytes)

        Returns:
            Response text hoặc None nếu thất bại
        """
        if client_and_model is None:
            return None

        client, model_name = client_and_model

        try:
            # Tạo parts: prompt + nhiều ảnh trang
            parts: List[Any] = [PROMPT_TABLE_RECOVERY]
            for pno, img in images:
                parts.append({"mime_type": "image/png", "data": img})

            # Generate content (sync call)
            resp = client.generate_content(prompt=parts, model_name=model_name)

            if hasattr(resp, "text") and resp.text:
                return resp.text
            return None
        except Exception as e:
            logger.debug(f"AI call lỗi: {e}", exc_info=True)
            return None

    def _parse_and_save(
        self,
        text: str,
        base_out_dir: Path,
        base_name: str,
        page_batch: List[int],
        save_markdown: bool,
    ) -> int:
        """
        Parse response: tách từng khối CSV/Markdown, lưu file.

        Args:
            text: Response text từ AI
            base_out_dir: Thư mục output
            base_name: Base name cho output files
            page_batch: List các page numbers trong batch này
            save_markdown: True để lưu markdown (hiện tại chưa implement)

        Returns:
            Số bảng đã tìm thấy và lưu
        """
        if not text:
            return 0
        base_out_dir.mkdir(parents=True, exist_ok=True)
        tables_found = 0

        # Tách theo dấu hiệu SECTION đơn giản
        blocks = text.split("CSV:")
        # Duyệt từng CSV block; cố tìm PAGE và TABLE trước đó
        for idx, block in enumerate(blocks[1:], start=1):
            try:
                # Tìm dòng PAGE và TABLE gần block này bằng cách back-scan từ phần trước
                # Đơn giản hoá: không back-scan, chỉ đánh số tăng dần
                csv_text = block.strip()
                # Nếu có code fences, loại bỏ
                lines = [
                    ln
                    for ln in csv_text.splitlines()
                    if not ln.strip().startswith("```")
                ]
                # Lấy đến khi gặp dòng trống lớn
                csv_lines: List[str] = []
                for ln in lines:
                    if not ln.strip():
                        if csv_lines:
                            break
                        else:
                            continue
                    csv_lines.append(ln)
                if not csv_lines:
                    continue
                tables_found += 1
                out_csv = (
                    base_out_dir
                    / f"{base_name}_batch{min(page_batch)}-{max(page_batch)}_{tables_found}.csv"
                )
                with open(out_csv, "w", encoding="utf-8", newline="") as f:
                    f.write("\n".join(csv_lines) + "\n")

                if save_markdown:
                    # Tìm phần MARKDOWN trước CSV trong cùng blocks[ idx ]
                    # Heuristic: tìm "MARKDOWN:" trong phần trước dấu CSV: ở blocks[idx] có phần trước khi split,
                    # ta không giữ được trực tiếp. Đơn giản: lưu toàn bộ phản hồi để review (tùy chọn)
                    pass
            except Exception:
                continue

        return tables_found

    async def recover_tables_to_csv(
        self,
        pdf_path: str,
        pages: Optional[List[int]],
        output_dir: str,
        save_markdown: bool = True,
        pages_limit: int = 50,
        batch_pages: int = 3,
    ) -> Tuple[int, List[Path]]:
        """
        Thử gọi Gemini Flash trước, nếu không có bảng thì gọi Pro. Lưu CSV, trả về (số bảng, danh sách file).
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(pdf_path).stem

        # Render ảnh trang
        images = self._render_pages_to_images(pdf_path, pages)
        if not images:
            return 0, []

        # Giới hạn trang và batching
        if pages_limit and len(images) > pages_limit:
            images = images[:pages_limit]

        total_tables = 0
        saved_files: List[Path] = []
        for i in range(0, len(images), max(1, batch_pages)):
            batch = images[i : i + batch_pages]
            page_batch = [p for p, _ in batch]
            prefer_flash = self.use_flash_first

            # Retry logic + model fallback
            response_text: Optional[str] = None
            for attempt in range(self.max_retries):
                key = None
                failed = False
                err_type, err_msg = "generation_error", ""
                try:
                    if self.key_manager:
                        # [v9.1] get_available_key is async
                        key = await self.key_manager.get_available_key()
                        if not key:
                            time.sleep(min(2**attempt, 8))
                            continue
                        client_and_model = self._client_and_model_from_key(key, prefer_flash)
                    else:
                        client_and_model = self._rotate_key_and_client(prefer_flash)
                    response_text = self._call_model_with_images(client_and_model, batch)
                    if response_text:
                        break
                except Exception as e:
                    failed = True
                    err_type = (
                        self.key_manager.handle_exception(key, e)
                        if (self.key_manager and key and hasattr(self.key_manager, "handle_exception"))
                        else "generation_error"
                    )
                    err_msg = str(e)
                finally:
                    if self.key_manager and key:
                        await self.key_manager.return_key(
                            _WORKER_ID_TABLE_RECOVERY,
                            key,
                            is_error=failed,
                            error_type=err_type,
                            error_message=err_msg,
                        )
                # Nếu Flash thất bại, thử Pro trong lần kế
                prefer_flash = False
                time.sleep(min(2**attempt, 8))

            if not response_text:
                logger.debug(
                    f"AI table recovery không có phản hồi cho batch trang {page_batch}"
                )
                continue

            # Parse & save
            try:
                found = self._parse_and_save(
                    response_text, out_dir, base_name, page_batch, save_markdown
                )
                total_tables += found
            except Exception as e:
                logger.debug(f"Lỗi parse/save AI table cho batch {page_batch}: {e}")
                continue

        # Gom danh sách file CSV lưu được
        try:
            saved_files = sorted(out_dir.glob(f"{base_name}_*.csv"))
        except Exception:
            saved_files = []

        return total_tables, saved_files
