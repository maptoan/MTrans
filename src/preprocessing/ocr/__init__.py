# -*- coding: utf-8 -*-
"""
OCR Utilities Package.
Standardized and refactored OCR logic for better maintenance and type safety.

Public API:
- ocr_pdf: Main function to OCR a PDF file.
- ai_cleanup_text: Cleanup OCR text using AI.
- ai_spell_check_and_paragraph_restore: Spell check and restore paragraphs using AI.
- load_ocr_config: Load OCR configuration from YAML.
- ensure_dependencies: Verify and install necessary dependencies.

Exceptions:
- OCRError: Base class for all OCR-related errors.
- DependencyError: Raised when a required dependency is missing.
- ConfigError: Raised when there's an issue with the configuration.
- AIProcessorError: Raised for AI-related processing failures.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Dict, List, Optional, Tuple

# Configuration & Dependencies
# AI Processing
from .ai_processor import (
    _ai_cleanup_parallel,
    _ai_spell_check_parallel,
    _cleanup_chunk_async,
    _preprocess_line_breaks,
    _retry_failed_chunks_cleanup,
    _retry_failed_chunks_spell_check,
    _spell_check_chunk_async,
    _split_text_at_sentence_boundaries,
    ai_cleanup_text,
    ai_spell_check_and_paragraph_restore,
)
from .config_loader import (
    _build_safety_settings,
    _bundle_base_dir,
    _detect_bundled_binaries,
    _ensure_logger_config,
    _load_yaml,
    _parse_pages,
    load_ocr_config,
)
from .dependency_manager import _ensure_dependencies, _pip_install, apply_tesseract_cfg, ensure_dependencies
from .docx_processor import (
    _convert_html_to_docx_with_pandoc,
    _create_html_from_items,
    batch_small_paragraphs,
    build_cleanup_prompt_with_hints,
    extract_format_hints,
    extract_images_from_paragraph,
    extract_paragraphs_with_hints,
    is_in_table,
)

# Exceptions
from .exceptions import (
    AIProcessorError,
    ConfigError,
    DependencyError,
    OCRBinaryNotFoundError,
    OCRError,
    PillowNotInstalledError,
    PopplerNotInstalledError,
    PyMuPDFNotInstalledError,
    TesseractNotInstalledError,
)
from .image_processor import _image_to_text, _preprocess_image_for_ocr

# Utilities
from .language_utils import (
    _count_cjk_characters,
    _detect_chinese_variant,
    _is_cjk_character,
    _normalize_lang_code,
    _resolve_language,
)
from .logging_filters import GoogleLogFilter, NoisyMessageFilter, _suppress_google_logs
from .menu_handler import _show_completion_menu

# Core Processing
from .pdf_processor import (
    convert_pdf_to_docx,
    convert_pdf_with_ocrmypdf,
    detect_pdf_type,
    extract_text_from_pdf,
    hybrid_workflow_pdf_to_docx,
    ocr_pdf,
)

__all__ = [
    # Public Functions
    "ocr_pdf",
    "ai_cleanup_text",
    "ai_spell_check_and_paragraph_restore",
    "load_ocr_config",
    "ensure_dependencies",
    "convert_pdf_to_docx",
    "hybrid_workflow_pdf_to_docx",
    "detect_pdf_type",
    "extract_text_from_pdf",
    
    # Exceptions
    "OCRError",
    "DependencyError",
    "ConfigError",
    "AIProcessorError",
    "OCRBinaryNotFoundError",
    "TesseractNotInstalledError",
    "PopplerNotInstalledError",
    "PillowNotInstalledError",
    "PyMuPDFNotInstalledError",
    
    # Utility (Public-ish)
    "apply_tesseract_cfg",
    
    # Internal but exported for ocr_reader.py delegation
    "NoisyMessageFilter",
    "GoogleLogFilter",
    "_suppress_google_logs",
    "_detect_bundled_binaries",
    "_ensure_logger_config",
    "_load_yaml",
    "_build_safety_settings",
    "_bundle_base_dir",
    "_parse_pages",
    "_normalize_lang_code",
    "_is_cjk_character",
    "_count_cjk_characters",
    "_detect_chinese_variant",
    "_resolve_language",
    "_image_to_text",
    "_preprocess_image_for_ocr",
    "_pip_install",
    "_ensure_dependencies",
    "_cleanup_chunk_async",
    "_ai_cleanup_parallel",
    "_split_text_at_sentence_boundaries",
    "_preprocess_line_breaks",
    "_spell_check_chunk_async",
    "_ai_spell_check_parallel",
    "_retry_failed_chunks_cleanup",
    "_retry_failed_chunks_spell_check",
    # DOCX Processor
    "extract_format_hints",
    "is_in_table",
    "extract_images_from_paragraph",
    "extract_paragraphs_with_hints",
    "batch_small_paragraphs",
    "build_cleanup_prompt_with_hints",
    "_create_html_from_items",
    "_convert_html_to_docx_with_pandoc",
    # Menu Handler
    "_show_completion_menu",
]
