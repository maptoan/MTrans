# -*- coding: utf-8 -*-
"""
Configuration loading utilities for OCR module.
Extracted from ocr_reader.py to improve code organization.

This module contains:
- _load_yaml: Load YAML config file
- load_ocr_config: Load OCR config from config.yaml
- _build_safety_settings: Build safety settings for Gemini API
- _bundle_base_dir: Get base directory for bundled resources
- _detect_bundled_binaries: Detect bundled Tesseract/Poppler paths
- _parse_pages: Parse page range strings
- _ensure_logger_config: Ensure logger is configured
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

import yaml

from .logging_filters import GoogleLogFilter, _suppress_google_logs

logger = logging.getLogger("NovelTranslator")


def _ensure_logger_config() -> None:
    """Đảm bảo logger có handler để in ra console và lưu file khi chạy trực tiếp.
    Tránh tình trạng không thấy log do thiếu cấu hình bên ngoài.
    """
    if getattr(_ensure_logger_config, "_configured", False):
        return

    # Suppress Google logs trước khi cấu hình logger
    _suppress_google_logs()

    logger.setLevel(logging.INFO)
    logger.propagate = False
    # Kiểm tra có StreamHandler/FileHandler chưa
    has_stream = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    has_file = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    # Console handler
    if not has_stream:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        ch.addFilter(GoogleLogFilter())  # Apply filter để loại bỏ Google logs
        logger.addHandler(ch)
    # File handler
    if not has_file:
        try:
            os.makedirs("logs", exist_ok=True)
            fh = logging.FileHandler(
                os.path.join("logs", "ocr_runtime.log"), encoding="utf-8"
            )
            fh.setLevel(logging.INFO)
            fh.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            fh.addFilter(GoogleLogFilter())  # Apply filter để loại bỏ Google logs
            logger.addHandler(fh)
        except Exception:
            pass
    setattr(_ensure_logger_config, "_configured", True)


def _load_yaml(path: str) -> Dict[str, Any]:
    """Load YAML config file."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_ocr_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load OCR config from config.yaml."""
    cfg = _load_yaml(config_path)
    ocr_cfg = cfg.get("ocr") or {}
    # Lưu config_path để dùng sau
    ocr_cfg["_config_path"] = config_path
    # Keep preprocessing subtree for OCR post-processing decisions.
    ocr_cfg["_preprocessing"] = cfg.get("preprocessing", {})
    # Lưu api_keys từ root config để dùng cho AI cleanup
    ocr_cfg["_root_api_keys"] = cfg.get("api_keys", [])
    # Lưu safety_level từ root config (nếu có) để dùng cho AI cleanup/spell check
    # Ưu tiên: ocr.safety_level > root safety_level > default BLOCK_ONLY_HIGH
    if "safety_level" not in ocr_cfg:
        ocr_cfg["safety_level"] = cfg.get("safety_level", "BLOCK_ONLY_HIGH")
    return ocr_cfg


def _build_safety_settings(safety_level: str = "BLOCK_ONLY_HIGH") -> List[Dict[str, Any]]:
    """
    Tạo safety settings cho Google Gemini API.
    Học hỏi từ module dịch thuật (model_router.py).

    Args:
        safety_level: Safety level từ config (BLOCK_NONE, BLOCK_ONLY_HIGH, etc.)

    Returns:
        List of safety settings dicts cho GenerativeModel
    """
    safety_level = safety_level.upper() if safety_level else "BLOCK_ONLY_HIGH"

    # Các levels hợp lệ từ Google Gemini API
    valid_levels = [
        "BLOCK_NONE",
        "BLOCK_ONLY_HIGH",
        "BLOCK_MEDIUM_AND_ABOVE",
        "BLOCK_LOW_AND_ABOVE",
    ]
    if safety_level not in valid_levels:
        logger.warning(
            f"Safety level '{safety_level}' không hợp lệ. Dùng default: BLOCK_ONLY_HIGH"
        )
        safety_level = "BLOCK_ONLY_HIGH"

    return [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": safety_level},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": safety_level},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": safety_level},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": safety_level},
    ]


def _bundle_base_dir() -> str:
    """Return base dir for bundled resources (PyInstaller) or script dir."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return getattr(sys, "_MEIPASS")  # PyInstaller temp dir
    # Fallback: repo/script directory
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def _detect_bundled_binaries(ocr_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    If config values are missing, try to detect bundled Tesseract and Poppler paths.
    - Looks for vendor/tesseract/tesseract.exe
    - Looks for vendor/poppler/bin
    """
    cfg = dict(ocr_cfg) if ocr_cfg else {}
    base = _bundle_base_dir()
    # Detect Tesseract
    if not cfg.get("tesseract_cmd"):
        cand = os.path.join(base, "tesseract", "tesseract.exe")
        if not os.path.exists(cand):
            cand = os.path.join(base, "vendor", "tesseract", "tesseract.exe")
        if os.path.exists(cand):
            cfg["tesseract_cmd"] = cand.replace("\\", "/")
    # Detect Poppler bin
    if not cfg.get("poppler_path"):
        cand_dir = os.path.join(base, "poppler", "bin")
        if not os.path.isdir(cand_dir):
            cand_dir = os.path.join(base, "vendor", "poppler", "bin")
        if os.path.isdir(cand_dir):
            cfg["poppler_path"] = cand_dir.replace("\\", "/")
    return cfg


def _parse_pages(pages_str: str) -> Optional[List[int]]:
    """
    Parse chuỗi pages thành danh sách số trang.
    Hỗ trợ:
    - "1,2,5,7" → [1, 2, 5, 7]
    - "1-7" → [1, 2, 3, 4, 5, 6, 7]
    - "1-3,5,7-9" → [1, 2, 3, 5, 7, 8, 9]

    Returns: List[int] hoặc None nếu không hợp lệ
    """
    if not pages_str or not pages_str.strip():
        return None

    pages_str = pages_str.strip()
    # Loại bỏ dấu ngoặc vuông hoặc ngoặc tròn nếu có (để tương thích ngược)
    if (pages_str.startswith("[") and pages_str.endswith("]")) or (
        pages_str.startswith("(") and pages_str.endswith(")")
    ):
        pages_str = pages_str[1:-1].strip()

    pages: List[int] = []
    parts = [p.strip() for p in pages_str.split(",")]

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Kiểm tra có phải range không (ví dụ: "1-7")
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start = int(start.strip())
                end = int(end.strip())
                if start > end:
                    logger.warning(f"Range không hợp lệ: {part} (start > end). Bỏ qua.")
                    continue
                pages.extend(range(start, end + 1))
            except ValueError:
                logger.warning(f"Range không hợp lệ: {part}. Bỏ qua.")
                continue
        else:
            # Số trang đơn lẻ
            try:
                page_num = int(part)
                if page_num > 0:
                    pages.append(page_num)
            except ValueError:
                logger.warning(f"Số trang không hợp lệ: {part}. Bỏ qua.")
                continue

    # Loại bỏ trùng lặp và sắp xếp
    pages = sorted(list(set(pages)))

    if not pages:
        logger.warning("Không có trang hợp lệ nào được parse.")
        return None

    return pages
