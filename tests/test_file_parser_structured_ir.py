from __future__ import annotations

from pathlib import Path

from src.preprocessing.file_parser import parse_file_advanced


def test_parse_file_advanced_includes_structured_ir_when_enabled(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("# Head\n\nParagraph", encoding="utf-8")
    config = {"preprocessing": {"structured_ir": {"enabled": True}, "force_encoding": "utf-8"}}
    parsed = parse_file_advanced(str(sample), config)
    assert parsed["structured_ir"] is not None
    assert len(parsed["structured_ir"]) >= 2
