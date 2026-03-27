#!/usr/bin/env python3
"""
Script xử lý residual cleanup cho các câu còn sót từ tiếng Trung
Tìm và dịch lại các câu có ký tự CJK trong file đã dịch
"""

import asyncio
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.gemini_api_service import GeminiAPIService
from src.utils.file_utils import ensure_dir_exists, load_text_file, save_text_file
from src.utils.logger import setup_main_logger


@dataclass
class CJKMatch:
    """Thông tin về ký tự CJK được tìm thấy"""

    line_number: int
    content: str
    cjk_text: str
    context_before: str
    context_after: str


class ResidualCleanupProcessor:
    """Xử lý cleanup cho các câu còn sót từ tiếng Trung"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.logger = setup_main_logger("ResidualCleanup")

        # Load config
        import yaml

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # Initialize API service
        self.api_service = GeminiAPIService(self.config)

        # CJK pattern
        self.cjk_pattern = re.compile(r"[\u4e00-\u9fff]+")

        # Cleanup settings
        self.cleanup_config = self.config.get("translation", {}).get("cleanup", {})
        self.residual_config = self.cleanup_config.get("residual_retry", {})

    def find_cjk_sentences(self, file_path: str) -> List[CJKMatch]:
        """Tìm các câu có ký tự CJK trong file"""
        self.logger.info(f"Đang quét file: {file_path}")

        content = load_text_file(file_path)
        lines = content.split("\n")

        cjk_matches = []
        context_window = self.cleanup_config.get("sentence_context_window", 2)

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            cjk_matches_in_line = self.cjk_pattern.findall(line)
            if cjk_matches_in_line:
                # Lấy context trước và sau
                start_idx = max(0, i - context_window)
                end_idx = min(len(lines), i + context_window + 1)

                context_before = "\n".join(lines[start_idx:i])
                context_after = "\n".join(lines[i + 1 : end_idx])

                match = CJKMatch(
                    line_number=i + 1,
                    content=line,
                    cjk_text=" ".join(cjk_matches_in_line),
                    context_before=context_before,
                    context_after=context_after,
                )
                cjk_matches.append(match)

        self.logger.info(f"Tìm thấy {len(cjk_matches)} dòng có ký tự CJK")
        return cjk_matches

    def create_cleanup_prompt(self, match: CJKMatch) -> str:
        """Tạo prompt cleanup cho câu có ký tự CJK"""
        prompt = f"""Bạn là chuyên gia dịch thuật tiếng Trung sang tiếng Việt. Nhiệm vụ của bạn là dịch lại câu sau để loại bỏ hoàn toàn các ký tự tiếng Trung còn sót.

CONTEXT TRƯỚC:
{match.context_before}

CÂU CẦN DỊCH LẠI (có ký tự tiếng Trung còn sót):
{match.content}

CONTEXT SAU:
{match.context_after}

YÊU CẦU:
1. Dịch lại câu trên sang tiếng Việt hoàn toàn tự nhiên
2. Loại bỏ TẤT CẢ ký tự tiếng Trung (CJK) còn sót
3. Giữ nguyên ý nghĩa và ngữ cảnh
4. Đảm bảo câu văn mượt mà, tự nhiên
5. Chỉ trả về câu đã dịch, không giải thích

