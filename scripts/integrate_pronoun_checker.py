#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tích hợp PronounComplianceChecker vào hệ thống chính
"""

import os
import shutil
import sys
from pathlib import Path

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def integrate_pronoun_checker():
    """Tích hợp PronounComplianceChecker vào compliance_checker.py"""
    
    # Đường dẫn files
    pronoun_checker_file = Path("src/translation/pronoun_compliance_checker.py")
    compliance_checker_file = Path("src/translation/compliance_checker.py")
    
    # Kiểm tra files tồn tại
    if not pronoun_checker_file.exists():
        print("❌ Không tìm thấy pronoun_compliance_checker.py")
        return False
    
    if not compliance_checker_file.exists():
        print("❌ Không tìm thấy compliance_checker.py")
        return False
    
    # Backup file gốc
    backup_file = compliance_checker_file.with_suffix('.py.backup')
    shutil.copy2(compliance_checker_file, backup_file)
    print(f"✅ Đã backup file gốc: {backup_file}")
    
    # Đọc file compliance_checker.py
    with open(compliance_checker_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Thêm import PronounComplianceChecker
    if "from src.translation.pronoun_compliance_checker import PronounComplianceChecker" not in content:
        # Tìm vị trí thêm import
        import_section = content.find("from src.translation.compliance_checker import ComplianceChecker")
        if import_section == -1:
            # Tìm vị trí khác
            import_section = content.find("import logging")
        
        if import_section != -1:
            # Thêm import
            new_import = "from src.translation.pronoun_compliance_checker import PronounComplianceChecker\n"
            content = content[:import_section] + new_import + content[import_section:]
            print("✅ Đã thêm import PronounComplianceChecker")
    
    # Thêm PronounComplianceChecker vào __init__
    if "self.pronoun_checker = PronounComplianceChecker()" not in content:
        # Tìm vị trí trong __init__
        init_section = content.find("self.compliance_checker = ComplianceChecker")
        if init_section != -1:
            # Thêm sau dòng compliance_checker
            new_line = "        self.pronoun_checker = PronounComplianceChecker()\n"
            content = content[:init_section] + content[init_section:].replace(
                "self.compliance_checker = ComplianceChecker", 
                "self.compliance_checker = ComplianceChecker" + "\n" + new_line
            )
            print("✅ Đã thêm PronounComplianceChecker vào __init__")
    
    # Thêm kiểm tra đại từ nhân xưng vào check_compliance
    if "pronoun_result = self.pronoun_checker.check_pronoun_compliance" not in content:
        # Tìm vị trí trong check_compliance
        check_section = content.find("if self.enable_glossary_check:")
        if check_section != -1:
            # Thêm trước phần kiểm tra glossary
            new_check = """        # Kiểm tra đại từ nhân xưng
        if hasattr(self, 'pronoun_checker'):
            pronoun_result = self.pronoun_checker.check_pronoun_compliance(
                translated_text, character_name, context, relationship, formality, emotion, scene
            )
            if not pronoun_result['is_valid']:
                all_violations.extend([{
                    'type': 'pronoun_violation',
                    'pronoun_cn': v.get('pronoun_cn', ''),
                    'current_vn': v.get('current_vn', ''),
                    'correct_vn': v.get('correct_vn', ''),
                    'character': v.get('character', ''),
                    'context': v.get('context', ''),
                    'severity': v.get('severity', 'medium')
                } for v in pronoun_result.get('violations', [])])
        
        """
            content = content[:check_section] + new_check + content[check_section:]
            print("✅ Đã thêm kiểm tra đại từ nhân xưng vào check_compliance")
    
    # Ghi file đã cập nhật
    with open(compliance_checker_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Đã tích hợp PronounComplianceChecker vào compliance_checker.py")
    return True

def create_pronoun_test_script():
    """Tạo script test PronounComplianceChecker"""
    
    test_script = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

\"\"\"
Script test PronounComplianceChecker
\"\"\"

import sys
import os

# Thêm src vào path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from translation.pronoun_compliance_checker import PronounComplianceChecker

def test_pronoun_checker():
    \"\"\"Test PronounComplianceChecker\"\"\"
    
    # Khởi tạo checker
    checker = PronounComplianceChecker()
    
    # Test cases
    test_cases = [
        {
            'text': '他走过来，看着她说："你好吗？"',
            'character_name': '崔小玄',
            'context': 'narration',
            'relationship': 'unknown',
            'formality': 'formal',
            'emotion': 'neutral',
            'scene': 'general'
        },
        {
            'text': '那厮竟然敢如此无礼！',
            'character_name': '方少麟',
            'context': 'dialogue',
            'relationship': 'rival',
            'formality': 'contempt',
            'emotion': 'angry',
            'scene': 'combat'
        }
    ]
    
    print("🧪 Testing PronounComplianceChecker...")
    print("=" * 50)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\\nTest case {i}:")
        print(f"Text: {case['text']}")
        print(f"Character: {case['character_name']}")
        print(f"Context: {case['context']}")
        
        result = checker.check_pronoun_compliance(
            case['text'], case['character_name'], case['context'],
            case['relationship'], case['formality'], case['emotion'], case['scene']
        )
        
        print(f"Result: {result}")
        print("-" * 30)

if __name__ == "__main__":
    test_pronoun_checker()
"""
    
    with open("test_pronoun_checker.py", 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print("✅ Đã tạo test_pronoun_checker.py")

def main():
    """Hàm main"""
    print("🔧 Tích hợp PronounComplianceChecker vào hệ thống...")
    print("=" * 60)
    
    # Tích hợp PronounComplianceChecker
    if integrate_pronoun_checker():
        print("✅ Tích hợp thành công!")
    else:
        print("❌ Tích hợp thất bại!")
        return
    
    # Tạo script test
    create_pronoun_test_script()
    
    print("\\n🎯 Hướng dẫn sử dụng:")
    print("1. Chạy test: python test_pronoun_checker.py")
    print("2. Kiểm tra metadata: Get-Content data\\metadata\\pronoun_metadata.csv -Encoding UTF8 -Head 10")
    print("3. Sử dụng trong dịch thuật: PronounComplianceChecker sẽ tự động kiểm tra đại từ nhân xưng")
    
    print("\\n✅ Hoàn thành tích hợp!")

if __name__ == "__main__":
    main()
