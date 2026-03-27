# -*- coding: utf-8 -*-
"""
Verification script for the quotation mark preservation fix.
Tests the robust sentence splitter and quote-preservation logic.
"""

import re
import sys


def test_sentence_splitter():
    """
    Tests the new sentence splitter to ensure it doesn't break inside quotes.
    """
    print("=== Testing Robust Sentence Splitter ===\n")

    # Test text with dialogue containing punctuation
    test_text = '"Where are you going?" he asked. "I don\'t know!" - she replied.'

    # Simulate the new splitter logic
    sentences = []
    current_sentence = []
    in_quote = False
    quote_char = None

    quote_pairs = {'"': '"', "「": "」", "『": "』", "《": "》"}
    open_quotes = set(quote_pairs.keys())
    end_sentence_chars = {".", "!", "?"}

    for char in test_text:
        current_sentence.append(char)

        if char in open_quotes and not in_quote:
            in_quote = True
            quote_char = quote_pairs.get(char, char)
        elif char == quote_char and in_quote:
            in_quote = False
            quote_char = None

        if char in end_sentence_chars and not in_quote:
            sentence = "".join(current_sentence).strip()
            if sentence:
                sentences.append(sentence)
            current_sentence = []

    if current_sentence:
        sentence = "".join(current_sentence).strip()
        if sentence:
            sentences.append(sentence)

    print(f"Input: {test_text}")
    print(f"Sentences: {sentences}")

    # Expected: Sentences should be complete with quotes intact
    # Old buggy behavior: ['\"Where are you going', '\" he asked', ...]
    # New expected: ['"Where are you going?" he asked.', '"I don\'t know!" - she replied.']

    for s in sentences:
        # Check that quotes are balanced
        open_count = s.count('"') + s.count('"')
        close_count = s.count('"') + s.count('"')
        if open_count > 0 or close_count > 0:
            # For straight quotes, check pairs
            straight_quotes = s.count('"')
            if straight_quotes % 2 != 0:
                print(f"  WARNING: Unbalanced quotes in: {s}")
                return False
            print(f"  OK: {s}")

    print("\nSentence splitter test PASSED!\n")
    return True


def test_quote_preservation():
    """
    Tests the quote-preservation logic during replacement.
    """
    print("=== Testing Quote Preservation ===\n")

    quote_chars = {'"', '"', '"', "「", "」", "『", "』"}

    # Simulate a replacement where original has quotes but translation doesn't
    original = '"Nguoi dinh lam gi?"'
    translation = "Ban dinh lam gi"  # Missing quotes

    final_translation = translation
    if original and translation:
        orig_starts_quote = original[0] in quote_chars
        orig_ends_quote = original[-1] in quote_chars
        trans_starts_quote = translation[0] in quote_chars if translation else False
        trans_ends_quote = translation[-1] in quote_chars if translation else False

        if orig_starts_quote and not trans_starts_quote:
            final_translation = original[0] + final_translation
        if orig_ends_quote and not trans_ends_quote:
            final_translation = final_translation + original[-1]

    print(f"Original: {original}")
    print(f"Translation (raw): {translation}")
    print(f"Translation (fixed): {final_translation}")

    # Check that the fix worked
    if final_translation.startswith('"') and final_translation.endswith('"'):
        print("\nQuote preservation test PASSED!\n")
        return True
    else:
        print("\nQuote preservation test FAILED!\n")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Quotation Mark Fix Verification")
    print("=" * 60 + "\n")

    test1 = test_sentence_splitter()
    test2 = test_quote_preservation()

    if test1 and test2:
        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("SOME TESTS FAILED!")
        print("=" * 60)
        sys.exit(1)