CÂU ĐÃ DỊCH:"""

        return prompt

    async def cleanup_sentence(self, match: CJKMatch) -> Optional[str]:
        """Dịch lại một câu có ký tự CJK"""
        try:
            prompt = self.create_cleanup_prompt(match)

            # Sử dụng Pro model cho cleanup
            model_name = self.residual_config.get("use_pro_model", True)
            if model_name:
                model_name = self.config.get("translation", {}).get("pro_model", "gemini-2.5-pro")
            else:
                model_name = self.config.get("translation", {}).get("default_model", "gemini-2.5-flash")

            self.logger.info(f"Dịch lại dòng {match.line_number} với model {model_name}")

            # Gọi API
            response = await self.api_service.generate_content_async(
                prompt=prompt, model_name=model_name, max_retries=3
            )

            if response and response.strip():
                # Kiểm tra xem còn ký tự CJK không
                remaining_cjk = self.cjk_pattern.findall(response)
                if remaining_cjk:
                    self.logger.warning(f"Dòng {match.line_number}: Vẫn còn ký tự CJK sau cleanup: {remaining_cjk}")
                    return None

                self.logger.info(f"Dòng {match.line_number}: Cleanup thành công")
                return response.strip()
            else:
                self.logger.error(f"Dòng {match.line_number}: Không nhận được response")
                return None

        except Exception as e:
            self.logger.error(f"Dòng {match.line_number}: Lỗi cleanup - {str(e)}")
            return None

    async def process_file(self, input_file: str, output_file: str = None) -> Dict:
        """Xử lý cleanup cho toàn bộ file"""
        if not output_file:
            output_file = input_file.replace(".txt", "_cleaned.txt")

        self.logger.info(f"Bắt đầu xử lý file: {input_file}")

        # Tìm các câu có ký tự CJK
        cjk_matches = self.find_cjk_sentences(input_file)

        if not cjk_matches:
            self.logger.info("Khong tim thay ky tu CJK nao can cleanup")
            return {"status": "success", "processed": 0, "errors": 0, "remaining_cjk": 0, "output_file": input_file}

        # Load nội dung file
        content = load_text_file(input_file)
        lines = content.split("\n")

        # Xử lý từng câu
        processed = 0
        errors = 0
        max_retries = self.residual_config.get("max_global_retries_per_sentence", 5)

        for match in cjk_matches:
            self.logger.info(f"Xử lý dòng {match.line_number}/{len(cjk_matches)}")

            success = False
            for attempt in range(max_retries):
                try:
                    cleaned_sentence = await self.cleanup_sentence(match)
                    if cleaned_sentence:
                        # Thay thế câu cũ bằng câu đã cleanup
                        lines[match.line_number - 1] = cleaned_sentence
                        processed += 1
                        success = True
                        break
                    else:
                        self.logger.warning(f"Dòng {match.line_number}: Thử lại lần {attempt + 1}/{max_retries}")
                        await asyncio.sleep(1)  # Delay trước khi retry

                except Exception as e:
                    self.logger.error(f"Dòng {match.line_number}: Lỗi attempt {attempt + 1} - {str(e)}")
                    await asyncio.sleep(2)

            if not success:
                errors += 1
                self.logger.error(f"Dòng {match.line_number}: Thất bại sau {max_retries} lần thử")

        # Lưu file đã cleanup
        cleaned_content = "\n".join(lines)
        save_text_file(output_file, cleaned_content)

        # Kiểm tra kết quả
        remaining_cjk = self.find_cjk_sentences(output_file)
        remaining_count = len(remaining_cjk)

        result = {
            "status": "success" if remaining_count == 0 else "partial",
            "processed": processed,
            "errors": errors,
            "remaining_cjk": remaining_count,
            "output_file": output_file,
        }

        self.logger.info(
            f"Hoàn thành cleanup: {processed} câu thành công, {errors} câu lỗi, {remaining_count} câu còn sót"
        )

        return result


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Residual Cleanup cho file da dich")
    parser.add_argument("-i", "--input", dest="input_file", help="File input can cleanup")
    parser.add_argument("input_file_pos", nargs="?", help="File input (positional)")
    parser.add_argument("-o", "--output", help="File output (mac dinh: input_cleaned.txt)")
    parser.add_argument("-c", "--config", default="config/config.yaml", help="File config")

    args = parser.parse_args()

    # Handle both -i and positional argument
    if args.input_file:
        input_file = args.input_file
    elif args.input_file_pos:
        input_file = args.input_file_pos
    else:
        print("Loi: Can phai cung cap file input (-i hoac positional)")
        return 1

    args.input_file = input_file

    # Kiểm tra file input
    if not os.path.exists(args.input_file):
        print(f"Lỗi: File {args.input_file} không tồn tại")
        return 1

    # Tạo processor
    processor = ResidualCleanupProcessor(args.config)

    # Xử lý file
    result = await processor.process_file(args.input_file, args.output)

    # In kết quả
    print("\n=== KẾT QUẢ CLEANUP ===")
    print(f"Trạng thái: {result['status']}")
    print(f"Đã xử lý: {result['processed']} câu")
    print(f"Lỗi: {result['errors']} câu")
    print(f"Còn sót: {result['remaining_cjk']} câu")
    print(f"File output: {result['output_file']}")

    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    asyncio.run(main())
