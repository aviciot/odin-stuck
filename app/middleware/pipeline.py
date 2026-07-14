from typing import Any, AsyncGenerator, Dict, List

from app.adapters.base import AdapterEvent, AgentAdapter
from app.middleware.base import CallNext, Middleware, MiddlewareContext


class MiddlewarePipeline(AgentAdapter):
    def __init__(
        self,
        adapter: AgentAdapter,
        middlewares: List[Middleware],
        ctx: MiddlewareContext,
    ) -> None:
        self._adapter = adapter
        self._middlewares = middlewares
        self._ctx = ctx

    async def stream_invoke(
        self,
        input: Dict[str, Any],
        timeout: float,
    ) -> AsyncGenerator[AdapterEvent, None]:
        if not self._middlewares:
            async for ev in self._adapter.stream_invoke(input=input, timeout=timeout):
                yield ev
            return

        def _terminal(inp: Dict[str, Any]) -> AsyncGenerator[AdapterEvent, None]:
            return self._adapter.stream_invoke(input=inp, timeout=timeout)

        call_next: CallNext = _terminal
        for mw in reversed(self._middlewares):
            call_next = self._wrap(mw, call_next)

        async for ev in call_next(input):
            yield ev

    def _wrap(self, mw: Middleware, nxt: CallNext) -> CallNext:
        ctx = self._ctx

        def _layer(inp: Dict[str, Any]) -> AsyncGenerator[AdapterEvent, None]:
            return mw.process(inp, ctx, nxt)

        return _layer
