#!/usr/bin/env python3
"""
Script cleanup đơn giản sử dụng trực tiếp Gemini API
Xử lý các câu còn sót từ tiếng Trung trong file đã dịch
"""

import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import google.generativeai as genai

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/simple_cleanup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SimpleCleanup")

class SimpleCleanupProcessor:
    """Xử lý cleanup đơn giản cho các câu còn sót từ tiếng Trung"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
        # CJK pattern
        self.cjk_pattern = re.compile(r'[\u4e00-\u9fff]+')
        
        # Initialize model
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
    def find_cjk_sentences(self, file_path: str) -> List[Dict]:
        """Tìm các câu có ký tự CJK trong file"""
        logger.info(f"Đang quét file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        cjk_matches = []
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            cjk_matches_in_line = self.cjk_pattern.findall(line)
            if cjk_matches_in_line:
                match = {
                    'line_number': i + 1,
                    'content': line,
                    'cjk_text': ' '.join(cjk_matches_in_line)
                }
                cjk_matches.append(match)
                
        logger.info(f"Tìm thấy {len(cjk_matches)} dòng có ký tự CJK")
        return cjk_matches
    
    def create_cleanup_prompt(self, match: Dict) -> str:
        """Tạo prompt cleanup cho câu có ký tự CJK"""
        prompt = f"""Bạn là chuyên gia dịch thuật tiếng Trung sang tiếng Việt. Nhiệm vụ của bạn là dịch lại câu sau để loại bỏ hoàn toàn các ký tự tiếng Trung còn sót.

CÂU CẦN DỊCH LẠI (có ký tự tiếng Trung còn sót):
{match['content']}

YÊU CẦU:
1. Dịch lại câu trên sang tiếng Việt hoàn toàn tự nhiên
2. Loại bỏ TẤT CẢ ký tự tiếng Trung (CJK) còn sót
3. Giữ nguyên ý nghĩa và ngữ cảnh
4. Đảm bảo câu văn mượt mà, tự nhiên
5. Chỉ trả về câu đã dịch, không giải thích

CÂU ĐÃ DỊCH:"""
        
        return prompt
    
    async def cleanup_sentence(self, match: Dict) -> str:
        """Dịch lại một câu có ký tự CJK"""
        try:
            prompt = self.create_cleanup_prompt(match)
            
            logger.info(f"Dịch lại dòng {match['line_number']}")
            
            # Gọi API
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )
            
            if response and response.text:
                cleaned_text = response.text.strip()
                
                # Kiểm tra xem còn ký tự CJK không
                remaining_cjk = self.cjk_pattern.findall(cleaned_text)
                if remaining_cjk:
                    logger.warning(f"Dòng {match['line_number']}: Vẫn còn ký tự CJK sau cleanup: {remaining_cjk}")
                    return None
                
                logger.info(f"Dòng {match['line_number']}: Cleanup thành công")
                return cleaned_text
            else:
                logger.error(f"Dòng {match['line_number']}: Không nhận được response")
                return None
                
        except Exception as e:
            logger.error(f"Dòng {match['line_number']}: Lỗi cleanup - {str(e)}")
            return None
    
    async def process_file(self, input_file: str, output_file: str = None) -> Dict:
        """Xử lý cleanup cho toàn bộ file"""
        if not output_file:
            output_file = input_file.replace('.txt', '_cleaned.txt')
        
        logger.info(f"Bắt đầu xử lý file: {input_file}")
        
        # Tìm các câu có ký tự CJK
        cjk_matches = self.find_cjk_sentences(input_file)
        
        if not cjk_matches:
            logger.info("Không tìm thấy ký tự CJK nào cần cleanup")
            return {"status": "success", "processed": 0, "errors": 0}
        
        # Load nội dung file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Xử lý từng câu
        processed = 0
        errors = 0
        
        for i, match in enumerate(cjk_matches):
            logger.info(f"Xử lý dòng {i+1}/{len(cjk_matches)}: {match['line_number']}")
            
            cleaned_sentence = await self.cleanup_sentence(match)
            if cleaned_sentence:
                # Thay thế câu cũ bằng câu đã cleanup
                lines[match['line_number'] - 1] = cleaned_sentence
                processed += 1
            else:
                errors += 1
                logger.error(f"Dòng {match['line_number']}: Thất bại cleanup")
        
        # Lưu file đã cleanup
        cleaned_content = '\n'.join(lines)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        # Kiểm tra kết quả
        remaining_cjk = self.find_cjk_sentences(output_file)
        remaining_count = len(remaining_cjk)
        
        result = {
            "status": "success" if remaining_count == 0 else "partial",
            "processed": processed,
            "errors": errors,
            "remaining_cjk": remaining_count,
            "output_file": output_file
        }
        
        logger.info(f"Hoàn thành cleanup: {processed} câu thành công, {errors} câu lỗi, {remaining_count} câu còn sót")
        
        return result

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple Cleanup cho file đã dịch")
    parser.add_argument("input_file", help="File input cần cleanup")
    parser.add_argument("-o", "--output", help="File output (mặc định: input_cleaned.txt)")
    parser.add_argument("-k", "--api-key", help="Gemini API key")
    
    args = parser.parse_args()
    
    # Kiểm tra file input
    if not os.path.exists(args.input_file):
        print(f"Lỗi: File {args.input_file} không tồn tại")
        return 1
    
    # Lấy API key
    api_key = args.api_key
    if not api_key:
        # Thử đọc từ config
        try:
            import yaml
            with open('config/config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            api_keys = config.get('api_keys', [])
            if api_keys and isinstance(api_keys, list):
                api_key = api_keys[0]
            else:
                print("Lỗi: Không tìm thấy API key. Vui lòng cung cấp bằng -k")
                return 1
        except Exception as e:
            print(f"Lỗi đọc config: {e}")
            return 1
    
    # Tạo processor
    processor = SimpleCleanupProcessor(api_key)
    
    # Xử lý file
    result = await processor.process_file(args.input_file, args.output)
    
    # In kết quả
    print("\n=== KẾT QUẢ CLEANUP ===")
    print(f"Trạng thái: {result['status']}")
    print(f"Đã xử lý: {result['processed']} câu")
    print(f"Lỗi: {result['errors']} câu")
    print(f"Còn sót: {result['remaining_cjk']} câu")
    print(f"File output: {result['output_file']}")
    
    return 0 if result['status'] == 'success' else 1

if __name__ == "__main__":
    asyncio.run(main())
