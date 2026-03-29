"""Ensure scan PDF OCR renders pages to disk to avoid multi-page stdout buffering (MemoryError)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


@patch("shutil.rmtree")
@patch("os.remove")
@patch("os.makedirs")
@patch("tempfile.mkdtemp", return_value=str(Path("/tmp/mt_ocr_test")))
@patch("src.preprocessing.ocr.image_processor._image_to_text", return_value="ok")
@patch("pdf2image.pdfinfo_from_path", return_value={"Pages": 2})
@patch("PIL.Image.open")
def test_ocr_pdf_writes_each_page_to_output_folder(
    mock_image_open,
    _mock_pdfinfo,
    _mock_img2txt,
    _mock_mkdtemp,
    _mock_makedirs,
    _mock_remove,
    _mock_rmtree,
) -> None:
    import src.preprocessing.ocr.pdf_processor as pdfp

    def _convert_fake(*_a: object, **kwargs: object) -> list[str]:
        p = int(kwargs["first_page"])
        return [str(Path(f"/tmp/mt_ocr_test/w{p:06d}/fake.jpg"))]

    mock_convert = MagicMock(side_effect=_convert_fake)
    cm = MagicMock()
    cm.__enter__.return_value = cm
    cm.__exit__.return_value = None
    mock_image_open.return_value = cm

    with (
        patch.object(pdfp, "convert_from_path", mock_convert),
        patch.object(pdfp, "_get_pdf_refs", lambda _cfg: None),
        patch(
            "src.preprocessing.ocr.dependency_manager.apply_tesseract_cfg",
            lambda _cfg: None,
        ),
        patch(
            "src.preprocessing.ocr.config_loader._detect_bundled_binaries",
            lambda c: c,
        ),
        patch(
            "src.preprocessing.ocr.config_loader.load_ocr_config",
            return_value={
                "dpi": 200,
                "lang": "eng",
                "pdf_ocr_max_workers": 1,
            },
        ),
    ):
        text, n = pdfp.ocr_pdf("dummy.pdf", config_path="config/config.yaml", pages=None)

    assert n == 2
    assert text == "ok\n\nok"
    assert mock_convert.call_count == 2
    for _name, args, kwargs in mock_convert.mock_calls:
        assert kwargs.get("output_folder") is not None
        assert kwargs.get("paths_only") is True
        assert kwargs.get("first_page") == kwargs.get("last_page")


def test_resolve_pdf_ocr_max_workers_caps_by_page_count() -> None:
    from src.preprocessing.ocr.pdf_processor import _resolve_pdf_ocr_max_workers

    assert _resolve_pdf_ocr_max_workers({"pdf_ocr_max_workers": 99}, 2) == 2
    assert _resolve_pdf_ocr_max_workers({"pdf_ocr_max_workers": 1}, 500) == 1


def test_resolve_pdf_ocr_max_workers_falls_back_to_performance_when_flagged() -> None:
    from src.preprocessing.ocr.pdf_processor import _resolve_pdf_ocr_max_workers

    cfg = {
        "_root_performance": {"max_parallel_workers": 3},
        "tesseract_cap_from_performance": True,
    }
    assert _resolve_pdf_ocr_max_workers(cfg, 100) == 3
    assert _resolve_pdf_ocr_max_workers(cfg, 2) == 2


def test_resolve_pdf_ocr_ignores_performance_without_flag() -> None:
    from unittest.mock import patch

    from src.preprocessing.ocr.pdf_processor import _resolve_pdf_ocr_max_workers

    cfg = {"_root_performance": {"max_parallel_workers": 3}}
    with patch("src.preprocessing.ocr.pdf_processor.os.cpu_count", return_value=8):
        assert _resolve_pdf_ocr_max_workers(cfg, 100) == 8


def test_resolve_pdf_ocr_tesseract_max_workers_hard_cap() -> None:
    from unittest.mock import patch

    from src.preprocessing.ocr.pdf_processor import _resolve_pdf_ocr_max_workers

    cfg = {"tesseract_max_workers": 2}
    with patch("src.preprocessing.ocr.pdf_processor.os.cpu_count", return_value=16):
        assert _resolve_pdf_ocr_max_workers(cfg, 100) == 2


def test_resolve_pdf_ocr_workers_per_cpu() -> None:
    from unittest.mock import patch

    from src.preprocessing.ocr.pdf_processor import _resolve_pdf_ocr_max_workers

    cfg = {"tesseract_workers_per_cpu": 0.5, "tesseract_max_workers": 8}
    with patch("src.preprocessing.ocr.pdf_processor.os.cpu_count", return_value=4):
        assert _resolve_pdf_ocr_max_workers(cfg, 100) == 2
