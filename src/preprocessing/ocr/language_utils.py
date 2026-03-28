# -*- coding: utf-8 -*-
"""
Language utilities for OCR module.
Extracted from ocr_reader.py to improve code organization.

This module contains:
- _normalize_lang_code: Normalize language codes for Tesseract
- _is_cjk_character: Check if character is CJK
- _count_cjk_characters: Count CJK characters in text
- _detect_chinese_variant: Detect Simplified/Traditional Chinese
- _resolve_language: Resolve language with variant detection
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from PIL.Image import Image

logger = logging.getLogger("NovelTranslator")


def _normalize_lang_code(lang: str) -> str:
    """
    Chuyển đổi mã ngôn ngữ từ format ngắn (VN, EN, CN) sang Tesseract format (vie, eng, chi).
    Hỗ trợ backward compatibility với format cũ.

    Args:
        lang: Language string có thể là "VN", "EN", "CN", "auto", hoặc format cũ "vie", "eng", "chi"

    Returns:
        Tesseract language code hoặc "auto"
    """
    if not lang:
        return "vie"

    lang = lang.strip().upper()

    # Mapping từ format ngắn sang Tesseract
    lang_map = {
        "VN": "vie",
        "EN": "eng",
        "CN": "chi",
        "VIE": "vie",  # Backward compatibility
        "ENG": "eng",  # Backward compatibility
        "CHI": "chi",  # Backward compatibility
        "AUTO": "auto",
    }

    # Xử lý kết hợp ngôn ngữ (VD: "VN+EN" hoặc "vie+eng")
    if "+" in lang:
        parts = lang.split("+")
        normalized_parts = []
        for part in parts:
            part = part.strip().upper()
            normalized = lang_map.get(
                part, part.lower()
            )  # Fallback về lowercase nếu không map được
            normalized_parts.append(normalized)
        return "+".join(normalized_parts)

    # Xử lý single language
    return lang_map.get(lang, lang.lower())  # Fallback về lowercase nếu không map được


def _is_cjk_character(char: str) -> bool:
    """
    Kiểm tra xem ký tự có phải là CJK (Chinese, Japanese, Korean) không.
    Dựa trên Unicode ranges cho CJK.
    """
    if not char:
        return False
    code = ord(char)
    # CJK Unified Ideographs: U+4E00–U+9FFF
    # CJK Extension A: U+3400–U+4DBF
    # CJK Extension B: U+20000–U+2A6DF
    # CJK Compatibility: U+F900–U+FAFF
    return (
        0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs
        or 0x3400 <= code <= 0x4DBF  # CJK Extension A
        or 0xF900 <= code <= 0xFAFF  # CJK Compatibility
    )


def _count_cjk_characters(text: str) -> int:
    """Đếm số ký tự CJK trong text."""
    return sum(1 for char in text if _is_cjk_character(char))


def _detect_chinese_variant(img: "Image", ocr_cfg: Dict[str, Any]) -> str:
    """
    Tự động nhận biết tiếng Trung giản thể hay phồn thể.
    Returns: "chi_sim" hoặc "chi_tra"
    
    Note: This function requires pytesseract to be installed.
    """
    try:
        import pytesseract
    except ImportError:
        logger.warning("pytesseract not installed, defaulting to chi_sim")
        return "chi_sim"
    
    # Set tesseract_cmd từ config nếu có
    if ocr_cfg.get("tesseract_cmd"):
        pytesseract.pytesseract.tesseract_cmd = ocr_cfg["tesseract_cmd"]
    
    # Thực hiện OCR với cả hai variant và so sánh confidence
    try:
        # OCR với Simplified Chinese
        sim_result = pytesseract.image_to_data(
            img, lang="chi_sim", output_type=pytesseract.Output.DICT
        )
        sim_confs = [
            c for c in sim_result.get("conf", []) if isinstance(c, (int, float)) and c > 0
        ]
        sim_avg = sum(sim_confs) / len(sim_confs) if sim_confs else 0

        # OCR với Traditional Chinese
        tra_result = pytesseract.image_to_data(
            img, lang="chi_tra", output_type=pytesseract.Output.DICT
        )
        tra_confs = [
            c for c in tra_result.get("conf", []) if isinstance(c, (int, float)) and c > 0
        ]
        tra_avg = sum(tra_confs) / len(tra_confs) if tra_confs else 0

        # Chọn variant có confidence cao hơn
        if tra_avg > sim_avg + 5:  # Thêm margin 5 điểm để tránh flip-flop
            logger.info(f"Detected Traditional Chinese (confidence: {tra_avg:.1f})")
            return "chi_tra"
        else:
            logger.info(f"Detected Simplified Chinese (confidence: {sim_avg:.1f})")
            return "chi_sim"

    except Exception as e:
        logger.warning(f"Chinese variant detection failed: {e}. Defaulting to chi_sim")
        return "chi_sim"


def _resolve_language(
    lang: str, ocr_cfg: Dict[str, Any], sample_img: Optional["Image"] = None
) -> str:
    """
    Resolve language code, chỉ hỗ trợ Chinese variant detection (giản thể/phồn thể).
    Auto-detect ngôn ngữ đã được loại bỏ do kém hiệu quả.

    Args:
        lang: Language string từ config (VD: EN, VN, vie+eng) — luôn được đưa qua
            _normalize_lang_code trước khi gọi Tesseract (file .traineddata là eng không phải EN).
        ocr_cfg: Config dictionary
        sample_img: Optional sample image for Chinese variant detection

    Returns:
        Resolved language string cho Tesseract (e.g., "chi_sim", "chi_tra", "vie+eng")
    """
    lang = _normalize_lang_code(lang)

    # Xử lý combined languages (e.g., "vie+eng")
    if "+" in lang:
        parts = lang.split("+")
        resolved_parts = []
        for part in parts:
            if part.lower() in ("chi", "chi_sim", "chi_tra"):
                # Chinese variant detection
                if sample_img is not None:
                    resolved = _detect_chinese_variant(sample_img, ocr_cfg)
                else:
                    resolved = "chi_sim"  # Default nếu không có sample
                resolved_parts.append(resolved)
            else:
                resolved_parts.append(part)
        return "+".join(resolved_parts)

    # Single language
    if lang.lower() in ("chi", "chi_sim", "chi_tra"):
        if sample_img is not None:
            return _detect_chinese_variant(sample_img, ocr_cfg)
        return "chi_sim"  # Default

    if lang.lower() == "auto":
        # Auto-detect đã bị loại bỏ, fallback về vie
        logger.warning("Auto language detection is deprecated. Defaulting to 'vie'.")
        return "vie"

    return lang
