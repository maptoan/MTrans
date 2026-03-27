#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script test toàn bộ API keys trong config.

Mục đích:
- Test tất cả API keys trong config.yaml
- Báo cáo chi tiết: valid/invalid, response time, error messages, account types
- Hỗ trợ cả new SDK và old SDK (theo config)
- Export kết quả ra file JSON và text report

Usage:
    python scripts/test_all_api_keys.py [--config config/config.yaml] [--output output_dir]
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.api_key_validator import APIKeyStatus, GeminiAPIChecker

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("APIKeyTester")


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Load config từ file YAML.
    
    Args:
        config_path: Đường dẫn đến file config
        
    Returns:
        Dictionary chứa config
        
    Raises:
        FileNotFoundError: Nếu file config không tồn tại
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def get_api_keys_from_config(config: Dict[str, Any]) -> List[str]:
    """
    Extract và filter API keys từ config.
    
    Args:
        config: Dictionary chứa config
        
    Returns:
        List các API keys hợp lệ (đã filter placeholder)
    """
    api_keys = config.get('api_keys', [])
    
    # Filter out empty keys và placeholder
    valid_keys = [
        key for key in api_keys 
        if key and isinstance(key, str) and "YOUR_GOOGLE_API_KEY" not in key
    ]
    
    return valid_keys


