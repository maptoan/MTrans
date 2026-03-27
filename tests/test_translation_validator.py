
import unittest

from src.utils.translation_validator import TranslationValidator


class TestTranslationValidator(unittest.TestCase):
    def setUp(self):
        self.validator = TranslationValidator()

    def test_sentence_integrity_valid(self):
        """Test câu kết thúc hợp lệ."""
        valid_sentences = [
            "Đây là một câu hoàn chỉnh.",
            "Câu hỏi này có đúng không?",
            "Tuyệt vời!",
            "Anh ấy nói: \"Xin chào.\"",
            "Kết thúc bằng ngoặc”",
            "Lửng lơ..." # Dấu ba chấm là hợp lệ
        ]
        for s in valid_sentences:
            with self.subTest(sentence=s):
                self.assertTrue(self.validator._check_sentence_integrity(s))

    def test_sentence_integrity_invalid(self):
        """Test câu bị cắt giữa chừng."""
        invalid_sentences = [
            "Đây là một câu bị cắt",
            "Không có dấu câu",
            "Anh ấy nói: \"Chưa đóng ngoặc",
            "Dấu phẩy cuối câu,",
        ]
        for s in invalid_sentences:
            with self.subTest(sentence=s):
                self.assertFalse(self.validator._check_sentence_integrity(s))

    def test_quote_balance_valid(self):
        """Test số lượng quote tương đồng."""
        original = 'Anh ấy nói: "Xin chào". Cô ấy đáp: "Chào anh".'
        translated = 'He said: "Hello". She replied: "Hi".'
        issues = self.validator._check_quote_balance(original, translated)
        self.assertEqual(len(issues), 0)

    def test_quote_balance_mismatch(self):
        """Test số lượng quote lệch nhiều."""
        original = 'A nói: "1". B nói: "2". C nói: "3".' # 6 quotes (3 pairs)
        translated = 'A, B và C đều nói chuyện.' # 0 quotes

        # 6 vs 0 -> 100% diff -> > 20% threshold
        issues = self.validator._check_quote_balance(original, translated)
        self.assertTrue(len(issues) > 0)
        self.assertIn("Cảnh báo chênh lệch hội thoại", issues[0])

    def test_cjk_quote_handling(self):
        """Test xử lý CJK quotes."""
        original = '「Xin chào」' # 2 quotes
        translated = '"Xin chào"' # 2 quotes
        issues = self.validator._check_quote_balance(original, translated)
        self.assertEqual(len(issues), 0)

if __name__ == '__main__':
    unittest.main()
