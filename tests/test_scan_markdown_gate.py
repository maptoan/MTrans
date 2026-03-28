from __future__ import annotations

from src.preprocessing.scan_markdown import maybe_markdownize_scan_text


def _cfg(enabled: bool = True) -> dict:
    return {
        "enabled": enabled,
        "min_chars": 40,
        "min_avg_line_length": 8.0,
        "max_short_line_ratio": 0.9,
        "max_noisy_line_ratio": 0.9,
    }


def test_markdown_gate_disabled_keeps_text() -> None:
    text = "Chapter 1\nThis is a clean paragraph."
    out, meta = maybe_markdownize_scan_text(text, _cfg(enabled=False))
    assert out == text
    assert meta["applied"] is False
    assert meta["reason"] == "disabled"


def test_markdown_gate_enabled_applies_heading_conversion() -> None:
    text = "Chapter 1\nThis is line one\nThis is line two."
    out, meta = maybe_markdownize_scan_text(text, _cfg(enabled=True))
    assert out.startswith("## Chapter 1")
    assert meta["applied"] is True


def test_markdown_gate_rejects_too_short_text() -> None:
    text = "too short"
    out, meta = maybe_markdownize_scan_text(text, _cfg(enabled=True))
    assert out == text
    assert meta["applied"] is False
    assert meta["reason"] == "below_min_chars"
