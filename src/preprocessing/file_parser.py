# -*- coding: utf-8 -*-
from __future__ import annotations

"""
(PHIÊN BẢN NÂNG CẤP) Module phân tích và trích xuất nội dung từ nhiều định dạng file.
Cải tiến: Better error handling, metadata extraction, progress tracking.
"""

import logging
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from xml.etree import ElementTree as ET

import chardet
import docx
import ebooklib
import PyPDF2
from bs4 import BeautifulSoup
from ebooklib import epub

logger = logging.getLogger("NovelTranslator")


class FileParsingError(Exception):
    """Custom exception cho lỗi parsing."""

    pass


class AdvancedFileParser:
    """
    File parser nâng cao với metadata extraction và error handling tốt hơn.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.supported_formats = {".txt", ".epub", ".docx", ".pdf"}

    def parse_txt(
        self, filepath: str, force_encoding: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Parse TXT file với auto-detection và metadata.
        Returns: (text_content, metadata)
        """
        encoding_to_use = force_encoding
        confidence = 1.0

        if not encoding_to_use or encoding_to_use.lower() == "auto":
            try:
                with open(filepath, "rb") as f:
                    raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding_to_use = detected["encoding"] or "utf-8"
                confidence = detected.get("confidence", 0.0)
                logger.info(
                    f"Auto-detected encoding: {encoding_to_use} (confidence: {confidence:.2%})"
                )

                # Nếu confidence thấp, thử utf-8 trước
                if confidence < 0.7:
                    logger.warning(
                        f"Low confidence ({confidence:.2%}), trying UTF-8 first"
                    )
                    encoding_to_use = "utf-8"
            except Exception as e:
                logger.warning(f"Encoding detection failed: {e}, using UTF-8")
                encoding_to_use = "utf-8"
        else:
            logger.info(f"Using specified encoding: {encoding_to_use}")

        # Try reading with detected encoding
        try:
            with open(filepath, "r", encoding=encoding_to_use, errors="replace") as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"Failed with {encoding_to_use}, retrying with UTF-8")
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            encoding_to_use = "utf-8"

        metadata = {
            "format": "txt",
            "encoding": encoding_to_use,
            "encoding_confidence": confidence,
            "size_bytes": os.path.getsize(filepath),
            "char_count": len(content),
        }

        return content, metadata

    def parse_epub(self, filepath: str) -> Tuple[str, Dict]:
        """
        Parse EPUB với metadata extraction tốt hơn.
        Returns: (text_content, metadata)
        """
        try:
            book = epub.read_epub(filepath)
        except Exception as e:
            # Một số EPUB có khai báo asset (logo, ảnh, font) trong manifest nhưng file thực tế không tồn tại.
            # ebooklib sẽ raise lỗi kiểu "There is no item named 'OEBPS/Images/logo1.png' in the archive"
            # Trong trường hợp này, ta fallback sang parser dựa trên zipfile và tự đọc XHTML, bỏ qua asset lỗi.
            message = str(e)
            if "There is no item named" in message and any(
                ext in message for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
            ):
                logger.warning(
                    "EPUB có asset bị thiếu trong archive (ví dụ logo/image). "
                    "Đang fallback sang zip-based EPUB parser để trích xuất text..."
                )
                return _parse_epub_zip_fallback(filepath)
            raise FileParsingError(f"Failed to read EPUB: {e}")

        # Extract metadata
        metadata = {
            "format": "epub",
            "title": book.get_metadata("DC", "title"),
            "author": book.get_metadata("DC", "creator"),
            "language": book.get_metadata("DC", "language"),
            "publisher": book.get_metadata("DC", "publisher"),
            "size_bytes": os.path.getsize(filepath),
        }

        # Flatten lists
        for key in ["title", "author", "language", "publisher"]:
            if isinstance(metadata[key], list):
                metadata[key] = metadata[key][0] if metadata[key] else None

        logger.info(
            f"EPUB Metadata: {metadata.get('title', 'Unknown')} by {metadata.get('author', 'Unknown')}"
        )

        # Extract text content with chapter tracking
        # CRITICAL: Use book.spine for correct reading order
        # get_items_of_type(ITEM_DOCUMENT) returns items in arbitrary hash order!
        chapters = []
        chapter_count = 0

        for itemref, linear in book.spine:
            item = book.get_item_with_id(itemref)
            if item is None:
                continue
            try:
                html_content = item.get_content().decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html_content, "html.parser")

                # Remove script and style tags
                for tag in soup(["script", "style", "nav"]):
                    tag.decompose()

                # Extract text với paragraph boundaries được bảo lưu
                # Sử dụng <p>, <div>, <h1-h6>, <br> để tách paragraph
                paragraphs = []

                # Tìm tất cả block elements (p, div, h1-h6, li, etc.)
                block_elements = soup.find_all(
                    ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"]
                )

                if block_elements:
                    # Có block elements: extract từng element
                    for elem in block_elements:
                        text = elem.get_text(separator=" ", strip=True)
                        if text.strip():
                            paragraphs.append(text.strip())
                else:
                    # Không có block elements: dùng get_text với separator
                    # Nhưng thêm logic để tách bằng <br> tags
                    for br in soup.find_all("br"):
                        br.replace_with("\n")
                    text = soup.get_text(separator="\n", strip=True)
                    # Tách thành paragraphs bằng double newline hoặc single newline nếu dài
                    if "\n\n" in text:
                        paragraphs = [
                            p.strip() for p in text.split("\n\n") if p.strip()
                        ]
                    else:
                        # Nếu không có double newline, tách bằng single newline
                        # Nhưng chỉ nếu line không quá ngắn (tránh tách từng câu)
                        lines = text.split("\n")
                        current_para = []
                        for line in lines:
                            line = line.strip()
                            if not line:
                                if current_para:
                                    paragraphs.append(" ".join(current_para))
                                    current_para = []
                            elif len(line) < 50 and current_para:
                                # Line ngắn: có thể là tiếp tục paragraph
                                current_para.append(line)
                            else:
                                # Line dài hoặc paragraph mới
                                if current_para:
                                    paragraphs.append(" ".join(current_para))
                                current_para = [line]
                        if current_para:
                            paragraphs.append(" ".join(current_para))

                # Ghép paragraphs với double newline (paragraph break)
                if paragraphs:
                    chapter_text = "\n\n".join(paragraphs)
                    chapters.append(chapter_text)
                    chapter_count += 1
            except Exception as e:
                logger.warning(f"Failed to parse item {item.get_name()}: {e}")
                continue

        if not chapters:
            raise FileParsingError("No readable content found in EPUB")

        full_text = "\n\n".join(chapters)
        metadata["chapter_count"] = chapter_count
        metadata["char_count"] = len(full_text)

        logger.info(
            f"Extracted {chapter_count} chapters, {len(full_text):,} characters"
        )

        return full_text, metadata

    def parse_docx(self, filepath: str) -> Tuple[str, Dict]:
        """
        Parse DOCX với better formatting preservation.
        Returns: (text_content, metadata)
        """
        try:
            doc = docx.Document(filepath)
        except Exception as e:
            raise FileParsingError(f"Failed to read DOCX: {e}")

        # Extract metadata
        core_properties = doc.core_properties
        metadata = {
            "format": "docx",
            "title": core_properties.title,
            "author": core_properties.author,
            "created": str(core_properties.created)
            if core_properties.created
            else None,
            "modified": str(core_properties.modified)
            if core_properties.modified
            else None,
            "size_bytes": os.path.getsize(filepath),
        }

        # Extract text with paragraph structure
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        if not paragraphs:
            raise FileParsingError("No readable content found in DOCX")

        full_text = "\n\n".join(paragraphs)
        metadata["paragraph_count"] = len(paragraphs)
        metadata["char_count"] = len(full_text)

        logger.info(
            f"Extracted {len(paragraphs)} paragraphs, {len(full_text):,} characters"
        )

        return full_text, metadata

    def parse_pdf(self, filepath: str) -> Tuple[str, Dict]:
        """
        Parse PDF với improved text extraction.
        Returns: (text_content, metadata)
        """
        try:
            with open(filepath, "rb") as f:
                reader = PyPDF2.PdfReader(f)

                # Extract metadata
                info = reader.metadata
                metadata = {
                    "format": "pdf",
                    "title": info.get("/Title") if info else None,
                    "author": info.get("/Author") if info else None,
                    "page_count": len(reader.pages),
                    "size_bytes": os.path.getsize(filepath),
                }

                # Extract text from all pages
                pages_text = []
                for i, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            pages_text.append(text)
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {i + 1}: {e}")
                        continue

                if not pages_text:
                    raise FileParsingError("No readable text found in PDF")

                full_text = "\n\n".join(pages_text)
                metadata["char_count"] = len(full_text)

                logger.info(
                    f"Extracted {len(pages_text)} pages, {len(full_text):,} characters"
                )

                return full_text, metadata

        except Exception as e:
            raise FileParsingError(f"Failed to read PDF: {e}")

    def parse(self, filepath: str) -> Dict[str, Any]:
        """
        Main parsing method - auto-detect format và parse.
        Returns: Dict with 'text', 'metadata', 'format'
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        file_path = Path(filepath)
        file_ext = file_path.suffix.lower()

        if file_ext not in self.supported_formats:
            raise ValueError(
                f"Unsupported file format: {file_ext}. Supported: {self.supported_formats}"
            )

        logger.info(f"Parsing file: {file_path.name} ({file_ext})")

        try:
            if file_ext == ".txt":
                force_encoding = self.config.get("preprocessing", {}).get(
                    "force_encoding"
                )
                text, metadata = self.parse_txt(filepath, force_encoding)
            elif file_ext == ".epub":
                text, metadata = self.parse_epub(filepath)
            elif file_ext == ".docx":
                text, metadata = self.parse_docx(filepath)
            elif file_ext == ".pdf":
                text, metadata = self.parse_pdf(filepath)
            else:
                raise ValueError(f"Unsupported format: {file_ext}")

            # Add common metadata
            metadata["filepath"] = str(file_path)
            metadata["filename"] = file_path.name

            logger.info(
                f"✓ Successfully parsed {file_path.name}: {len(text):,} characters"
            )

            return {
                "text": text,
                "metadata": metadata,
                "format": file_ext[1:],  # Remove dot
            }

        except FileParsingError as e:
            logger.error(f"Parsing error: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error parsing {file_path.name}: {e}", exc_info=True
            )
            raise FileParsingError(f"Failed to parse file: {e}")


def _parse_epub_zip_fallback(filepath: str) -> Tuple[str, Dict[str, Any]]:
    """
    Fallback parser cho EPUB khi ebooklib.read_epub() fail do thiếu asset (ảnh/logo/...).

    Logic:
    - Dùng zipfile để mở EPUB.
    - Đọc META-INF/container.xml để tìm rootfile (.opf).
    - Đọc .opf, parse manifest + spine.
    - Duyệt spine theo đúng reading order, chỉ đọc các item XHTML/HTML.
    - Bỏ qua hoàn toàn các asset (ảnh, CSS, font) – kể cả khi chúng bị thiếu.
    """
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            # 1. Tìm rootfile (.opf) từ container.xml
            try:
                container_data = zf.read("META-INF/container.xml")
            except KeyError as e:
                raise FileParsingError(f"EPUB container.xml missing: {e}")

            try:
                container_root = ET.fromstring(container_data)
            except Exception as e:
                raise FileParsingError(f"Invalid container.xml in EPUB: {e}")

            ns_map = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
            rootfile_elem = container_root.find(".//c:rootfile", ns_map)
            if rootfile_elem is None:
                raise FileParsingError("EPUB rootfile not found in container.xml")

            opf_path = rootfile_elem.attrib.get("full-path")
            if not opf_path:
                raise FileParsingError("EPUB rootfile path missing in container.xml")

            try:
                opf_data = zf.read(opf_path)
            except KeyError as e:
                raise FileParsingError(f"EPUB package document missing: {e}")

            try:
                opf_root = ET.fromstring(opf_data)
            except Exception as e:
                raise FileParsingError(f"Invalid OPF package document: {e}")

            # Namespace cho OPF (thường là http://www.idpf.org/2007/opf)
            opf_ns = {"opf": opf_root.tag.split("}")[0].strip("{")}
            # 2. Manifest: id -> (href, media-type)
            manifest: Dict[str, Tuple[str, str]] = {}
            for item in opf_root.findall(".//opf:manifest/opf:item", opf_ns):
                item_id = item.attrib.get("id")
                href = item.attrib.get("href")
                media_type = item.attrib.get("media-type", "")
                if item_id and href:
                    manifest[item_id] = (href, media_type)

            # 3. Spine: danh sách idref theo thứ tự đọc
            spine_ids = []
            for itemref in opf_root.findall(".//opf:spine/opf:itemref", opf_ns):
                idref = itemref.attrib.get("idref")
                if idref:
                    spine_ids.append(idref)

            if not spine_ids:
                raise FileParsingError("EPUB spine is empty – no reading order defined")

            # Cơ sở thư mục tương đối cho opf (dạng POSIX để khớp với entry name trong ZIP)
            opf_dir = os.path.dirname(opf_path).replace("\\", "/")

            chapters: list[str] = []
            chapter_count = 0

            for idref in spine_ids:
                entry = manifest.get(idref)
                if entry is None:
                    logger.warning(
                        f"EPUB fallback: spine item '{idref}' không có trong manifest, bỏ qua."
                    )
                    continue

                href, media_type = entry
                if not media_type.startswith("application/xhtml+xml") and not media_type.startswith(
                    "text/html"
                ):
                    # Không phải nội dung text – ví dụ image/stylesheet – bỏ qua.
                    continue

                # Đường dẫn tương đối trong zip (luôn dùng '/' để khớp với ZIP entry)
                href_norm = href.replace("\\", "/")
                if opf_dir:
                    content_path = f"{opf_dir.rstrip('/')}/{href_norm.lstrip('/')}"
                else:
                    content_path = href_norm

                try:
                    raw_html = zf.read(content_path)
                except KeyError:
                    logger.warning(
                        f"EPUB fallback: không tìm thấy spine content '{content_path}' trong archive, bỏ qua."
                    )
                    continue

                try:
                    html_content = raw_html.decode("utf-8", errors="ignore")
                except Exception as e:
                    logger.warning(
                        f"EPUB fallback: không thể decode '{content_path}' thành UTF-8: {e}"
                    )
                    continue

                soup = BeautifulSoup(html_content, "html.parser")

                # Loại bỏ script/style/nav
                for tag in soup(["script", "style", "nav"]):
                    tag.decompose()

                paragraphs: list[str] = []
                block_elements = soup.find_all(
                    ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"]
                )

                if block_elements:
                    for elem in block_elements:
                        text = elem.get_text(separator=" ", strip=True)
                        if text.strip():
                            paragraphs.append(text.strip())
                else:
                    for br in soup.find_all("br"):
                        br.replace_with("\n")
                    text = soup.get_text(separator="\n", strip=True)
                    if "\n\n" in text:
                        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                    else:
                        lines = text.split("\n")
                        current_para: list[str] = []
                        for line in lines:
                            line = line.strip()
                            if not line:
                                if current_para:
                                    paragraphs.append(" ".join(current_para))
                                    current_para = []
                            elif len(line) < 50 and current_para:
                                current_para.append(line)
                            else:
                                if current_para:
                                    paragraphs.append(" ".join(current_para))
                                current_para = [line]
                        if current_para:
                            paragraphs.append(" ".join(current_para))

                if paragraphs:
                    chapter_text = "\n\n".join(paragraphs)
                    chapters.append(chapter_text)
                    chapter_count += 1

            if not chapters:
                raise FileParsingError("No readable content found in EPUB (zip fallback)")

            full_text = "\n\n".join(chapters)

            metadata: Dict[str, Any] = {
                "format": "epub",
                "title": None,
                "author": None,
                "language": None,
                "publisher": None,
                "size_bytes": os.path.getsize(filepath),
                "chapter_count": chapter_count,
                "char_count": len(full_text),
            }

            logger.info(
                f"[EPUB zip fallback] Extracted {chapter_count} chapters, {len(full_text):,} characters"
            )

            return full_text, metadata

    except FileParsingError:
        # Đã được wrap ở trên – ném tiếp
        raise
    except Exception as e:
        raise FileParsingError(f"Failed to parse EPUB via zip fallback: {e}")


# Backward compatible function
def parse_file(filepath: str, config: Dict[str, Any]) -> str:
    """
    Backward compatible wrapper cho code cũ.
    Chỉ trả về text content.
    """
    parser = AdvancedFileParser(config)
    result = parser.parse(filepath)
    return result["text"]


# New function với full output
def parse_file_advanced(filepath: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Advanced parsing với metadata.
    Returns: Dict with 'text', 'metadata', 'format'
    """
    parser = AdvancedFileParser(config)
    return parser.parse(filepath)
