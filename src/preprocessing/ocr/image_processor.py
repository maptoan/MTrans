# -*- coding: utf-8 -*-
"""
Image preprocessing and OCR logic for OCR module.
Extracted from ocr_reader.py.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from PIL import Image

from .language_utils import _resolve_language

logger = logging.getLogger("NovelTranslator")


def _preprocess_image_for_ocr(img: "Image.Image", ocr_cfg: Dict[str, Any]) -> "Image.Image":
    """
    Preprocess image để cải thiện chất lượng OCR.
    Bao gồm: contrast enhancement, denoise, convert to grayscale nếu cần.
    """
    try:
        from PIL import Image as PIL_Image
        
        # Convert to RGB nếu cần (PIL Image có thể là RGBA, L, P, etc.)
        if img.mode not in ("RGB", "L"):
            if img.mode == "RGBA":
                # Tạo background trắng cho RGBA
                rgb_img = PIL_Image.new("RGB", img.size, (255, 255, 255))
                # Paste uses alpha channel as mask if available
                if len(img.split()) >= 4:
                    rgb_img.paste(img, mask=img.split()[3])
                else:
                    rgb_img.paste(img)
                img = rgb_img
            else:
                img = img.convert("RGB")

        # Convert to grayscale để cải thiện OCR (đặc biệt cho Chinese text)
        if ocr_cfg.get("preprocess_grayscale", True):
            img = img.convert("L")  # Grayscale

        # Contrast enhancement
        if ocr_cfg.get("preprocess_enhance_contrast", True):
            try:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)  # Tăng contrast 20%
            except Exception:
                pass  # Nếu không có ImageEnhance, bỏ qua

        # Sharpness enhancement
        if ocr_cfg.get("preprocess_enhance_sharpness", True):
            try:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.1)  # Tăng sharpness 10%
            except Exception:
                pass

        return img
    except Exception as e:
        logger.debug(f"Image preprocessing failed: {e}, using original image")
        return img


def _image_to_text(
    img: "Image.Image", 
    ocr_cfg: Dict[str, Any], 
    lang_override: Optional[str] = None
) -> str:
    """
    OCR một ảnh thành text.

    Args:
        img: PIL Image object
        ocr_cfg: OCR config dictionary
        lang_override: Optional resolved language string
    """
    from . import dependency_manager

    # Preprocess image trước khi OCR
    if ocr_cfg.get("preprocess_image", True):
        img = _preprocess_image_for_ocr(img, ocr_cfg)

    lang = lang_override
    if lang is None:
        raw_lang = ocr_cfg.get("lang", "vie+eng")
        lang = _resolve_language(raw_lang, ocr_cfg, sample_img=img)

    # PSM mode: PSM 3 (auto) is often better for complex layouts
    default_psm = 3
    psm = int(ocr_cfg.get("psm", default_psm) or default_psm)

    # Warning for Chinese PSM 6
    if "chi" in lang.lower() and psm == 6:
        logger.debug(
            "PSM 6 (single block) có thể không phù hợp với Chinese text có layout phức tạp. "
            "Đề xuất dùng PSM 3 (auto) hoặc PSM 4 (single column)."
        )

    config = f"--psm {psm}"
    return dependency_manager.pytesseract.image_to_string(img, lang=lang, config=config)
