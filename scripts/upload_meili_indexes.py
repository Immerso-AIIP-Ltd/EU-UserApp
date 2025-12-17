import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
from pathlib import Path
import meilisearch
from app.core.search.config import load_index_configs
from app.settings import settings
from scripts.utils import check_config, get_tasks, process_tasks


async def main():

    client = meilisearch.Client(settings.meilisearch_host, settings.meilisearch_api_key)

    config_path = Path(
        os.path.join(
            os.path.dirname(__file__), "..", "app", "core", "search", "indexes.json"
        )
    )
    config = load_index_configs(config_path)

    check_config(client, config)

    tasks = get_tasks()

    await process_tasks(tasks, config, client)


if __name__ == "__main__":
    asyncio.run(main())
