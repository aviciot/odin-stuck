"""
Database Connection Management
===============================
Manages PostgreSQL connection pool.
Direct connection to them-postgres (no PgBouncer).
search_path set via init callback so it works with any Postgres.
"""

import asyncpg
import logging
from urllib.parse import urlparse, urlunparse
from typing import Optional

from .settings import settings

logger = logging.getLogger(__name__)

_db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    global _db_pool

    if _db_pool is None:
        try:
            # Strip query params — use init callback for search_path instead
            parsed = urlparse(settings.DATABASE_URL)
            clean_url = urlunparse(parsed._replace(query=""))

            async def _set_search_path(conn):
                await conn.execute("SET search_path TO auth_service")

            _db_pool = await asyncpg.create_pool(
                clean_url,
                min_size=settings.DB_POOL_MIN_SIZE,
                max_size=settings.DB_POOL_MAX_SIZE,
                init=_set_search_path,
            )
            logger.info(f"Database pool created: {settings.DB_POOL_MIN_SIZE}-{settings.DB_POOL_MAX_SIZE} connections")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    return _db_pool


async def close_db_pool() -> None:
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("Database pool closed")
