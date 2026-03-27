# -*- coding: utf-8 -*-
"""
PDF Pre-Cleaner: Xóa header/footer lặp và watermark theo từ khóa trực tiếp trên PDF (PyMuPDF),
trước khi convert PDF→DOCX, để tăng hiệu quả làm sạch.
"""

from __future__ import annotations

import logging
import math
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NovelTranslator")

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


def _normalize(s: str) -> str:
    return (s or "").strip()


def _strip_diacritics(s: str) -> str:
    if not s:
        return s
    n = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in n if not unicodedata.combining(ch))


def _collect_band_words(
    page, band: Tuple[float, float, float, float]
) -> List[Tuple[float, float, float, float, str]]:
    """Thu thập các words nằm trong band (x0,y0,x1,y1). Trả về list (x0,y0,x1,y1,text)."""
    words = []
    try:
        # get_text("words") → [(x0,y0,x1,y1, word, block_no, line_no, word_no), ...]
        for w in page.get_text("words") or []:
            x0, y0, x1, y1, txt = w[0], w[1], w[2], w[3], w[4]
            if x0 >= band[0] and y0 >= band[1] and x1 <= band[2] and y1 <= band[3]:
                if _normalize(txt):
                    words.append((x0, y0, x1, y1, txt))
    except Exception:
        pass
    return words


def _join_line_texts(
    words: List[Tuple[float, float, float, float, str]], y_tol: float = 2.0
) -> List[Tuple[float, float, float, float, str]]:
    """Gộp words theo dòng (gần nhau theo Y) để tạo chuỗi header/footer ngắn."""
    if not words:
        return []
    # Sort by y, then x
    words_sorted = sorted(words, key=lambda w: (w[1], w[0]))
    lines = []
    cur_line: List[Tuple[float, float, float, float, str]] = []
    cur_y: Optional[float] = None
    for w in words_sorted:
        if cur_y is None:
            cur_line = [w]
            cur_y = w[1]
        else:
            if abs(w[1] - cur_y) <= y_tol:
                cur_line.append(w)
            else:
                # flush
                x0 = min(x for x, y0_val, x1, y1_val, t in cur_line)
                y0 = min(y0_val for x, y0_val, x1, y1_val, t in cur_line)
                x1 = max(x1_val for x, y0_val, x1_val, y1_val, t in cur_line)
                y1 = max(y1_val for x, y0_val, x1_val, y1_val, t in cur_line)
                text = " ".join(t for x0c, y0c, x1c, y1c, t in cur_line)
                lines.append((x0, y0, x1, y1, text))
                cur_line = [w]
                cur_y = w[1]
    if cur_line:
        x0 = min(x for x, y0_val, x1, y1_val, t in cur_line)
        y0 = min(y0_val for x, y0_val, x1, y1_val, t in cur_line)
        x1 = max(x1_val for x, y0_val, x1_val, y1_val, t in cur_line)
        y1 = max(y1_val for x, y0_val, x1_val, y1_val, t in cur_line)
        text = " ".join(t for x0c, y0c, x1c, y1c, t in cur_line)
        lines.append((x0, y0, x1, y1, text))
    return lines


def _find_repeated_strings(
    lines_per_page: List[List[Tuple[float, float, float, float, str]]],
    threshold_ratio: float,
) -> List[str]:
    freq: Dict[str, int] = {}
    total_pages = len(lines_per_page)
    for lines in lines_per_page:
        seen = set()
        for _, _, _, _, text in lines:
            t = _normalize(text)
            if not t:
                continue
            seen.add(t)
        for t in seen:
            freq[t] = freq.get(t, 0) + 1
    repeated = [
        t for t, c in freq.items() if c / max(1, total_pages) >= threshold_ratio
    ]
    return repeated


