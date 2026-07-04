"""
context_service — shared context / memory for the A2A task graph.

The-M is the sole writer. Agents see context inlined in outbound messages.
Redis hot cache (them:ctx:{context_id}:heads, TTL 300s) avoids a DB hit
on every delegation for active runs. Falls through to Postgres on miss.
"""

import json
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.database as db_module
from app.models import Artifact
from app.services import task_store
from app.utils.logger import logger

_CTX_KEY_PREFIX = "them:ctx:"
_CTX_KEY_SUFFIX = ":heads"
_CTX_TTL = 300  # seconds


def _cache_key(context_id: uuid.UUID) -> str:
    return f"{_CTX_KEY_PREFIX}{context_id}{_CTX_KEY_SUFFIX}"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def get_context_artifacts(
    context_id: uuid.UUID,
    db: AsyncSession,
    limit: int = 10,
) -> list[dict]:
    """
    Return the most recent completed artifacts for a context, as portable dicts.

    Cache key: them:ctx:{context_id}:heads (JSON list, TTL 300s)
    On cache hit: return parsed list.
    On cache miss: query DB, write result to cache, return list.
    """
    key = _cache_key(context_id)

    # Try Redis cache first
    if db_module.redis_client is not None:
        try:
            cached = await db_module.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as exc:
            logger.warning(
                "context_service: cache read failed, falling through to DB",
                context_id=str(context_id),
                error=str(exc),
            )

    # Cache miss — query DB
    try:
        result = await db.execute(
            select(Artifact)
            .where(Artifact.context_id == context_id, Artifact.last_chunk == True)
            .order_by(Artifact.created_at.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())

        artifacts = [
            {
                "artifact_id": row.artifact_id,
                "name": row.name,
                "parts": row.parts,
                "created_at": str(row.created_at),
            }
            for row in rows
        ]
    except Exception as exc:
        logger.warning(
            "context_service: DB query failed",
            context_id=str(context_id),
            error=str(exc),
        )
        return []

    # Write to cache
    if db_module.redis_client is not None:
        try:
            await db_module.redis_client.setex(key, _CTX_TTL, json.dumps(artifacts))
        except Exception as exc:
            logger.warning(
                "context_service: cache write failed",
                context_id=str(context_id),
                error=str(exc),
            )

    return artifacts


async def invalidate_context_cache(context_id: uuid.UUID) -> None:
    """
    Delete the hot cache for this context.
    Fire-and-forget — never raises.
    """
    if db_module.redis_client is None:
        return
    try:
        await db_module.redis_client.delete(_cache_key(context_id))
    except Exception as exc:
        logger.warning(
            "context_service: cache invalidation failed",
            context_id=str(context_id),
            error=str(exc),
        )


async def record_and_cache_artifact(
    *,
    task_id: uuid.UUID,
    context_id: uuid.UUID,
    artifact_id: str,
    parts: list[dict],
    name: Optional[str],
    db: AsyncSession,
) -> None:
    """
    Write artifact to DB via task_store, then invalidate the context cache.

    Write → invalidate → next read repopulates: guarantees cache consistency.
    """
    await task_store.record_artifact(
        db,
        task_id=task_id,
        context_id=context_id,
        artifact_id=artifact_id,
        parts=parts,
        name=name,
    )
    await invalidate_context_cache(context_id)
