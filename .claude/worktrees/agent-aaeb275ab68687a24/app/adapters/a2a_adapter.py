"""
A2aAdapter — STUB. Google Agent-to-Agent protocol not yet implemented.
Never set transport='a2a' on production agents.
"""

from typing import AsyncGenerator

from app.adapters.base import AdapterEvent, AgentAdapter


class A2aAdapter(AgentAdapter):
    async def stream_invoke(
        self,
        input: dict,
        timeout: float,
    ) -> AsyncGenerator[AdapterEvent, None]:
        raise NotImplementedError("A2A transport is not implemented")
        yield  # make this an async generator
