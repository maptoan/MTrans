#!/usr/bin/env python3
"""
Script cleanup sử dụng Gemini 2.5 Flash với API key rotation
Xử lý các câu còn sót từ tiếng Trung trong file đã dịch
"""

import asyncio
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.gemini_api_service import GeminiAPIService
from src.utils.logger import setup_main_logger

# Setup logging
logger = setup_main_logger("FlashCleanup")

class FlashCleanupProcessor:
    """Xử lý cleanup sử dụng Gemini 2.5 Flash với API rotation"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        
        # Load config
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize API service với rotation
        self.api_service = GeminiAPIService(self.config)
        
        # CJK pattern
        self.cjk_pattern = re.compile(r'[\u4e00-\u9fff]+')
        
        # Kiểm tra API keys
        available_keys = self.api_service.get_available_keys_count()
        logger.info(f"Số API keys khả dụng: {available_keys}")
        
        if available_keys == 0:
            raise Exception("Không có API key nào khả dụng!")
        
        # Kiểm tra tính hợp lệ của API keys trước khi bắt đầu
        self.valid_keys = []
        self._validate_api_keys()
        
        # Cấu hình xử lý song song (giảm để tránh rate limit)
        self.max_concurrent = min(len(self.valid_keys), 5)  # Giảm xuống 5 concurrent
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        logger.info(f"Cấu hình xử lý song song: {self.max_concurrent} concurrent requests")
    
    def _validate_api_keys(self):
        """Kiểm tra tính hợp lệ của tất cả API keys trước khi bắt đầu"""
        logger.info("Đang kiểm tra tính hợp lệ của API keys...")
        
        # Lấy danh sách API keys từ config
        api_keys = self.config.get('api_keys', [])
        if not api_keys:
            raise Exception("Không tìm thấy API keys trong config!")
        
        valid_count = 0
        invalid_count = 0
        
        for i, api_key in enumerate(api_keys):
            try:
                # Test API key với một request đơn giản
                test_result = self._test_api_key(api_key)
                if test_result:
                    self.valid_keys.append(api_key)
                    valid_count += 1
                    logger.info(f"API key {i+1}: ✓ Hợp lệ")
                else:
                    invalid_count += 1
                    logger.warning(f"API key {i+1}: ✗ Không hợp lệ")
            except Exception as e:
                invalid_count += 1
                logger.warning(f"API key {i+1}: ✗ Lỗi - {str(e)}")
        
        logger.info(f"Kết quả kiểm tra: {valid_count} keys hợp lệ, {invalid_count} keys không hợp lệ")
        
        if valid_count == 0:
            raise Exception("Không có API key nào hợp lệ! Vui lòng kiểm tra lại config.")
        
        logger.info(f"Sẽ sử dụng {valid_count} API keys hợp lệ cho cleanup")
    
    def _test_api_key(self, api_key: str) -> bool:
        """Test một API key với request đơn giản"""
        try:
            import google.generativeai as genai
            
            # Configure với key này
            genai.configure(api_key=api_key)
            
            # Tạo model
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Test với prompt đơn giản
            test_prompt = "Dịch từ tiếng Trung sang tiếng Việt: 你好"
            
            # Thực hiện request test
            response = model.generate_content(test_prompt)
            
            # Kiểm tra response
            if response and response.text and response.text.strip():
                return True
            else:
                return False
                
        except Exception as e:
            logger.debug(f"Test API key failed: {str(e)}")
            return False
    
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
        """Dịch lại một câu có ký tự CJK (legacy method)"""
        try:
            prompt = self.create_cleanup_prompt(match)
            
            logger.info(f"Dịch lại dòng {match['line_number']} với Gemini 2.5 Flash")
            
            # Sử dụng API service với rotation
            response = await self.api_service.generate_content_async(
                prompt=prompt,
                model_name="gemini-2.5-flash",  # Sử dụng Flash model
                max_retries=3
            )
            
            if response and response.strip():
                cleaned_text = response.strip()
                
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
    
    async def cleanup_sentence_with_valid_key(self, match: Dict, key_index: int) -> str:
        """Dịch lại một câu có ký tự CJK sử dụng API key đã được xác thực"""
        async with self.semaphore:  # Giới hạn concurrent requests
            try:
                prompt = self.create_cleanup_prompt(match)
                
                # Sử dụng API key đã được xác thực
                api_key = self.valid_keys[key_index]
                logger.debug(f"Dịch lại dòng {match['line_number']} với Gemini 2.5 Flash (key {key_index + 1})")
                
                # Gọi API trực tiếp với key đã xác thực
                response = await self._call_gemini_api_direct(api_key, prompt)
                
                if response and response.strip():
                    cleaned_text = response.strip()
                    
                    # Kiểm tra xem còn ký tự CJK không
                    remaining_cjk = self.cjk_pattern.findall(cleaned_text)
                    if remaining_cjk:
                        logger.warning(f"Dòng {match['line_number']}: Vẫn còn ký tự CJK sau cleanup: {remaining_cjk}")
                        return None
                    
                    return cleaned_text
                else:
                    logger.error(f"Dòng {match['line_number']}: Không nhận được response")
                    return None
                    
            except Exception as e:
                logger.error(f"Dòng {match['line_number']}: Lỗi cleanup - {str(e)}")
                return None
    
    async def _call_gemini_api_direct(self, api_key: str, prompt: str, max_retries: int = 3) -> str:
        """Gọi Gemini API trực tiếp với key cụ thể và retry logic"""
        import google.generativeai as genai
        
        for attempt in range(max_retries):
            try:
                # Configure với key này
                genai.configure(api_key=api_key)
                
                # Tạo model
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # Thực hiện request
                response = model.generate_content(prompt)
                
                # Trả về text
                if response and response.text:
                    return response.text.strip()
                else:
                    return None
                    
            except Exception as e:
                error_msg = str(e)
                logger.debug(f"API call attempt {attempt + 1} failed: {error_msg}")
                
                # Kiểm tra loại lỗi
                if "429" in error_msg or "quota" in error_msg.lower():
                    if attempt < max_retries - 1:
                        # Exponential backoff cho quota errors
                        wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                        logger.warning(f"Quota exhausted, waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Max retries reached for quota error: {error_msg}")
                        raise e
                else:
                    # Lỗi khác, retry ngay
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                    else:
                        raise e
        
        return None
    
    async def process_file(self, input_file: str, output_file: str = None) -> Dict:
        """Xử lý cleanup cho toàn bộ file với xử lý song song"""
        if not output_file:
            output_file = input_file.replace('.txt', '_cleaned.txt')
        
        logger.info(f"Bắt đầu xử lý file: {input_file}")
        
        # Kiểm tra lại API keys trước khi bắt đầu
        if not self.valid_keys:
            logger.error("Không có API key hợp lệ nào để sử dụng!")
            return {"status": "error", "processed": 0, "errors": 0, "message": "No valid API keys"}
        
        # Tìm các câu có ký tự CJK
        cjk_matches = self.find_cjk_sentences(input_file)
        
        if not cjk_matches:
            logger.info("Không tìm thấy ký tự CJK nào cần cleanup")
            return {"status": "success", "processed": 0, "errors": 0}
        
        # Load nội dung file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Xử lý song song
        start_time = time.time()
        results = await self._process_parallel(cjk_matches)
        
        # Cập nhật file với kết quả
        processed = 0
        errors = 0
        
        for i, (match, cleaned_sentence) in enumerate(zip(cjk_matches, results)):
            if cleaned_sentence:
                lines[match['line_number'] - 1] = cleaned_sentence
                processed += 1
            else:
                errors += 1
        
        # Lưu file đã cleanup
        cleaned_content = '\n'.join(lines)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        # Tính thời gian xử lý
        processing_time = time.time() - start_time
        
        # Kiểm tra kết quả
        remaining_cjk = self.find_cjk_sentences(output_file)
        remaining_count = len(remaining_cjk)
        
        result = {
            "status": "success" if remaining_count == 0 else "partial",
            "processed": processed,
            "errors": errors,
            "remaining_cjk": remaining_count,
            "output_file": output_file,
            "valid_keys_used": len(self.valid_keys),
            "processing_time": round(processing_time, 2),
            "speed": round(processed / processing_time, 2) if processing_time > 0 else 0
        }
        
        logger.info(f"Hoàn thành cleanup: {processed} câu thành công, {errors} câu lỗi, {remaining_count} câu còn sót")
        logger.info(f"Thời gian xử lý: {processing_time:.2f}s, Tốc độ: {result['speed']} câu/s")
        logger.info(f"Sử dụng {len(self.valid_keys)} API keys hợp lệ")
        
        return result
    
    async def _process_parallel(self, cjk_matches: List[Dict]) -> List[str]:
        """Xử lý song song các câu có ký tự CJK theo batches"""
        logger.info(f"Bắt đầu xử lý song song {len(cjk_matches)} câu...")
        
        # Chia thành batches để tránh quá tải
        batch_size = self.max_concurrent
        total_batches = (len(cjk_matches) + batch_size - 1) // batch_size
        
        logger.info(f"Chia thành {total_batches} batches, mỗi batch {batch_size} câu")
        
        all_results = []
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(cjk_matches))
            batch_matches = cjk_matches[start_idx:end_idx]
            
            progress = (batch_idx + 1) / total_batches * 100
            logger.info(f"Xử lý batch {batch_idx + 1}/{total_batches} ({len(batch_matches)} câu) - Tiến độ: {progress:.1f}%")
            
            # Tạo tasks cho batch hiện tại
            tasks = []
            for i, match in enumerate(batch_matches):
                key_index = (start_idx + i) % len(self.valid_keys)  # Round-robin key assignment
                task = self.cleanup_sentence_with_valid_key(match, key_index)
                tasks.append(task)
            
            # Thực hiện batch song song
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Xử lý kết quả batch
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch {batch_idx + 1}, Task {i+1} failed: {str(result)}")
                    all_results.append(None)
                else:
                    all_results.append(result)
            
            # Kiểm tra kết quả batch và xử lý quota errors
            quota_errors = sum(1 for result in batch_results if isinstance(result, Exception) and "429" in str(result))
            
            if quota_errors > len(batch_results) * 0.7:  # Nếu >70% requests bị 429
                logger.warning(f"Batch {batch_idx + 1}: {quota_errors}/{len(batch_results)} requests bị quota error")
                logger.info("Chờ 60s để quota reset...")
                await asyncio.sleep(60)
            
            # Delay nhỏ giữa các batches để tránh rate limit
            if batch_idx < total_batches - 1:
                await asyncio.sleep(2)  # Tăng delay lên 2s
        
        logger.info(f"Hoàn thành xử lý {len(all_results)} câu")
        return all_results

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Flash Cleanup cho file đã dịch")
    parser.add_argument("input_file", help="File input cần cleanup")
    parser.add_argument("-o", "--output", help="File output (mặc định: input_cleaned.txt)")
    parser.add_argument("-c", "--config", default="config/config.yaml", help="File config")
    
    args = parser.parse_args()
    
    # Kiểm tra file input
    if not os.path.exists(args.input_file):
        print(f"Lỗi: File {args.input_file} không tồn tại")
        return 1
    
    try:
        # Tạo processor
        processor = FlashCleanupProcessor(args.config)
        
        # Xử lý file
        result = await processor.process_file(args.input_file, args.output)
        
        # In kết quả
        print("\n=== KẾT QUẢ CLEANUP ===")
        print(f"Trạng thái: {result['status']}")
        print(f"Đã xử lý: {result['processed']} câu")
        print(f"Lỗi: {result['errors']} câu")
        print(f"Còn sót: {result['remaining_cjk']} câu")
        print(f"API keys hợp lệ: {result.get('valid_keys_used', 0)}")
        print(f"Thời gian xử lý: {result.get('processing_time', 0)}s")
        print(f"Tốc độ: {result.get('speed', 0)} câu/s")
        print(f"File output: {result['output_file']}")
        
        return 0 if result['status'] == 'success' else 1
        
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        return 1

if __name__ == "__main__":
    asyncio.run(main())
