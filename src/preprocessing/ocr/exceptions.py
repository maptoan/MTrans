"""Custom exceptions for OCR processing package.

This module defines a hierarchy of exceptions for better error handling
and debugging across the OCR processing pipeline.
"""

from __future__ import annotations


class OCRError(Exception):
    """Base exception for all OCR-related errors.
    
    All custom exceptions in the OCR package inherit from this class,
    making it easy to catch any OCR-specific error with a single except clause.
    """
    pass


class DependencyError(OCRError):
    """Raised when a required dependency is missing or fails to install.
    
    Examples:
        - Tesseract not found
        - Python package installation failed
        - Missing system binaries
    """
    pass


class ConfigError(OCRError):
    """Raised when configuration is invalid or missing.
    
    Examples:
        - Invalid YAML syntax
        - Missing required config keys
        - Invalid parameter values
    """
    pass


class AIProcessorError(OCRError):
    """Raised when AI processing fails.
    
    Examples:
        - API timeout
        - Safety filter blocks content
        - Invalid response from AI model
    """
    pass


class PDFProcessorError(OCRError):
    """Raised when PDF processing fails.
    
    Examples:
        - Corrupted PDF file
        - Unsupported PDF format
        - Text extraction failure
    """
    pass


class DOCXProcessorError(OCRError):
    """Raised when DOCX processing fails.
    
    Examples:
        - Corrupted DOCX file
        - Pandoc conversion failure
        - Image insertion failure
    """
    pass


class OCRBinaryNotFoundError(DependencyError):
    """Raised when a specific binary (Tesseract, Poppler) is not found."""
    pass


class TesseractNotInstalledError(OCRBinaryNotFoundError):
    """Raised when Tesseract OCR binary is not found."""
    pass


class PopplerNotInstalledError(OCRBinaryNotFoundError):
    """Raised when Poppler (pdf2image) binaries are not found."""
    pass


class PillowNotInstalledError(DependencyError):
    """Raised when Pillow (PIL) is not installed."""
    pass


class PyMuPDFNotInstalledError(DependencyError):
    """Raised when PyMuPDF (fitz) is not installed."""
    pass
