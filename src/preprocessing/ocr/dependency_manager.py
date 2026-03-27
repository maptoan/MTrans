# -*- coding: utf-8 -*-
"""
Dependency management for OCR module.
Handles lazy loading of heavy libraries and binary detection.
Extracted from ocr_reader.py.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import traceback
from typing import Any, Dict, List, Optional

from src.utils.helpers import lazy_import_and_install

from .config_loader import _detect_bundled_binaries
from .exceptions import DependencyError

logger = logging.getLogger("NovelTranslator")

# Lazy-loaded modules and objects (initially None)
Image = None
pytesseract = None
convert_from_path = None
tqdm = None
PyPDF2 = None
pdfplumber = None
fitz = None
Document = None
Inches = None
Pt = None
WD_PARAGRAPH_ALIGNMENT = None
Converter = None
ocrmypdf = None
ocrmypdf_available = False


def _pip_install(package: str) -> None:
    """Helper to install a package using pip via lazy_import_and_install."""
    try:
        lazy_import_and_install(package)
    except Exception as e:
        raise DependencyError(f"Không thể cài gói '{package}': {e}")


def ensure_dependencies(ocr_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure all required dependencies are installed and imported.
    Returns a dictionary of initialized modules/objects.
    """
    global \
        Image, \
        pytesseract, \
        convert_from_path, \
        tqdm, \
        PyPDF2, \
        pdfplumber, \
        fitz, \
        Document, \
        Inches, \
        Pt, \
        WD_PARAGRAPH_ALIGNMENT, \
        Converter, \
        ocrmypdf, \
        ocrmypdf_available

    # Pillow
    if Image is None:
        PIL = lazy_import_and_install("Pillow", "PIL", ">=10.0.0")
        Image = getattr(PIL, "Image")
    
    # pdf2image
    if convert_from_path is None:
        pdf2image = lazy_import_and_install("pdf2image", "pdf2image", ">=1.17.0")
        convert_from_path = getattr(pdf2image, "convert_from_path")
    
    # pytesseract
    if pytesseract is None:
        pytesseract = lazy_import_and_install("pytesseract", "pytesseract", ">=0.3.10")
    
    # pdfplumber
    if pdfplumber is None:
        try:
            pdfplumber = lazy_import_and_install("pdfplumber", "pdfplumber", ">=0.9.0")
        except Exception:
            pass
    
    # PyPDF2
    if PyPDF2 is None:
        try:
            PyPDF2 = lazy_import_and_install("PyPDF2", "PyPDF2", ">=3.0.0")
        except Exception:
            pass
    
    # tqdm
    if bool(ocr_cfg.get("show_progress", True)) and tqdm is None:
        try:
            _tqdm_mod = lazy_import_and_install("tqdm", "tqdm", ">=4.65.0")
            from tqdm import tqdm as _tqdm
            tqdm = _tqdm
        except Exception:
            tqdm = None
    
    # PyMuPDF (fitz)
    if fitz is None:
        try:
            fitz = lazy_import_and_install("PyMuPDF", "fitz", ">=1.23.0,<1.26.5")
        except Exception:
            try:
                fitz = lazy_import_and_install("PyMuPDF==1.26.4", "fitz")
            except Exception:
                fitz = None
    
    # python-docx
    if Document is None:
        try:
            lazy_import_and_install("python-docx", "docx", ">=1.0.0")
            from docx import Document as _Document
            from docx.enum.text import WD_PARAGRAPH_ALIGNMENT as _WD_PARAGRAPH_ALIGNMENT
            from docx.shared import Inches as _Inches
            from docx.shared import Pt as _Pt

            Document = _Document
            Inches = _Inches
            Pt = _Pt
            WD_PARAGRAPH_ALIGNMENT = _WD_PARAGRAPH_ALIGNMENT
        except Exception:
            Document = None
            Inches = None
            Pt = None
            WD_PARAGRAPH_ALIGNMENT = None
    
    # pdf2docx
    if Converter is None:
        try:
            _pdf2docx = lazy_import_and_install("pdf2docx", "pdf2docx", ">=0.5.0")
            from pdf2docx import Converter as _Converter
            Converter = _Converter
        except Exception:
            Converter = None

    # OCRmyPDF
    if not ocrmypdf_available:
        try:
            logger.debug("🔍 Bước 1: Đang import Python module ocrmypdf...")
            _ocrmypdf = lazy_import_and_install("ocrmypdf", "ocrmypdf", ">=15.0.0")
            ocrmypdf = _ocrmypdf
            logger.debug("✅ Bước 1: Python module ocrmypdf đã import thành công")

            logger.debug("🔍 Bước 2: Đang tìm command 'ocrmypdf' trên PATH...")
            ocrmypdf_cmd = shutil.which("ocrmypdf")

            if not ocrmypdf_cmd and sys.platform == "win32":
                python_exe = sys.executable
                scripts_dir = os.path.join(os.path.dirname(python_exe), "Scripts")
                ocrmypdf_exe = os.path.join(scripts_dir, "ocrmypdf.exe")
                if os.path.exists(ocrmypdf_exe):
                    ocrmypdf_cmd = ocrmypdf_exe

            if ocrmypdf_cmd:
                # Ghostscript check
                gs_cmd = None
                if sys.platform == "win32":
                    gs_cmd = shutil.which("gswin64c") or shutil.which("gswin32c")
                    if not gs_cmd:
                        for gs_name in ["gswin64c.exe", "gswin32c.exe"]:
                            for prog_dir in [
                                os.path.join(os.environ.get("ProgramFiles", ""), "gs"),
                                os.path.join(os.environ.get("ProgramFiles(x86)", ""), "gs"),
                            ]:
                                if prog_dir:
                                    for root, dirs, files in os.walk(prog_dir):
                                        if gs_name in files:
                                            gs_cmd = os.path.join(root, gs_name)
                                            break
                                    if gs_cmd: break
                            if gs_cmd: break
                else:
                    gs_cmd = shutil.which("gs")

                if not gs_cmd:
                    ocrmypdf_available = False
                    ocrmypdf = None
                    logger.warning("⚠️  OCRmyPDF không khả dụng: Thiếu Ghostscript")
                else:
                    # Tesseract check
                    tesseract_cmd = shutil.which("tesseract")
                    if not tesseract_cmd and sys.platform == "win32":
                        _cfg = _detect_bundled_binaries(ocr_cfg)
                        tesseract_cmd = _cfg.get("tesseract_cmd")
                    
                    if not tesseract_cmd:
                        ocrmypdf_available = False
                        ocrmypdf = None
                        logger.warning("⚠️  OCRmyPDF không khả dụng: Thiếu Tesseract OCR")
                    else:
                        # Version check
                        try:
                            cmd_to_run = [ocrmypdf_cmd, "--version"] if os.path.isabs(ocrmypdf_cmd) else ["ocrmypdf", "--version"]
                            result = subprocess.run(cmd_to_run, capture_output=True, text=True, timeout=10)
                            if result.returncode == 0:
                                ocrmypdf_available = True
                                logger.info(f"✅ OCRmyPDF khả dụng: {ocrmypdf_cmd}")
                            else:
                                ocrmypdf_available = False
                                ocrmypdf = None
                        except Exception as e:
                            ocrmypdf_available = False
                            ocrmypdf = None
                            logger.warning(f"⚠️  OCRmyPDF không khả dụng: Lỗi khi chạy command: {e}")
            else:
                ocrmypdf_available = False
                ocrmypdf = None
                logger.warning("⚠️  OCRmyPDF không khả dụng: Command 'ocrmypdf' không tìm thấy trên PATH")
        except Exception as e:
            ocrmypdf_available = False
            ocrmypdf = None
            logger.warning(f"⚠️  OCRmyPDF không khả dụng: Exception: {e}")
            logger.debug(f"   - Traceback: {traceback.format_exc()}")

    # Return a dictionary of all managed dependencies
    return {
        "Image": Image,
        "pytesseract": pytesseract,
        "convert_from_path": convert_from_path,
        "tqdm": tqdm,
        "PyPDF2": PyPDF2,
        "pdfplumber": pdfplumber,
        "fitz": fitz,
        "Document": Document,
        "Inches": Inches,
        "Pt": Pt,
        "WD_PARAGRAPH_ALIGNMENT": WD_PARAGRAPH_ALIGNMENT,
        "Converter": Converter,
        "ocrmypdf": ocrmypdf,
        "ocrmypdf_available": ocrmypdf_available,
    }


# Backward compatibility alias for ocr_reader.py
_ensure_dependencies = ensure_dependencies


def apply_tesseract_cfg(ocr_cfg: Dict[str, Any], pytesseract_mod: Any = None) -> None:
    """Apply Tesseract configuration (path to binary)."""
    target_pytesseract = pytesseract_mod if pytesseract_mod else pytesseract
    if target_pytesseract is None:
        raise DependencyError("pytesseract not installed. Please install pytesseract and system Tesseract.")
    
    cfg = _detect_bundled_binaries(ocr_cfg)
    tesseract_cmd = cfg.get("tesseract_cmd")
    if tesseract_cmd:
        target_pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
