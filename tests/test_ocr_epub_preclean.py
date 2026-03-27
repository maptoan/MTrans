from pathlib import Path
from typing import Any, Dict

import pytest

from src.preprocessing import ocr_reader


def _build_minimal_ocr_cfg() -> Dict[str, Any]:
    """
    Tạo config OCR tối thiểu cho test:
    - Không bật AI cleanup / spell check để tránh gọi API.
    """
    return {
        "_root_config": {},
        "ai_cleanup": {"enabled": False},
        "ai_spell_check": {"enabled": False},
    }


def test_ocr_file_epub_uses_parse_file_advanced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Đảm bảo nhánh AI Pre-clean cho .epub không gọi trực tiếp AdvancedFileParser.parse,
    mà sử dụng parse_file_advanced và không ném lỗi.
    """
    # Tạo file .epub giả (nội dung không quan trọng vì đã mock parser)
    input_path = tmp_path / "test.epub"
    input_path.write_text("dummy", encoding="utf-8")

    # Ghi nhận việc parse_file_advanced được gọi
    called: Dict[str, Any] = {}

    def fake_load_ocr_config(_: str) -> Dict[str, Any]:
        return _build_minimal_ocr_cfg()

    def fake_detect_bundled(cfg: Dict[str, Any]) -> Dict[str, Any]:
        return cfg

    def fake_ensure_logger_config() -> None:
        return None

    def fake_ensure_dependencies(_: Dict[str, Any]) -> None:
        return None

    def fake_parse_file_advanced(filepath: str, config: Dict[str, Any]) -> Dict[str, Any]:
        called["filepath"] = filepath
        called["config"] = config
        return {
            "text": "EPUB content",
            "metadata": {"page_count": 1},
            "format": "epub",
        }

    # Monkeypatch các dependency nặng để test chỉ tập trung vào nhánh parse .epub
    monkeypatch.setattr(ocr_reader, "_ensure_logger_config", fake_ensure_logger_config)
    monkeypatch.setattr(ocr_reader, "load_ocr_config", fake_load_ocr_config)
    monkeypatch.setattr(ocr_reader, "_detect_bundled_binaries", fake_detect_bundled)
    monkeypatch.setattr(ocr_reader, "_ensure_dependencies", fake_ensure_dependencies)

    # parse_file_advanced được import dynamic bên trong ocr_file,
    # nên cần patch trực tiếp vào module file_parser nơi hàm được định nghĩa.
    from src.preprocessing import file_parser

    monkeypatch.setattr(file_parser, "parse_file_advanced", fake_parse_file_advanced)

    result = ocr_reader.ocr_file(
        input_path=str(input_path),
        config_path="dummy.yaml",
        pages=None,
        output_path=None,
        skip_steps=None,
        pdf_type=None,
        skip_completion_menu=True,
    )

    # Đảm bảo parser được gọi đúng
    assert called["filepath"] == str(input_path)
    assert isinstance(called["config"], dict)

    # Và ocr_file trả về text như mong đợi, không ném exception
    assert result["text"] == "EPUB content"


def test_ocr_spell_check_hard_timeout_does_not_hang(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Regression: OCR workflow không được phép treo vô hạn sau khi cleanup xong.

    Tái hiện: spell check bị block (ví dụ do chờ key/429) → phải bị cắt bởi hard timeout
    và OCR vẫn trả kết quả để pipeline đi tiếp.
    """
    input_path = tmp_path / "test.epub"
    input_path.write_text("dummy", encoding="utf-8")

    # Mock OCR config: bật spell check + hard timeout rất nhỏ
    def fake_load_ocr_config(_: str) -> Dict[str, Any]:
        return {
            "_root_config": {},
            "ai_cleanup": {"enabled": False},
            "ai_spell_check": {"enabled": True, "hard_timeout_seconds": 0.2},
        }

    def fake_detect_bundled(cfg: Dict[str, Any]) -> Dict[str, Any]:
        return cfg

    def fake_ensure_logger_config() -> None:
        return None

    def fake_ensure_dependencies(_: Dict[str, Any]) -> None:
        return None

    def fake_parse_file_advanced(filepath: str, config: Dict[str, Any]) -> Dict[str, Any]:
        return {"text": "EPUB content", "metadata": {"page_count": 1}, "format": "epub"}

    # Spell check giả lập bị treo (sleep lâu hơn hard timeout)
    import time as _time

    def fake_spell_check(text: str, ocr_cfg: Dict[str, Any], key_manager: Any = None):
        _time.sleep(2.0)
        return (text + "\nSPELLCHECK", [], [text])

    monkeypatch.setattr(ocr_reader, "_ensure_logger_config", fake_ensure_logger_config)
    monkeypatch.setattr(ocr_reader, "load_ocr_config", fake_load_ocr_config)
    monkeypatch.setattr(ocr_reader, "_detect_bundled_binaries", fake_detect_bundled)
    monkeypatch.setattr(ocr_reader, "_ensure_dependencies", fake_ensure_dependencies)

    from src.preprocessing import file_parser

    monkeypatch.setattr(file_parser, "parse_file_advanced", fake_parse_file_advanced)

    # Patch spell check impl (ocr_reader dùng symbol đã import)
    monkeypatch.setattr(ocr_reader, "ai_spell_check_and_paragraph_restore", fake_spell_check)

    start = _time.time()
    result = ocr_reader.ocr_file(
        input_path=str(input_path),
        config_path="dummy.yaml",
        pages=None,
        output_path=None,
        skip_steps=None,
        pdf_type=None,
        skip_completion_menu=True,
    )
    elapsed = _time.time() - start

    # Nếu không có hard timeout, test sẽ mất ~2s; ta kỳ vọng cắt sớm
    assert elapsed < 1.0
    assert result["text"] == "EPUB content"
