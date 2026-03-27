#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script test các cải tiến chunk validation
"""

import os
import sys

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from translation.chunk_size_validator import ChunkSizeValidator
from utils.logger import setup_main_logger

logger = setup_main_logger("ChunkValidationTest")

def test_punctuation_check():
    """Test kiểm tra dấu câu - chỉ câu cuối"""
    
    print("🧪 Testing Punctuation Check (Câu cuối only)...")
    print("=" * 60)
    
    # Mock config
    config = {
        'translation': {
            'enable_chunk_size_validation': True,
            'chunk_size_validation': {
                'enable_punctuation_check': True,
                'size_deviation_threshold': 0.15,
                'min_absolute_size': 300
            }
        }
    }
    
    validator = ChunkSizeValidator(config)
    
    # Test cases
    test_cases = [
        {
            'name': 'Chunk kết thúc đúng dấu câu',
            'text': 'Đây là câu đầu tiên. Đây là câu thứ hai! Đây là câu cuối cùng?',
            'expected_issues': 0
        },
        {
            'name': 'Chunk kết thúc bằng dấu chấm',
            'text': 'Đây là câu đầu tiên. Đây là câu thứ hai. Đây là câu cuối cùng.',
            'expected_issues': 0
        },
        {
            'name': 'Chunk kết thúc bằng dấu chấm than',
            'text': 'Đây là câu đầu tiên. Đây là câu thứ hai! Đây là câu cuối cùng!',
            'expected_issues': 0
        },
        {
            'name': 'Chunk kết thúc bằng dấu hỏi',
            'text': 'Đây là câu đầu tiên. Đây là câu thứ hai? Đây là câu cuối cùng?',
            'expected_issues': 0
        },
        {
            'name': 'Chunk KHÔNG kết thúc bằng dấu câu',
            'text': 'Đây là câu đầu tiên. Đây là câu thứ hai. Đây là câu cuối cùng',
            'expected_issues': 1
        },
        {
            'name': 'Chunk kết thúc bằng dấu phẩy (sai)',
            'text': 'Đây là câu đầu tiên. Đây là câu thứ hai, Đây là câu cuối cùng,',
            'expected_issues': 1
        },
        {
            'name': 'Chunk có câu cuối không trọn vẹn',
            'text': 'Đây là câu đầu tiên. Đây là câu thứ hai. Và đây là câu',
            'expected_issues': 1
        },
        {
            'name': 'Chunk bắt đầu bằng chữ thường',
            'text': 'đây là câu đầu tiên. Đây là câu thứ hai. Đây là câu cuối cùng.',
            'expected_issues': 1
        },
        {
            'name': 'Chunk có dấu ngoặc kép',
            'text': 'Anh nói: "Tôi sẽ đi." Cô trả lời: "Được rồi." Họ chia tay.',
            'expected_issues': 0
        }
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {test_case['name']}")
        print(f"Text: {test_case['text'][:50]}...")
        
        issues = validator._check_punctuation_issues(test_case['text'])
        actual_issues = len(issues)
        expected_issues = test_case['expected_issues']
        
        print(f"Expected issues: {expected_issues}")
        print(f"Actual issues: {actual_issues}")
        print(f"Issues: {issues}")
        
        if actual_issues == expected_issues:
            print("✅ PASS")
            success_count += 1
        else:
            print("❌ FAIL")
        
        print("-" * 50)
    
    success_rate = (success_count / total_count) * 100
    print("\n📊 KẾT QUẢ PUNCTUATION CHECK:")
    print(f"  - Tổng test cases: {total_count}")
    print(f"  - Thành công: {success_count}")
    print(f"  - Thất bại: {total_count - success_count}")
    print(f"  - Tỷ lệ thành công: {success_rate:.1f}%")
    
    return success_rate >= 80

def test_size_validation():
    """Test kiểm tra kích thước chunk"""
    
    print("\n🧪 Testing Size Validation...")
    print("=" * 60)
    
    # Mock config
    config = {
        'translation': {
            'enable_chunk_size_validation': True,
            'chunk_size_validation': {
                'enable_size_check': True,
                'size_deviation_threshold': 0.15,
                'min_absolute_size': 300,
                'size_check_method': 'statistical'
            }
        }
    }
    
    validator = ChunkSizeValidator(config)
    
    # Thêm một số chunk mẫu để có dữ liệu thống kê
    sample_chunks = [
        {'chunk_id': 1, 'original_size': 1000, 'translated_size': 950, 'size_ratio': 0.95},
        {'chunk_id': 2, 'original_size': 1000, 'translated_size': 980, 'size_ratio': 0.98},
        {'chunk_id': 3, 'original_size': 1000, 'translated_size': 920, 'size_ratio': 0.92},
        {'chunk_id': 4, 'original_size': 1000, 'translated_size': 1000, 'size_ratio': 1.0},
        {'chunk_id': 5, 'original_size': 1000, 'translated_size': 1050, 'size_ratio': 1.05}
    ]
    
    for chunk in sample_chunks:
        validator.add_chunk_size(chunk['chunk_id'], chunk['original_size'], chunk['translated_size'])
    
    print(f"Average size: {validator.average_size:.0f}")
    print(f"Std deviation: {validator.std_deviation:.0f}")
    
    # Test cases
    test_cases = [
        {
            'name': 'Chunk bình thường',
            'original_size': 1000,
            'translated_size': 950,
            'expected_valid': True
        },
        {
            'name': 'Chunk quá nhỏ (20% trung bình)',
            'original_size': 1000,
            'translated_size': int(validator.average_size * 0.2),
            'expected_valid': False
        },
        {
            'name': 'Chunk quá lớn (400% trung bình)',
            'original_size': 1000,
            'translated_size': int(validator.average_size * 4.0),
            'expected_valid': False
        },
        {
            'name': 'Chunk nhỏ hơn min_absolute_size',
            'original_size': 1000,
            'translated_size': 250,
            'expected_valid': False
        },
        {
            'name': 'Chunk cuối cùng nhỏ (được phép)',
            'original_size': 1000,
            'translated_size': int(validator.average_size * 0.6),
            'expected_valid': True,
            'is_last_chunk': True
        }
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {test_case['name']}")
        print(f"Original: {test_case['original_size']}, Translated: {test_case['translated_size']}")
        
        result = validator.validate_chunk_size(
            chunk_id=100 + i,
            original_size=test_case['original_size'],
            translated_size=test_case['translated_size'],
            translated_text="Test text.",
            is_last_chunk=test_case.get('is_last_chunk', False)
        )
        
        actual_valid = result['is_valid']
        expected_valid = test_case['expected_valid']
        
        print(f"Expected valid: {expected_valid}")
        print(f"Actual valid: {actual_valid}")
        print(f"Reason: {result['reason']}")
        
        if actual_valid == expected_valid:
            print("✅ PASS")
            success_count += 1
        else:
            print("❌ FAIL")
        
        print("-" * 50)
    
    success_rate = (success_count / total_count) * 100
    print("\n📊 KẾT QUẢ SIZE VALIDATION:")
    print(f"  - Tổng test cases: {total_count}")
    print(f"  - Thành công: {success_count}")
    print(f"  - Thất bại: {total_count - success_count}")
    print(f"  - Tỷ lệ thành công: {success_rate:.1f}%")
    
    return success_rate >= 80

def main():
    """Hàm main"""
    print("🔧 Testing Chunk Validation Improvements...")
    print("=" * 60)
    
    # Test punctuation check
    punctuation_success = test_punctuation_check()
    
    # Test size validation
    size_success = test_size_validation()
    
    # Tổng kết
    print("\n🎯 TỔNG KẾT:")
    print(f"  - Punctuation Check: {'✅ PASS' if punctuation_success else '❌ FAIL'}")
    print(f"  - Size Validation: {'✅ PASS' if size_success else '❌ FAIL'}")
    
    if punctuation_success and size_success:
        print("🎉 Tất cả tests đều PASS! Cải tiến hoạt động tốt.")
    else:
        print("⚠️ Một số tests FAIL. Cần kiểm tra lại logic.")
    
    print("\n✅ Hoàn thành test chunk validation improvements!")

if __name__ == "__main__":
    main()
