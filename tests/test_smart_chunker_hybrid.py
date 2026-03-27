
import unittest
from unittest.mock import MagicMock

from src.preprocessing.chunker import SmartChunker


class TestSmartChunkerHybrid(unittest.TestCase):
    def setUp(self):
        # Mock config
        self.config = {
            'preprocessing': {
                'chunking': {
                    'max_chunk_tokens': 100, # Small limit for testing
                    'safety_ratio': 1.0,
                    'adaptive_mode': False,
                    'use_markers': False
                }
            },
            'translation': {}
        }
        self.chunker = SmartChunker(self.config)
        # Mock token counter: 1 char = 1 token for simplicity
        self.chunker._count_tokens = MagicMock(side_effect=lambda x: len(x))

    def test_split_chapters(self):
        text = """Intro text here.
Chương 1: Mở đầu.
Nội dung chương 1.
Chương 2: Diễn biến.
Nội dung chương 2."""
        chapters = self.chunker._split_chapters(text)
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0]['title'], 'Intro')
        self.assertIn('Chương 1', chapters[1]['title'])
        self.assertIn('Chương 2', chapters[2]['title'])

    def test_chunk_0_merging(self):
        # Intro + Chap 1 + Chap 2 < Limit * 1.5 (150)
        # Intro (16) + Chap 1 (30) + Chap 2 (30) = 76 chars. Limit=100.
        # Current logic merges everything until Limit reached or oversized.
        text = """Intro text here.
Chương 1: Start.
Content of chapter 1 is short.
Chương 2: Next.
Content of chapter 2."""
        # Setup tokens: intro=16, ch1=30, ch2=30

        chunks = self.chunker.chunk_novel(text)

        # Expectation: Everything merged into 1 chunk because total (76) < limit (100)
        self.assertEqual(len(chunks), 1)
        self.assertIn('Intro text here', chunks[0]['text_original'])
        self.assertIn('Content of chapter 1', chunks[0]['text_original'])
        self.assertIn('Content of chapter 2', chunks[0]['text_original'])

    def test_chapter_too_long_splitting(self):
        # Chapter 2 length > Limit (100) -> Should split
        long_content = "X" * 150 # 150 tokens
        text = f"""Intro.
Chương 1.
Short.
Chương 2.
{long_content}"""

        chunks = self.chunker.chunk_novel(text)

        # Chunk 0 = Intro + Chap 1 (Short)
        # Chunk 1, 2 = Chap 2 split
        # Current default type is 'paragraph_split'
        self.assertEqual(chunks[0]['type'], 'paragraph_split')
        # Check subsequent chunks are paragraph splits
        self.assertEqual(chunks[1]['type'], 'paragraph_split')

if __name__ == '__main__':
    unittest.main()
