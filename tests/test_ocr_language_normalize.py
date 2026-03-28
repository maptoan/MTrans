"""OCR lang codes: config uses EN/VN/CN; Tesseract needs eng/vie/chi_* .traineddata names."""

from __future__ import annotations

from src.preprocessing.ocr.language_utils import _normalize_lang_code, _resolve_language


def test_normalize_en_to_eng() -> None:
    assert _normalize_lang_code("EN") == "eng"
    assert _normalize_lang_code("en") == "eng"


def test_resolve_language_accepts_config_style_en() -> None:
    assert _resolve_language("EN", {}, sample_img=None) == "eng"


def test_resolve_language_vn_plus_en() -> None:
    assert _resolve_language("VN+EN", {}, sample_img=None) == "vie+eng"


def test_normalize_preserves_chi_sim() -> None:
    assert _normalize_lang_code("chi_sim") == "chi_sim"
