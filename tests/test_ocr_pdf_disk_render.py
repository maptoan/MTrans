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

    mock_convert = MagicMock(
        side_effect=[
            [str(Path("/tmp/mt_ocr_test/w000001/fake1.jpg"))],
            [str(Path("/tmp/mt_ocr_test/w000002/fake2.jpg"))],
        ]
    )
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
            return_value={"dpi": 200, "lang": "eng"},
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
