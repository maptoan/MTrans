import os
import sys
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.translation.refiners import TranslationRefiner


class TestAutoFix(unittest.TestCase):
    def setUp(self):
        # Mock config and relation_manager needed for TranslationRefiner
        self.config = {"translation": {}}
        self.relation_manager = MagicMock()
        self.refiner = TranslationRefiner(self.config, self.relation_manager)

    def test_auto_fix_pinyin(self):
        text = "Xiao Yaofeng là một nơi đẹp. Cheng Shui Ruo đang đứng đó."
        terms = [
            {"Original_Term_Pinyin": "Xiao Yaofeng", "Translated_Term_VI": "Tiêu Dao Phong"},
            {"Original_Term_Pinyin": "Cheng Shui Ruo", "Translated_Term_VI": "Trình Thủy Nhược"},
        ]

        # Use the correct method from refiner
        fixed, count = self.refiner.auto_fix_glossary(text, terms)

        self.assertEqual(count, 2)
        self.assertIn("Tiêu Dao Phong", fixed)
        self.assertIn("Trình Thủy Nhược", fixed)
        self.assertNotIn("Xiao Yaofeng", fixed)

    def test_auto_fix_cn(self):
        text = "Tại 逍遥峰, có một người tên là 程水若."
        terms = [
            {"Original_Term_CN": "逍遥峰", "Translated_Term_VI": "Tiêu Dao Phong"},
            {"Original_Term_CN": "程水若", "Translated_Term_VI": "Trình Thủy Nhược"},
        ]

        fixed, count = self.refiner.auto_fix_glossary(text, terms)

        self.assertEqual(count, 2)
        self.assertIn("Tiêu Dao Phong", fixed)
        self.assertIn("Trình Thủy Nhược", fixed)
        self.assertNotIn("逍遥峰", fixed)

    def test_mixed_and_case_insensitive(self):
        text = "xiao yaofeng rất cao. 逍遥峰 rất thấp."
        terms = [
            {
                "Original_Term_Pinyin": "Xiao Yaofeng",
                "Original_Term_CN": "逍遥峰",
                "Translated_Term_VI": "Tiêu Dao Phong",
            }
        ]

        fixed, count = self.refiner.auto_fix_glossary(text, terms)

        self.assertEqual(count, 2)
        self.assertEqual(fixed, "Tiêu Dao Phong rất cao. Tiêu Dao Phong rất thấp.")


if __name__ == "__main__":
    unittest.main()
