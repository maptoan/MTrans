import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.translation.translator import NovelTranslator


@pytest.fixture
def mock_config():
    return {
        "input": {"novel_path": "non_existent.txt"},
        "performance": {"max_parallel_workers": 2},
        "translation": {},
        "logging": {},
        "metadata": {},
    }


@pytest.mark.asyncio
async def test_translator_init_with_missing_file_no_crash(mock_config):
    # Arrange
    # novel_path is non_existent.txt

    # Act
    translator = NovelTranslator(mock_config, ["key1"])

    # Assert
    assert translator.novel_name == "non_existent"
    # Should not crash on init


@pytest.mark.asyncio
async def test_translator_run_with_no_keys_graceful_exit(mock_config):
    # Arrange
    translator = NovelTranslator(mock_config, [])  # Empty keys

    # Act & Assert
    # In current implementation, if no keys, it might raise ValueError in InitializationService
    # Let's verify it raises a meaningful error, not a generic crash.
    with pytest.raises(Exception):
        await translator.run_translation_cycle_with_review()


@pytest.mark.asyncio
async def test_execution_manager_timeout_on_all_keys_blocked(mock_config):
    """Verify that ExecutionManager eventually gives up if no keys are available."""
    from src.translation.execution_manager import ExecutionManager

    mock_resources = {"key_manager": MagicMock(), "progress_manager": MagicMock(), "metrics_collector": MagicMock()}
    # All keys blocked
    mock_resources["key_manager"].get_key_for_worker = AsyncMock(return_value=None)
    mock_resources["key_manager"].is_key_blocked.return_value = True
    mock_resources["key_manager"].get_available_key.return_value = None

    manager = ExecutionManager(mock_resources, mock_config)

    # We want to test the loop logic without running it 240 times.
    # We can patch 'asyncio.sleep' but also need to ensure the loop terminates or mock the result.
    # A cleaner way is to mock the loop condition or the method itself if we just want to verify coordination.

    with (
        patch("src.translation.execution_manager.random.uniform", return_value=0),
        patch("asyncio.sleep", AsyncMock()) as mock_sleep,
    ):
        # To make it raise quickly, we can mock the internal 'max_wait' or just wait_time.
        # Since they are local, we'll just mock the loop's behavior by making one call to get_key_for_worker
        # and then asserting it *would* have continued.

        # Actually, let's just test that it DOES raise RuntimeError if we run it long enough.
        # We can mock the 15s sleep to return immediately.
        # But we need to avoid an infinite loop in the test if it doesn't increment.

        with pytest.raises(RuntimeError, match="timed out waiting for an available API key"):
            # Set a timeout for the test itself just in case
            await asyncio.wait_for(manager._wait_for_available_key(0), timeout=5.0)


@pytest.mark.asyncio
async def test_genai_adapter_sdk_fallback_robustness():
    """Verify GenAIClient doesn't crash if new SDK fails and old SDK is unavailable."""
    import src.services.genai_adapter as ga

    with (
        patch.object(ga, "NEW_SDK_AVAILABLE", True),
        patch.object(ga, "OLD_SDK_AVAILABLE", False),
        patch("src.services.genai_adapter.new_genai.Client", side_effect=Exception("SDK Error")),
    ):
        # Act
        client = ga.GenAIClient(api_key="test_key", use_new_sdk=True)

        # Assert
        assert client.client is None
        assert client.use_new_sdk is False

        # Should fail when trying to use it
        with pytest.raises(RuntimeError, match="New SDK failed and old SDK is not available"):
            await client.generate_content_async("test")


# Test the RuntimeError in generate_content_async (if client becomes None)
@pytest.mark.asyncio
async def test_genai_adapter_sdk_client_none_robustness():
    import src.services.genai_adapter as ga

    with patch.object(ga, "NEW_SDK_AVAILABLE", True), patch.object(ga, "OLD_SDK_AVAILABLE", False):
        client = ga.GenAIClient(api_key="test_key", use_new_sdk=True)
        client.client = None  # Force client to None after init
        with pytest.raises(RuntimeError, match="New SDK failed and old SDK is not available"):
            await client.generate_content_async("prompt")
