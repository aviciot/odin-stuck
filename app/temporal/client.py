"""
Temporal client singleton — mirrors the redis_client pattern in app/database.py.
Call get_temporal_client() to get a connected Client; it is cached after first connect.
"""

import asyncio
from typing import Optional

from temporalio.client import Client

from app.utils.logger import logger

_client: Optional[Client] = None
_lock = asyncio.Lock()


async def get_temporal_client() -> Client:
    global _client
    if _client is not None:
        return _client
    async with _lock:
        if _client is not None:
            return _client
        from app.temporal.config import get_temporal_config
        cfg = get_temporal_config()
        try:
            _client = await Client.connect(cfg.host, namespace=cfg.namespace)
            logger.info("temporal: client connected", host=cfg.host, namespace=cfg.namespace)
        except Exception as exc:
            logger.error("temporal: client connect failed", host=cfg.host, error=str(exc))
            raise
        return _client


def reset_client() -> None:
    """For testing — reset singleton so next call reconnects."""
    global _client
    _client = None
