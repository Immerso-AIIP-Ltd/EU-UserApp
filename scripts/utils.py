import re
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import text

from app.api.queries import GET_CATEGORIES_QUERY, GET_GAMES_QUERY, GET_TOOLS_QUERY
from app.core.constants import AppUserApp, MeiliSearchIndexes
from app.db.factory import DatabaseFactory
from app.settings import settings


def get_dummy_hashtags() -> list[dict[str, str]]:
    """Returns dummy data for Hashtags index."""
    tags = [
        "#action",
        "#adventure",
        "#rpg",
        "#strategy",
        "#puzzle",
        "#arcade",
        "#simulation",
        "#sports",
        "#racing",
        "#fighting",
    ]
    data = []
    for i, tag in enumerate(tags):
        data.append(
            {
                "id": f"tag_{i}",
                "tag": tag,
            },
        )
    return data


def get_dummy_history() -> list[dict[str, Any]]:
    """Returns dummy data for Query History index."""
    queries = [
        "minecraft",
        "gta",
        "pubg",
        "fortnite",
        "roblox",
        "call of duty",
        "among us",
        "league of legends",
        "valorant",
        "apex legends",
    ]
    data = []
    for i, query in enumerate(queries):
        data.append(
            {
                "id": f"history_{i}",
                "query": query,
                "popularity": 100 - i,
                "updated_at": datetime.now().isoformat(),
            },
        )
    return data


def get_dummy_mini_apps() -> list[dict[str, Any]]:
    """Returns dummy data for Super App index."""
    apps = ["eros-create", "eros-eternal", "eros-now", "eros-play", "eros-world"]
    data = []
    for i, app_id in enumerate(apps):
        data.append(
            {
                "id": app_id,
                "title": app_id.replace("-", " ").title(),
                "description": f"Description for {app_id}",
                "type": "mini-app",
                "icon_url": f"https://example.com/{app_id}.png",
                "app_url": f"https://example.com/{app_id}",
                "rating": 4.5 + (i * 0.1) % 0.5,  # Dummy rating
            },
        )
    return data


def get_sortable_attributes(ranking_rules: list[str]) -> list[str]:
    """Extract sortable attributes from ranking rules."""
    sortable = set()
    for rule in ranking_rules:
        match = re.search(r"(asc|desc)\((.*)\)", rule)
        if match:
            sortable.add(match.group(2))
    return list(sortable)


async def fetch_data(query_str: str, db_base: str) -> list[dict[str, Any]]:
    """Fetch data from database using the provided SQL query."""
    logger.debug(f"Executing query: {query_str.strip().splitlines()[0]}...")

    db_factory = DatabaseFactory(
        db_url=str(settings.db_url(db_base)),
        db_echo=settings.db_echo,
    )

    data = []
    try:
        async with db_factory.get_session() as session:
            result = await session.execute(text(query_str))
            keys = list(result.keys())
            rows = result.fetchall()

            for row in rows:
                row_dict = {}
                for i, key in enumerate(keys):
                    val = row[i]
                    if isinstance(val, datetime):
                        val = val.isoformat()
                    row_dict[key] = val
                data.append(row_dict)

    except Exception as e:
        logger.error(f"Error fetching data: {e}")
    finally:
        await db_factory.close()

    return data


