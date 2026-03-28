from __future__ import annotations

import re
from typing import Any, Dict, Tuple


_HEADING_PATTERN = re.compile(
    r"^(?:chapter\s+\d+|chương\s+\d+|第\s*\d+\s*章|part\s+\d+|phần\s+\d+)\b",
    re.IGNORECASE,
)


def _compute_quality_metrics(text: str) -> Dict[str, float]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return {
            "line_count": 0.0,
            "avg_line_length": 0.0,
            "short_line_ratio": 1.0,
            "noisy_line_ratio": 1.0,
        }

    short_lines = 0
    noisy_lines = 0
    total_len = 0
    for line in lines:
        total_len += len(line)
        if len(line) < 8:
            short_lines += 1
        non_word = sum(1 for ch in line if not (ch.isalnum() or ch.isspace()))
        if line and (non_word / max(1, len(line))) > 0.45:
            noisy_lines += 1

    count = float(len(lines))
    return {
        "line_count": count,
        "avg_line_length": float(total_len) / count,
        "short_line_ratio": float(short_lines) / count,
        "noisy_line_ratio": float(noisy_lines) / count,
    }


def _should_markdownize_scan_text(text: str, cfg: Dict[str, Any]) -> Tuple[bool, str, Dict[str, float]]:
    metrics = _compute_quality_metrics(text)
    if not cfg.get("enabled", False):
        return False, "disabled", metrics

    min_chars = int(cfg.get("min_chars", 800))
    if len(text.strip()) < min_chars:
        return False, "below_min_chars", metrics

    if metrics["avg_line_length"] < float(cfg.get("min_avg_line_length", 24.0)):
        return False, "avg_line_too_short", metrics
    if metrics["short_line_ratio"] > float(cfg.get("max_short_line_ratio", 0.55)):
        return False, "too_many_short_lines", metrics
    if metrics["noisy_line_ratio"] > float(cfg.get("max_noisy_line_ratio", 0.25)):
        return False, "too_noisy", metrics
    return True, "passed", metrics


def _convert_text_to_markdown(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    output_lines = []
    paragraph_buffer = []

    def flush_paragraph() -> None:
        if paragraph_buffer:
            output_lines.append(" ".join(paragraph_buffer).strip())
            paragraph_buffer.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            if output_lines and output_lines[-1] != "":
                output_lines.append("")
            continue

        if _HEADING_PATTERN.match(line):
            flush_paragraph()
            output_lines.append(f"## {line}")
            continue

        # Join wrapped scan lines into one paragraph.
        paragraph_buffer.append(line)

    flush_paragraph()
    return "\n".join(output_lines).strip()


def maybe_markdownize_scan_text(text: str, cfg: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    should_apply, reason, metrics = _should_markdownize_scan_text(text, cfg or {})
    if not should_apply:
        return text, {"applied": False, "reason": reason, "metrics": metrics}
    converted = _convert_text_to_markdown(text)
    return converted, {"applied": True, "reason": reason, "metrics": metrics}
