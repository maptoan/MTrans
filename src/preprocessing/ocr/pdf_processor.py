# -*- coding: utf-8 -*-
from __future__ import annotations

import gc
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import PDFProcessorError

# Thư viện xử lý PDF sẽ được lazy import hoặc mong đợi từ ocr_reader truyền vào
logger = logging.getLogger("NovelTranslator")

# Placeholder cho các dependencies nặng
pdfplumber = None
PyPDF2 = None
fitz = None
convert_from_path = None
ocrmypdf = None
Converter = None
tqdm = None


def _get_pdf_refs(ocr_cfg: Optional[dict] = None) -> None:
    """Lấy các reference cần thiết cho PDF từ ocr_reader hoặc import."""
    global pdfplumber, PyPDF2, fitz, convert_from_path, ocrmypdf, Converter, tqdm
    try:
        import fitz as fz
        import ocrmypdf as ocr
        import pdfplumber as pl
        import PyPDF2 as p2
        from pdf2docx import Converter as Cnv
        from pdf2image import convert_from_path as cfp
        from tqdm import tqdm as tq

        pdfplumber, PyPDF2, fitz, convert_from_path, ocrmypdf, Converter, tqdm = pl, p2, fz, cfp, ocr, Cnv, tq
    except ImportError:
        pass


