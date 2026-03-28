# -*- coding: utf-8 -*-
from __future__ import annotations

"""
OCR reader module: extract text from scanned PDFs or images based on settings in config/config.yaml.

Dependencies:
- pytesseract (Python wrapper for Tesseract OCR)
- pdf2image (convert PDF pages to images)
- Pillow (image processing)
- PyYAML (read YAML config)

Config example in config/config.yaml:
  ocr:
    enabled: true
    tesseract_cmd: "C:/Program Files/Tesseract-OCR/tesseract.exe"
    lang: "vie+eng"
    psm: 3
    dpi: 300
"""

import asyncio
import concurrent.futures
import gc
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Thêm project root vào sys.path nếu chạy trực tiếp
# Để có thể import từ src.utils.helpers
if __name__ == "__main__":
    # Tìm project root (thư mục chứa src)
    current_file = Path(__file__).resolve()
    # current_file = src/preprocessing/ocr_reader.py
    # project_root = thư mục chứa src
    project_root = current_file.parent.parent.parent
    project_root_str = str(project_root)
    # Chỉ thêm nếu chưa có trong sys.path
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

# Suppress noisy logs từ Google libraries (absl, gRPC) trước khi import
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"  # Suppress INFO và WARNING từ GLOG/absl
os.environ["GRPC_PYTHON_LOG_LEVEL"] = "ERROR"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # Suppress TensorFlow logs nếu có


# Define StderrFilter trước để filter stderr ngay từ đầu
# Import from modularized ocr subpackage
from .ocr import (
    GoogleLogFilter,
    NoisyMessageFilter,
    _build_safety_settings,
    _bundle_base_dir,
    _count_cjk_characters,
    _detect_bundled_binaries,
    _detect_chinese_variant,
    _ensure_logger_config,
    _image_to_text,
    _is_cjk_character,
    _load_yaml,
    _normalize_lang_code,
    _parse_pages,
    # New Phase 2B modular imports
    _pip_install,
    _preprocess_image_for_ocr,
    _resolve_language,
    _suppress_google_logs,
    apply_tesseract_cfg,
    ensure_dependencies,
    load_ocr_config,
)

# Legacy: NoisyMessageFilter now imported from .ocr.logging_filters
# Alias cho backward compatibility
StderrFilter = NoisyMessageFilter

# Suppress warnings từ absl trước khi import google libraries
try:
    import absl.logging

    absl.logging.set_verbosity(absl.logging.ERROR)
except Exception:
    pass

# Suppress logging từ các Google libraries
for lib_name in [
    "google",
    "grpc",
    "absl",
    "google.generativeai",
    "google.api_core",
    "google.auth",
]:
    lib_logger = logging.getLogger(lib_name)
    lib_logger.setLevel(logging.ERROR)
    lib_logger.propagate = False

# Filter stderr ngay từ đầu để chặn messages in trực tiếp
# (không filter stdout ở đây để không ảnh hưởng đến user interaction)
_stderr_filter_active = False
_stdout_filter_active = False
try:
    original_stderr = sys.stderr
    sys.stderr = NoisyMessageFilter(original_stderr)
    _stderr_filter_active = True
except Exception:
    pass

import yaml

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

try:
    from tqdm import tqdm  # progress bar (optional)
except Exception:
    tqdm = None

try:
    import PyPDF2
except Exception:
    PyPDF2 = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from docx import Document
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    from docx.shared import Inches, Pt
except Exception:
    Document = None

# pdf2docx và ocrmypdf sẽ được import lazy trong _ensure_dependencies để tránh treo khi load module
Converter = None

# OCRmyPDF (for fallback when pdf2docx fails)
ocrmypdf_available = False
ocrmypdf = None

logger = logging.getLogger("NovelTranslator")

