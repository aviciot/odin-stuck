import json
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MiddlewareDef, MiddlewareWiring
from app.middleware.spec import MiddlewareSpec
from app.utils.merge import deep_merge
from app.utils.logger import logger

_CACHE_PREFIX = "them:mw:chain:"
_TTL = 600


def _cache_key(application_id: str, agent_id: str) -> str:
    return f"{_CACHE_PREFIX}{application_id}:{agent_id}"


async def resolve_chain(
    db: AsyncSession,
    redis: Any,
    *,
    application_id: Optional[str],
    agent_id: str,
) -> List[MiddlewareSpec]:
    if application_id is None:
        return []

    key = _cache_key(application_id, agent_id)

    if redis is not None:
        try:
            cached = await redis.get(key)
            if cached:
                raw = json.loads(cached)
                return [
                    MiddlewareSpec(
                        kind=s["kind"],
                        def_slug=s["def_slug"],
                        node_id=s.get("node_id"),
                        position=s["position"],
                        config=s.get("config", {}),
                    )
                    for s in raw
                ]
        except Exception as exc:
            logger.warning("mw_resolver: redis get failed", key=key, error=str(exc))

    stmt = (
        select(MiddlewareWiring, MiddlewareDef)
        .join(MiddlewareDef, MiddlewareWiring.def_id == MiddlewareDef.id)
        .where(
            MiddlewareWiring.application_id == application_id,
            MiddlewareWiring.agent_id == agent_id,
            MiddlewareWiring.enabled.is_(True),
            MiddlewareDef.enabled.is_(True),
        )
        .order_by(MiddlewareWiring.position.asc())
    )
    rows = (await db.execute(stmt)).all()

    specs: List[MiddlewareSpec] = []
    for wiring, definition in rows:
        merged = deep_merge(definition.config or {}, wiring.config_override or {})
        specs.append(
            MiddlewareSpec(
                kind=definition.kind,
                def_slug=definition.slug,
                node_id=wiring.node_id,
                position=wiring.position,
                config=merged,
            )
        )

    if redis is not None:
        try:
            payload = json.dumps([
                {"kind": s.kind, "def_slug": s.def_slug, "node_id": s.node_id,
                 "position": s.position, "config": s.config}
                for s in specs
            ])
            await redis.set(key, payload, ex=_TTL)
        except Exception as exc:
            logger.warning("mw_resolver: redis set failed", key=key, error=str(exc))

    return specs