def detect_pdf_type(pdf_path: str, ocr_cfg: Optional[dict] = None) -> str:
    """Phát hiện PDF là scan hay text-based."""
    _get_pdf_refs(ocr_cfg)
    import threading

    result_container = {"result": None, "done": False}
    exception_container = {"exception": None}

    def _detect_inner():
        try:
            if PyPDF2 is not None:
                try:
                    with open(pdf_path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        total_pages = len(reader.pages)
                        if total_pages == 0:
                            result_container["result"] = "scan"
                            result_container["done"] = True
                            return
                        # Sample pages
                        sample_indices = [0]
                        if total_pages > 1:
                            sample_indices.append(total_pages - 1)
                        if total_pages > 2:
                            sample_indices.append(total_pages // 2)

                        total_text = ""
                        for idx in sample_indices:
                            page_text = reader.pages[idx].extract_text() or ""
                            total_text += page_text

                        if len(total_text.strip()) > 200:
                            result_container["result"] = "text"
                            result_container["done"] = True
                            return
                except Exception:
                    pass

            if pdfplumber is not None:
                with pdfplumber.open(pdf_path) as pdf:
                    pages_to_check = pdf.pages[:5]
                    total_chars = 0
                    for page in pages_to_check:
                        text = page.extract_text() or ""
                        total_chars += len(text.strip())
                    if total_chars > 200:
                        result_container["result"] = "text"
                    else:
                        result_container["result"] = "scan"
                    result_container["done"] = True
        except Exception as e:
            exception_container["exception"] = e

    t = threading.Thread(target=_detect_inner)
    t.daemon = True
    t.start()
    t.join(timeout=15)

    if result_container["result"]:
        return result_container["result"]
    return "scan"


def extract_text_from_pdf(pdf_path: str, ocr_cfg: dict, pages: Optional[List[int]] = None) -> str:
    """Extract text từ PDF có text layer."""
    _get_pdf_refs(ocr_cfg)
    texts: List[str] = []
    if pdfplumber is not None:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                target_pages = [pdf.pages[i - 1] for i in pages if 1 <= i <= len(pdf.pages)] if pages else pdf.pages
                for page in target_pages:
                    texts.append(page.extract_text() or "")
            return "\n\n".join(texts)
        except Exception as e:
            logger.warning(f"Lỗi trích xuất pdfplumber: {e}")

    if PyPDF2 is not None:
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total = len(reader.pages)
                indices = [i - 1 for i in pages if 1 <= i <= total] if pages else range(total)
                for i in indices:
                    texts.append(reader.pages[i].extract_text() or "")
            return "\n\n".join(texts)
        except Exception as e:
            logger.warning(f"Lỗi trích xuất PyPDF2: {e}")
    return ""


def extract_text_blocks_with_position(
    pdf_path: str, ocr_cfg: dict, pages: Optional[List[int]] = None
) -> tuple[List[dict], int]:
    """Extract text blocks với Y-position từ PDF."""
    _get_pdf_refs(ocr_cfg)
    text_blocks_by_page = {}
    total_pages = 0
    if pdfplumber is not None:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                indices = [i - 1 for i in pages if 1 <= i <= total_pages] if pages else range(total_pages)
                for i in indices:
                    page = pdf.pages[i]
                    blocks = page.extract_words(extra_attrs=["y_position", "x_position", "top", "bottom"])
                    text_blocks_by_page[i + 1] = [{"text": b["text"], "y_position": b["top"]} for b in blocks]
            return text_blocks_by_page, total_pages
        except Exception:
            pass
    return {}, 0


def convert_pdf_with_ocrmypdf(pdf_path: str, output_path: str, ocr_cfg: dict, pages: Optional[List[int]] = None) -> str:
    """Convert PDF → PDF searchable bằng OCRmyPDF."""
    import subprocess

    logger.info(f"Đang chạy OCRmyPDF: {pdf_path} -> {output_path}")
    cmd: List[str] = ["ocrmypdf", "--skip-text", pdf_path, output_path]
    if pages:
        cmd.extend(["--pages", ",".join(map(str, pages))])
    try:
        # Never capture huge stdout/stderr into RAM (long runs can trigger MemoryError in _readerthread).
        subprocess.run(
            cmd,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=None,
        )
        return output_path
    except Exception as e:
        logger.error(f"OCRmyPDF thất bại: {e}")
        raise


def convert_pdf_to_docx(pdf_path: str, output_path: str, pages: Optional[List[int]] = None) -> str:
    """Convert PDF → DOCX trực tiếp bằng pdf2docx."""
    _get_pdf_refs()
    if Converter is None:
        raise PDFProcessorError("pdf2docx chưa được cài đặt.")
    cv = Converter(pdf_path)
    if pages:
        cv.convert(output_path, pages=[p - 1 for p in pages])
    else:
        cv.convert(output_path)
    cv.close()
    return output_path


def create_docx_from_pdf(
    pdf_path: str,
    output_path: str,
    ocr_cfg: dict,
    pages: Optional[List[int]] = None,
    apply_cleanup: bool = True,
    apply_spell_check: bool = True,
) -> str:
    """Tạo file DOCX từ PDF có text layer (Backward compatibility)."""
    # Sử dụng local import để tránh circular dependency
    from .docx_processor import create_docx_from_processed_text

    pages_data, total_pages = extract_text_and_images_from_pdf(pdf_path, ocr_cfg, pages)
    return create_docx_from_processed_text(pages_data, output_path, ocr_cfg)


async def hybrid_workflow_pdf_to_docx(
    pdf_path: str,
    output_path: str,
    ocr_cfg: dict,
    pages: Optional[List[int]] = None,
    key_manager: Any = None,
) -> str:
    """Hybrid workflow: PDF → DOCX (via pdf2docx) → Cleanup & Spell Check → DOCX. key_manager: dùng chung pool/cooldown nếu có."""
    # Local imports to avoid circular deps
    from .docx_processor import (
        batch_small_paragraphs,
        cleanup_paragraph_with_hints,
        extract_paragraphs_with_hints,
        update_docx_with_processed_text,
    )

    logger.info("🚀 BẮT ĐẦU QUY TRÌNH LAI")
    temp_docx = output_path.replace(".docx", "_temp_raw.docx")
    convert_pdf_to_docx(pdf_path, temp_docx, pages)

    paragraphs_data = extract_paragraphs_with_hints(temp_docx)
    batched = batch_small_paragraphs(paragraphs_data)

    processed = []
    for para in batched:
        processed.append(await cleanup_paragraph_with_hints(para, ocr_cfg, key_manager=key_manager))

    update_docx_with_processed_text(temp_docx, processed, ocr_cfg)
    os.replace(temp_docx, output_path)
    return output_path


def extract_text_and_images_from_pdf(
    pdf_path: str, ocr_cfg: dict, pages: Optional[List[int]] = None
) -> tuple[List[dict], int]:
    """Extract text và images từ PDF có text layer."""
    _get_pdf_refs()
    pages_data = []
    if fitz is not None:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        indices = [i - 1 for i in pages if 1 <= i <= total_pages] if pages else range(total_pages)
        for i in indices:
            page = doc[i]
            text = page.get_text()
            images = []
            for img_index, img in enumerate(page.get_images()):
                xref = img[0]
                base_image = doc.extract_image(xref)
                images.append({"data": base_image["image"], "ext": base_image["ext"]})
            pages_data.append({"page_num": i + 1, "text": text, "images": images})
        doc.close()
        return pages_data, total_pages
    return [], 0


def _normalize_pdf_ocr_page_list(
    pdf_path: str,
    pages: Optional[List[int]],
    poppler_path: Optional[str],
    userpw: Optional[str] = None,
) -> List[int]:
    """Return sorted unique 1-based page indices to OCR."""
    from pdf2image import pdfinfo_from_path

    info = pdfinfo_from_path(pdf_path, userpw=userpw, poppler_path=poppler_path)
    total = int(info.get("Pages", 0))
    if total < 1:
        return []
    if pages is not None:
        if len(pages) == 0:
            return []
        return sorted({p for p in pages if 1 <= p <= total})
    return list(range(1, total + 1))


def ocr_pdf(
    pdf_path: str, config_path: str = "config/config.yaml", pages: Optional[List[int]] = None
) -> tuple[str, int]:
    """
    OCR scan PDF: render each page to disk, then OCR one image at a time.

    pdf2image without output_folder buffers Poppler stdout in memory; large
    PDFs cause MemoryError. Per-page output_folder + paths_only avoids that.
    """
    from PIL import Image

    from .config_loader import _detect_bundled_binaries, load_ocr_config
    from .dependency_manager import apply_tesseract_cfg as _apply_tesseract_cfg
    from .image_processor import _image_to_text

    ocr_cfg = _detect_bundled_binaries(load_ocr_config(config_path))
    _get_pdf_refs(ocr_cfg)
    _apply_tesseract_cfg(ocr_cfg)

    if convert_from_path is None:
        raise PDFProcessorError("pdf2image chưa được cài đặt.")

    poppler = ocr_cfg.get("poppler_path") or None
    if poppler == "":
        poppler = None
    userpw = ocr_cfg.get("pdf_password") or ocr_cfg.get("userpw")

    dpi = int(ocr_cfg.get("dpi", 250) or 250)
    fmt = str(
        ocr_cfg.get("pdf_ocr_render_fmt") or ocr_cfg.get("image_format", "jpeg") or "jpeg"
    ).lower()
    if fmt not in ("jpeg", "jpg", "png", "ppm", "tiff", "tif"):
        fmt = "jpeg"
    if fmt == "jpg":
        fmt = "jpeg"
    q = int(ocr_cfg.get("jpeg_quality", 90) or 90)
    jpegopt = {"quality": min(100, max(1, q)), "optimize": True}

    page_list = _normalize_pdf_ocr_page_list(pdf_path, pages, poppler, userpw=userpw)
    if not page_list:
        return "", 0

    log_every = max(1, int(ocr_cfg.get("pdf_ocr_progress_pages", 25) or 25))
    texts: List[str] = []
    work_root = tempfile.mkdtemp(prefix="mtranslator_pdf_ocr_")

    try:
        for idx, page_num in enumerate(page_list):
            page_dir = os.path.join(work_root, f"w{page_num:06d}")
            os.makedirs(page_dir, exist_ok=True)
            try:
                image_paths: List[str] = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    first_page=page_num,
                    last_page=page_num,
                    output_folder=page_dir,
                    fmt=fmt,
                    paths_only=True,
                    thread_count=1,
                    poppler_path=poppler,
                    userpw=userpw,
                    jpegopt=jpegopt if fmt == "jpeg" else None,
                )
                for img_path in image_paths:
                    try:
                        with Image.open(img_path) as im:
                            text = _image_to_text(im, ocr_cfg)
                            texts.append(text)
                    finally:
                        try:
                            os.remove(img_path)
                        except OSError:
                            pass
            finally:
                shutil.rmtree(page_dir, ignore_errors=True)

            if (idx + 1) % log_every == 0 or idx + 1 == len(page_list):
                logger.info(f"OCR scan PDF: đã xử lý {idx + 1}/{len(page_list)} trang")

            gc.collect()

    finally:
        shutil.rmtree(work_root, ignore_errors=True)

    return "\n\n".join(texts), len(page_list)
