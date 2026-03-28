# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Module: input_preprocessor.py
Mục tiêu: Tự động phát hiện và tiền xử lý file đầu vào trước khi vào pipeline dịch thuật.

Quy tắc (theo quyết định người dùng):
- Luôn LƯU processed file (TXT) khi OCR với PDF scan
- Khi OCR thất bại → Fallback sang trích xuất text (nếu có thể)
- Nếu processed file đã tồn tại → HỎI người dùng: reuse hay re-run OCR
- Hiển thị progress chi tiết và thời gian xử lý
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("NovelTranslator")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _ask_user_yes_no(question: str, default: str = "y") -> bool:
    prompt = f"{question} (y/n) [{default}]: ".strip()
    try:
        answer = input(prompt).strip().lower()
        if not answer:
            answer = default
        return answer.startswith("y")
    except Exception:
        return default.startswith("y")


async def detect_and_preprocess_input(
    novel_path: str, config: Dict, key_manager: Any = None
) -> str:
    """
    Detect loại file đầu vào và tiền xử lý nếu cần.

    - PDF scan: chạy OCR (cleanup + spell check theo config của OCR module), lưu TXT, trả về đường dẫn processed.
    - PDF text/DOCX/EPUB/TXT: giữ nguyên đường dẫn gốc.
    - key_manager: nếu có, AI cleanup/spell check dùng chung quản lý key với quy trình chính.

    Returns: đường dẫn file (gốc hoặc processed) để tiếp tục pipeline dịch thuật.
    """
    # Imports moved down to avoid loading OCR libs for non-PDF files

    input_path = Path(novel_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file đầu vào: {input_path}")

    ext = input_path.suffix.lower()
    
    # [v7.5] Kiểm tra cấu hình AI Pre-clean cho tệp Text-based
    ai_preclean_cfg = (config.get("preprocessing") or {}).get("ai_preclean") or {}
    ai_preclean_enabled = ai_preclean_cfg.get("enabled", False)

    # Nếu không phải PDF và không bật AI Pre-clean → đi tiếp
    if ext != ".pdf" and not ai_preclean_enabled:
        logger.info(f"📄 File '{ext}' → đi tiếp quy trình hiện tại (không cần OCR/AI Pre-clean).")
        return str(input_path)

    # PDF hoặc Text-based có bật AI Pre-clean
    if ext == ".pdf":
        logger.info("🔎 Đang nhận biết loại PDF (scan hay text-based)...")
    else:
        logger.info(f"📝 Kích hoạt AI Pre-clean cho tệp văn bản '{ext}'...")

    from src.preprocessing.ocr_reader import (
        _detect_bundled_binaries,
        detect_pdf_type,
        extract_text_from_pdf,
        load_ocr_config,
        ocr_file,
    )

    ocr_cfg = _detect_bundled_binaries(
        load_ocr_config(config.get("config_path", "config/config.yaml"))
    )
    
    pdf_type = None
    # Chỉ detect PDF type nếu là file PDF
    if ext == ".pdf":
        start_detect = time.time()
        pdf_type = detect_pdf_type(str(input_path), ocr_cfg)
        logger.info(f"🔖 PDF type: {pdf_type} (mất {time.time() - start_detect:.2f}s)")

        if pdf_type != "scan" and not ai_preclean_enabled:
            logger.info(
                "📄 PDF text-based phát hiện (AI Pre-clean TẮT) → Extract text trực tiếp (không cần OCR)."
            )
            logger.info("📄 File PDF gốc sẽ được dùng cho quy trình dịch thuật.")
            return str(input_path)
        elif pdf_type != "scan" and ai_preclean_enabled:
            logger.info("📄 PDF text-based phát hiện + AI Pre-clean BẬT → Bắt đầu xử lý AI...")
    
    # Chuẩn bị đường dẫn lưu processed file (dùng chung cho cả PDF scan và AI Pre-clean)
    out_cfg = (config.get("preprocessing") or {}).get("ocr_preprocessing") or {}
    save_dir = Path(out_cfg.get("processed_file_dir", "data/output"))
    _ensure_dir(save_dir)
    processed_file = save_dir / f"{input_path.stem}_processed.txt"

    # Nếu processed đã tồn tại → hỏi reuse hay re-run
    if processed_file.exists():
        logger.info(f"💾 Đã tìm thấy file processed sẵn có: {processed_file}")
        reuse = _ask_user_yes_no(
            "Bạn muốn dùng lại file đã xử lý (reuse)? Nếu chọn 'n' sẽ chạy lại quy trình AI",
            default="y",
        )
        if reuse:
            logger.info("↪️  Reuse processed file hiện có.")
            return str(processed_file)
        logger.info("🔁 Sẽ chạy lại quy trình AI để tạo processed file mới.")

    # Chạy quy trình AI (OCR/Cleanup/Spell Check)
    if ext == ".pdf":
        logger.info("📷 Bắt đầu OCR/AI workflow cho PDF...")
    else:
        logger.info("🤖 Bắt đầu AI Pre-clean workflow cho tệp văn bản...")
        
    ocr_start = time.time()
    try:
        text_result = await ocr_file(
            input_path=str(input_path),
            config_path=config.get("config_path", "config/config.yaml"),
            pages=None,
            output_path=str(processed_file),
            skip_steps={},
            pdf_type=pdf_type,
            skip_completion_menu=True,
            key_manager=key_manager,
        )
        # ocr_file trả về dict với key 'text'
        # File đã được lưu tự động trong ocr_file() khi skip_completion_menu=True
        # Chỉ cần kiểm tra file đã tồn tại, nếu chưa thì lưu lại
        if isinstance(text_result, dict) and "text" in text_result:
            text_out = text_result["text"]
            # File đã được lưu trong ocr_file(), nhưng kiểm tra lại để chắc chắn
            if not processed_file.exists():
                with open(processed_file, "w", encoding="utf-8") as f:
                    f.write(text_out)
        elif isinstance(text_result, str):
            text_out = text_result
            # Lưu file nếu chưa tồn tại
            if not processed_file.exists():
                with open(processed_file, "w", encoding="utf-8") as f:
                    f.write(text_out)
        else:
            text_out = str(text_result)
            # Lưu file nếu chưa tồn tại
            if not processed_file.exists():
                with open(processed_file, "w", encoding="utf-8") as f:
                    f.write(text_out)

        elapsed = time.time() - ocr_start
        size_kb = (
            processed_file.stat().st_size // 1024 if processed_file.exists() else 0
        )
        logger.info(
            f"✅ OCR hoàn tất: {processed_file} ({size_kb} KB) - {elapsed:.1f}s"
        )
        logger.info("📄 Tiếp tục quy trình dịch thuật với file processed...")
        return str(processed_file)

    except Exception as e:
        logger.warning(f"⚠️ OCR thất bại: {e}")
        logger.info(
            "🔄 Fallback: cố gắng trích xuất text trực tiếp từ PDF (nếu có text layer)..."
        )
        try:
            text_out = extract_text_from_pdf(str(input_path), ocr_cfg, pages=None)
            if not text_out or len(text_out.strip()) < 10:
                raise RuntimeError("Extract text trả về nội dung quá ngắn hoặc rỗng.")
            with open(processed_file, "w", encoding="utf-8") as f:
                f.write(text_out)
            elapsed = time.time() - ocr_start
            size_kb = (
                processed_file.stat().st_size // 1024 if processed_file.exists() else 0
            )
            logger.info(
                f"✅ Fallback thành công: {processed_file} ({size_kb} KB) - {elapsed:.1f}s"
            )
            return str(processed_file)
        except Exception as e2:
            logger.error(f"❌ Fallback cũng thất bại: {e2}")
            # Fail fast theo yêu cầu fallback: đã thử, giờ dừng với lỗi rõ ràng
            raise
