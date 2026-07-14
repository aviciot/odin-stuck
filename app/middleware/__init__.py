from typing import Any

from app.adapters.base import AgentAdapter
from app.adapters.factory import get_adapter
from app.middleware.base import MiddlewareContext
from app.middleware.pipeline import MiddlewarePipeline
from app.middleware.registry import build_middleware
from app.middleware.resolver import resolve_chain

__all__ = ["build_agent_pipeline", "MiddlewareContext"]


async def build_agent_pipeline(
    agent: Any,
    *,
    db: Any,
    redis: Any,
    ctx: MiddlewareContext,
    context_id: str | None = None,
) -> AgentAdapter:
    adapter = get_adapter(agent, context_id=context_id)
    specs = await resolve_chain(
        db,
        redis,
        application_id=ctx.application_id,
        agent_id=ctx.agent_id,
    )
    if not specs:
        return adapter
    middlewares = [build_middleware(s) for s in specs]
    return MiddlewarePipeline(adapter, middlewares, ctx)
