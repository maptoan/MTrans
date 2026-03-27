import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.translation.initialization_service import InitializationService


@pytest.fixture
def mock_config():
    return {
        "performance": {"max_parallel_workers": 2, "use_optimized_key_workflow": True, "max_concurrent_requests": 3},
        "translation": {"use_new_sdk": True, "context_caching": {"enabled": True, "ttl_minutes": 60}},
        "metadata": {
            "style_profile_path": "dummy_style.json",
            "glossary_path": "dummy_glossary.csv",
            "character_relations_path": "dummy_relations.csv",
        },
        "input": {"novel_path": "dummy.txt"},
    }


@pytest.mark.asyncio
async def test_initialize_all_success(mock_config):
    # Arrange
    service = InitializationService(mock_config)
    valid_keys = ["key1", "key2"]

    # Mocking all dependencies that require files or actual logic
    with (
        patch("src.services.smart_key_distributor.SmartKeyDistributor") as mock_skd_cls,
        patch("src.managers.style_manager.StyleManager"),
        patch("src.managers.glossary_manager.GlossaryManager"),
        patch("src.managers.relation_manager.RelationManager"),
        patch("src.managers.progress_manager.ProgressManager"),
        patch("src.output.formatter.OutputFormatter"),
        patch("src.services.gemini_api_service.GeminiAPIService"),
        patch("src.translation.model_router.SmartModelRouter"),
        patch("src.preprocessing.chunker.SmartChunker"),
        patch("src.translation.prompt_builder.PromptBuilder"),
    ):
        # mock_skd_cls.return_value.test_and_assign_keys = AsyncMock(return_value={'valid_keys': valid_keys})
        mock_skd_cls.return_value.get_active_key_count.return_value = 2

        # Act
        resources = await service.initialize_all(valid_keys, "test_novel")

        # Assert
        assert "key_manager" in resources
        assert "metrics_collector" in resources
        assert "model_router" in resources
        assert isinstance(resources["request_semaphore"], asyncio.Semaphore)
        assert resources["document_type"] == "novel"

    @pytest.mark.asyncio
    async def test_init_key_manager_optimized(mock_config):
        # Arrange
        service = InitializationService(mock_config)
        valid_keys = ["key1"]

        with patch("src.services.smart_key_distributor.SmartKeyDistributor") as mock_skd_cls:
            mock_skd_cls.return_value.get_active_key_count.return_value = 1

        # Act
        await service._init_key_manager(valid_keys)

        # Assert
        mock_skd_cls.assert_called_once()


@pytest.mark.asyncio
async def test_warm_up_resources_standard_model(mock_config):
    # Arrange
    service = InitializationService(mock_config)
    mock_gemini = AsyncMock()
    # Mocking get_or_create_context_cache to be a regular function that returns a value,
    # since it is called via run_in_executor which expects a sync function
    mock_gemini.get_or_create_context_cache = MagicMock(return_value="cache_123")
    mock_gemini.count_tokens_async = AsyncMock(return_value=100)

    resources = {
        "gemini_service": mock_gemini,
        "prompt_builder": MagicMock(),
        "glossary_manager": MagicMock(),
        "relation_manager": MagicMock(),
        "request_semaphore": asyncio.Semaphore(1),
    }
    resources["prompt_builder"].build_cacheable_prefix.return_value = "static prefix"
    resources["glossary_manager"].get_full_glossary_dict.return_value = {}
    resources["relation_manager"].get_full_relation_text.return_value = ""

    # Act
    key_cache_map = await service.warm_up_resources(resources, ["key1"])

    # Assert
    assert key_cache_map["key1"] == "cache_123"
    # Verify standard model gemini-2.5-flash was used (as per source code default)
    # Note: run_in_executor calls the lambda, which calls get_or_create_context_cache
    mock_gemini.get_or_create_context_cache.assert_called_with(
        content="static prefix", ttl_minutes=60, model_name="gemini-2.5-flash", api_key="key1"
    )


def test_check_metadata_logging(mock_config, caplog):
    # Arrange
    service = InitializationService(mock_config)
    mock_resources = {"style_manager": MagicMock(), "glossary_manager": MagicMock(), "relation_manager": MagicMock()}
    mock_resources["style_manager"].is_loaded.return_value = True
    mock_resources["style_manager"].profile = {"a": 1}
    mock_resources["glossary_manager"].glossary = {"b": 2}
    mock_resources["relation_manager"].relations = {}

    # Act
    with caplog.at_level("INFO"):
        service.check_metadata(mock_resources)

    # Assert
    assert "METADATA COMPLIANCE CHECK" in caplog.text
    assert "Style profile: Loaded" in caplog.text
    assert "Glossary: Loaded" in caplog.text
