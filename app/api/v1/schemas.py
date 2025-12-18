from typing import List, Optional, Any

from pydantic import BaseModel


class CacheStats(BaseModel):
    """
    Schema for Redis cache statistics.
    """

    used_memory_human: Optional[str] = None
    connected_clients: Optional[Any] = None
    total_commands_processed: Optional[Any] = None
    uptime_in_days: Optional[Any] = None
    total_keys: int
    keys: List[str]
