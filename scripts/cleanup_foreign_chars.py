#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script cleanup ký tự nước ngoài trong các chunk đã dịch
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import google.generativeai as genai

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ForeignCharCleanupProcessor:
    """Xử lý cleanup ký tự nước ngoài trong chunk dịch"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
        # Patterns để phát hiện ký tự nước ngoài
        self.foreign_pattern = re.compile(r'[\u4e00-\u9fff\u0e00-\u0e7f\uac00-\ud7af\u3040-\u309f\u30a0-\u30ff]+')
        self.cjk_pattern = re.compile(r'[\u4e00-\u9fff]+')  # Tiếng Trung
        self.thai_pattern = re.compile(r'[\u0e00-\u0e7f]+')  # Tiếng Thái
        self.korean_pattern = re.compile(r'[\uac00-\ud7af]+')  # Tiếng Hàn
        self.japanese_pattern = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]+')  # Tiếng Nhật
        
        # Initialize model
        self.model = genai.GenerativeModel('gemini-2.5-pro')
    
    def find_chunks_with_foreign_chars(self, chunks_dir: str) -> List[Dict]:
        """Tìm các chunk có ký tự nước ngoài"""
        logger.info(f"Đang quét thư mục: {chunks_dir}")
        
        chunks_with_foreign = []
        
        for chunk_file in Path(chunks_dir).glob("*.txt"):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                foreign_matches = self.foreign_pattern.findall(content)
                if foreign_matches:
                    # Phân loại ký tự
                    cjk_matches = self.cjk_pattern.findall(content)
                    thai_matches = self.thai_pattern.findall(content)
                    korean_matches = self.korean_pattern.findall(content)
                    japanese_matches = self.japanese_pattern.findall(content)
                    
                    chunk_info = {
                        'file_path': str(chunk_file),
                        'file_name': chunk_file.name,
                        'content': content,
                        'foreign_characters': foreign_matches,
                        'cjk_chars': cjk_matches,
                        'thai_chars': thai_matches,
                        'korean_chars': korean_matches,
                        'japanese_chars': japanese_matches
                    }
                    chunks_with_foreign.append(chunk_info)
                    
            except Exception as e:
                logger.error(f"Lỗi đọc file {chunk_file}: {e}")
        
        logger.info(f"Tìm thấy {len(chunks_with_foreign)} chunk có ký tự nước ngoài")
        return chunks_with_foreign
    
    def create_cleanup_prompt(self, chunk_info: Dict) -> str:
        """Tạo prompt cleanup cho chunk có ký tự nước ngoài"""
        foreign_chars = chunk_info['foreign_characters']
        content = chunk_info['content']
        
        # Tạo danh sách ký tự cần loại bỏ
        char_list = []
        if chunk_info['cjk_chars']:
            char_list.append(f"Tiếng Trung: {chunk_info['cjk_chars']}")
        if chunk_info['thai_chars']:
            char_list.append(f"Tiếng Thái: {chunk_info['thai_chars']}")
        if chunk_info['korean_chars']:
            char_list.append(f"Tiếng Hàn: {chunk_info['korean_chars']}")
        if chunk_info['japanese_chars']:
            char_list.append(f"Tiếng Nhật: {chunk_info['japanese_chars']}")
        
        char_description = "\n".join(char_list)
        
        prompt = f"""Bạn là chuyên gia dịch thuật tiếng Trung sang tiếng Việt. Nhiệm vụ của bạn là làm sạch đoạn văn sau bằng cách loại bỏ TẤT CẢ ký tự nước ngoài còn sót.

ĐOẠN VĂN CẦN LÀM SẠCH:
{content}

KÝ TỰ NƯỚC NGOÀI CẦN LOẠI BỎ:
{char_description}

YÊU CẦU:
1. Loại bỏ TẤT CẢ ký tự nước ngoài (Trung, Thái, Hàn, Nhật) còn sót
2. Thay thế bằng từ tiếng Việt phù hợp hoặc loại bỏ nếu không cần thiết
3. Giữ nguyên ý nghĩa và ngữ cảnh của đoạn văn
4. Đảm bảo văn bản mượt mà, tự nhiên
5. Chỉ trả về đoạn văn đã làm sạch, không giải thích

