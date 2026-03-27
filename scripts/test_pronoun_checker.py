#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script test PronounComplianceChecker với hệ thống mới
"""

import os
import sys

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.utils.logger import setup_main_logger
from translation.pronoun_compliance_checker import PronounComplianceChecker

logger = setup_main_logger("PronounCheckerTest")

def test_pronoun_checker():
    """Test PronounComplianceChecker với hệ thống mới"""
    
    print("🧪 Testing PronounComplianceChecker với hệ thống mới...")
    print("=" * 60)
    
    # Khởi tạo checker
    checker = PronounComplianceChecker()
    
    # Test cases
    test_cases = [
        {
            'text': 'Thôi Tiểu Huyền đi tới, anh nhìn cô ấy và nói: "Chào em!"',
            'character_type': 'Nam chính (Main Character)',
            'context': 'narration',
            'relationship': 'Tác Giả Tường Thuật',
            'emotion': 'neutral',
            'expected_pronouns': ['hắn', 'chàng', 'gã']
        },
        {
            'text': 'Lâm sư huynh nhìn sư đệ và nói: "Hắn đã tiến bộ rất nhiều!"',
            'character_type': 'Nam chính (Main Character)',
            'context': 'dialogue',
            'relationship': 'Sư huynh / Sư tỷ (gọi Nam chính)',
            'emotion': 'respectful',
            'expected_pronouns': ['hắn', 'sư đệ']
        },
        {
            'text': 'Nàng nhìn chàng với ánh mắt đầy yêu thương.',
            'character_type': 'Nữ chính / Hậu cung',
            'context': 'narration',
            'relationship': 'Tác Giả Tường Thuật',
            'emotion': 'affectionate',
            'expected_pronouns': ['nàng', 'cô', 'thiếu nữ']
        },
        {
            'text': 'Tên ma đầu đó thật đáng ghét!',
            'character_type': 'Nam phản diện / Tà tu',
            'context': 'narration',
            'relationship': 'Tác Giả Tường Thuật',
            'emotion': 'contemptuous',
            'expected_pronouns': ['hắn', 'gã', 'y']
        }
    ]
    
    print(f"📊 Chạy {len(test_cases)} test cases...")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test case {i}:")
        print(f"  Text: {test_case['text']}")
        print(f"  Character Type: {test_case['character_type']}")
        print(f"  Context: {test_case['context']}")
        print(f"  Relationship: {test_case['relationship']}")
        print(f"  Emotion: {test_case['emotion']}")
        
        # Kiểm tra compliance
        result = checker.check_pronoun_compliance(
            text=test_case['text'],
            character_type=test_case['character_type'],
            context=test_case['context'],
            relationship=test_case['relationship'],
            emotion=test_case['emotion']
        )
        
        print(f"  Result: {result}")
        print(f"  Is Valid: {result['is_valid']}")
        print(f"  Violations: {result['total_violations']}")
        
        if result['violations']:
            print("  Violations:")
            for violation in result['violations']:
                print(f"    - {violation}")
        
        # Lấy suggestions
        suggestions = checker.get_pronoun_suggestions(
            character_type=test_case['character_type'],
            context=test_case['context'],
            relationship=test_case['relationship'],
            emotion=test_case['emotion']
        )
        
        print(f"  Suggestions: {suggestions}")
        print("  " + "-" * 50)
        print()
    
    print("✅ Hoàn thành test PronounComplianceChecker!")

if __name__ == "__main__":
    test_pronoun_checker()
