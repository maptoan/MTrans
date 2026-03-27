#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script trích xuất metadata về đại từ nhân xưng ngôi thứ ba
"""

import asyncio
import csv
import os
import sys
from pathlib import Path

import yaml

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from preprocessing.file_parser import AdvancedFileParser
from services.gemini_api_service import GeminiAPIService
from utils.logger import setup_main_logger

logger = setup_main_logger("PronounExtractor")

class PronounMetadataExtractor:
    """Trích xuất metadata về đại từ nhân xưng"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Khởi tạo extractor"""
        self.config_path = config_path
        self.config = self._load_config()
        self.api_service = GeminiAPIService(self.config)
        self.file_parser = AdvancedFileParser(self.config)
        
        # Đường dẫn output
        self.output_dir = Path("data/metadata")
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info("PronounMetadataExtractor khởi tạo thành công")
    
    def _load_config(self) -> dict:
        """Load config từ file YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Đã load config từ {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Lỗi load config: {e}")
            raise
    
    async def extract_pronoun_metadata(self, input_file: str) -> str:
        """Trích xuất metadata về đại từ nhân xưng"""
        try:
            logger.info(f"Bắt đầu trích xuất metadata đại từ nhân xưng từ {input_file}")
            
            # Parse file input
            parsed = self.file_parser.parse(input_file)
            text = parsed['text']
            
            if not text:
                raise ValueError("Không thể đọc được nội dung từ file input")
            
            logger.info(f"Đã đọc {len(text)} ký tự từ file input")
            
            # Chia text thành chunks nhỏ hơn để xử lý
            chunk_size = 10000  # 10k ký tự mỗi chunk
            chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
            
            logger.info(f"Chia thành {len(chunks)} chunks để xử lý")
            
            # Load prompt
            prompt_path = "prompts/notebooklm/4_prompt_pronoun_extraction.txt"
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            all_results = []
            
            # Xử lý từng chunk
            for i, chunk in enumerate(chunks):
                logger.info(f"Xử lý chunk {i+1}/{len(chunks)}")
                
                # Tạo prompt cho chunk này
                prompt = f"{prompt_template}\n\n## VĂN BẢN CẦN PHÂN TÍCH:\n{chunk}"
                
                # Gọi API
                try:
                    response = await self.api_service.generate_content_async(
                        prompt=prompt,
                        model_name="gemini-2.5-flash",
                        response_mime_type="text/csv"
                    )
                    
                    if response and response.strip():
                        # Parse CSV response
                        csv_data = self._parse_csv_response(response)
                        all_results.extend(csv_data)
                        logger.info(f"Chunk {i+1}: Trích xuất được {len(csv_data)} dòng dữ liệu")
                    else:
                        logger.warning(f"Chunk {i+1}: Không nhận được response")
                        
                except Exception as e:
                    logger.error(f"Chunk {i+1}: Lỗi API - {e}")
                    continue
            
            # Lưu kết quả
            output_file = self.output_dir / "pronoun_metadata.csv"
            self._save_csv(all_results, output_file)
            
            logger.info(f"Hoàn thành trích xuất. Đã lưu {len(all_results)} dòng dữ liệu vào {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Lỗi trong quá trình trích xuất: {e}")
            raise
    
    def _parse_csv_response(self, response: str) -> list:
        """Parse CSV response từ API"""
        try:
            # Loại bỏ markdown code fences nếu có
            if response.startswith('```csv'):
                response = response[6:]
            if response.endswith('```'):
                response = response[:-3]
            
            response = response.strip()
            
            # Parse CSV
            lines = response.split('\n')
            if len(lines) < 2:
                return []
            
            # Lấy header
            header = [col.strip() for col in lines[0].split(',')]
            
            # Parse data rows
            data = []
            for line in lines[1:]:
                if line.strip():
                    row = [col.strip().strip('"') for col in line.split(',')]
                    if len(row) >= len(header):
                        # Tạo dict từ header và row
                        row_dict = dict(zip(header, row))
                        data.append(row_dict)
            
            return data
            
        except Exception as e:
            logger.error(f"Lỗi parse CSV: {e}")
            return []
    
    def _save_csv(self, data: list, output_file: Path) -> None:
        """Lưu dữ liệu vào file CSV"""
        if not data:
            logger.warning("Không có dữ liệu để lưu")
            return
        
        # Lấy tất cả keys từ tất cả rows
        all_keys = set()
        for row in data:
            all_keys.update(row.keys())
        
        # Sắp xếp keys theo thứ tự mong muốn
        preferred_order = [
            'Character_Name', 'Character_Pinyin', 'Pronoun_CN', 'Pronoun_Context',
            'Speaker_Relationship', 'Formality_Level', 'Emotional_Tone', 'Scene_Type',
            'Gender', 'Age_Group', 'Social_Status', 'Suggested_VN_Pronoun',
            'Alternative_VN_Pronouns', 'Usage_Rule', 'Example_Sentence', 'Frequency'
        ]
        
        # Tạo fieldnames với thứ tự ưu tiên
        fieldnames = []
        for key in preferred_order:
            if key in all_keys:
                fieldnames.append(key)
                all_keys.remove(key)
        
        # Thêm các keys còn lại
        fieldnames.extend(sorted(all_keys))
        
        # Ghi file CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Đã lưu {len(data)} dòng dữ liệu vào {output_file}")

async def main():
    """Hàm main"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Trích xuất metadata đại từ nhân xưng")
    parser.add_argument("input_file", help="Đường dẫn file input (txt, epub, docx, pdf)")
    parser.add_argument("--config", default="config/config.yaml", help="Đường dẫn file config")
    
    args = parser.parse_args()
    
    try:
        extractor = PronounMetadataExtractor(args.config)
        output_file = await extractor.extract_pronoun_metadata(args.input_file)
        print(f"✅ Hoàn thành! Đã lưu metadata vào: {output_file}")
        
    except Exception as e:
        logger.error(f"Lỗi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
