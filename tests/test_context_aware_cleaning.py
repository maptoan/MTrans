from __future__ import annotations

from src.preprocessing.text_cleaner import clean_text


def test_domain_technical_keeps_url_and_email() -> None:
    config = {
        "preprocessing": {"cleaning": {"profile": "domain_technical"}},
        "translation": {"advanced_whitespace_normalization": True},
    }
    text = "Reference: https://example.com/spec and contact team@example.com"
    cleaned = clean_text(text, config=config)
    assert "https://example.com/spec" in cleaned
    assert "team@example.com" in cleaned


def test_aggressive_removes_url_and_email() -> None:
    config = {
        "preprocessing": {"cleaning": {"profile": "aggressive"}},
        "translation": {"advanced_whitespace_normalization": True},
    }
    text = "Reference: https://example.com/spec and contact team@example.com"
    cleaned = clean_text(text, config=config)
    assert "https://example.com/spec" not in cleaned
    assert "team@example.com" not in cleaned
