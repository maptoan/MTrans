#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script test thuật toán chunk validation đã tối ưu hóa
"""

import os
import sys
import time

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from translation.chunk_size_validator import ChunkSizeValidator
from utils.logger import setup_main_logger

logger = setup_main_logger("OptimizedChunkValidationTest")

def test_performance():
    """Test performance của thuật toán tối ưu hóa"""
    
    print("🚀 Testing Performance của thuật toán tối ưu hóa...")
    print("=" * 60)
    
    # Mock config
    config = {
        'translation': {
            'enable_chunk_size_validation': True,
            'chunk_size_validation': {
                'enable_size_check': True,
                'size_deviation_threshold': 0.15,
                'min_absolute_size': 300,
                'max_retries_for_size': 3,
                'size_check_method': 'statistical',
                'enable_punctuation_check': True,
                'last_chunk_relaxed_threshold': 1.2
            }
        }
    }
    
    validator = ChunkSizeValidator(config)
    
    # Thêm dữ liệu mẫu để có thống kê
    sample_chunks = [
        {'chunk_id': i, 'original_size': 1000, 'translated_size': 950 + i*10, 'size_ratio': 0.95 + i*0.01}
        for i in range(1, 21)
    ]
    
    for chunk in sample_chunks:
        validator.add_chunk_size(chunk['chunk_id'], chunk['original_size'], chunk['translated_size'])
    
    print(f"Average size: {validator.average_size:.0f}")
    print(f"Std deviation: {validator.std_deviation:.0f}")
    
    # Test cases với timing
    test_cases = [
        {
            'name': 'Chunk bình thường',
            'original_size': 1000,
            'translated_size': 950,
            'text': 'Đây là câu bình thường. Kết thúc đúng dấu câu.',
            'expected_valid': True
        },
        {
            'name': 'Chunk quá nhỏ',
            'original_size': 1000,
            'translated_size': 200,
            'text': 'Câu ngắn.',
            'expected_valid': False
        },
        {
            'name': 'Chunk quá lớn',
            'original_size': 1000,
            'translated_size': 3000,
            'text': 'Đây là câu rất dài với nhiều từ và kết thúc đúng dấu câu.',
            'expected_valid': False
        },
        {
            'name': 'Chunk có câu cuối không trọn vẹn',
            'original_size': 1000,
            'translated_size': 950,
            'text': 'Đây là câu bình thường. Và đây là câu',
            'expected_valid': False
        },
        {
            'name': 'Chunk không kết thúc bằng dấu câu',
            'original_size': 1000,
            'translated_size': 950,
            'text': 'Đây là câu bình thường nhưng không kết thúc đúng',
            'expected_valid': False
        },
        {
            'name': 'Chunk cuối cùng nhỏ (được phép)',
            'original_size': 1000,
            'translated_size': 600,
            'text': 'Đây là chunk cuối cùng.',
            'expected_valid': True,
            'is_last_chunk': True
        }
    ]
    
    # Test performance
    start_time = time.time()
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest case {i}: {test_case['name']}")
        
        case_start = time.time()
        result = validator.validate_chunk_size(
            chunk_id=100 + i,
            original_size=test_case['original_size'],
            translated_size=test_case['translated_size'],
            translated_text=test_case['text'],
            is_last_chunk=test_case.get('is_last_chunk', False)
        )
        case_time = time.time() - case_start
        
        actual_valid = result['is_valid']
        expected_valid = test_case['expected_valid']
        
        print(f"  Expected: {expected_valid}, Actual: {actual_valid}")
        print(f"  Reason: {result['reason']}")
        print(f"  Time: {case_time*1000:.2f}ms")
        
        if actual_valid == expected_valid:
            print("  ✅ PASS")
            success_count += 1
        else:
            print("  ❌ FAIL")
        
        print("-" * 50)
    
    total_time = time.time() - start_time
    success_rate = (success_count / total_count) * 100
    
    print("\n📊 KẾT QUẢ PERFORMANCE:")
    print(f"  - Tổng test cases: {total_count}")
    print(f"  - Thành công: {success_count}")
    print(f"  - Thất bại: {total_count - success_count}")
    print(f"  - Tỷ lệ thành công: {success_rate:.1f}%")
    print(f"  - Tổng thời gian: {total_time:.3f}s")
    print(f"  - Thời gian trung bình: {total_time/total_count*1000:.2f}ms")
    
    return success_rate >= 80

def test_edge_cases():
    """Test các trường hợp edge case"""
    
    print("\n🧪 Testing Edge Cases...")
    print("=" * 60)
    
    config = {
        'translation': {
            'enable_chunk_size_validation': True,
            'chunk_size_validation': {
                'enable_size_check': True,
                'size_deviation_threshold': 0.15,
                'min_absolute_size': 300,
                'size_check_method': 'statistical',
                'enable_punctuation_check': True
            }
        }
    }
    
    validator = ChunkSizeValidator(config)
    
    # Thêm dữ liệu mẫu
    for i in range(1, 11):
        validator.add_chunk_size(i, 1000, 950 + i*5)
    
    edge_cases = [
        {
            'name': 'Text rỗng',
            'text': '',
            'expected_issues': 0
        },
        {
            'name': 'Text chỉ có khoảng trắng',
            'text': '   \n\t   ',
            'expected_issues': 0
        },
        {
            'name': 'Text rất ngắn',
            'text': 'A',
            'expected_issues': 1
        },
        {
            'name': 'Text có dấu ngoặc kép phức tạp',
            'text': 'Anh nói: "Tôi sẽ đi." Cô trả lời: "Được rồi." Họ chia tay.',
            'expected_issues': 0
        },
        {
            'name': 'Text có số với dấu chấm',
            'text': 'Giá là 1.000.000 VND. Đây là câu bình thường.',
            'expected_issues': 0
        },
        {
            'name': 'Text có dấu chấm lửng',
            'text': 'Đây là câu có dấu chấm lửng... Kết thúc đúng.',
            'expected_issues': 0
        }
    ]
    
    success_count = 0
    total_count = len(edge_cases)
    
    for i, test_case in enumerate(edge_cases, 1):
        print(f"\nEdge case {i}: {test_case['name']}")
        print(f"Text: '{test_case['text']}'")
        
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
    print("\n📊 KẾT QUẢ EDGE CASES:")
    print(f"  - Tổng test cases: {total_count}")
    print(f"  - Thành công: {success_count}")
    print(f"  - Thất bại: {total_count - success_count}")
    print(f"  - Tỷ lệ thành công: {success_rate:.1f}%")
    
    return success_rate >= 80

def test_different_methods():
    """Test các phương pháp kiểm tra khác nhau"""
    
    print("\n🔬 Testing Different Methods...")
    print("=" * 60)
    
    methods = ['statistical', 'percentile', 'fixed_ratio']
    success_count = 0
    total_count = 0
    
    for method in methods:
        print(f"\nTesting method: {method}")
        
        config = {
            'translation': {
                'enable_chunk_size_validation': True,
                'chunk_size_validation': {
                    'enable_size_check': True,
                    'size_deviation_threshold': 0.15,
                    'min_absolute_size': 300,
                    'size_check_method': method,
                    'enable_punctuation_check': True
                }
            }
        }
        
        validator = ChunkSizeValidator(config)
        
        # Thêm dữ liệu mẫu
        for i in range(1, 15):
            validator.add_chunk_size(i, 1000, 950 + i*10)
        
        # Test cases
        test_cases = [
            {'size': 950, 'expected': True, 'name': 'Normal'},
            {'size': 200, 'expected': False, 'name': 'Too small'},
            {'size': 2000, 'expected': False, 'name': 'Too large'}
        ]
        
        method_success = 0
        for test_case in test_cases:
            result = validator.validate_chunk_size(
                chunk_id=100,
                original_size=1000,
                translated_size=test_case['size'],
                translated_text="Test text."
            )
            
            actual = result['is_valid']
            expected = test_case['expected']
            
            if actual == expected:
                method_success += 1
                print(f"  ✅ {test_case['name']}: PASS")
            else:
                print(f"  ❌ {test_case['name']}: FAIL (expected {expected}, got {actual})")
            
            total_count += 1
        
        method_rate = (method_success / len(test_cases)) * 100
        print(f"  Method {method} success rate: {method_rate:.1f}%")
        
        if method_rate >= 80:
            success_count += 1
    
    overall_success_rate = (success_count / len(methods)) * 100
    print("\n📊 KẾT QUẢ METHODS:")
    print(f"  - Methods tested: {len(methods)}")
    print(f"  - Methods passed: {success_count}")
    print(f"  - Overall success rate: {overall_success_rate:.1f}%")
    
    return overall_success_rate >= 80

def main():
    """Hàm main"""
    print("🔧 Testing Optimized Chunk Validation Algorithm...")
    print("=" * 60)
    
    # Test performance
    performance_success = test_performance()
    
    # Test edge cases
    edge_success = test_edge_cases()
    
    # Test different methods
    methods_success = test_different_methods()
    
    # Tổng kết
    print("\n🎯 TỔNG KẾT:")
    print(f"  - Performance Test: {'✅ PASS' if performance_success else '❌ FAIL'}")
    print(f"  - Edge Cases Test: {'✅ PASS' if edge_success else '❌ FAIL'}")
    print(f"  - Methods Test: {'✅ PASS' if methods_success else '❌ FAIL'}")
    
    if performance_success and edge_success and methods_success:
        print("🎉 Tất cả tests đều PASS! Thuật toán tối ưu hóa hoạt động tốt.")
    else:
        print("⚠️ Một số tests FAIL. Cần kiểm tra lại logic.")
    
    print("\n✅ Hoàn thành test optimized chunk validation!")

if __name__ == "__main__":
    main()
