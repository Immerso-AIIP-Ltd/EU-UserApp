# ruff: noqa: SLF001
from typing import List
from unittest.mock import MagicMock

import pytest

from app.core.search.client import MeiliSearchClient


# Mock config for testing
class MockConfig:
    def __init__(self, filterable_attributes: List[str]) -> None:
        self.filterable_attributes = filterable_attributes


@pytest.fixture
def client_with_mock_config() -> None:
    # Reset singleton
    MeiliSearchClient.reset_instance()

    # Create instance (will try to load real config, but we'll patch it)
    # Actually, we can just instantiate and then patch the internal state
    # But __init__ loads config. We should mock load_index_configs.

    with pytest.MonkeyPatch.context() as m:
        mock_configs = {
            "_template_index_a": MockConfig(["attr_a", "common_attr"]),
            "_template_index_b": MockConfig(["attr_b", "common_attr"]),
            "_template_index_c": MockConfig([]),  # No filters
        }
        m.setattr("app.core.search.client.load_index_configs", lambda x: mock_configs)

        return MeiliSearchClient()


def test_get_valid_filters_simple_valid(
    client_with_mock_config: MeiliSearchClient,
) -> None:
    # attr_a is valid for index_a
    assert (
        client_with_mock_config._get_valid_filters("index_a", "attr_a = 1")
        == "attr_a = 1"
    )


def test_get_valid_filters_simple_invalid_known(
    client_with_mock_config: MeiliSearchClient,
) -> None:
    # attr_b is NOT valid for index_a, but IS known (from index_b) -> Should be DROPPED
    assert client_with_mock_config._get_valid_filters("index_a", "attr_b = 1") is None


def test_get_valid_filters_simple_unknown(
    client_with_mock_config: MeiliSearchClient,
) -> None:
    # unknown_attr is not in any index config -> Should be KEPT (safe default)
    assert (
        client_with_mock_config._get_valid_filters("index_a", "unknown_attr = 1")
        == "unknown_attr = 1"
    )


def test_get_valid_filters_list_mixed(
    client_with_mock_config: MeiliSearchClient,
) -> None:
    # List with valid and invalid filters
    filters = ["attr_a = 1", "attr_b = 2", "common_attr = 3", "unknown = 4"]
    expected = ["attr_a = 1", "common_attr = 3", "unknown = 4"]

    result = client_with_mock_config._get_valid_filters("index_a", filters)
    assert result == expected


def test_get_valid_filters_nested_list(
    client_with_mock_config: MeiliSearchClient,
) -> None:
    # Nested list (OR)
    filters = [["attr_a = 1", "attr_b = 2"], "common_attr = 3"]
    # attr_b dropped from inner list
    expected = [["attr_a = 1"], "common_attr = 3"]

    result = client_with_mock_config._get_valid_filters("index_a", filters)
    assert result == expected


def test_get_valid_filters_complex_string(
    client_with_mock_config: MeiliSearchClient,
) -> None:
    # Complex string with parentheses
    assert (
        client_with_mock_config._get_valid_filters(
            "index_a",
            "(attr_a = 1 OR common_attr = 2)",
        )
        == "(attr_a = 1 OR common_attr = 2)"
    )

    assert (
        client_with_mock_config._get_valid_filters(
            "index_a",
            "attr_b = 1 OR attr_a = 1",
        )
        is None
    )


def test_get_valid_filters_geo(client_with_mock_config: MeiliSearchClient) -> None:
    # Geo filters should always be kept
    assert (
        client_with_mock_config._get_valid_filters("index_a", "_geoRadius(1, 2, 3)")
        == "_geoRadius(1, 2, 3)"
    )


def test_sync_multi_search_cleaning(client_with_mock_config: MeiliSearchClient) -> None:
    # Mock the actual meilisearch client
    client_with_mock_config.client = MagicMock()
    client_with_mock_config.client.multi_search.return_value = {"results": []}

    queries = [
        {
            "indexUid": "index_a",
            "q": "test",
            "filter": "attr_b = 1",
        },  # Should be cleaned to None (or removed if None handling)
        {"indexUid": "index_b", "q": "test", "filter": "attr_b = 1"},  # Should be kept
    ]

    client_with_mock_config._sync_multi_search(queries)

    # Check what was passed to multi_search
    call_args = client_with_mock_config.client.multi_search.call_args[0][0]

    assert "filter" not in call_args[0], "Invalid filter should be removed from query"
    assert call_args[1]["filter"] == "attr_b = 1"