def setup_index(
    client: Any,
    index_name: str,
    config: dict[str, Any],
    data: list[dict[str, Any]],
) -> None:
    """Setup a MeiliSearch index with config and data."""
    logger.debug(f"Setting up index: {index_name}")

    if not data:
        logger.debug(f"No data to index for {index_name}. Skipping.")
        return

    # Create index if it doesn't exist
    try:
        client.create_index(index_name, {"primaryKey": config.get("primaryKey", "id")})
        logger.debug(f"Index '{index_name}' created.")
    except Exception as e:
        # Check if error is because index already exists
        if "index_already_exists" in str(e) or "already exists" in str(e):
            logger.debug(f"Index '{index_name}' already exists.")
        else:
            logger.error(
                f"Note: create_index failed with: {e}. "
                "Attempting to proceed with existing index.",
            )

    index = client.index(index_name)

    # Extract settings from config
    searchable = config.get("searchableAttributes", [])
    filterable = config.get("filterableAttributes", [])
    ranking_rules = config.get("rankingRules", [])
    displayed = config.get("displayedAttributes", [])
    typo_tolerance = config.get("typoTolerance", {})
    sortable = config.get("sortableAttributes", [])

    # Update settings
    logger.debug(f"Updating settings for {index_name}...")
    try:
        index.update_searchable_attributes(searchable)
        index.update_filterable_attributes(filterable)
        index.update_sortable_attributes(sortable)
        index.update_ranking_rules(ranking_rules)
        index.update_displayed_attributes(displayed)
        index.update_typo_tolerance(typo_tolerance)
    except Exception as e:
        logger.error(f"Error updating settings: {e}")

    # Add documents
    logger.debug(f"Adding {len(data)} documents to {index_name}...")
    try:
        task = index.add_documents(data)
        logger.debug(f"Task UID: {task.task_uid}")
    except Exception as e:
        logger.error(f"Error adding documents: {e}")


def check_config(client: Any, config: dict[str, Any]) -> None:
    """Check and setup template indexes if present in config."""

    logger.debug("Loading index configs...")

    if "_template_superapp_miniapp_v1" in config:
        super_app_data = get_dummy_mini_apps()
        index_cfg = config["_template_superapp_miniapp_v1"].model_dump(by_alias=True)
        setup_index(
            client,
            MeiliSearchIndexes.SUPERAPP_MINIAPP,
            index_cfg,
            super_app_data,
        )
    else:
        logger.debug("Config key _template_superapp_miniapp_v1 not found. Skipping.")

    if "_template_hashtags_v1" in config:
        hashtags_data = get_dummy_hashtags()
        index_cfg = config["_template_hashtags_v1"].model_dump(by_alias=True)
        setup_index(
            client,
            MeiliSearchIndexes.HASHTAGS,
            index_cfg,
            hashtags_data,
        )
    else:
        logger.debug("Config key _template_hashtags_v1 not found. Skipping.")

    if "_template_query_history_v1" in config:
        history_data = get_dummy_history()
        index_cfg = config["_template_query_history_v1"].model_dump(by_alias=True)
        setup_index(
            client,
            MeiliSearchIndexes.QUERY_HISTORY,
            index_cfg,
            history_data,
        )
    else:
        logger.debug("Config key _template_query_history_v1 not found. Skipping.")


def get_tasks() -> list[tuple[str, str, str, str]]:
    """Get list of indexing tasks (query, index, config_key, db)."""

    return [
        (
            GET_GAMES_QUERY,
            MeiliSearchIndexes.PLAY_GAME,
            "_template_play_game_v1",
            AppUserApp.DB_BASE_PLAY,
        ),
        (
            GET_TOOLS_QUERY,
            MeiliSearchIndexes.ETERNAL_TOOL,
            "_template_eternal_tool_v1",
            AppUserApp.DB_BASE_CATALOGUE,
        ),
        (
            GET_CATEGORIES_QUERY,
            MeiliSearchIndexes.PLAY_CATEGORY,
            "_template_play_category_v1",
            AppUserApp.DB_BASE_PLAY,
        ),
    ]


async def process_tasks(
    tasks: list[tuple[str, str, str, str]],
    config: dict[str, Any],
    client: Any,
) -> None:
    """Process indexing tasks sequentially."""

    for query, index_name, config_key, db_base in tasks:
        logger.debug(f"\n--- Processing {index_name} ---")
        if config_key not in config:
            logger.debug(
                f"Config key {config_key} not found in indexes.json. Skipping.",
            )
            continue

        data = await fetch_data(query, db_base)
        index_cfg = config[config_key].model_dump(by_alias=True)
        setup_index(client, index_name, index_cfg, data)