def _call_with_hard_timeout(
    func: Any,
    timeout_seconds: Optional[float],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Gọi hàm sync với hard-timeout. Nếu quá hạn sẽ raise TimeoutError.

    Lý do: Một số call có thể bị block lâu (ví dụ chờ key/quota), cần cơ chế cắt ở tầng OCR reader
    để tránh treo toàn pipeline.
    """
    if timeout_seconds is None or timeout_seconds <= 0:
        return func(*args, **kwargs)
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(func, *args, **kwargs)
    timed_out = False
    try:
        return fut.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError:
        timed_out = True
        # Không chờ thread đang chạy xong (tránh treo toàn pipeline).
        # cancel_futures chỉ hủy được task chưa bắt đầu; nếu đang chạy thì thread vẫn chạy nền và sẽ tự kết thúc.
        ex.shutdown(wait=False, cancel_futures=True)
        raise
    finally:
        # Nếu không timeout thì tắt executor bình thường.
        if not timed_out:
            ex.shutdown(wait=True, cancel_futures=False)


# Legacy: _suppress_google_logs, _stderr_filter_active now imported from .ocr.logging_filters


# Legacy: _parse_pages now imported from .ocr.config_loader
# Legacy: config functions now imported from .ocr.config_loader
# (_ensure_logger_config, _load_yaml, load_ocr_config, _build_safety_settings,
#  _bundle_base_dir, _detect_bundled_binaries)


from src.utils.helpers import lazy_import_and_install

from ..services.genai_adapter import create_client

# Xử lý relative imports khi chạy trực tiếp
try:
    from .ai_table_recovery import AITableRecovery
    from .docx_postprocessor import postprocess_docx
    from .pdf_precleaner import preclean_pdf
    from .table_marker_extractor import extract_tables_as_marked_text
except ImportError:
    # Fallback khi chạy trực tiếp (không phải package)
    from src.preprocessing.ai_table_recovery import AITableRecovery
    from src.preprocessing.docx_postprocessor import postprocess_docx
    from src.preprocessing.pdf_precleaner import preclean_pdf
    from src.preprocessing.table_marker_extractor import extract_tables_as_marked_text


def _pip_install(package: str) -> None:
    """Helper to install a package using pip. Delegated to .ocr.dependency_manager."""
    from .ocr import _pip_install as modular_pip_install

    modular_pip_install(package)


def _ensure_dependencies(ocr_cfg: dict) -> None:
    """Ensure all required dependencies are installed. Delegated to .ocr.dependency_manager."""
    # We call modular ensure_dependencies and update our local globals
    deps = ensure_dependencies(ocr_cfg)
    globals().update(deps)


def _apply_tesseract_cfg(ocr_cfg: dict) -> None:
    """Apply Tesseract configuration. Delegated to .ocr.dependency_manager."""
    from .ocr import apply_tesseract_cfg as modular_apply_tesseract_cfg

    modular_apply_tesseract_cfg(ocr_cfg, pytesseract)


# Legacy: language functions now imported from .ocr.language_utils
# (_normalize_lang_code, _is_cjk_character, _count_cjk_characters)


# Legacy comment: Language detection functions (_detect_language_from_image,
# _detect_language_from_multiple_pages) were deprecated and removed.
# Auto-detect was ineffective in practice. Use explicit language config instead.


def _detect_chinese_variant(img: "Image.Image", ocr_cfg: dict) -> str:
    """
    Tự động nhận biết tiếng Trung giản thể hay phồn thể.
    Returns: "chi_sim" hoặc "chi_tra"
    """
    psm = int(ocr_cfg.get("psm", 3) or 3)
    config = f"--psm {psm}"

    try:
        # OCR với cả 2 ngôn ngữ và so sánh confidence
        # Simplified Chinese
        data_sim = pytesseract.image_to_data(img, lang="chi_sim", config=config, output_type=pytesseract.Output.DICT)
        confidences_sim = [int(conf) for conf in data_sim["conf"] if int(conf) > 0]
        avg_conf_sim = sum(confidences_sim) / len(confidences_sim) if confidences_sim else 0
        # Đếm số ký tự được nhận dạng (có confidence > 0)
        char_count_sim = sum(
            1 for i, text_item in enumerate(data_sim["text"]) if text_item.strip() and int(data_sim["conf"][i]) > 0
        )

        # Traditional Chinese
        data_tra = pytesseract.image_to_data(img, lang="chi_tra", config=config, output_type=pytesseract.Output.DICT)
        confidences_tra = [int(conf) for conf in data_tra["conf"] if int(conf) > 0]
        avg_conf_tra = sum(confidences_tra) / len(confidences_tra) if confidences_tra else 0
        # Đếm số ký tự được nhận dạng (có confidence > 0)
        char_count_tra = sum(
            1 for i, text_item in enumerate(data_tra["text"]) if text_item.strip() and int(data_tra["conf"][i]) > 0
        )

        # Quyết định dựa trên confidence và số ký tự
        # Ưu tiên confidence, nếu gần bằng nhau thì ưu tiên số ký tự nhiều hơn
        score_sim = avg_conf_sim * 0.7 + (char_count_sim / max(char_count_sim + char_count_tra, 1)) * 30 * 0.3
        score_tra = avg_conf_tra * 0.7 + (char_count_tra / max(char_count_sim + char_count_tra, 1)) * 30 * 0.3

        if score_sim > score_tra:
            detected = "chi_sim"
            logger.debug(
                f"Phát hiện biến thể tiếng Trung: Giản thể (conf: {avg_conf_sim:.1f}, chars: {char_count_sim})"
            )
        else:
            detected = "chi_tra"
            logger.debug(
                f"Phát hiện biến thể tiếng Trung: Phồn thể (conf: {avg_conf_tra:.1f}, chars: {char_count_tra})"
            )

        return detected
    except Exception as e:
        # Fallback: mặc định là Simplified (phổ biến hơn)
        logger.warning(f"Không thể phát hiện biến thể tiếng Trung: {e}. Mặc định dùng chi_sim")
        return "chi_sim"


def _resolve_language(lang: str, ocr_cfg: dict, sample_img: Optional["Image.Image"] = None) -> str:
    """
    Resolve language code, chỉ hỗ trợ Chinese variant detection (giản thể/phồn thể).
    Auto-detect ngôn ngữ đã được loại bỏ do kém hiệu quả.

    Args:
        lang: Language string từ config (có thể là "VN", "EN", "CN", "VN+EN", "chi", "chi_sim", "chi_tra", etc.)
        ocr_cfg: OCR config
        sample_img: Optional sample image để detect Chinese variant (chỉ khi lang="CN" hoặc "chi")

    Returns:
        Resolved language string cho Tesseract (e.g., "chi_sim", "chi_tra", "vie+eng")
    """
    if not lang:
        return "vie"

    # Normalize: VN/EN/CN → vie/eng/chi
    lang = _normalize_lang_code(lang)

    # Loại bỏ auto-detect: nếu config là "auto", cảnh báo và fallback về "vie"
    if lang == "auto" or lang.startswith("auto+"):
        logger.warning(
            f"Auto-detect ngôn ngữ đã bị loại bỏ do kém hiệu quả. "
            f"Config '{lang}' không được hỗ trợ. Vui lòng chỉ định rõ ngôn ngữ (VN/EN/CN). "
            f"Fallback về 'vie'."
        )
        lang = "vie"

    # Chỉ hỗ trợ detect Chinese variant (giản thể/phồn thể) khi lang="CN" hoặc "chi"
    # Kiểm tra nếu có "chi" (cần detect variant: Simplified vs Traditional)
    if "chi" in lang.lower() and "chi_sim" not in lang and "chi_tra" not in lang:
        # Cần detect variant
        if sample_img is not None:
            detected_variant = _detect_chinese_variant(sample_img, ocr_cfg)
            # Replace "chi" bằng variant detected
            lang = lang.replace("chi", detected_variant).replace("Chi", detected_variant)
            # Clean up duplicate "+" nếu có
            lang = lang.replace(f"{detected_variant}+{detected_variant}", detected_variant)
            logger.info(f"Tự động phát hiện biến thể tiếng Trung: {detected_variant} → Ngôn ngữ: {lang}")
        else:
            # Không có sample image → mặc định Simplified
            detected_variant = "chi_sim"
            lang = lang.replace("chi", detected_variant).replace("Chi", detected_variant)
            logger.info(f"Không có ảnh mẫu để phát hiện, mặc định dùng chi_sim → Ngôn ngữ: {lang}")

    return lang


# Logic moved to .ocr.image_processor._preprocess_image_for_ocr
# Wrapper remains for local usage within this file
def _preprocess_image_for_ocr(img: "Image.Image", ocr_cfg: dict) -> "Image.Image":
    from .ocr import _preprocess_image_for_ocr as modular_preprocess

    return modular_preprocess(img, ocr_cfg)


# Logic moved to .ocr.image_processor._image_to_text
def _image_to_text(img: "Image.Image", ocr_cfg: dict, lang_override: Optional[str] = None) -> str:
    from .ocr import _image_to_text as modular_image_to_text

    return modular_image_to_text(img, ocr_cfg, lang_override)


def detect_pdf_type(pdf_path: str, ocr_cfg: Optional[dict] = None) -> str:
    """Phát hiện PDF là scan hay text-based. Delegated to .ocr."""
    from .ocr import detect_pdf_type as _delegate

    return _delegate(pdf_path, ocr_cfg)


def extract_text_from_pdf(pdf_path: str, ocr_cfg: dict, pages: Optional[List[int]] = None) -> str:
    """Extract text từ PDF có text layer. Delegated to .ocr."""
    from .ocr import extract_text_from_pdf as _delegate

    return _delegate(pdf_path, ocr_cfg, pages)


def extract_text_blocks_with_position(
    pdf_path: str, ocr_cfg: dict, pages: Optional[List[int]] = None
) -> tuple[List[dict], int]:
    """Extract text blocks với Y-position từ PDF. Delegated to .ocr."""
    from .ocr import extract_text_blocks_with_position as _delegate

    return _delegate(pdf_path, ocr_cfg, pages)


def extract_format_hints(para, para_index: int, total_paragraphs: int) -> dict:
    """Extract format hints chi tiết từ paragraph. Delegated to .ocr."""
    from .ocr import extract_format_hints as _delegate

    return _delegate(para, para_index, total_paragraphs)


def is_in_table(para) -> bool:
    """Check nếu paragraph nằm trong table. Delegated to .ocr."""
    from .ocr.docx_processor import is_in_table as _is_in_table

    return _is_in_table(para)


def extract_images_from_paragraph(para) -> List[dict]:
    """Extract images từ paragraph. Delegated to .ocr."""
    from .ocr.docx_processor import extract_images_from_paragraph as _extract_images_from_paragraph

    return _extract_images_from_paragraph(para)


def extract_paragraphs_with_hints(docx_path: str) -> List[dict]:
    """Extract paragraphs từ DOCX với format hints và images. Delegated to .ocr."""
    from .ocr.docx_processor import extract_paragraphs_with_hints as _extract_paragraphs_with_hints

    return _extract_paragraphs_with_hints(docx_path)


def batch_small_paragraphs(paragraphs_data: List[dict], min_chars: int = 50) -> List[dict]:
    """Batch các paragraphs nhỏ lại với nhau. Delegated to .ocr."""
    from .ocr.docx_processor import batch_small_paragraphs as _batch_small_paragraphs

    return _batch_small_paragraphs(paragraphs_data, min_chars)


def build_cleanup_prompt_with_hints(text: str, hints: dict) -> str:
    """Build cleanup prompt với format hints chi tiết. Delegated to .ocr."""
    from .ocr.docx_processor import build_cleanup_prompt_with_hints as _build_cleanup_prompt_with_hints

    return _build_cleanup_prompt_with_hints(text, hints)


def cleanup_paragraph_with_hints(
    para_data: dict, ocr_cfg: dict, key_manager: Any = None
) -> dict:
    """Cleanup một paragraph/batch với format hints. Delegated to .ocr."""
    from .ocr.docx_processor import cleanup_paragraph_with_hints as _cleanup_paragraph_with_hints

    return _cleanup_paragraph_with_hints(para_data, ocr_cfg, key_manager=key_manager)


def spell_check_paragraph(
    para_data: dict, ocr_cfg: dict, key_manager: Any = None
) -> str:
    """Spell check một paragraph/batch. Delegated to .ocr."""
    from .ocr.docx_processor import spell_check_paragraph as _spell_check_paragraph

    return _spell_check_paragraph(para_data, ocr_cfg, key_manager=key_manager)


def convert_pdf_with_ocrmypdf(pdf_path: str, output_path: str, ocr_cfg: dict, pages: Optional[List[int]] = None) -> str:
    """PDF -> PDF searchable bằng OCRmyPDF. Delegated to .ocr."""
    from .ocr.pdf_processor import convert_pdf_with_ocrmypdf as _convert_pdf_with_ocrmypdf

    return _convert_pdf_with_ocrmypdf(pdf_path, output_path, ocr_cfg, pages)


def convert_pdf_to_docx(pdf_path: str, output_path: str, pages: Optional[List[int]] = None) -> str:
    """PDF -> DOCX trực tiếp bằng pdf2docx. Delegated to .ocr."""
    from .ocr.pdf_processor import convert_pdf_to_docx as _convert_pdf_to_docx

    return _convert_pdf_to_docx(pdf_path, output_path, pages)


def update_paragraph_in_place(para: Any, new_text: str) -> None:
    """Update paragraph text nhưng giữ nguyên formatting. Delegated to .ocr."""
    from .ocr.docx_processor import update_paragraph_in_place as _update_paragraph_in_place

    _update_paragraph_in_place(para, new_text)


def re_insert_images_to_paragraph(para: Any, images: List[Dict[str, Any]]) -> None:
    """Re-insert images vào paragraph. Delegated to .ocr."""
    from .ocr.docx_processor import re_insert_images_to_paragraph as _re_insert_images_to_paragraph

    _re_insert_images_to_paragraph(para, images)


def split_batched_result(batched_text: str, original_count: int) -> List[str]:
    """Split batched result về số paragraphs ban đầu. Delegated to .ocr."""
    from .ocr.docx_processor import split_batched_result as _split_batched_result

    return _split_batched_result(batched_text, original_count)


def update_docx_with_processed_text(docx_path: str, processed_paragraphs: List[dict], ocr_cfg: dict) -> str:
    """Update DOCX với processed text. Delegated to .ocr."""
    from .ocr.docx_processor import update_docx_with_processed_text as _update_docx_with_processed_text

    return _update_docx_with_processed_text(docx_path, processed_paragraphs, ocr_cfg)


def convert_docx_to_epub(docx_path: str, epub_path: str, ocr_cfg: dict) -> str:
    """Convert DOCX -> EPUB using pypandoc. Delegated to .ocr."""
    from .ocr.docx_processor import convert_docx_to_epub as _convert_docx_to_epub

    return _convert_docx_to_epub(docx_path, epub_path, ocr_cfg)


def hybrid_workflow_pdf_to_docx(
    pdf_path: str,
    output_path: str,
    ocr_cfg: dict,
    pages: Optional[List[int]] = None,
    key_manager: Any = None,
) -> str:
    """Hybrid workflow: PDF -> DOCX -> Cleanup & Spell Check -> DOCX. Delegated to .ocr."""
    from .ocr.pdf_processor import hybrid_workflow_pdf_to_docx as _hybrid_workflow_pdf_to_docx

    return _hybrid_workflow_pdf_to_docx(pdf_path, output_path, ocr_cfg, pages, key_manager=key_manager)


def extract_text_and_images_from_pdf(
    pdf_path: str, ocr_cfg: dict, pages: Optional[List[int]] = None
) -> tuple[List[dict], int]:
    """Extract text và images từ PDF có text layer. Delegated to .ocr."""
    from .ocr.pdf_processor import extract_text_and_images_from_pdf as _extract_text_and_images_from_pdf

    return _extract_text_and_images_from_pdf(pdf_path, ocr_cfg, pages)


def create_docx_from_processed_text(
    pdf_path: str,
    output_path: str,
    processed_text: str,
    ocr_cfg: dict,
    pages: Optional[List[int]] = None,
) -> str:
    """Tạo file DOCX từ text đã xử lý và images từ PDF. Delegated to .ocr."""
    from .ocr.pdf_processor import create_docx_from_processed_text as _create_docx_from_processed_text

    return _create_docx_from_processed_text(pdf_path, output_path, processed_text, ocr_cfg, pages)


def create_docx_from_pdf(
    pdf_path: str,
    output_path: str,
    ocr_cfg: dict,
    pages: Optional[List[int]] = None,
    apply_cleanup: bool = True,
    apply_spell_check: bool = True,
) -> str:
    """Tạo file DOCX từ PDF có text layer. Delegated to .ocr."""
    from .ocr.pdf_processor import create_docx_from_pdf as _create_docx_from_pdf

    return _create_docx_from_pdf(pdf_path, output_path, ocr_cfg, pages, apply_cleanup, apply_spell_check)


def _fix_docx_leading_tabs_and_soft_wraps(docx_path: str) -> None:
    """
    Khắc phục các tab thừa đầu dòng do soft-wrap khi convert PDF→DOCX (pdf2docx).
    Quy tắc an toàn (không xâm phạm layout nhiều):
    - Nếu một paragraph bắt đầu bằng tab (\t) và ký tự đầu tiên có nghĩa sau tab là chữ thường/không phải số/bullet,
      và paragraph trước đó KHÔNG kết thúc bằng dấu câu (., !, ?), thì loại bỏ các tab/space đầu paragraph đó.
    - Không merge/xóa paragraph để tránh rủi ro layout; chỉ loại bỏ tab đầu dòng gây xấu văn bản.
    """
    try:
        if Document is None:
            return
        doc = Document(docx_path)
        prev_text = ""
        for para in doc.paragraphs:
            full_text = para.text or ""
            try:
                import re
            except Exception:
                re = None

            # Bỏ qua đoạn có URL để tránh phá hyperlink/format
            if re and re.search(r"https?://\S+", full_text):
                prev_text = full_text
                continue

            # 1) Loại tab nội tuyến trong từng run để giữ hyperlink và format
            for run in getattr(para, "runs", []):
                if not run.text:
                    continue
                if re:
                    new_run_text = re.sub(r"\s*\t+\s*", " ", run.text)
                else:
                    new_run_text = run.text.replace("\t", " ")
                if new_run_text != run.text:
                    run.text = new_run_text

            # Cập nhật lại full_text sau bước (1)
            full_text = para.text or ""
            stripped = full_text.lstrip("\t ")
            starts_with_tab = full_text != stripped
            prev_ends_with_punct = bool(re.search(r"[.!?]$", prev_text.strip())) if (re and prev_text) else False
            is_bullet_like = (
                bool(re.match(r"^[•·\-*]\s", stripped)) or bool(re.match(r"^\d+[.)]\s", stripped)) if re else False
            )

            # 2) Loại tab/space đầu đoạn (continuation của câu trước), chỉ tác động lên runs đầu
            if starts_with_tab and not prev_ends_with_punct and not is_bullet_like:
                remaining_to_strip = len(full_text) - len(stripped)
                # Bỏ qua nếu stripping làm rỗng hoàn toàn (an toàn)
                if remaining_to_strip > 0 and stripped:
                    for run in getattr(para, "runs", []):
                        if remaining_to_strip <= 0:
                            break
                        if not run.text:
                            continue
                        run_len = len(run.text)
                        # Tính số ký tự whitespace đầu run có thể cắt
                        prefix = 0
                        while prefix < run_len and remaining_to_strip > 0 and run.text[prefix] in ("\t", " "):
                            prefix += 1
                            remaining_to_strip -= 1
                        if prefix > 0:
                            run.text = run.text[prefix:]
                        # Nếu run không còn whitespace đầu và vẫn còn remaining_to_strip, tiếp tục sang run kế

            prev_text = para.text or ""
        doc.save(docx_path)
    except Exception:
        # Không chặn pipeline nếu chỉnh sửa thất bại
        pass


async def _cleanup_chunk_async(
    chunk: str,
    api_key: str,
    model_name: str,
    prompt: str,
    chunk_idx: int,
    total_chunks: int,
    timeout_s: float,
    safety_settings: Optional[List[dict]] = None,
    use_new_sdk: bool = True,
) -> str:
    """Cleanup một chunk text bằng AI (async). Delegated to .ocr."""
    from .ocr.ai_processor import _cleanup_chunk_async as _cleanup_chunk_async_impl

    return await _cleanup_chunk_async_impl(
        chunk, api_key, model_name, prompt, chunk_idx, total_chunks, timeout_s, safety_settings, use_new_sdk
    )


def ai_cleanup_text(
    text: str, ocr_cfg: Dict[str, Any], key_manager: Any = None
) -> Tuple[str, List[int], List[str]]:
    """Sử dụng AI để dọn rác text. Delegated to .ocr."""
    from .ocr.ai_processor import ai_cleanup_text as _ai_cleanup_text

    return _ai_cleanup_text(text, ocr_cfg, key_manager=key_manager)


async def _ai_cleanup_parallel(
    text_chunks: List[str],
    api_keys: List[str],
    model_name: str,
    prompt: str,
    max_parallel: int,
    delay: float,
    show_progress: bool,
    timeout_s: float,
    max_retries: int,
    progress_interval: float,
    safety_settings: Optional[List[dict]] = None,
) -> Tuple[str, int, int, List[int]]:
    """Xử lý song song nhiều chunks với nhiều API keys. Delegated to .ocr."""
    from .ocr.ai_processor import _ai_cleanup_parallel as _ai_cleanup_parallel_impl

    return await _ai_cleanup_parallel_impl(
        text_chunks,
        api_keys,
        model_name,
        prompt,
        max_parallel,
        delay,
        show_progress,
        timeout_s,
        max_retries,
        progress_interval,
        safety_settings,
    )


async def _as_completed_iter(coros):
    """Yield futures as they complete. Delegated to .ocr."""
    from .ocr.ai_processor import _as_completed_iter as _as_completed_iter_impl

    async for result in _as_completed_iter_impl(coros):
        yield result


def _split_text_at_sentence_boundaries(text: str, max_chunk_size: int) -> List[str]:
    """Chia text thành chunks ở ranh giới câu. Delegated to .ocr."""
    from .ocr.ai_processor import _split_text_at_sentence_boundaries as _split_impl

    return _split_impl(text, max_chunk_size)


def _preprocess_line_breaks(text: str) -> str:
    """Nối lại các câu bị ngắt do line breaks. Delegated to .ocr."""
    from .ocr.ai_processor import _preprocess_line_breaks as _preprocess_impl

    return _preprocess_impl(text)


async def _spell_check_chunk_async(
    chunk: str,
    api_key: str,
    model_name: str,
    prompt: str,
    chunk_idx: int,
    total_chunks: int,
    timeout_s: float,
    safety_settings: Optional[List[dict]] = None,
    use_new_sdk: bool = True,
) -> str:
    """Soát lỗi chính tả và phục hồi paragraph bằng AI (async). Delegated to .ocr."""
    from .ocr.ai_processor import _spell_check_chunk_async as _spell_check_chunk_async_impl

    return await _spell_check_chunk_async_impl(
        chunk, api_key, model_name, prompt, chunk_idx, total_chunks, timeout_s, safety_settings, use_new_sdk
    )


async def _ai_spell_check_parallel(
    text_chunks: List[str],
    api_keys: List[str],
    model_name: str,
    prompt: str,
    max_parallel: int,
    delay: float,
    show_progress: bool,
    timeout_s: float,
    max_retries: int,
    progress_interval: float,
    safety_settings: Optional[List[dict]] = None,
) -> Tuple[str, int, int, List[int]]:
    """Xử lý song song cho spell check. Delegated to .ocr."""
    from .ocr.ai_processor import _ai_spell_check_parallel as _ai_spell_check_parallel_impl

    return await _ai_spell_check_parallel_impl(
        text_chunks,
        api_keys,
        model_name,
        prompt,
        max_parallel,
        delay,
        show_progress,
        timeout_s,
        max_retries,
        progress_interval,
        safety_settings,
    )


def ai_spell_check_and_paragraph_restore(
    text: str, ocr_cfg: Dict[str, Any], key_manager: Any = None
) -> Tuple[str, List[int], List[str]]:
    """Sử dụng AI để soát lỗi chính tả. Delegated to .ocr."""
    from .ocr import ai_spell_check_and_paragraph_restore as _ai_spell_check

    return _ai_spell_check(text, ocr_cfg, key_manager=key_manager)


def _retry_failed_chunks_cleanup(
    failed_indices: List[int],
    all_chunks: List[str],
    api_keys: List[str],
    model_name: str,
    prompt: str,
    ocr_cfg: Dict[str, Any],
) -> Tuple[Dict[int, str], List[int]]:
    """Retry các chunk failed cho AI Cleanup. Delegated to .ocr."""
    from .ocr.ai_processor import _retry_failed_chunks_cleanup as _retry_impl

    return _retry_impl(failed_indices, all_chunks, api_keys, model_name, prompt, ocr_cfg)


def _retry_failed_chunks_spell_check(
    failed_indices: List[int],
    all_chunks: List[str],
    api_keys: List[str],
    model_name: str,
    prompt: str,
    ocr_cfg: Dict[str, Any],
) -> Tuple[Dict[int, str], List[int]]:
    """Retry các chunk failed cho AI Spell Check. Delegated to .ocr."""
    from .ocr.ai_processor import _retry_failed_chunks_spell_check as _retry_impl

    return _retry_impl(failed_indices, all_chunks, api_keys, model_name, prompt, ocr_cfg)


def _get_intermediate_file_path(output_path: str, suffix: str) -> str:
    """Tạo đường dẫn file tạm thời dựa trên output_path và suffix."""
    output_dir = os.path.dirname(output_path) if os.path.dirname(output_path) else "."
    output_basename = os.path.basename(output_path)
    output_name_without_ext = os.path.splitext(output_basename)[0]
    return os.path.join(output_dir, output_name_without_ext + suffix)


def _cleanup_intermediate_files(output_path: str):
    """
    Xóa các file trung gian (_ocred.txt, _cleanup.txt) sau khi đã tạo file final.

    Args:
        output_path: Đường dẫn file output final (để tạo tên file trung gian)
    """
    intermediate_files = [
        _get_intermediate_file_path(output_path, "_ocred.txt"),
        _get_intermediate_file_path(output_path, "_cleanup.txt"),
    ]

    for file_path in intermediate_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"🗑️  Đã xóa file trung gian: {file_path}")
        except Exception as e:
            logger.debug(f"Không thể xóa file trung gian {file_path}: {e}")


def _check_existing_files(output_path: str) -> Dict[str, Any]:
    """Kiểm tra các file đã tồn tại từ phiên làm việc trước."""
    results = {"ocred": None, "cleanup": None, "output": None, "all_exist": False}

    ocred_path = _get_intermediate_file_path(output_path, "_ocred.txt")
    cleanup_path = _get_intermediate_file_path(output_path, "_cleanup.txt")

    if os.path.exists(ocred_path):
        results["ocred"] = ocred_path
    if os.path.exists(cleanup_path):
        results["cleanup"] = cleanup_path
    if os.path.exists(output_path):
        results["output"] = output_path

    results["all_exist"] = any([results["ocred"], results["cleanup"], results["output"]])
    return results


def _load_resume_file(file_path: str, step_name: str) -> Optional[str]:
    """Load file từ phiên trước để resume."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"✅ Đã load file {step_name}: {file_path}")
        return content
    except Exception as e:
        logger.warning(f"Không thể load file {step_name} ({file_path}): {e}")
        return None


def _show_completion_menu(cleanup_failed: int, spell_check_failed: int, output_path: str = None) -> str:
    """Hiển thị menu lựa chọn sau OCR hoàn tất. Delegated to .ocr.menu_handler."""
    from .ocr import _show_completion_menu as modular_impl

    return modular_impl(cleanup_failed, spell_check_failed, output_path)


def ocr_image(image_path: str, config_path: str = "config/config.yaml") -> str:
    """OCR một ảnh thành text. Delegated to .ocr."""
    from PIL import Image

    from .ocr import (
        _detect_bundled_binaries,
        _image_to_text,
        _normalize_lang_code,
        _resolve_language,
        apply_tesseract_cfg,
        ensure_dependencies,
        load_ocr_config,
    )

    ocr_cfg = _detect_bundled_binaries(load_ocr_config(config_path))
    ensure_dependencies(ocr_cfg)
    apply_tesseract_cfg(ocr_cfg)

    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)

    img = Image.open(image_path)
    raw_lang = ocr_cfg.get("lang", "vie")
    normalized_lang = _normalize_lang_code(raw_lang)

    # Chỉ detect Chinese variant nếu lang="CN" hoặc "chi"
    needs_chinese_variant_detection = (
        "chi" in normalized_lang.lower() and "chi_sim" not in normalized_lang and "chi_tra" not in normalized_lang
    )

    if needs_chinese_variant_detection:
        resolved_lang = _resolve_language(raw_lang, ocr_cfg, sample_img=img)
        text = _image_to_text(img, ocr_cfg, lang_override=resolved_lang)
    else:
        resolved_lang = _resolve_language(raw_lang, ocr_cfg, sample_img=None)
        text = _image_to_text(img, ocr_cfg, lang_override=resolved_lang)
    return text