def preclean_pdf(
    pdf_path: str, out_path: str, cfg: Dict[str, Any], pages: Optional[List[int]] = None
) -> Optional[str]:
    """
    Làm sạch PDF in-place (ghi ra out_path):
    - Xóa header/footer lặp (dò trong dải top/bottom theo tỉ lệ chiều cao trang)
    - Xóa watermark theo từ khóa (mọi vị trí)
    Trả về đường dẫn out_path nếu thành công, None nếu không xử lý.
    """
    if fitz is None:
        logger.warning("PyMuPDF không khả dụng; bỏ qua pre-clean PDF.")
        return None

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.debug(f"Không thể mở PDF cho pre-clean: {e}")
        return None

    top_ratio = float(cfg.get("top_band_ratio", 0.08) or 0.08)
    bottom_ratio = float(cfg.get("bottom_band_ratio", 0.08) or 0.08)
    thr = float(cfg.get("repetition_threshold_ratio", 0.6) or 0.6)
    keywords = cfg.get("watermark_keywords", []) or []
    ci = bool(cfg.get("case_insensitive", True))

    # Xác định trang xử lý
    total = doc.page_count
    if pages:
        pages_to_use = [p for p in pages if 1 <= p <= total]
    else:
        pages_to_use = list(range(1, total + 1))

    # Pass 1: thu thập text lines ở dải top/bottom để tìm chuỗi lặp
    top_lines_all: List[List[Tuple[float, float, float, float, str]]] = []
    bottom_lines_all: List[List[Tuple[float, float, float, float, str]]] = []

    for pno in pages_to_use:
        try:
            page = doc.load_page(pno - 1)
            rect = page.rect
            top_band = (rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * top_ratio)
            bottom_band = (
                rect.x0,
                rect.y1 - rect.height * bottom_ratio,
                rect.x1,
                rect.y1,
            )
            top_lines = _join_line_texts(_collect_band_words(page, top_band))
            bottom_lines = _join_line_texts(_collect_band_words(page, bottom_band))
            top_lines_all.append(top_lines)
            bottom_lines_all.append(bottom_lines)
        except Exception:
            top_lines_all.append([])
            bottom_lines_all.append([])

    repeated_top = _find_repeated_strings(top_lines_all, thr)
    repeated_bottom = _find_repeated_strings(bottom_lines_all, thr)

    # Pass 2: tạo redaction cho các bboxes thuộc các chuỗi lặp & watermark theo từ khóa
    removed_boxes = 0
    for pno in pages_to_use:
        try:
            page = doc.load_page(pno - 1)
            # Header/Footer theo chuỗi lặp
            for band_lines, band_rect in (
                (
                    top_lines_all[pno - 1],
                    (
                        page.rect.x0,
                        page.rect.y0,
                        page.rect.x1,
                        page.rect.y0 + page.rect.height * top_ratio,
                    ),
                ),
                (
                    bottom_lines_all[pno - 1],
                    (
                        page.rect.x0,
                        page.rect.y1 - page.rect.height * bottom_ratio,
                        page.rect.x1,
                        page.rect.y1,
                    ),
                ),
            ):
                for x0, y0, x1, y1, text in band_lines:
                    t = _normalize(text)
                    if t in repeated_top or t in repeated_bottom:
                        try:
                            page.add_redact_annot(fitz.Rect(x0, y0, x1, y1))
                            removed_boxes += 1
                        except Exception:
                            pass

            # Watermark từ khóa: duyệt toàn trang theo words
            try:
                words = page.get_text("words") or []
            except Exception:
                words = []
            if keywords:
                for w in words:
                    try:
                        x0, y0, x1, y1, txt = w[0], w[1], w[2], w[3], w[4]
                        t = _normalize(txt)
                        if not t:
                            continue
                        # so khớp cả không dấu
                        hay = t.lower() if ci else t
                        hay_nodiac = _strip_diacritics(hay).lower()
                        hit = False
                        for kw in keywords:
                            if not kw:
                                continue
                            needle = kw.lower() if ci else kw
                            needle_nd = _strip_diacritics(needle).lower()
                            if needle in hay or needle_nd in hay_nodiac:
                                hit = True
                                break
                        if hit:
                            page.add_redact_annot(fitz.Rect(x0, y0, x1, y1))
                            removed_boxes += 1
                    except Exception:
                        continue

            # Watermark nghiêng: duyệt theo dòng từ get_text('dict') để xét góc
            try:
                angle_min = float(cfg.get("diagonal_angle_min_deg", 20) or 20)
                angle_max = float(cfg.get("diagonal_angle_max_deg", 70) or 70)
                min_len = int(cfg.get("watermark_min_text_len", 8) or 8)
                d = page.get_text("dict")
                for block in d.get("blocks", []):
                    for line in block.get("lines", []):
                        # Ước lượng góc từ vector span đầu tiên (dir)
                        spans = line.get("spans", [])
                        if not spans:
                            continue
                        dir_vec = spans[0].get("dir", [1, 0])
                        try:
                            dx, dy = float(dir_vec[0]), float(dir_vec[1])
                            angle = abs(math.degrees(math.atan2(dy, dx)))
                        except Exception:
                            angle = 0.0
                        if not (angle_min <= angle <= angle_max):
                            continue
                        # Text của line
                        line_text = "".join(s.get("text", "") for s in spans)
                        lt_norm = _normalize(line_text)
                        if len(lt_norm) < min_len:
                            continue
                        lt_l = lt_norm.lower()
                        lt_nd = _strip_diacritics(lt_l)
                        # So khớp từ khóa
                        matched = False
                        for kw in keywords:
                            if not kw:
                                continue
                            k = kw.lower()
                            knd = _strip_diacritics(k)
                            if k in lt_l or knd in lt_nd:
                                matched = True
                                break
                        if not matched:
                            continue
                        # Redact theo bbox của line
                        bbox = line.get("bbox")
                        if bbox and len(bbox) == 4:
                            try:
                                page.add_redact_annot(fitz.Rect(*bbox))
                                removed_boxes += 1
                            except Exception:
                                pass
            except Exception:
                pass

            # Footer dạng dòng chấm + số (bottom band): dò theo pattern
            try:
                import re

                pat = cfg.get("footer_dots_pattern")
                if pat:
                    rx = re.compile(pat)
                    rect = page.rect
                    bottom_band = (
                        rect.x0,
                        rect.y1 - rect.height * bottom_ratio,
                        rect.x1,
                        rect.y1,
                    )
                    blines = _join_line_texts(_collect_band_words(page, bottom_band))
                    for x0, y0, x1, y1, text in blines:
                        t = _normalize(text)
                        if rx.match(t):
                            try:
                                page.add_redact_annot(fitz.Rect(x0, y0, x1, y1))
                                removed_boxes += 1
                            except Exception:
                                pass
            except Exception:
                pass

            # Áp dụng redactions trên trang này
            try:
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
            except Exception:
                pass
        except Exception:
            continue

    if removed_boxes == 0:
        doc.close()
        return None

    try:
        doc.save(out_path)
        doc.close()
        return out_path
    except Exception as e:
        logger.debug(f"Không thể lưu PDF đã pre-clean: {e}")
        try:
            doc.close()
        except Exception:
            pass
        return None
