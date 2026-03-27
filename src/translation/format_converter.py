# -*- coding: utf-8 -*-

"""
Format Converter
================
[Phase 10.1] Handles format conversion (EPUB, DOCX, PDF).

Extracted from NovelTranslator to separate translation concerns from format concerns.

Responsibilities:
- Convert TXT to EPUB
- Convert TXT to DOCX (via pandoc)
- Convert TXT to PDF (via pandoc)
- Convert heading tags to markdown

PHIÊN BẢN: v10.0+
"""

import asyncio
import logging
import os
import re
import tempfile
from typing import Any, Dict, Optional

logger = logging.getLogger("NovelTranslator")


class FormatConverter:
    """
    [Phase 10.1] Handles format conversion operations.

    Separates format conversion from core translation logic.
    """

    def __init__(
        self,
        output_formatter: Any,
        config: Dict[str, Any],
    ):
        """
        Initialize FormatConverter.

        Args:
            output_formatter: OutputFormatter instance for EPUB.
            config: Configuration dictionary.
        """
        self.output_formatter = output_formatter
        self.config = config
        self._pypandoc_cache = None

    def _validate_and_fix_tags(self, content: str) -> str:
        """
        [v7.6] Kiểm tra và sửa lỗi tag Heading (H1/H2/H3) của AI.
        """
        # 1. Sửa lỗi tag bị lệch (mọi hoán vị mở Hx đóng Hy)
        for i in range(1, 4):
            for j in range(1, 4):
                if i == j: continue
                pattern = rf"\[H{i}\](.*?)\[/H{j}\]"
                replacement = rf"[H{i}]\1[/H{i}]"
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE | re.DOTALL)
        
        # 2. Sửa lỗi tag bị dính khoảng trắng lạ
        content = re.sub(r"\[\s*H([1-3])\s*\]", r"[H\1]", content, flags=re.IGNORECASE)
        content = re.sub(r"\[\s*/\s*H([1-3])\s*\]", r"[/H\1]", content, flags=re.IGNORECASE)
        
        # 3. Sửa lỗi thiếu tag đóng (nếu dòng bắt đầu bằng [H1] nhưng không có [/H1] ở cuối)
        lines = content.split("\n")
        fixed_lines = []
        for line in lines:
            stripped = line.strip()
            # Tìm xem có tag mở nào ở đầu dòng không
            match = re.match(r"^\[H([1-3])\].*$", stripped, re.IGNORECASE)
            if match:
                tag_num = match.group(1)
                closing_tag = f"[/H{tag_num}]"
                # Nếu không thấy tag đóng tương ứng
                if closing_tag.upper() not in stripped.upper():
                    # Xóa các tag đóng sai khác nếu có ở cuối
                    line = re.sub(r"\[/H[1-3]\]$", "", stripped, flags=re.IGNORECASE).strip()
                    line = f"{line} {closing_tag}"
            fixed_lines.append(line)
            
        return "\n".join(fixed_lines)

    def _convert_heading_tags(self, content: str) -> str:
        """Convert [H1]/[H2]/[H3] tags to markdown headings."""
        # Validate trước khi convert
        content = self._validate_and_fix_tags(content)
        
        content = re.sub(r"\[H1\](.*?)\[/H1\]", r"# \1", content, flags=re.IGNORECASE)
        content = re.sub(r"\[H2\](.*?)\[/H2\]", r"## \1", content, flags=re.IGNORECASE)
        content = re.sub(r"\[H3\](.*?)\[/H3\]", r"### \1", content, flags=re.IGNORECASE)
        return content

    async def convert_to_epub(self, txt_path: str, novel_name: str) -> str:
        """
        Convert TXT file to EPUB.

        Args:
            txt_path: Path to TXT file.
            novel_name: Name of the novel.

        Returns:
            Path to created EPUB file.
        """
        try:
            epub_options = self.config.get("output", {}).get("epub_options", {})

            # Run conversion in thread to avoid blocking IO
            await asyncio.to_thread(
                self.output_formatter.convert_txt_to_epub,
                txt_path,
                novel_name,
                epub_options,
            )

            epub_path = txt_path.replace(".txt", ".epub")
            return epub_path

        except Exception as e:
            logger.error(f"Lỗi convert sang epub: {e}")
            raise

    def _convert_to_docx_sync(self, txt_path: str) -> Optional[str]:
        """Blocking pandoc TXT→DOCX (chạy trong thread để không block event loop)."""
        try:
            if self._pypandoc_cache is None:
                import pypandoc

                self._pypandoc_cache = pypandoc
            else:
                pypandoc = self._pypandoc_cache

            output_path = self.config.get("output", {}).get("output_path", "data/output/")
            novel_name = os.path.splitext(os.path.basename(txt_path))[0].replace("_translated", "")
            docx_path = os.path.join(output_path, f"{novel_name}.docx")

            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = self._convert_heading_tags(content)

            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
                tmp.write(content)
                temp_md_path = tmp.name

            md_reader = "markdown+hard_line_breaks"
            pypandoc.convert_file(
                source_file=temp_md_path,
                to="docx",
                format=md_reader,
                outputfile=docx_path,
            )
            os.unlink(temp_md_path)
            return docx_path
        except ImportError:
            raise
        except Exception as e:
            logger.error(f"❌ Lỗi convert sang DOCX: {e}")
            return None

    async def convert_to_docx(self, txt_path: str) -> Optional[str]:
        """
        Convert TXT file to DOCX using pandoc (chạy trong thread để tránh treo khi convert song song với PDF).
        """
        try:
            logger.info("🔄 Đang convert TXT → DOCX...")
            return await asyncio.to_thread(self._convert_to_docx_sync, txt_path)
        except ImportError:  # pypandoc chưa cài (từ sync chạy trong thread)
            logger.warning("⚠️ pypandoc chưa được cài đặt. Không thể convert sang DOCX.")
            logger.info("💡 Cài đặt: pip install pypandoc")
            return None

    def _convert_to_pdf_sync(self, txt_path: str) -> Optional[str]:
        """Blocking pandoc TXT→PDF (chạy trong thread để không block event loop)."""
        try:
            if self._pypandoc_cache is None:
                import pypandoc

                self._pypandoc_cache = pypandoc
            else:
                pypandoc = self._pypandoc_cache

            output_path = self.config.get("output", {}).get("output_path", "data/output/")
            novel_name = os.path.splitext(os.path.basename(txt_path))[0].replace("_translated", "")
            pdf_path = os.path.join(output_path, f"{novel_name}.pdf")

            with open(txt_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = self._convert_heading_tags(content)

            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
                tmp.write(content)
                temp_md_path = tmp.name

            pdf_engine = self.config.get("output", {}).get("pdf_engine", "xelatex")
            styles = self.config.get("output", {}).get("styles", {})
            pdf_css = styles.get("pdf_css")
            extra_args = [f"--pdf-engine={pdf_engine}"]

            import sys
            if sys.platform == "win32":
                extra_args.extend(["-V", "mainfont:Arial"])
            elif sys.platform == "darwin":
                extra_args.extend(["-V", "mainfont:Helvetica Neue"])
            else:
                extra_args.extend(["-V", "mainfont:DejaVu Sans"])

            if ("wkhtmltopdf" in pdf_engine or "weasyprint" in pdf_engine) and pdf_css and os.path.exists(pdf_css):
                extra_args.append(f"--css={pdf_css}")

            md_reader = "markdown+hard_line_breaks"
            pypandoc.convert_file(
                source_file=temp_md_path,
                to="pdf",
                format=md_reader,
                outputfile=pdf_path,
                extra_args=extra_args,
            )
            os.unlink(temp_md_path)
            return pdf_path
        except ImportError:
            raise
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg or "pdf-engine" in error_msg:
                logger.error(
                    f"❌ Lỗi PDF Engine: Không tìm thấy '{self.config.get('output', {}).get('pdf_engine', 'xelatex')}'."
                )
                logger.info(
                    "💡 GIẢI PHÁP: Vui lòng cài đặt MiKTeX (cho xelatex) hoặc wkhtmltopdf, sau đó cập nhật config.yaml."
                )
            else:
                logger.error(f"❌ Lỗi convert sang PDF: {e}")
            return None

    async def convert_to_pdf(self, txt_path: str) -> Optional[str]:
        """
        Convert TXT file to PDF using pandoc (chạy trong thread để tránh treo khi convert song song với DOCX).
        """
        try:
            logger.info("🔄 Đang convert TXT → PDF...")
            pdf_path = await asyncio.to_thread(self._convert_to_pdf_sync, txt_path)
            return pdf_path
        except ImportError:  # pypandoc chưa cài (từ sync chạy trong thread)
            logger.warning("⚠️ pypandoc chưa được cài đặt. Không thể convert sang PDF.")
            logger.info("💡 Cài đặt: pip install pypandoc")
            return None