ĐOẠN VĂN ĐÃ LÀM SẠCH:"""
        
        return prompt
    
    async def cleanup_chunk(self, chunk_info: Dict) -> str:
        """Cleanup một chunk"""
        try:
            prompt = self.create_cleanup_prompt(chunk_info)
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            cleaned_content = response.text.strip()
            
            # Kiểm tra xem còn ký tự nước ngoài không
            remaining_foreign = self.foreign_pattern.findall(cleaned_content)
            if remaining_foreign:
                logger.warning(f"Chunk {chunk_info['file_name']} vẫn còn ký tự nước ngoài: {remaining_foreign}")
                return None
            
            return cleaned_content
            
        except Exception as e:
            logger.error(f"Lỗi cleanup chunk {chunk_info['file_name']}: {e}")
            return None
    
    async def cleanup_all_chunks(self, chunks_dir: str, backup_dir: str = None) -> Dict[str, Any]:
        """Cleanup tất cả chunk có ký tự nước ngoài"""
        logger.info("Bắt đầu quá trình cleanup ký tự nước ngoài")
        
        # Tìm chunks có vấn đề
        chunks_with_foreign = self.find_chunks_with_foreign_chars(chunks_dir)
        
        if not chunks_with_foreign:
            logger.info("Không tìm thấy chunk nào có ký tự nước ngoài")
            return {
                'total_chunks': 0,
                'cleaned_chunks': 0,
                'failed_chunks': 0,
                'details': []
            }
        
        # Tạo backup nếu cần
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)
            logger.info(f"Tạo backup tại: {backup_dir}")
        
        results = {
            'total_chunks': len(chunks_with_foreign),
            'cleaned_chunks': 0,
            'failed_chunks': 0,
            'details': []
        }
        
        # Cleanup từng chunk
        for chunk_info in chunks_with_foreign:
            logger.info(f"Đang cleanup: {chunk_info['file_name']}")
            
            # Tạo backup
            if backup_dir:
                backup_path = os.path.join(backup_dir, chunk_info['file_name'])
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(chunk_info['content'])
            
            # Cleanup
            cleaned_content = await self.cleanup_chunk(chunk_info)
            
            if cleaned_content:
                # Ghi file đã cleanup
                with open(chunk_info['file_path'], 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                
                results['cleaned_chunks'] += 1
                results['details'].append({
                    'file': chunk_info['file_name'],
                    'status': 'success',
                    'foreign_chars_removed': chunk_info['foreign_characters']
                })
                logger.info(f"✅ Đã cleanup: {chunk_info['file_name']}")
            else:
                results['failed_chunks'] += 1
                results['details'].append({
                    'file': chunk_info['file_name'],
                    'status': 'failed',
                    'foreign_chars': chunk_info['foreign_characters']
                })
                logger.error(f"❌ Thất bại: {chunk_info['file_name']}")
        
        logger.info(f"Hoàn thành cleanup: {results['cleaned_chunks']}/{results['total_chunks']} chunk")
        return results

async def main():
    """Main function"""
    # Đọc API key từ file
    api_key_file = "tools/check_API_keys/api_keys.txt"
    try:
        with open(api_key_file, 'r', encoding='utf-8') as f:
            api_key = f.read().strip()
    except FileNotFoundError:
        logger.error(f"Không tìm thấy file API key: {api_key_file}")
        return
    
    # Khởi tạo processor
    processor = ForeignCharCleanupProcessor(api_key)
    
    # Đường dẫn thư mục chunks
    chunks_dir = "data/progress/TDTTT_chunks"
    backup_dir = "data/progress/TDTTT_chunks_backup"
    
    if not os.path.exists(chunks_dir):
        logger.error(f"Thư mục chunks không tồn tại: {chunks_dir}")
        return
    
    # Chạy cleanup
    results = await processor.cleanup_all_chunks(chunks_dir, backup_dir)
    
    # In kết quả
    print("\n" + "="*60)
    print("KẾT QUẢ CLEANUP KÝ TỰ NƯỚC NGOÀI")
    print("="*60)
    print(f"Tổng số chunk: {results['total_chunks']}")
    print(f"Cleanup thành công: {results['cleaned_chunks']}")
    print(f"Cleanup thất bại: {results['failed_chunks']}")
    
    if results['details']:
        print("\nChi tiết:")
        for detail in results['details']:
            status_icon = "✅" if detail['status'] == 'success' else "❌"
            print(f"{status_icon} {detail['file']}: {detail['status']}")

if __name__ == "__main__":
    asyncio.run(main())
