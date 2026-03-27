# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

# Thêm thư mục gốc vào path để import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.preprocessing.metadata_generator import MetadataGenerator


class TestMetadataGenerator(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = {
            'input': {'novel_path': 'data/input/test.txt'},
            'metadata': {'document_type': 'novel'},
            'translation': {},
            'performance': {},
            'models': {'flash': 'gemini-3-flash-preview'}
        }
        self.api_keys = ["key1", "key2"]

        # Patch GeminiAPIService để không gọi API thật
        with patch('src.preprocessing.metadata_generator.GeminiAPIService') as MockService:
            self.generator = MetadataGenerator(self.config, self.api_keys)
            self.generator.gemini_service = MockService.return_value
            self.generator.gemini_service.generate_content_async = AsyncMock()

    def test_qc_style_profile_valid(self):
        valid_json = json.dumps({
            "thong_tin_tac_pham": "X",
            "the_loai": "Y",
            "huong_dan_dich_thuat": "Z"
        })
        error = self.generator._qc_style_profile(valid_json)
        self.assertIsNone(error)

    def test_qc_style_profile_invalid(self):
        invalid_json = json.dumps({
            "thong_tin_tac_pham": "X"
        })
        error = self.generator._qc_style_profile(invalid_json)
        self.assertIn("Thiếu các trường bắt buộc", error)

    def test_qc_glossary_valid(self):
        valid_csv = "Type,Original_Term_CN,Translated_Term_VI\nCharacter,A,B"
        error = self.generator._qc_glossary(valid_csv)
        self.assertIsNone(error)

    def test_qc_glossary_invalid(self):
        invalid_csv = "Wrong,Header\nData,Data"
        error = self.generator._qc_glossary(invalid_csv)
        self.assertIn("Thiếu các cột bắt buộc", error)

    async def test_document_type_customization_technical(self):
        # Đổi document_type sang technical_doc
        self.generator.document_type = "technical_doc"

        with patch('src.preprocessing.metadata_generator.AdvancedFileParser') as MockParser:
            MockParser.return_value.parse.return_value = {'text': 'Some content'}

            # Mock các hàm extract để không chạy thật (vì ta chỉ test logic điều hướng)
            self.generator._extract_style = AsyncMock(return_value=True)
            self.generator._extract_glossary = AsyncMock(return_value=True)
            self.generator._extract_relations = AsyncMock(return_value=True)

            await self.generator.generate_all_metadata()

            # _extract_relations KHÔNG được gọi cho technical_doc
            self.generator._extract_relations.assert_not_called()

    async def test_self_correction_loop(self):
        # Case: Style Profile lần đầu sai (thiếu key), lần 2 AI sửa đúng
        bad_response = json.dumps({"only_one_key": "val"})
        good_response = json.dumps({
            "thong_tin_tac_pham": "X",
            "the_loai": "Y",
            "huong_dan_dich_thuat": "Z"
        })

        # Mock API trả về lần lượt sai, rồi đúng
        self.generator.gemini_service.generate_content_async.side_effect = [
            bad_response, # Lần đầu (generate)
            good_response  # Lần 2 (self-correct)
        ]

        # Cần patch Path.exists và open để tránh ghi file thật
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', unittest.mock.mock_open()), \
             patch('os.path.exists', return_value=True):

            success = await self.generator._extract_style("Test content")

            self.assertTrue(success)
            # Kiểm tra generate_content_async được gọi 2 lần (1 gốc + 1 sửa)
            self.assertEqual(self.generator.gemini_service.generate_content_async.call_count, 2)

if __name__ == '__main__':
    unittest.main()
