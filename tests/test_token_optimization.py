
import os
import sys
import unittest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.token_optimizer import TokenOptimizer


class TestTokenOptimizer(unittest.TestCase):

    def test_minify_text(self):
        text = "  Hello   World  \n\n  Line 2  "
        # Implementation preserves 1 empty line for paragraph structure
        expected = "Hello World\n\nLine 2"
        self.assertEqual(TokenOptimizer.minify_text(text), expected)

    def test_minify_context_chunk(self):
        text = "**Bold** text.\n\nParagraph 2."
        # Expect bold removed, newlines preserved but single
        expected = "Bold text.\nParagraph 2."
        self.assertEqual(TokenOptimizer.minify_context_chunk(text), expected)

    def test_compact_list(self):
        items = ["A", "B", " C "]
        expected = "A | B | C"
        self.assertEqual(TokenOptimizer.compact_list(items), expected)

    def test_compact_dict(self):
        data = {"Name": "Gemini", "Type": " AI "}
        expected = "Name:Gemini; Type:AI"
        self.assertEqual(TokenOptimizer.compact_dict(data), expected)

    def test_compact_glossary_terms(self):
        terms = [
            {'Original_Term_CN': '剑', 'Original_Term_Pinyin': 'jian', 'Translated_Term_VI': 'Kiếm', 'Notes': 'Weapon'},
            {'Original_Term_CN': '刀', 'Translated_Term_VI': 'Đao'}
        ]
        # Format: Original(Pinyin)->Translated[Notes]; ...
        expected = "剑(jian)->Kiếm[Weapon]; 刀->Đao"
        self.assertEqual(TokenOptimizer.compact_glossary_terms(terms), expected)

if __name__ == '__main__':
    unittest.main()
