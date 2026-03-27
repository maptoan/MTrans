#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tạo character mapping để kết nối tên nhân vật với loại nhân vật
"""

import csv
import json
import os
import sys

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import setup_main_logger

logger = setup_main_logger("CharacterMappingCreator")

class CharacterMappingCreator:
    """Tạo character mapping từ tên nhân vật thực tế đến loại nhân vật"""
    
    def __init__(self):
        """Khởi tạo creator"""
        self.character_mapping = {}
        self.character_metadata = {}
        
    def create_character_mapping(self):
        """Tạo mapping dựa trên phân tích tên nhân vật"""
        
        # Dữ liệu nhân vật từ các tác phẩm phổ biến
        character_data = {
            # Nam chính (Main Character)
            "NAM_CHINH": {
                "names": [
                    "Thôi Tiểu Huyền", "崔小玄", "Cui Xiao Xuan",
                    "Lâm Phong", "林风", "Lin Feng",
                    "Tiểu Huyền", "小玄", "Xiao Xuan",
                    "Huyền", "玄", "Xuan"
                ],
                "patterns": ["小玄", "Tiểu Huyền", "Cui", "Huyền", "玄"],
                "description": "Nam chính của tác phẩm, thường là người có năng lực đặc biệt"
            },
            
            # Nữ chính / Hậu cung
            "NU_CHINH": {
                "names": [
                    "Cheng Shui Ruo", "程水若", "Thủy Nhược", "水若",
                    "Lý Tiên Tử", "李仙子", "Li Xian Zi",
                    "Tiên Tử", "仙子", "Xian Zi",
                    "Thủy Nhược", "水若", "Shui Ruo"
                ],
                "patterns": ["水若", "Thủy Nhược", "Cheng", "仙子", "Tiên Tử"],
                "description": "Nữ chính hoặc thành viên hậu cung"
            },
            
            # Nam quyền quý/cấp cao
            "NAM_QUYEN_QUY": {
                "names": [
                    "Sư phụ", "师父", "Master", "Lão sư", "老师",
                    "Sư tôn", "师祖", "Grand Master", "Lão tổ", "老祖",
                    "Hoàng đế", "皇帝", "Emperor", "Bệ hạ", "陛下",
                    "Tông chủ", "宗主", "Sect Leader", "Chủ tịch", "主席"
                ],
                "patterns": ["师父", "Sư phụ", "Master", "皇帝", "Hoàng đế", "Tông chủ"],
                "description": "Nam giới có địa vị cao trong tông môn hoặc triều đình"
            },
            
            # Nữ quyền quý/cấp cao
            "NU_QUYEN_QUY": {
                "names": [
                    "Sư thái", "师太", "Elder Sister", "Lão bà bà", "老奶奶",
                    "Hoàng hậu", "皇后", "Empress", "Nương nương", "娘娘",
                    "Nữ đế", "女帝", "Female Emperor", "Bệ hạ nữ", "陛下女",
                    "Tông chủ nữ", "女宗主", "Female Sect Leader"
                ],
                "patterns": ["师太", "Sư thái", "皇后", "Hoàng hậu", "女帝", "Nữ đế"],
                "description": "Nữ giới có địa vị cao trong tông môn hoặc triều đình"
            },
            
            # Nam phản diện/Tà tu
            "NAM_PHAN_DIEN": {
                "names": [
                    "Tà Hoàng Uyên Ất", "邪皇渊乙", "Xie Huang Yuan Yi",
                    "Ma tôn", "魔尊", "Demon Lord", "Ma quân", "魔君",
                    "Tà tu", "邪修", "Evil Cultivator", "Ma tu", "魔修",
                    "Uyên Ất", "渊乙", "Yuan Yi"
                ],
                "patterns": ["邪皇", "Tà Hoàng", "魔尊", "Ma tôn", "邪修", "Tà tu"],
                "description": "Nam phản diện hoặc tu sĩ tà đạo"
            },
            
            # Nữ phản diện/Ma nữ
            "NU_PHAN_DIEN": {
                "names": [
                    "Yêu nữ", "妖女", "Demoness", "Ma nữ", "魔女",
                    "Hồ ly tinh", "狐狸精", "Fox Spirit", "Yêu tinh", "妖精",
                    "Ma hậu", "魔后", "Demon Queen", "Yêu hậu", "妖后"
                ],
                "patterns": ["妖女", "Yêu nữ", "狐狸精", "Hồ ly", "魔女", "Ma nữ"],
                "description": "Nữ phản diện hoặc yêu ma"
            },
            
            # Yêu thú/Linh thú
            "YEU_THU": {
                "names": [
                    "Tiểu Hắc", "小黑", "Little Black", "Hắc Hổ", "黑虎",
                    "Kim Sư", "金狮", "Golden Lion", "Bạch Hổ", "白虎",
                    "Thanh Long", "青龙", "Azure Dragon", "Huyền Vũ", "玄武"
                ],
                "patterns": ["小黑", "Tiểu Hắc", "金狮", "Kim Sư", "青龙", "Thanh Long"],
                "description": "Yêu thú hoặc linh thú có linh trí"
            },
            
            # Ma tộc/Chủng tộc khác
            "MA_TOC": {
                "names": [
                    "Ma vương", "魔王", "Demon King", "Ma tộc", "魔族",
                    "Yêu vương", "妖王", "Monster King", "Yêu tộc", "妖族",
                    "Quỷ vương", "鬼王", "Ghost King", "Quỷ tộc", "鬼族"
                ],
                "patterns": ["魔王", "Ma vương", "妖王", "Yêu vương", "鬼王", "Quỷ vương"],
                "description": "Thành viên của các chủng tộc phi nhân"
            }
        }
        
        # Tạo mapping
        for char_type, data in character_data.items():
            for name in data["names"]:
                self.character_mapping[name] = {
                    "type": char_type,
                    "description": data["description"],
                    "patterns": data["patterns"]
                }
        
        # Tạo metadata
        self.character_metadata = character_data
        
        logger.info(f"Đã tạo mapping cho {len(self.character_mapping)} tên nhân vật")
    
    def save_character_mapping(self, output_file: str = "data/metadata/character_mapping.json"):
        """Lưu character mapping"""
        mapping_data = {
            "character_mapping": self.character_mapping,
            "character_metadata": self.character_metadata,
            "version": "1.0",
            "description": "Mapping từ tên nhân vật thực tế đến loại nhân vật trong hệ thống đại từ"
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Đã lưu character mapping vào {output_file}")
        return output_file
    
    def create_character_csv(self, output_file: str = "data/metadata/character_types.csv"):
        """Tạo file CSV cho character types"""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['Character_Name', 'Character_Type', 'Description', 'Patterns']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for name, data in self.character_mapping.items():
                writer.writerow({
                    'Character_Name': name,
                    'Character_Type': data['type'],
                    'Description': data['description'],
                    'Patterns': '|'.join(data['patterns'])
                })
        
        logger.info(f"Đã lưu character types CSV vào {output_file}")
        return output_file

def main():
    """Hàm main"""
    print("🔧 Tạo character mapping...")
    print("=" * 50)
    
    creator = CharacterMappingCreator()
    
    # Tạo mapping
    print("📝 Đang tạo character mapping...")
    creator.create_character_mapping()
    
    # Lưu files
    print("💾 Đang lưu files...")
    json_file = creator.save_character_mapping()
    csv_file = creator.create_character_csv()
    
    print("✅ Hoàn thành! Đã tạo:")
    print(f"  - {json_file}")
    print(f"  - {csv_file}")
    print(f"📊 Tổng số mapping: {len(creator.character_mapping)}")

if __name__ == "__main__":
    main()
