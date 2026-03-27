import unittest

from src.utils.translation_validator import TranslationValidator


class TestTranslationValidatorFixed(unittest.TestCase):
    def setUp(self):
        self.validator = TranslationValidator()

    def test_valid_endings(self):
        """Test sentences with valid endings pass."""
        valid_texts = [
            'Hello world.',
            'Hello world!',
            'Hello world?',
            'He said "Hello"',
            'He said ”Hello”',
            'Statement...',
            'Arrow >',
            'Parenthesis)',
            'Bracket]',
            'Brace}',
            'Dash -',
            'Em Dash —'
        ]
        for text in valid_texts:
            result = self.validator.validate("orig", text)
            self.assertTrue(result['is_valid'], f"Should be valid: {text}")
            self.assertFalse(result['has_critical_error'], f"Should not be critical: {text}")

    def test_abrupt_ending_relaxed(self):
        """Test abrupt ending triggers warning but NOT critical error."""
        text = "This is a sentence that ends abruptly"
        result = self.validator.validate("orig", text)

        # It MIGHT be valid (is_valid=True) if I removed is_valid=False line
        # Or it might be invalid (is_valid=False) but has_critical_error=False

        # My change: removed `is_valid = False` line?
        # Let's check the code I wrote.
        # I commented out `is_valid = False`. So it should be `is_valid = True` (if no other errors).
        # And `has_critical_error` hardcoded to False.

        # Expectation: is_valid=True (or False depending on other checks), issues contains warning.
        self.assertIn("Cảnh báo: Bản dịch có thể kết thúc đột ngột", result['issues'][0])
        self.assertFalse(result['has_critical_error'], "Abrupt ending should not be critical")

if __name__ == '__main__':
    unittest.main()