def format_report(
    results: List[APIKeyStatus],
    config: Dict[str, Any]
) -> str:
    """
    Format báo cáo text từ kết quả test.
    
    Args:
        results: List các APIKeyStatus objects
        config: Dictionary chứa config
        
    Returns:
        String chứa báo cáo đã format
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("BÁO CÁO TEST API KEYS")
    report_lines.append("=" * 80)
    report_lines.append(f"Thời gian test: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Tổng số keys: {len(results)}")
    report_lines.append("")
    
    # Phân loại keys
    valid_keys = [r for r in results if r.is_valid]
    invalid_keys = [r for r in results if not r.is_valid]
    
    # Phân loại theo account type
    free_tier = [r for r in results if r.account_type == "free_tier"]
    paid_tier_required = [r for r in results if r.account_type == "paid_tier_required"]
    restricted = [r for r in results if r.account_type == "restricted"]
    unknown = [r for r in results if r.account_type == "unknown"]
    
    # Summary
    report_lines.append("--- TỔNG KẾT ---")
    report_lines.append(f"✅ Hợp lệ: {len(valid_keys)}/{len(results)}")
    report_lines.append(f"❌ Không hợp lệ: {len(invalid_keys)}/{len(results)}")
    report_lines.append("")
    report_lines.append("--- PHÂN LOẠI THEO ACCOUNT TYPE ---")
    report_lines.append(f"🆓 Free tier: {len(free_tier)}")
    report_lines.append(f"💳 Cần billing: {len(paid_tier_required)}")
    report_lines.append(f"🚫 Bị giới hạn: {len(restricted)}")
    report_lines.append(f"❓ Không xác định: {len(unknown)}")
    report_lines.append("")
    
    # Chi tiết từng key
    report_lines.append("=" * 80)
    report_lines.append("CHI TIẾT TỪNG KEY")
    report_lines.append("=" * 80)
    
    # Sort: valid trước, sau đó invalid
    sorted_results = sorted(results, key=lambda r: (not r.is_valid, r.key_masked))
    
    for i, result in enumerate(sorted_results, 1):
        report_lines.append("")
        report_lines.append(f"--- Key {i}: {result.key_masked} ---")
        report_lines.append(f"Trạng thái: {'✅ HỢP LỆ' if result.is_valid else '❌ KHÔNG HỢP LỆ'}")
        report_lines.append(f"Account type: {result.account_type}")
        
        if result.is_valid:
            report_lines.append(f"Response time: {result.response_time:.3f}s")
        else:
            report_lines.append(f"Lỗi: {result.error_message}")
        
        report_lines.append(f"Tested at: {result.tested_at}")
    
    # Response time statistics (chỉ cho valid keys)
    if valid_keys:
        response_times = [r.response_time for r in valid_keys if r.response_time is not None]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            report_lines.append("")
            report_lines.append("=" * 80)
            report_lines.append("THỐNG KÊ RESPONSE TIME (chỉ keys hợp lệ)")
            report_lines.append("=" * 80)
            report_lines.append(f"Trung bình: {avg_time:.3f}s")
            report_lines.append(f"Tối thiểu: {min_time:.3f}s")
            report_lines.append(f"Tối đa: {max_time:.3f}s")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    
    return "\n".join(report_lines)


def export_json_report(
    results: List[APIKeyStatus],
    output_path: Path
) -> None:
    """
    Export kết quả ra file JSON.
    
    Args:
        results: List các APIKeyStatus objects
        output_path: Đường dẫn file output
    """
    # Convert to dict (hide full_key for security)
    json_data = {
        "tested_at": datetime.now().isoformat(),
        "total_keys": len(results),
        "valid_count": len([r for r in results if r.is_valid]),
        "invalid_count": len([r for r in results if not r.is_valid]),
        "results": [r.to_dict(hide_full_key=True) for r in results]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Đã export JSON report: {output_path}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test toàn bộ API keys trong config",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Đường dẫn đến file config (default: config/config.yaml)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='output',
        help='Thư mục output cho reports (default: output)'
    )
    parser.add_argument(
        '--use-new-sdk',
        action='store_true',
        help='Sử dụng new SDK (google-genai) thay vì old SDK'
    )
    
    args = parser.parse_args()
    
    try:
        # Load config
        logger.info(f"Đang load config từ: {args.config}")
        config = load_config(args.config)
        
        # Get API keys
        api_keys = get_api_keys_from_config(config)
        if not api_keys:
            logger.error("❌ Không tìm thấy API key nào trong config!")
            return 1
        
        logger.info(f"✅ Tìm thấy {len(api_keys)} API keys trong config")
        
        # Determine SDK to use
        use_new_sdk = args.use_new_sdk or config.get('translation', {}).get('use_new_sdk', False)
        logger.info(f"SDK mode: {'New SDK (google-genai)' if use_new_sdk else 'Old SDK (google-generativeai)'}")
        
        # Ensure output directory exists
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize checker
        logger.info("Đang khởi tạo API key checker...")
        checker = GeminiAPIChecker(
            api_keys=api_keys,
            config=config,
            use_new_sdk=use_new_sdk
        )
        
        # Run checks
        logger.info(f"Bắt đầu test {len(api_keys)} API keys...")
        logger.info("(Quá trình này có thể mất vài phút, vui lòng đợi...)")
        results = checker.run_checks()
        
        # Generate reports
        logger.info("Đang tạo báo cáo...")
        
        # Text report
        text_report = format_report(results, config)
        text_report_path = output_dir / f"api_keys_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(text_report_path, 'w', encoding='utf-8') as f:
            f.write(text_report)
        logger.info(f"✅ Đã lưu text report: {text_report_path}")
        
        # JSON report
        json_report_path = output_dir / f"api_keys_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_json_report(results, json_report_path)
        
        # Print summary to console
        print("\n" + "=" * 80)
        print("TỔNG KẾT")
        print("=" * 80)
        valid_count = len([r for r in results if r.is_valid])
        invalid_count = len([r for r in results if not r.is_valid])
        print(f"✅ Hợp lệ: {valid_count}/{len(results)}")
        print(f"❌ Không hợp lệ: {invalid_count}/{len(results)}")
        print(f"\n📄 Xem chi tiết trong: {text_report_path}")
        print(f"📄 JSON report: {json_report_path}")
        print("=" * 80)
        
        return 0 if invalid_count == 0 else 1
        
    except FileNotFoundError as e:
        logger.error(f"❌ Lỗi: {e}")
        return 1
    except Exception as e:
        logger.exception(f"❌ Lỗi không mong đợi: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