def ocr_pdf(
    pdf_path: str,
    config_path: str = "config/config.yaml",
    pages: Optional[List[int]] = None,
) -> tuple[str, int]:
    """OCR file PDF thành text. Delegated to .ocr.pdf_processor."""
    from .ocr import ocr_pdf as _ocr_pdf_impl

    return _ocr_pdf_impl(pdf_path, config_path, pages)


async def ocr_file(
    input_path: str,
    config_path: str = "config/config.yaml",
    pages: Optional[List[int]] = None,
    output_path: Optional[str] = None,
    skip_steps: Optional[Dict[str, Any]] = None,
    pdf_type: Optional[str] = None,
    skip_completion_menu: bool = False,
    key_manager: Any = None,
) -> Dict[str, Any]:
    """
    Extract text từ file PDF hoặc ảnh.
    Tự động detect PDF scan vs text-based để tối ưu.

    Args:
        output_path: Đường dẫn file output (để tạo tên file tạm thời)
        skip_steps: Dict với keys 'ocr', 'cleanup', 'spell_check' để skip các bước đã hoàn tất
    """
    _ensure_logger_config()
    pipeline_start_time = time.time()
    total_pages_processed = 0

    if skip_steps is None:
        skip_steps = {}

    if not os.path.exists(input_path):
        raise FileNotFoundError(input_path)

    ocr_cfg = _detect_bundled_binaries(load_ocr_config(config_path))
    _ensure_dependencies(ocr_cfg)

    ext = os.path.splitext(input_path)[-1].lower()

    # Xử lý PDF
    if ext == ".pdf":
        auto_detect = ocr_cfg.get("auto_detect_pdf_type", True)

        # Chỉ detect nếu chưa có pdf_type được truyền vào (tránh detect lại)
        if pdf_type is None and auto_detect:
            logger.info(f"Đang phát hiện loại PDF: {input_path}")
            pdf_type = detect_pdf_type(input_path, ocr_cfg)
            logger.info(f"Loại PDF: {pdf_type}")
        elif pdf_type is not None:
            logger.debug(f"Sử dụng loại PDF đã được truyền vào: {pdf_type}")
        elif not auto_detect:
            # Nếu không auto_detect và không có pdf_type, mặc định là scan
            pdf_type = "scan"
            logger.debug(f"Tự động phát hiện tắt, mặc định loại PDF: {pdf_type}")

        # Xử lý theo pdf_type (sau khi đã xác định)
        if pdf_type == "text":
            logger.info("PDF có lớp văn bản → Trích xuất văn bản trực tiếp (nhanh)")
            text = extract_text_from_pdf(input_path, ocr_cfg, pages)
            # Đếm số trang đã xử lý
            if pages:
                # Validate và đếm số trang hợp lệ
                try:
                    if pdfplumber is not None:
                        with pdfplumber.open(input_path) as pdf:
                            total = len(pdf.pages)
                            valid_pages = [p for p in pages if 1 <= p <= total]
                            total_pages_processed = len(valid_pages)
                    elif PyPDF2 is not None:
                        with open(input_path, "rb") as f:
                            reader = PyPDF2.PdfReader(f)
                            total = len(reader.pages)
                            valid_pages = [p for p in pages if 1 <= p <= total]
                            total_pages_processed = len(valid_pages)
                    else:
                        total_pages_processed = len(pages)  # Fallback
                except Exception:
                    total_pages_processed = len(pages)  # Fallback
            else:
                try:
                    if pdfplumber is not None:
                        with pdfplumber.open(input_path) as pdf:
                            total_pages_processed = len(pdf.pages)
                    elif PyPDF2 is not None:
                        with open(input_path, "rb") as f:
                            reader = PyPDF2.PdfReader(f)
                            total_pages_processed = len(reader.pages)
                except Exception:
                    total_pages_processed = 0
        else:
            # pdf_type == "scan" hoặc None (fallback)
            logger.info("PDF dạng scan → Sử dụng OCR")
            text, total_pages_processed = ocr_pdf(input_path, config_path, pages)
    # Xử lý ảnh
    elif ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}:
        text = ocr_image(input_path, config_path)
        total_pages_processed = 1  # Một ảnh = 1 trang
    # [NEW v7.5] Xử lý tệp Text-based (TXT, DOCX, EPUB) cho AI Pre-clean
    elif ext in {".txt", ".docx", ".epub"}:
        logger.info(f"Phát hiện tệp văn bản '{ext}' → Trích xuất nội dung trực tiếp cho AI Pre-clean")
        try:
            # Sử dụng parse_file_advanced để giữ logic parsing tập trung tại file_parser
            from .file_parser import parse_file_advanced

            parse_result = parse_file_advanced(
                input_path,
                ocr_cfg.get("_root_config", {}),
            )
            text = parse_result["text"]
            # EPUB/DOCX/TXT không có khái niệm "page" rõ ràng trong parser → mặc định 1
            total_pages_processed = parse_result.get("metadata", {}).get("page_count", 1)
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất văn bản từ {ext}: {e}")
            raise ValueError(f"Không thể đọc tệp văn bản để tiền xử lý AI: {e}")
    else:
        raise ValueError(f"Định dạng đầu vào không được hỗ trợ cho OCR/AI Pre-clean: {ext}")

    # Lưu file sau bước OCR nếu chưa skip và có output_path
    if not skip_steps.get("ocr", False) and output_path:
        ocred_path = _get_intermediate_file_path(output_path, "_ocred.txt")
        try:
            with open(ocred_path, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"💾 Đã lưu kết quả OCR: {ocred_path}")
        except Exception as e:
            logger.warning(f"Không thể lưu tệp OCR: {e}")

    # Áp dụng AI cleanup nếu enabled
    cleanup_cfg = ocr_cfg.get("ai_cleanup", {})
    cleanup_failed = 0
    cleanup_failed_indices = []
    cleanup_original_chunks = []

    if cleanup_cfg.get("enabled", False) and not skip_steps.get("cleanup", False):
        # Mặc định: SỬ DỤNG key_manager chung để đồng bộ quota state (v9.1 fix).
        use_shared_km = bool(cleanup_cfg.get("use_shared_key_manager", True))
        effective_key_manager = key_manager if (use_shared_km and key_manager is not None) else None
        if use_shared_km and effective_key_manager is None and key_manager is None:
            logger.info("AI Cleanup: use_shared_key_manager=true nhưng không có key_manager chung; fallback về pool riêng.")

        result = await ai_cleanup_text(text, ocr_cfg, key_manager=effective_key_manager)
        if isinstance(result, tuple):
            text, cleanup_failed_indices, cleanup_original_chunks = result
            cleanup_failed = len(cleanup_failed_indices)
        else:
            text = result

        # Lưu file sau bước cleanup nếu có output_path
        if output_path:
            cleanup_path = _get_intermediate_file_path(output_path, "_cleanup.txt")
            try:
                with open(cleanup_path, "w", encoding="utf-8") as f:
                    f.write(text)
                logger.info(f"💾 Đã lưu kết quả Cleanup: {cleanup_path}")
            except Exception as e:
                logger.warning(f"Không thể lưu tệp Dọn dẹp: {e}")
    elif skip_steps.get("cleanup", False):
        logger.info("⏭️  Bỏ qua bước Dọn dẹp (đã có tệp từ phiên trước)")

    # Áp dụng AI spell check và paragraph restoration nếu enabled
    spell_check_cfg = ocr_cfg.get("ai_spell_check", {})
    spell_check_failed = 0
    spell_check_failed_indices = []
    spell_check_original_chunks = []

    if spell_check_cfg.get("enabled", False) and not skip_steps.get("spell_check", False):
        # Mặc định: SỬ DỤNG key_manager chung để đồng bộ quota state (v9.1 fix).
        use_shared_km = bool(spell_check_cfg.get("use_shared_key_manager", True))
        effective_key_manager = key_manager if (use_shared_km and key_manager is not None) else None

        hard_timeout_s = spell_check_cfg.get("hard_timeout_seconds")
        try:
            if hard_timeout_s is not None:
                result = await asyncio.wait_for(
                    ai_spell_check_and_paragraph_restore(text, ocr_cfg, key_manager=effective_key_manager),
                    timeout=float(hard_timeout_s)
                )
            else:
                result = await ai_spell_check_and_paragraph_restore(text, ocr_cfg, key_manager=effective_key_manager)
        except asyncio.TimeoutError:
            logger.warning(
                "AI Soát lỗi chính tả: hard-timeout sau %.1fs. Bỏ qua spell-check và dùng text hiện tại.",
                float(hard_timeout_s) if hard_timeout_s else 0.0,
            )
            result = (text, [], [text])
        if isinstance(result, tuple):
            text, spell_check_failed_indices, spell_check_original_chunks = result
            spell_check_failed = len(spell_check_failed_indices)
        else:
            text = result
    elif skip_steps.get("spell_check", False):
        logger.info("⏭️  Bỏ qua bước Soát lỗi chính tả (đã có tệp từ phiên trước)")

    # Log tổng kết
    total_time = time.time() - pipeline_start_time
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    seconds = int(total_time % 60)
    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"

    logger.info("=" * 80)
    logger.info("📊 TỔNG KẾT QUY TRÌNH OCR")
    logger.info(f"⏱️  Tổng thời gian: {time_str} ({total_time:.2f} giây)")
    logger.info(f"📄 Số trang đã OCR: {total_pages_processed}")
    if cleanup_cfg.get("enabled", False):
        if cleanup_failed > 0:
            logger.info(f"🧹 AI Cleanup: {cleanup_failed} phân đoạn thất bại (đã lưu nội dung gốc)")
        else:
            logger.info("🧹 AI Cleanup: Hoàn tất không có lỗi")
    if spell_check_cfg.get("enabled", False):
        if spell_check_failed > 0:
            logger.info(f"✅ AI Soát lỗi chính tả: {spell_check_failed} phân đoạn thất bại (đã lưu nội dung gốc)")
        else:
            logger.info("✅ AI Soát lỗi chính tả: Hoàn tất không có lỗi")
    logger.info("=" * 80)

    # Lưu lại cấu trúc chunks để có thể merge lại sau retry
    cleanup_all_chunks = cleanup_original_chunks if cleanup_original_chunks else []
    spell_check_all_chunks = spell_check_original_chunks if spell_check_original_chunks else []

    markdown_postprocess = {"applied": False, "reason": "not_scan_pdf", "metrics": {}}
    preprocessing_cfg = ocr_cfg.get("_preprocessing", {}) if isinstance(ocr_cfg, dict) else {}
    scan_md_cfg = (preprocessing_cfg.get("scan_pdf_markdown_after_cleanup") or {})
    if ext == ".pdf" and pdf_type == "scan":
        from src.preprocessing.scan_markdown import maybe_markdownize_scan_text

        text, markdown_postprocess = maybe_markdownize_scan_text(text, scan_md_cfg)
        logger.info(
            "Scan Markdown postprocess: applied=%s reason=%s",
            markdown_postprocess.get("applied"),
            markdown_postprocess.get("reason"),
        )

    # Tự động lưu file cuối cùng nếu skip_completion_menu (được gọi từ workflow dịch)
    if output_path and skip_completion_menu:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"💾 Đã tự động lưu kết quả OCR (cuối cùng): {output_path}")
        except Exception as e:
            logger.warning(f"Không thể lưu tệp OCR cuối cùng: {e}")

    # Trả về text và thông tin failures để menu xử lý
    return {
        "text": text,
        "cleanup_failed": cleanup_failed,
        "cleanup_failed_indices": cleanup_failed_indices,
        "cleanup_original_chunks": cleanup_original_chunks,
        "cleanup_all_chunks": cleanup_all_chunks,  # Tất cả chunks (để merge lại)
        "spell_check_failed": spell_check_failed,
        "spell_check_failed_indices": spell_check_failed_indices,
        "spell_check_original_chunks": spell_check_original_chunks,
        "spell_check_all_chunks": spell_check_all_chunks,  # Tất cả chunks (để merge lại)
        "markdown_postprocess": markdown_postprocess,
        "ocr_cfg": ocr_cfg,
    }


