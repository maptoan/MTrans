# -*- coding: utf-8 -*-
"""
Helper: Trích bảng từ PDF và chuyển thành văn bản có marker để hậu kỳ Convert Text→Table.
Phạm vi: PDF có text layer (pdfplumber). Với PDF scan, khả năng phát hiện bảng hạn chế; sẽ cố pdfplumber,
nếu không có bảng thì trả về rỗng.
"""

import logging
from typing import List, Optional, Tuple

try:
    import pdfplumber  # type: ignore
except Exception:
    pdfplumber = None

logger = logging.getLogger("NovelTranslator")


def extract_tables_as_marked_text(
    pdf_path: str,
    pages: Optional[list[int]] = None,
    column_delimiter: str = " | ",
    row_delimiter: str = "\n",
    include_page_info: bool = True,
    max_tables_per_page: int = 50,
) -> Tuple[str, int]:
    """
    Trích bảng từ PDF (ưu tiên pdfplumber) và đóng gói thành văn bản có marker.

    Returns:
        (marked_text, total_tables)
    """
    if pdfplumber is None:
        logger.debug("Table marker: pdfplumber không khả dụng, bỏ qua trích bảng.")
        return "", 0

    total_tables = 0
    parts: list[str] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            if pages:
                pages_to_scan = [p for p in pages if 1 <= p <= total_pages]
            else:
                pages_to_scan = list(range(1, total_pages + 1))

            table_index_global = 0
            for page_num in pages_to_scan:
                try:
                    page = pdf.pages[page_num - 1]
                    tables = page.extract_tables() or []
                except Exception as e:
                    logger.debug(
                        f"Table marker: Lỗi extract_tables tại trang {page_num}: {e}"
                    )
                    tables = []

                if not tables:
                    continue

                limit = min(
                    len(tables),
                    max_tables_per_page
                    if max_tables_per_page and max_tables_per_page > 0
                    else len(tables),
                )
                for local_idx, tbl in enumerate(tables[:limit], start=1):
                    # Lọc bảng hợp lệ: cần >=2 hàng và hàng có >=2 cột
                    if not tbl or len(tbl) < 2:
                        continue
                    # Đếm số cột mỗi hàng
                    col_counts: List[int] = [len(r) for r in tbl if isinstance(r, list)]
                    if not col_counts:
                        continue
                    # Số cột mục tiêu = mode
                    try:
                        counts: dict[int, int] = {}
                        for c in col_counts:
                            counts[c] = counts.get(c, 0) + 1
                        target_cols = max(counts, key=counts.get)
                    except Exception:
                        target_cols = max(col_counts)
                    if target_cols < 2:
                        continue

                    table_index_global += 1
                    total_tables += 1
                    header = f"[begin_table_{table_index_global}]"
                    if include_page_info:
                        header = f"{header} page={page_num}"

                    parts.append(header)

                    # Xuất từng dòng theo delimiter; chuẩn hóa số cột và escape delimiter khi cần
                    for row in tbl or []:
                        # Bỏ qua hàng None
                        if row is None:
                            continue
                        # Đảm bảo là list
                        r = list(row)
                        # Pad/truncate để số cột = target_cols
                        if len(r) < target_cols:
                            r = r + [""] * (target_cols - len(r))
                        elif len(r) > target_cols:
                            r = r[:target_cols]

                        cells: List[str] = []
                        for cell in r:
                            if cell is None:
                                cells.append("")
                                continue
                            # Làm sạch newline trong ô
                            text = (
                                str(cell).replace("\r", " ").replace("\n", " ").strip()
                            )
                            if column_delimiter == "\t":
                                # Với TAB không cần escape đặc biệt (DOCX xử lý tốt)
                                # Nhưng nếu có TAB trong text, thay TAB nội bộ bằng khoảng trắng để không vỡ cột
                                if "\t" in text:
                                    text = text.replace("\t", " ")
                                cells.append(text)
                            else:
                                # Nếu text chứa delimiter, áp dụng CSV quoting: "..." và escape " bằng ""
                                if column_delimiter and column_delimiter in text:
                                    qt = '"'
                                    text = qt + text.replace(qt, qt + qt) + qt
                                cells.append(text)

                        parts.append(column_delimiter.join(cells))

                    parts.append(f"[end_table_{table_index_global}]")

    except Exception as e:
        logger.debug(f"Table marker: Không thể mở/đọc PDF cho table extraction: {e}")
        return "", 0

    if not parts:
        return "", 0

    # Ghép theo row_delimiter, giữa các bảng đã có header/end nên chỉ cần newline thông thường
    # Đảm bảo có khoảng trống rõ ràng trước block marker
    marked_text = "\n\n" + row_delimiter.join(parts).strip() + "\n\n"
    return marked_text, total_tables
