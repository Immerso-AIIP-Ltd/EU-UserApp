import json
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions.exceptions import MeiliSearchError
from app.core.search.client import MeiliSearchClient
from app.core.search.config import IndexConfig, TypoTolerance, load_index_configs


@pytest.fixture(autouse=True)
def cleanup_singleton() -> Generator[None, None, None]:
    """Ensure singleton is reset before and after each test."""
    MeiliSearchClient.reset_instance()
    yield
    MeiliSearchClient.reset_instance()


@pytest.fixture
def mock_meilisearch_client() -> Generator[MagicMock, None, None]:
    """Mock the meilisearch.Client."""
    with patch("app.core.search.client.meilisearch.Client") as mock:
        yield mock


@pytest.fixture
def mock_settings() -> Generator[MagicMock, None, None]:
    """Mock the application settings."""
    with patch("app.core.search.client.settings") as mock:
        mock.meilisearch_host = "http://localhost:7700"
        mock.meilisearch_api_key = "masterKey"
        yield mock


def test_load_index_configs(tmp_path: Path) -> None:
    """Test loading index configurations from JSON file."""
    config_data = {
        "test_index": {
            "primaryKey": "id",
            "searchableAttributes": ["title"],
            "filterableAttributes": ["category"],
            "displayedAttributes": ["id", "title"],
            "rankingRules": ["words"],
            "typoTolerance": {"enabled": True, "disableOnWords": []},
        },
    }
    config_file = tmp_path / "indexes.json"
    with config_file.open("w") as f:
        json.dump(config_data, f)

    configs = load_index_configs(config_file)
    assert "test_index" in configs
    assert isinstance(configs["test_index"], IndexConfig)
    assert configs["test_index"].primary_key == "id"


@pytest.mark.asyncio
async def test_initialize_indexes(
    mock_meilisearch_client: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test that initialize_indexes logs the loaded configurations.

    Note: initialize_indexes no longer creates indexes - it only loads configs.
    Use sync_indexes() to provision indexes.
    """
    client_wrapper = MeiliSearchClient.get_instance()

    # Mock index config
    client_wrapper.indexes_config = {
        "_template_games_v1": IndexConfig(
            primary_key="id",
            searchable_attributes=["title"],
            filterable_attributes=["category"],
            displayed_attributes=["id", "title"],
            ranking_rules=["words"],
            typo_tolerance=TypoTolerance(enabled=True, disable_on_words=[]),
        ),
    }

    # initialize_indexes should complete without creating indexes
    await client_wrapper.initialize_indexes()

    # Verify create_index was NOT called (it's now done via sync_indexes)
    mock_meilisearch_client.return_value.create_index.assert_not_called()


@pytest.mark.asyncio
async def test_search(
    mock_meilisearch_client: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test single index search."""
    client_wrapper = MeiliSearchClient.get_instance()

    mock_index = MagicMock()
    mock_meilisearch_client.return_value.index.return_value = mock_index
    mock_index.search.return_value = {"hits": [{"id": 1, "title": "Test"}]}

    result = await client_wrapper.search("games", "test")

    mock_meilisearch_client.return_value.index.assert_called_with("games")
    mock_index.search.assert_called_with("test", None)
    assert "hits" in result
    assert result["hits"][0]["id"] == 1


@pytest.mark.asyncio
async def test_search_empty_index_name_raises_error(
    mock_meilisearch_client: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test that search raises ValueError for empty index name."""
    client_wrapper = MeiliSearchClient.get_instance()

    with pytest.raises(ValueError, match="index_name cannot be empty"):
        await client_wrapper.search("", "test")


@pytest.mark.asyncio
async def test_multi_search(
    mock_meilisearch_client: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test multi-index search returns formatted results with metadata."""
    client_wrapper = MeiliSearchClient.get_instance()

    mock_meilisearch_client.return_value.multi_search.return_value = {
        "results": [
            {
                "indexUid": "games",
                "hits": [{"id": 1}],
                "estimatedTotalHits": 10,
                "processingTimeMs": 5,
            },
        ],
    }

    results = await client_wrapper.multi_search([{"indexUid": "games", "q": "test"}])

    # Verify new formatted structure with metadata
    assert "games" in results
    assert results["games"]["status"] == "success"
    assert results["games"]["hits"][0]["id"] == 1
    assert results["games"]["estimatedTotalHits"] == 10
    assert results["games"]["processingTimeMs"] == 5


@pytest.mark.asyncio
async def test_multi_search_empty_queries_raises_error(
    mock_meilisearch_client: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test that multi_search raises ValueError for empty queries."""
    client_wrapper = MeiliSearchClient.get_instance()

    with pytest.raises(ValueError, match="queries list cannot be empty"):
        await client_wrapper.multi_search([])


@pytest.mark.asyncio
async def test_multi_search_missing_index_uid_raises_error(
    mock_meilisearch_client: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test that multi_search raises ValueError for missing indexUid."""
    client_wrapper = MeiliSearchClient.get_instance()

    with pytest.raises(ValueError, match="missing required 'indexUid' key"):
        await client_wrapper.multi_search([{"q": "test"}])


@pytest.mark.asyncio
async def test_search_failure_raises_meilisearch_error(
    mock_meilisearch_client: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test that search raises MeiliSearchError on failure."""
    client_wrapper = MeiliSearchClient.get_instance()

    mock_index = MagicMock()
    mock_meilisearch_client.return_value.index.return_value = mock_index
    mock_index.search.side_effect = Exception("Connection failed")

    with pytest.raises(MeiliSearchError, match="Search failed"):
        await client_wrapper.search("games", "test")


@pytest.mark.asyncio
async def test_multi_search_index_not_found(
    mock_meilisearch_client: MagicMock,
    mock_settings: MagicMock,
) -> None:
    """Test that multi_search handles index not found error gracefully."""
    client_wrapper = MeiliSearchClient.get_instance()

    # Simulate MeiliSearch returning an error for a non-existent index
    mock_meilisearch_client.return_value.multi_search.return_value = {
        "results": [
            {
                "indexUid": "nonexistent",
                "error": {"code": "index_not_found", "message": "Index not found"},
            },
        ],
    }

    results = await client_wrapper.multi_search(
        [{"indexUid": "nonexistent", "q": "test"}],
    )

    assert "nonexistent" in results
    assert results["nonexistent"]["status"] == "index_not_found"
    assert results["nonexistent"]["hits"] == []