def _create_html_from_items(all_items_with_position: List[dict], output_path: str) -> str:
    """Tạo file HTML từ all_items_with_position. Delegated to .ocr.docx_processor."""
    from .ocr import _create_html_from_items as modular_impl

    return modular_impl(all_items_with_position, output_path)


def _convert_html_to_docx_with_pandoc(html_path: str, output_path: str, ocr_cfg: dict) -> bool:
    """Convert HTML sang DOCX bằng pandoc. Delegated to .ocr.docx_processor."""
    from .ocr import _convert_html_to_docx_with_pandoc as modular_impl

    return modular_impl(html_path, output_path, ocr_cfg)


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="OCR scan file (PDF/image) and extract text")
    parser.add_argument("input", help="Path to image or PDF file (scan)")
    parser.add_argument("--config", default="config/config.yaml", help="Path to YAML config")
    parser.add_argument("--output", help="Save recognized text to file")
    parser.add_argument(
        "--pages",
        help="Chỉ định các trang cần OCR. Ví dụ: '1,2,5,7' hoặc '1-7' hoặc '1-3,5,7-9'",
    )
    parser.add_argument(
        "--format",
        choices=["txt", "docx"],
        default=None,
        help="Định dạng file output (txt hoặc docx). Nếu không chỉ định, sẽ tự động detect từ extension của --output",
    )
    args = parser.parse_args()
    return args


