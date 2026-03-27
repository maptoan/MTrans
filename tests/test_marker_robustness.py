# -*- coding: utf-8 -*-
import re
import unittest

import sys
import io

# Thiết lập encoding cho stdout để in ký tự Unicode trên Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class TestMarkerRobustness(unittest.TestCase):
    """
    Test logic dọn dẹp marker với các định dạng ID khác nhau (số, chuỗi, chuỗi có dấu hai chấm).
    """

    def test_marker_cleanup_regex(self):
        # Mẫu Regex hiện tại (dự kiến thất bại với ID alphanumeric hoặc compound)
        current_regex = r"\[CHUNK:\d+:(START|END)\]"
        
        # Mẫu Regex mới đề xuất
        improved_regex = r"\[CHUNK:.*?:(START|END)\]"

        test_cases = [
            # ID số (nguyên bản)
            ("[CHUNK:11:START] Nội dung [CHUNK:11:END]", "Nội dung"),
            
            # ID compound (lỗi do AI tự chế)
            ("[CHUNK:11:231:START] Nội dung paragraph [CHUNK:11:231:END]", "Nội dung paragraph"),
            
            # ID EPUB (Alphanumeric)
            ("[CHUNK:chapter06.xhtml-0042:START] Nội dung chapter [CHUNK:chapter06.xhtml-0042:END]", "Nội dung chapter"),
            
            # Kết hợp nhiều marker
            ("[CHUNK:1:START] [CHUNK:1:2:START] Mix [CHUNK:1:2:END] [CHUNK:1:END]", "Mix")
        ]

        for original, expected in test_cases:
            # Chạy thử với Regex mới
            cleaned_new = re.sub(improved_regex, "", original).strip()
            
            print(f"\n--- Testing: {original} ---")
            print(f"New Regex Result: '{cleaned_new}'")
            
            # Regex mới PHẢI pass tất cả các trường hợp ID phức tạp
            self.assertEqual(cleaned_new, expected, f"New regex failed for: {original}")

if __name__ == "__main__":
    unittest.main()
