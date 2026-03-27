from pathlib import Path
from typing import Any, Dict, Tuple
from unittest.mock import patch

import pytest

from src.preprocessing.file_parser import (
    AdvancedFileParser,
    FileParsingError,
    _parse_epub_zip_fallback,  # type: ignore[attr-defined]
)


def _create_dummy_epub(tmp_path: Path) -> str:
    """
    Tạo một đường dẫn .epub giả (không cần là EPUB hợp lệ cho các test mock).
    """
    epub_path = tmp_path / "dummy.epub"
    epub_path.write_text("dummy", encoding="utf-8")
    return str(epub_path)


@pytest.mark.parametrize(
    "error_message",
    [
        'There is no item named "OEBPS/Images/logo1.png" in the archive',
        "There is no item named 'OEBPS/Images/logo1.png' in the archive",
    ],
)
def test_parse_epub_missing_asset_uses_zip_fallback(tmp_path: Path, error_message: str) -> None:
    """
    Khi ebooklib.epub.read_epub() lỗi vì missing asset (logo/image),
    AdvancedFileParser.parse_epub phải fallback sang zip-based parser thay vì ném FileParsingError.
    """
    epub_path = _create_dummy_epub(tmp_path)
    parser = AdvancedFileParser({})

    with patch("src.preprocessing.file_parser.epub.read_epub") as mock_read_epub, patch(
        "src.preprocessing.file_parser._parse_epub_zip_fallback"
    ) as mock_fallback:
        mock_read_epub.side_effect = Exception(error_message)
        mock_fallback.return_value = ("fallback text", {"format": "epub"})

        text, metadata = parser.parse_epub(epub_path)

        assert text == "fallback text"
        assert metadata["format"] == "epub"
        mock_fallback.assert_called_once_with(epub_path)


def test_parse_epub_other_error_raises_fileparsingerror(tmp_path: Path) -> None:
    """
    Với các lỗi EPUB khác (không phải missing asset), parse_epub vẫn phải ném FileParsingError.
    """
    epub_path = _create_dummy_epub(tmp_path)
    parser = AdvancedFileParser({})

    with patch("src.preprocessing.file_parser.epub.read_epub") as mock_read_epub:
        mock_read_epub.side_effect = Exception("Corrupted EPUB structure")

        with pytest.raises(FileParsingError) as exc_info:
            parser.parse_epub(epub_path)

        assert "Failed to read EPUB" in str(exc_info.value)


def test_parse_epub_zip_fallback_handles_posix_paths_in_zip(tmp_path: Path) -> None:
    """
    _parse_epub_zip_fallback phải đọc được nội dung khi các entry trong ZIP dùng dấu '/' (POSIX),
    kể cả khi chạy trên Windows (nơi os.path.join tạo '\\').
    """
    import zipfile

    epub_path = tmp_path / "posix_paths.epub"

    # Tạo EPUB tối thiểu với:
    # - META-INF/container.xml
    # - OEBPS/content.opf
    # - OEBPS/Text/ch1.xhtml
    with zipfile.ZipFile(epub_path, "w") as zf:
        # container.xml
        container_xml = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
        zf.writestr("META-INF/container.xml", container_xml)

        # content.opf với manifest & spine
        opf_xml = """<?xml version="1.0" encoding="utf-8"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
  <manifest>
    <item id="ch1" href="Text/ch1.xhtml" media-type="application/xhtml+xml" />
  </manifest>
  <spine toc="ncx">
    <itemref idref="ch1" />
  </spine>
</package>
"""
        zf.writestr("OEBPS/content.opf", opf_xml)

        # Nội dung chương
        ch1_html = "<html><body><p>Xin chao Tay Du Ky</p></body></html>"
        # Lưu ý: đường dẫn trong ZIP dùng '/', không phải '\\'
        zf.writestr("OEBPS/Text/ch1.xhtml", ch1_html)

    text, metadata = _parse_epub_zip_fallback(str(epub_path))

    assert "Xin chao Tay Du Ky" in text
    assert metadata["format"] == "epub"