async def main_async():
    args = parse_args()
    _ensure_logger_config()
    key_manager = None

    # Xác định output_path và output_format
    if args.output:
        output_path = args.output
        # Detect format từ extension nếu --format không được chỉ định
        if args.format:
            output_format = args.format
        else:
            ext = os.path.splitext(output_path)[1].lower()
            if ext == ".docx":
                output_format = "docx"
            else:
                output_format = "txt"
    else:
        # Tạo output_path mặc định từ input_path
        input_dir = os.path.dirname(args.input) if os.path.dirname(args.input) else "."
        input_basename = os.path.basename(args.input)
        input_name_without_ext = os.path.splitext(input_basename)[0]
        if args.format == "docx":
            output_path = os.path.join(input_dir, input_name_without_ext + "_ocr_result.docx")
            output_format = "docx"
        else:
            output_path = os.path.join(input_dir, input_name_without_ext + "_ocr_result.txt")
            output_format = "txt"

    # Check & Resume: Kiểm tra file từ phiên trước
    existing_files = _check_existing_files(output_path)
    skip_steps = {}

    if existing_files["all_exist"]:
        logger.info("\n" + "=" * 80)
        logger.info("🔍 PHÁT HIỆN FILE TỪ PHIÊN LÀM VIỆC TRƯỚC")
        logger.info("=" * 80)

        found_files = []
        if existing_files["ocred"]:
            found_files.append(f"  • File OCR: {existing_files['ocred']}")
        if existing_files["cleanup"]:
            found_files.append(f"  • File Cleanup: {existing_files['cleanup']}")
        if existing_files["output"]:
            found_files.append(f"  • File Output: {existing_files['output']}")

        if found_files:
            logger.info("\nCác file đã phát hiện:")
            for f in found_files:
                logger.info(f)
            logger.info("")

            logger.info("Bạn có muốn sử dụng các file này để tiếp tục?")
            logger.info("")
            logger.info("  1. Có, tiếp tục từ Cleanup")
            logger.info("  2. Có, tiếp tục từ Spell Check")
            logger.info("  3. Có, nhưng chạy lại toàn bộ (OCR + Cleanup + Spell Check)")
            logger.info("  4. Không, kết thúc tác vụ")
            logger.info("")

            while True:
                try:
                    choice = input("Nhập lựa chọn (1/2/3/4): ").strip()
                    if choice == "1":
                        # Resume từ Cleanup (cần file _ocred.txt)
                        if existing_files["ocred"]:
                            skip_steps["ocr"] = True
                            logger.info("⏭️  Sẽ bỏ qua OCR, tiếp tục từ Cleanup")
                        else:
                            logger.warning("⚠️  Không tìm thấy file OCR (_ocred.txt). Không thể tiếp tục từ Cleanup.")
                            logger.info("🔄 Sẽ chạy lại toàn bộ quy trình")
                            skip_steps = {}
                        break
                    elif choice == "2":
                        # Resume từ Spell Check (cần file _cleanup.txt)
                        if existing_files["cleanup"]:
                            skip_steps["ocr"] = True
                            skip_steps["cleanup"] = True
                            logger.info("⏭️  Sẽ bỏ qua OCR và Cleanup, chỉ chạy Spell Check")
                        else:
                            logger.warning(
                                "⚠️  Không tìm thấy file Cleanup (_cleanup.txt). Không thể tiếp tục từ Spell Check."
                            )
                            if existing_files["ocred"]:
                                logger.info("💡 Phát hiện file OCR. Sẽ tiếp tục từ Cleanup.")
                                skip_steps["ocr"] = True
                            else:
                                logger.info("🔄 Sẽ chạy lại toàn bộ quy trình")
                                skip_steps = {}
                        break
                    elif choice == "3":
                        # Chạy lại toàn bộ
                        skip_steps = {}
                        logger.info("🔄 Sẽ chạy lại toàn bộ quy trình")
                        break
                    elif choice == "4":
                        logger.info("Kết thúc tác vụ.")
                        sys.exit(0)
                    else:
                        logger.warning("Vui lòng nhập 1, 2, 3 hoặc 4.")
                except (KeyboardInterrupt, EOFError):
                    logger.info("\nKết thúc tác vụ.")
                    sys.exit(0)

    logger.info("Bắt đầu OCR pipeline...")

    # Load config
    ocr_cfg = _detect_bundled_binaries(load_ocr_config(args.config))

    # Khởi tạo initial_text để có thể được set bởi OCRmyPDF workflow (PDF scan)
    initial_text = None

    # Parse pages nếu có
    pages_list = None
    if args.pages:
        pages_list = _parse_pages(args.pages)
        if pages_list:
            logger.info(f"Chỉ xử lý các trang: {pages_list}")
        else:
            logger.warning(f"Không parse được pages từ '{args.pages}'. Sẽ xử lý tất cả trang.")

    # Step 1: Nhận biết file PDF là scan hay text-based (TRƯỚC KHI gọi _ensure_dependencies để tránh treo)
    input_path_lower = args.input.lower()
    is_pdf = input_path_lower.endswith(".pdf")

    if is_pdf:
        logger.info(f"Đang nhận biết loại PDF: {args.input}")
        logger.debug(f"pdfplumber available: {pdfplumber is not None}")
        logger.debug(f"PyPDF2 available: {PyPDF2 is not None}")
        logger.debug("Bắt đầu gọi detect_pdf_type...")
        pdf_type = detect_pdf_type(args.input, ocr_cfg)
        logger.debug("Đã hoàn thành detect_pdf_type")
        logger.info(f"PDF type: {pdf_type}")

        # 2.2. Nếu là text-based → convert trực tiếp tùy output format
        if pdf_type == "text":
            if output_format == "docx":
                # 2.2.2. PDF text-based + DOCX: Đưa ra 2 options cho người dùng
                _ensure_dependencies(ocr_cfg)
                logger.info("=" * 80)
                logger.info("📄 PDF text-based phát hiện + Output DOCX")
                logger.info("=" * 80)
                logger.info("Vui lòng chọn quy trình xử lý:")
                logger.info("  1. Convert nhanh: PDF → DOCX giữ nguyên layout (không cleanup/spell check)")
                logger.info("  2. Convert full: Cleanup + Spell Check → DOCX (chất lượng cao, tốn thời gian hơn)")
                logger.info("=" * 80)
                while True:
                    try:
                        choice = input("Nhập lựa chọn (1 hoặc 2): ").strip()
                        if choice == "1":
                            logger.info("📄 Đang convert PDF → DOCX (nhanh, giữ layout)...")
                            try:
                                convert_pdf_to_docx(args.input, output_path, pages_list)
                                try:
                                    _fix_docx_leading_tabs_and_soft_wraps(output_path)
                                except Exception:
                                    pass
                                logger.info(f"✅ Đã tạo DOCX thành công: {output_path}")
                                logger.info(
                                    "Hoàn tất OCR pipeline (PDF text-based → DOCX không cần cleanup/spell check)."
                                )
                                sys.exit(0)
                            except Exception as e:
                                logger.error(f"❌ Lỗi khi convert PDF → DOCX: {e}")
                                error_msg = str(e).lower()
                                if "get_area" in error_msg or "rect" in error_msg:
                                    logger.warning("⚠️  Phát hiện lỗi tương thích giữa pdf2docx và PyMuPDF.")
                                    logger.warning("💡 Giải pháp: Cài PyMuPDF==1.26.4 hoặc thấp hơn:")
                                    logger.warning("   pip install PyMuPDF==1.26.4")
                                raise
                        elif choice == "2":
                            logger.info("📄 Đang convert PDF → DOCX (full cleanup + spell check)...")
                            try:
                                hybrid_workflow_pdf_to_docx(args.input, output_path, ocr_cfg, pages_list)
                                logger.info(f"✅ Đã tạo DOCX thành công: {output_path}")
                                logger.info(
                                    "Hoàn tất OCR pipeline (PDF text-based → DOCX với full cleanup + spell check)."
                                )
                                sys.exit(0)
                            except Exception as e:
                                logger.error(f"❌ Lỗi khi convert PDF → DOCX (full workflow): {e}")
                                raise
                        else:
                            logger.warning("⚠️  Lựa chọn không hợp lệ. Vui lòng nhập 1 hoặc 2.")
                            continue
                    except KeyboardInterrupt:
                        logger.info("\n⚠️  Đã hủy bởi người dùng.")
                        sys.exit(1)
                    except Exception as e:
                        logger.error(f"❌ Lỗi: {e}")
                        raise
            elif output_format == "txt":
                # 2.2.1. Convert PDF → TXT → cleanup → spell check
                logger.info("📄 PDF text-based + TXT output → Extract text → Cleanup → Spell Check...")
                # Fall through để chạy standard workflow (extract text → cleanup → spell check)
        else:
            # 2.1. Nếu là scan → thử dùng OCRmyPDF trước, nếu không có thì dùng pytesseract
            logger.info("📷 PDF scan → Xử lý OCR...")

            # Ưu tiên dùng OCRmyPDF nếu khả dụng (tạo PDF searchable → extract text nhanh hơn)
            if ocrmypdf_available:
                logger.info("🔍 OCRmyPDF khả dụng → Dùng OCRmyPDF để tạo PDF searchable...")
                try:
                    # Step 1: Dùng OCRmyPDF tạo PDF searchable
                    temp_searchable_pdf = os.path.splitext(output_path)[0] + "_searchable.pdf"
                    logger.info("📄 Bước 1: OCRmyPDF đang tạo PDF searchable...")
                    convert_pdf_with_ocrmypdf(args.input, temp_searchable_pdf, ocr_cfg, pages_list)

                    # Step 2: Extract text từ PDF searchable (nhanh hơn OCR từng ảnh)
                    logger.info("📄 Bước 2: Extract text từ PDF searchable...")
                    extracted_text = extract_text_from_pdf(temp_searchable_pdf, ocr_cfg, pages_list)

                    if not extracted_text or len(extracted_text.strip()) < 10:
                        raise RuntimeError("Extract text từ PDF searchable không thành công hoặc text quá ngắn.")

                    # Lưu kết quả OCR vào initial_text để tiếp tục workflow
                    initial_text = extracted_text

                    # Cleanup temp PDF searchable (giữ lại nếu user muốn dùng sau)
                    cleanup_temp_pdf = ocr_cfg.get("cleanup_temp_searchable_pdf", True)
                    if cleanup_temp_pdf:
                        try:
                            if os.path.exists(temp_searchable_pdf):
                                os.remove(temp_searchable_pdf)
                                logger.debug(f"🗑️  Đã xóa file temp: {temp_searchable_pdf}")
                        except Exception:
                            pass
                    else:
                        logger.info(f"💾 Giữ lại PDF searchable: {temp_searchable_pdf}")

                    logger.info("✅ Đã tạo text từ PDF searchable bằng OCRmyPDF. Tiếp tục Cleanup & Spell Check...")
                    # Skip OCR step vì đã có text từ OCRmyPDF
                    skip_steps["ocr"] = True

                except Exception as ocr_fallback_error:
                    error_msg_str = str(ocr_fallback_error)
                    logger.warning(f"⚠️  OCRmyPDF thất bại: {error_msg_str}")
                    logger.warning("🔄 Fallback về pytesseract OCR workflow (tiêu chuẩn)...")

                    # Kiểm tra và thông báo về missing dependencies
                    if (
                        "ghostscript" in error_msg_str.lower()
                        or "gswin64c" in error_msg_str.lower()
                        or "gs" in error_msg_str.lower()
                    ):
                        logger.warning("⚠️  OCRmyPDF cần Ghostscript nhưng không tìm thấy.")
                        logger.warning("💡 Hướng dẫn: choco install ghostscript")
                    elif "tesseract" in error_msg_str.lower():
                        logger.warning("⚠️  OCRmyPDF cần Tesseract OCR nhưng không tìm thấy.")
                        logger.warning("💡 Hướng dẫn: choco install tesseract")

                    # Fall through để chạy standard OCR workflow (pytesseract)
                    initial_text = None
            else:
                logger.info("⚠️  OCRmyPDF không khả dụng → Dùng pytesseract OCR workflow (tiêu chuẩn)...")
                # Fall through để chạy standard OCR workflow (pytesseract)
                initial_text = None

            # Fall through để chạy standard workflow (OCR → cleanup → spell check)
    else:
        # Không phải PDF → workflow hiện tại
        logger.info("Xử lý file không phải PDF...")
        # Fall through để chạy standard workflow

    # Load file từ phiên trước nếu resume
    # Note: initial_text có thể đã được set bởi OCRmyPDF workflow cho PDF scan
    # Nếu chưa có initial_text từ OCRmyPDF, kiểm tra resume files
    if initial_text is None and skip_steps.get("ocr", False):
        if skip_steps.get("cleanup", False):
            # Resume từ Spell Check → load file Cleanup
            if existing_files["cleanup"]:
                initial_text = _load_resume_file(existing_files["cleanup"], "Cleanup")
            else:
                logger.error("❌ Không tìm thấy file Cleanup để resume từ Spell Check!")
                logger.info("🔄 Sẽ chạy lại toàn bộ quy trình")
                skip_steps = {}
        else:
            # Resume từ Cleanup → load file OCR
            if existing_files["ocred"]:
                initial_text = _load_resume_file(existing_files["ocred"], "OCR")
            else:
                logger.error("❌ Không tìm thấy file OCR để resume từ Cleanup!")
                logger.info("🔄 Sẽ chạy lại toàn bộ quy trình")
                skip_steps = {}

    # Chạy pipeline với skip_steps
    if initial_text:
        # Resume từ file đã có → chỉ cần chạy các bước còn lại
        ocr_cfg = _detect_bundled_binaries(load_ocr_config(args.config))
        _ensure_dependencies(ocr_cfg)
        text = initial_text

        cleanup_cfg = ocr_cfg.get("ai_cleanup", {})
        cleanup_failed = 0
        cleanup_failed_indices = []
        cleanup_original_chunks = []

        # Chạy cleanup nếu cần (không skip)
        if cleanup_cfg.get("enabled", False) and not skip_steps.get("cleanup", False):
            result = await ai_cleanup_text(text, ocr_cfg, key_manager=key_manager)
            if isinstance(result, tuple):
                text, cleanup_failed_indices, cleanup_original_chunks = result
                cleanup_failed = len(cleanup_failed_indices)
            else:
                text = result

            # Lưu file sau cleanup
            cleanup_path = _get_intermediate_file_path(output_path, "_cleanup.txt")
            try:
                with open(cleanup_path, "w", encoding="utf-8") as f:
                    f.write(text)
                logger.info(f"💾 Đã lưu kết quả Cleanup: {cleanup_path}")
            except Exception as e:
                logger.warning(f"Không thể lưu file Cleanup: {e}")

        # Chạy spell check nếu cần
        spell_check_cfg = ocr_cfg.get("ai_spell_check", {})
        spell_check_failed = 0
        spell_check_failed_indices = []
        spell_check_original_chunks = []

        if spell_check_cfg.get("enabled", False):
            result = await ai_spell_check_and_paragraph_restore(text, ocr_cfg, key_manager=key_manager)
            if isinstance(result, tuple):
                text, spell_check_failed_indices, spell_check_original_chunks = result
                spell_check_failed = len(spell_check_failed_indices)
            else:
                text = result

        # Tạo result dict giống format của ocr_file
        result = {
            "text": text,
            "cleanup_failed": cleanup_failed,
            "cleanup_failed_indices": cleanup_failed_indices,
            "cleanup_original_chunks": cleanup_original_chunks,
            "cleanup_all_chunks": cleanup_original_chunks if cleanup_original_chunks else [],
            "spell_check_failed": spell_check_failed,
            "spell_check_failed_indices": spell_check_failed_indices,
            "spell_check_original_chunks": spell_check_original_chunks,
            "spell_check_all_chunks": spell_check_original_chunks if spell_check_original_chunks else [],
            "markdown_postprocess": {"applied": False, "reason": "resume_mode", "metrics": {}},
            "ocr_cfg": ocr_cfg,
        }
    else:
        # Chạy toàn bộ pipeline (OCR → Cleanup → Spell Check)
        # Workflow thống nhất cho cả TXT và DOCX
        # Truyền pdf_type đã detect vào ocr_file để tránh detect lại
        result = await ocr_file(
            args.input,
            config_path=args.config,
            pages=pages_list,
            output_path=output_path,
            skip_steps=skip_steps,
            pdf_type=pdf_type if is_pdf else None,
        )

    # Xử lý kết quả từ ocr_file
    result_text = result["text"]
    cleanup_failed = result["cleanup_failed"]
    spell_check_failed = result["spell_check_failed"]
    ocr_cfg = result["ocr_cfg"]

    # PDF text-based + DOCX đã được xử lý ở trên (convert trực tiếp)
    # Không cần xử lý thêm ở đây vì đã exit(0)

    # Nếu còn ở đây → là PDF scan + DOCX hoặc PDF text-based + TXT
    # Cả 2 trường hợp đều xuất TXT (không hỗ trợ DOCX cho scan)
    if output_format == "docx" and is_pdf:
        # PDF scan không thể extract images → fallback về TXT
        logger.warning("⚠️  PDF scan không thể extract images để tạo DOCX. Chỉ có thể xuất text.")
        logger.warning("🔄 Fallback về định dạng TXT...")
        output_format = "txt"
        output_path = os.path.splitext(output_path)[0] + ".txt"

    # Hiển thị menu completion (cho TXT hoặc sau khi DOCX failed)
    if output_path:
        logger.info(f"\n📁 File output: {output_path}")
        user_choice = _show_completion_menu(cleanup_failed, spell_check_failed, output_path)

        if user_choice == "retry":
            # Retry các chunk failed và merge lại (logic giống phần else)
            cleanup_cfg = ocr_cfg.get("ai_cleanup", {})
            spell_check_cfg = ocr_cfg.get("ai_spell_check", {})
            updated_text = result_text

            if result["cleanup_failed"] > 0 and cleanup_cfg.get("enabled", False) and result["cleanup_all_chunks"]:
                logger.info(f"Đang retry {result['cleanup_failed']} chunks AI Cleanup failed...")
                api_keys = cleanup_cfg.get("api_keys", [])
                if not api_keys:
                    api_keys = ocr_cfg.get("_root_api_keys", [])
                model_name = cleanup_cfg.get("model", "gemini-2.5-flash")
                prompt = """Bạn là một AI chuyên dọn dẹp văn bản OCR/scan. Nhiệm vụ:
1. Loại bỏ header/footer lặp lại ở mỗi trang
2. Loại bỏ các ký tự rác, vệt đen vô nghĩa từ quá trình scan
3. Loại bỏ số trang, watermark
4. Giữ nguyên nội dung chính của văn bản
5. Chuẩn hóa khoảng trắng thừa
6. Giữ nguyên định dạng đoạn văn

Trả về chỉ văn bản đã được dọn dẹp, không giải thích thêm.

Văn bản cần dọn dẹp:
"""
                retry_results, still_failed = _retry_failed_chunks_cleanup(
                    result["cleanup_failed_indices"],
                    result["cleanup_all_chunks"],
                    api_keys,
                    model_name,
                    prompt,
                    ocr_cfg,
                )

                all_chunks = list(result["cleanup_all_chunks"])
                for idx, retry_text in retry_results.items():
                    if idx < len(all_chunks):
                        all_chunks[idx] = retry_text
                updated_text = "\n\n".join(all_chunks)
                logger.info(
                    f"AI Cleanup Retry: {result['cleanup_failed'] - len(still_failed)}/{result['cleanup_failed']} chunks retry thành công."
                )

            if result["spell_check_failed"] > 0 and spell_check_cfg.get("enabled", False):
                logger.info(f"Đang retry {result['spell_check_failed']} chunks AI Spell Check failed...")
                if not api_keys:
                    api_keys = ocr_cfg.get("_root_api_keys", [])
                model_name = spell_check_cfg.get("model", "gemini-2.5-flash")
                prompt = """Bạn là một AI chuyên soát lỗi chính tả và phục hồi cấu trúc văn bản OCR. Nhiệm vụ chính của bạn là PHÂN TÍCH NGỮ CẢNH và QUYẾT ĐỊNH THÔNG MINH.

=== NHIỆM VỤ CHÍNH: PHÂN TÍCH VÀ PHỤC HỒI CÂU BỊ NGẮT (Ưu tiên cao nhất) ===

Bạn cần ĐỌC KỸ NỘI DUNG và PHÂN TÍCH để phân biệt:

A. CÂU BỊ NGẮT DO CONVERT PDF → TXT (CẦN NỐI LẠI):
   - Đọc ngữ cảnh: Nếu dòng trước chưa hoàn thành ý và dòng sau tiếp nối ý đó → nối lại
   - Ví dụ: 
     * "Our client is also the owner of Vietnam Trade Mark Registration No. 315843 for "MICROBAN"
       in Class 5 covering..." 
     → Phân tích: "in Class 5" tiếp nối câu trước → NỐI LẠI thành một câu
   
   - Dấu hiệu cần nối:
     * Dòng trước không kết thúc bằng dấu câu (. ! ?) HOẶC kết thúc bằng dấu phẩy, hai chấm
     * Dòng sau bắt đầu bằng chữ thường (tiếp nối câu trước)
     * Nội dung dòng sau về mặt ngữ pháp và ngữ nghĩa là phần tiếp theo của câu trước
     * Đọc toàn bộ ngữ cảnh để hiểu rõ mối quan hệ

B. NGẮT PARAGRAPH CÓ CHỦ ĐÍCH (KHÔNG NỐI):
   - Đọc ngữ cảnh: Nếu dòng sau là ý mới, chủ đề mới, hoặc đoạn văn mới → KHÔNG nối
   - Ví dụ:
     * "...attached as Exhibit 1.
       
       Khách hàng của chúng tôi là chủ sở hữu..."
     → Phân tích: Đây là đoạn mới (chuyển từ tiếng Anh sang tiếng Việt) → KHÔNG NỐI
   
   - Dấu hiệu KHÔNG nối:
     * Dòng trước kết thúc bằng dấu chấm (. ! ?) và dòng sau bắt đầu bằng chữ hoa
     * Dòng sau là câu đầu tiên của một đoạn mới (ý tưởng mới, chủ đề mới)
     * Có sự thay đổi rõ ràng về ngữ cảnh (ví dụ: chuyển từ phần này sang phần khác)
     * Đọc toàn bộ ngữ cảnh để xác định đây là ngắt đoạn có chủ đích

QUY TRÌNH PHÂN TÍCH:
1. ĐỌC toàn bộ văn bản để hiểu cấu trúc và ngữ cảnh
2. PHÂN TÍCH từng vị trí ngắt dòng:
   - Xem xét nội dung trước và sau dòng ngắt
   - Đánh giá mối quan hệ ngữ pháp và ngữ nghĩa
   - Xác định đây là câu bị ngắt hay ngắt đoạn có chủ đích
3. QUYẾT ĐỊNH:
   - Nếu là câu bị ngắt → NỐI lại (thay line break bằng space)
   - Nếu là ngắt đoạn có chủ đích → GIỮ NGUYÊN (có thể thêm dòng trống nếu cần)
4. ÁP DỤNG nhất quán cho toàn bộ văn bản

=== CÁC NHIỆM VỤ KHÁC ===

1. SOÁT LỖI CHÍNH TẢ:
   - Sửa các lỗi chính tả do OCR (ví dụ: "Kíng" → "Kính", "hang" → "hàng")
   - Sửa các lỗi chính tả thông thường
   - KHÔNG thay đổi từ ngữ chuyên ngành, tên riêng, địa danh
   - KHÔNG thay đổi số liệu, ngày tháng, địa chỉ

2. PHỤC HỒI CẤU TRÚC PARAGRAPH:
   - Sau khi đã nối các câu bị ngắt, xác định các ngắt đoạn hợp lý
   - Mỗi đoạn văn nên có một ý chính hoàn chỉnh
   - Giữ nguyên các dòng trống giữa các đoạn đã được xác định là có chủ đích
   - Đảm bảo các câu trong một đoạn có liên quan với nhau

3. BẢO VỆ TOÀN VẸN NỘI DUNG:
   - TUYỆT ĐỐI KHÔNG thay đổi ý nghĩa của văn bản
   - KHÔNG thêm, bớt, hoặc diễn giải lại nội dung
   - KHÔNG thay đổi thứ tự từ trong câu (chỉ nối lại khi cần)
   - GIỮ NGUYÊN định dạng đặc biệt (bullet points, numbered lists, bảng)
   - GIỮ NGUYÊN các từ viết hoa nếu chúng là tên riêng, thuật ngữ

4. ĐỊNH DẠNG:
   - Giữ nguyên định dạng văn bản song ngữ (nếu có)
   - Giữ nguyên các dấu câu quan trọng
   - Chuẩn hóa khoảng trắng thừa giữa các từ (nhưng không thay đổi paragraph breaks hợp lý)
   - Đảm bảo mỗi câu kết thúc bằng dấu câu thích hợp

=== NGUYÊN TẮC QUAN TRỌNG ===

- SỬ DỤNG SỨC MẠNH PHÂN TÍCH NGỮ CẢNH: Đọc và hiểu nội dung, không chỉ dựa vào quy tắc cú pháp
- QUYẾT ĐỊNH THÔNG MINH: Mỗi quyết định nối hay không nối phải dựa trên phân tích ngữ cảnh cụ thể
- NHẤT QUÁN: Áp dụng cùng một tiêu chuẩn phân tích cho toàn bộ văn bản
- BẢO TOÀN Ý NGHĨA: Chỉ điều chỉnh cấu trúc, KHÔNG thay đổi nội dung hoặc ý nghĩa

Trả về chỉ văn bản đã được soát và phục hồi, không giải thích thêm.

Văn bản cần phân tích và xử lý:
"""

                spell_check_chunks = [
                    updated_text[i : i + spell_check_cfg.get("chunk_size", 10000)]
                    for i in range(0, len(updated_text), spell_check_cfg.get("chunk_size", 10000))
                ]
                retry_results, still_failed = _retry_failed_chunks_spell_check(
                    result["spell_check_failed_indices"],
                    spell_check_chunks,
                    api_keys,
                    model_name,
                    prompt,
                    ocr_cfg,
                )

                spell_check_chunks_list = list(spell_check_chunks)
                for idx, retry_text in retry_results.items():
                    if idx < len(spell_check_chunks_list):
                        spell_check_chunks_list[idx] = retry_text
                updated_text = "\n\n".join(spell_check_chunks_list)
                logger.info(
                    f"AI Spell Check Retry: {result['spell_check_failed'] - len(still_failed)}/{result['spell_check_failed']} chunks retry thành công."
                )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(updated_text)
            logger.info(f"OCR: Đã lưu text đã được retry vào: {output_path}")
            # Cleanup intermediate files
            _cleanup_intermediate_files(output_path)
        elif user_choice == "save":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result_text)
            logger.info(f"OCR: Đã lưu vào: {output_path}")
            # Cleanup intermediate files
            _cleanup_intermediate_files(output_path)
        elif user_choice == "exit":
            logger.info("Thoát không lưu.")
        else:
            # Auto-save
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result_text)
            logger.info(f"OCR: Đã tự động lưu vào: {output_path}")
            # Cleanup intermediate files
            _cleanup_intermediate_files(output_path)

    logger.info("Hoàn tất OCR pipeline.")
if __name__ == '__main__':
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info('\nKết thúc tác vụ.')
        sys.exit(0)
