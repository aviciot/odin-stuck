import hashlib
import json
from typing import Any, AsyncGenerator, Dict, List

from app.adapters.base import AdapterEvent
from app.middleware.base import CallNext, Middleware, MiddlewareContext
from app.utils.logger import logger

_KEY_ROOT = "them:mw:cache:"


class CacheMiddleware(Middleware):
    kind = "cache"

    def _scope_prefix(self, ctx: MiddlewareContext) -> str:
        scope = self.config.get("scope", "global")
        if scope == "app":
            return f"app:{ctx.application_id}"
        if scope == "session":
            return f"ctx:{ctx.context_id}"
        if scope == "user":
            return f"user:{ctx.user_id}"
        return ""

    def _hash(self, input: Dict[str, Any]) -> str:
        key_fields: List[str] = self.config.get("key_fields", ["message"])
        subset = {f: input.get(f) for f in key_fields}
        canonical = json.dumps(subset, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _cache_key(self, ctx: MiddlewareContext, input: Dict[str, Any]) -> str:
        return f"{_KEY_ROOT}{self._scope_prefix(ctx)}:{ctx.agent_slug}:{self._hash(input)}"

    async def process(
        self,
        input: Dict[str, Any],
        ctx: MiddlewareContext,
        call_next: CallNext,
    ) -> AsyncGenerator[AdapterEvent, None]:
        redis = ctx.redis
        ttl = int(self.config.get("ttl_seconds", 300))
        max_chars = int(self.config.get("max_result_chars", 100000))
        key = self._cache_key(ctx, input)

        if redis is not None:
            try:
                cached = await redis.get(key)
            except Exception as exc:
                cached = None
                logger.warning("cache: redis get failed", key=key, error=str(exc))
            if cached:
                if isinstance(cached, bytes):
                    cached = cached.decode("utf-8")
                logger.info("cache: hit", agent=ctx.agent_slug, run_id=ctx.run_id)
                yield AdapterEvent(type="done", result=cached)
                return

        buffered_tokens: List[str] = []
        done_result: str | None = None
        errored = False

        async for ev in call_next(input):
            if ev.type == "token":
                buffered_tokens.append(ev.text or "")
            elif ev.type == "done":
                done_result = ev.result if ev.result is not None else "".join(buffered_tokens)
            elif ev.type == "error":
                errored = True
            yield ev

        if errored or redis is None:
            return
        result_text = done_result if done_result is not None else "".join(buffered_tokens)
        if result_text and len(result_text) <= max_chars:
            try:
                await redis.set(key, result_text, ex=ttl)
                logger.info("cache: stored", agent=ctx.agent_slug, run_id=ctx.run_id, ttl=ttl)
            except Exception as exc:
                logger.warning("cache: redis set failed", key=key, error=str(exc))
