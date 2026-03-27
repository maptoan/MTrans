#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script trích xuất metadata đại từ nhân xưng (phiên bản đơn giản - không dùng API)
"""

import csv
import os
import re
import sys
from pathlib import Path

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from preprocessing.file_parser import AdvancedFileParser
from utils.logger import setup_main_logger

logger = setup_main_logger("PronounExtractorSimple")

class SimplePronounExtractor:
    """Trích xuất metadata đại từ nhân xưng đơn giản"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Khởi tạo extractor"""
        self.config_path = config_path
        self.config = self._load_config()
        self.file_parser = AdvancedFileParser(self.config)
        
        # Đường dẫn output
        self.output_dir = Path("data/metadata")
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info("SimplePronounExtractor khởi tạo thành công")
    
    def _load_config(self) -> dict:
        """Load config từ file YAML"""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Đã load config từ {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Lỗi load config: {e}")
            raise
    
    def extract_pronoun_metadata(self, input_file: str) -> str:
        """Trích xuất metadata về đại từ nhân xưng"""
        try:
            logger.info(f"Bắt đầu trích xuất metadata đại từ nhân xưng từ {input_file}")
            
            # Parse file input
            parsed = self.file_parser.parse(input_file)
            text = parsed['text']
            
            if not text:
                raise ValueError("Không thể đọc được nội dung từ file input")
            
            logger.info(f"Đã đọc {len(text)} ký tự từ file input")
            
            # Trích xuất metadata dựa trên quy tắc cố định
            pronoun_data = self._extract_pronouns_from_text(text)
            
            # Lưu kết quả
            output_file = self.output_dir / "pronoun_metadata.csv"
            self._save_csv(pronoun_data, output_file)
            
            logger.info(f"Hoàn thành trích xuất. Đã lưu {len(pronoun_data)} dòng dữ liệu vào {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Lỗi trong quá trình trích xuất: {e}")
            raise
    
    def _extract_pronouns_from_text(self, text: str) -> list:
        """Trích xuất đại từ nhân xưng từ text dựa trên quy tắc cố định"""
        data = []
        
        # Danh sách nhân vật chính (từ character_relations.csv)
        main_characters = [
            "崔小玄", "程水若", "崔采婷", "飞萝", "李梦棠", "夏小婉", 
            "武翩跹", "婀妍", "方少麟", "雪涵", "绮姬", "黑无霸",
            "玉桃娘娘", "袁自在", "黎山老母", "摘霞"
        ]
        
        # Mapping đại từ tiếng Trung -> tiếng Việt
        pronoun_mapping = {
            "他": {
                "formal": "anh",
                "informal": "cậu", 
                "contempt": "hắn",
                "romantic": "chàng",
                "elder": "ông"
            },
            "她": {
                "formal": "cô",
                "informal": "nàng",
                "romantic": "nàng",
                "elder": "bà"
            },
            "它": {
                "default": "nó"
            }
        }
        
        # Tìm các đoạn hội thoại và tường thuật
        dialogue_pattern = r'["""]([^"""]*)["""]'
        narration_pattern = r'[^。！？]*[。！？]'
        
        # Tìm hội thoại
        dialogues = re.findall(dialogue_pattern, text)
        for dialogue in dialogues:
            if len(dialogue) > 10:  # Chỉ lấy đoạn hội thoại dài
                self._analyze_dialogue(dialogue, data, main_characters, pronoun_mapping)
        
        # Tìm tường thuật
        narrations = re.findall(narration_pattern, text)
        for narration in narrations:
            if len(narration) > 20:  # Chỉ lấy đoạn tường thuật dài
                self._analyze_narration(narration, data, main_characters, pronoun_mapping)
        
        return data
    
    def _analyze_dialogue(self, dialogue: str, data: list, characters: list, pronoun_mapping: dict):
        """Phân tích đoạn hội thoại"""
        # Tìm đại từ trong hội thoại
        for pronoun_cn in pronoun_mapping.keys():
            if pronoun_cn in dialogue:
                # Xác định ngữ cảnh
                context = "dialogue"
                formality = "informal"  # Hội thoại thường informal
                
                # Tìm nhân vật liên quan
                for char in characters:
                    if char in dialogue:
                        # Tạo dữ liệu
                        row = {
                            'Character_Name': char,
                            'Character_Pinyin': self._get_pinyin(char),
                            'Pronoun_CN': pronoun_cn,
                            'Pronoun_Context': context,
                            'Speaker_Relationship': 'unknown',
                            'Formality_Level': formality,
                            'Emotional_Tone': 'neutral',
                            'Scene_Type': 'dialogue',
                            'Gender': 'male' if pronoun_cn == '他' else 'female' if pronoun_cn == '她' else 'unknown',
                            'Age_Group': 'unknown',
                            'Social_Status': 'unknown',
                            'Suggested_VN_Pronoun': pronoun_mapping[pronoun_cn].get(formality, pronoun_cn),
                            'Alternative_VN_Pronouns': list(pronoun_mapping[pronoun_cn].values()),
                            'Usage_Rule': f'Trong hội thoại, sử dụng {pronoun_mapping[pronoun_cn].get(formality, pronoun_cn)}',
                            'Example_Sentence': dialogue[:100] + "...",
                            'Frequency': 'High'
                        }
                        data.append(row)
                        break
    
    def _analyze_narration(self, narration: str, data: list, characters: list, pronoun_mapping: dict):
        """Phân tích đoạn tường thuật"""
        # Tìm đại từ trong tường thuật
        for pronoun_cn in pronoun_mapping.keys():
            if pronoun_cn in narration:
                # Xác định ngữ cảnh
                context = "narration"
                formality = "formal"  # Tường thuật thường formal
                
                # Tìm nhân vật liên quan
                for char in characters:
                    if char in narration:
                        # Tạo dữ liệu
                        row = {
                            'Character_Name': char,
                            'Character_Pinyin': self._get_pinyin(char),
                            'Pronoun_CN': pronoun_cn,
                            'Pronoun_Context': context,
                            'Speaker_Relationship': 'unknown',
                            'Formality_Level': formality,
                            'Emotional_Tone': 'neutral',
                            'Scene_Type': 'narration',
                            'Gender': 'male' if pronoun_cn == '他' else 'female' if pronoun_cn == '她' else 'unknown',
                            'Age_Group': 'unknown',
                            'Social_Status': 'unknown',
                            'Suggested_VN_Pronoun': pronoun_mapping[pronoun_cn].get(formality, pronoun_cn),
                            'Alternative_VN_Pronouns': list(pronoun_mapping[pronoun_cn].values()),
                            'Usage_Rule': f'Trong tường thuật, sử dụng {pronoun_mapping[pronoun_cn].get(formality, pronoun_cn)}',
                            'Example_Sentence': narration[:100] + "...",
                            'Frequency': 'High'
                        }
                        data.append(row)
                        break
    
    def _get_pinyin(self, chinese_name: str) -> str:
        """Lấy pinyin cho tên tiếng Trung (đơn giản)"""
        # Mapping cơ bản
        pinyin_map = {
            "崔小玄": "Cui Xiao Xuan",
            "程水若": "Cheng Shui Ruo", 
            "崔采婷": "Cui Cai Ting",
            "飞萝": "Fei Luo",
            "李梦棠": "Li Meng Tang",
            "夏小婉": "Xia Xiao Wan",
            "武翩跹": "Wu Pian Xian",
            "婀妍": "E Yan",
            "方少麟": "Fang Shao Lin",
            "雪涵": "Xue Han",
            "绮姬": "Qi Ji",
            "黑无霸": "Hei Wu Ba",
            "玉桃娘娘": "Yu Tao Niang Niang",
            "袁自在": "Yuan Zi Zai",
            "黎山老母": "Li Shan Lao Mu",
            "摘霞": "Zhai Xia"
        }
        return pinyin_map.get(chinese_name, chinese_name)
    
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

def main():
    """Hàm main"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Trích xuất metadata đại từ nhân xưng (phiên bản đơn giản)")
    parser.add_argument("input_file", help="Đường dẫn file input (txt, epub, docx, pdf)")
    parser.add_argument("--config", default="config/config.yaml", help="Đường dẫn file config")
    
    args = parser.parse_args()
    
    try:
        extractor = SimplePronounExtractor(args.config)
        output_file = extractor.extract_pronoun_metadata(args.input_file)
        print(f"✅ Hoàn thành! Đã lưu metadata vào: {output_file}")
        
    except Exception as e:
        logger.error(f"Lỗi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
