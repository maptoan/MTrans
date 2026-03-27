import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.preprocessing.ocr.ai_processor import AIProcessorError, _cleanup_chunk_async


class TestAIProcessor(unittest.IsolatedAsyncioTestCase):
    async def test_cleanup_chunk_async_success(self):
        # Mock client and response
        mock_response = MagicMock()
        mock_response.text = " Cleaned Text "
        mock_response.candidates = [MagicMock()]
        mock_response.prompt_feedback = None # Ensure no safety block

        mock_client = AsyncMock()
        mock_client.generate_content_async.return_value = mock_response
        mock_client.aclose = AsyncMock()

        with patch('src.preprocessing.ocr.ai_processor.create_client', return_value=mock_client):
            result = await _cleanup_chunk_async(
                chunk="raw chunk",
                api_key="test_key",
                model_name="test_model",
                prompt="Cleanup: ",
                chunk_idx=1,
                total_chunks=1,
                timeout_s=10.0
            )

            self.assertEqual(result, "Cleaned Text")
            mock_client.generate_content_async.assert_called_once()
            mock_client.aclose.assert_called_once()

    async def test_cleanup_chunk_async_no_candidates(self):
        # Mock client and response with no candidates
        mock_response = MagicMock()
        mock_response.candidates = []
        mock_response.prompt_feedback = None

        mock_client = AsyncMock()
        mock_client.generate_content_async.return_value = mock_response
        mock_client.aclose = AsyncMock()

        with patch('src.preprocessing.ocr.ai_processor.create_client', return_value=mock_client):
            with self.assertRaises(AIProcessorError):
                await _cleanup_chunk_async(
                    chunk="raw chunk",
                    api_key="test_key",
                    model_name="test_model",
                    prompt="Cleanup: ",
                    chunk_idx=1,
                    total_chunks=1,
                    timeout_s=10.0
                )
            mock_client.aclose.assert_called_once()

    async def test_cleanup_chunk_async_blocked(self):
        # Mock client and response blocked by safety
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.prompt_feedback = MagicMock()
        mock_response.prompt_feedback.block_reason = MagicMock()
        mock_response.prompt_feedback.block_reason.name = "SAFETY"

        mock_client = AsyncMock()
        mock_client.generate_content_async.return_value = mock_response
        mock_client.aclose = AsyncMock()

        with patch('src.preprocessing.ocr.ai_processor.create_client', return_value=mock_client):
            with self.assertRaises(AIProcessorError):
                await _cleanup_chunk_async(
                    chunk="raw chunk",
                    api_key="test_key",
                    model_name="test_model",
                    prompt="Cleanup: ",
                    chunk_idx=1,
                    total_chunks=1,
                    timeout_s=10.0
                )
            mock_client.aclose.assert_called_once()

if __name__ == '__main__':
    unittest.main()
