#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script test character mapping
"""

import os
import sys

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from translation.pronoun_compliance_checker import PronounComplianceChecker
from utils.logger import setup_main_logger

logger = setup_main_logger("CharacterMappingTest")

def test_character_mapping():
    """Test character mapping system"""
    
    print("🧪 Testing Character Mapping System...")
    print("=" * 60)
    
    # Khởi tạo checker
    checker = PronounComplianceChecker()
    
    # Test cases với tên nhân vật thực tế
    test_cases = [
        {
            'character_name': 'Thôi Tiểu Huyền',
            'expected_type': 'NAM_CHINH',
            'expected_pronoun_type': 'Nam chính (Main Character)'
        },
        {
            'character_name': '崔小玄',
            'expected_type': 'NAM_CHINH',
            'expected_pronoun_type': 'Nam chính (Main Character)'
        },
        {
            'character_name': 'Cheng Shui Ruo',
            'expected_type': 'NU_CHINH',
            'expected_pronoun_type': 'Nữ chính / Hậu cung'
        },
        {
            'character_name': '程水若',
            'expected_type': 'NU_CHINH',
            'expected_pronoun_type': 'Nữ chính / Hậu cung'
        },
        {
            'character_name': 'Sư phụ',
            'expected_type': 'NAM_QUYEN_QUY',
            'expected_pronoun_type': 'Nam quyền quý/cấp cao'
        },
        {
            'character_name': '师父',
            'expected_type': 'NAM_QUYEN_QUY',
            'expected_pronoun_type': 'Nam quyền quý/cấp cao'
        },
        {
            'character_name': 'Tà Hoàng Uyên Ất',
            'expected_type': 'NAM_PHAN_DIEN',
            'expected_pronoun_type': 'Nam phản diện / Tà tu'
        },
        {
            'character_name': '邪皇渊乙',
            'expected_type': 'NAM_PHAN_DIEN',
            'expected_pronoun_type': 'Nam phản diện / Tà tu'
        },
        {
            'character_name': 'Yêu nữ',
            'expected_type': 'NU_PHAN_DIEN',
            'expected_pronoun_type': 'Nữ phản diện / Ma nữ'
        },
        {
            'character_name': '妖女',
            'expected_type': 'NU_PHAN_DIEN',
            'expected_pronoun_type': 'Nữ phản diện / Ma nữ'
        }
    ]
    
    print(f"📊 Chạy {len(test_cases)} test cases...")
    print()
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        character_name = test_case['character_name']
        expected_type = test_case['expected_type']
        expected_pronoun_type = test_case['expected_pronoun_type']
        
        print(f"Test case {i}: {character_name}")
        
        # Test get_character_type
        actual_type = checker.get_character_type(character_name)
        type_correct = actual_type == expected_type
        
        # Test map_character_type_to_pronoun_type
        actual_pronoun_type = checker.map_character_type_to_pronoun_type(actual_type)
        pronoun_type_correct = actual_pronoun_type == expected_pronoun_type
        
        # Test check_pronoun_compliance với character_name
        result = checker.check_pronoun_compliance(
            text=f"{character_name} đi tới, anh nhìn cô ấy và nói: 'Chào em!'",
            character_name=character_name,
            context="narration",
            relationship="Tác Giả Tường Thuật",
            emotion="neutral"
        )
        
        print(f"  Character Type: {actual_type} {'✅' if type_correct else '❌'} (expected: {expected_type})")
        print(f"  Pronoun Type: {actual_pronoun_type} {'✅' if pronoun_type_correct else '❌'} (expected: {expected_pronoun_type})")
        print(f"  Compliance: Valid={result['is_valid']}, Violations={result['total_violations']}")
        
        if type_correct and pronoun_type_correct:
            success_count += 1
            print("  Status: ✅ PASS")
        else:
            print("  Status: ❌ FAIL")
        
        print("  " + "-" * 50)
        print()
    
    # Summary
    success_rate = (success_count / total_count) * 100
    print("📊 KẾT QUẢ TỔNG HỢP:")
    print(f"  - Tổng test cases: {total_count}")
    print(f"  - Thành công: {success_count}")
    print(f"  - Thất bại: {total_count - success_count}")
    print(f"  - Tỷ lệ thành công: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("  🎉 Character mapping hoạt động tốt!")
    elif success_rate >= 60:
        print("  ⚠️ Character mapping cần cải thiện")
    else:
        print("  ❌ Character mapping cần sửa lỗi")
    
    print("\n✅ Hoàn thành test character mapping!")

if __name__ == "__main__":
    test_character_mapping()
