from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Dict, Optional

from app.adapters.base import AdapterEvent

CallNext = Callable[[Dict[str, Any]], AsyncGenerator[AdapterEvent, None]]


@dataclass
class MiddlewareContext:
    run_id: str
    context_id: str
    agent_id: str
    agent_slug: str
    user_id: Optional[str]
    session_id: Optional[str]
    application_id: Optional[str]
    tool_call_id: str
    timeout: float
    redis: Any
    db_session_factory: Callable[[], Any]


class Middleware(ABC):
    kind: str = ""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config: Dict[str, Any] = config or {}

    @abstractmethod
    async def process(
        self,
        input: Dict[str, Any],
        ctx: MiddlewareContext,
        call_next: CallNext,
    ) -> AsyncGenerator[AdapterEvent, None]:
        raise NotImplementedError
        if False:
            yield  # type: ignore[misc]

    @staticmethod
    def _refuse(message: str, reason: str) -> AdapterEvent:
        # type="error" so blocks are recorded as failures in run_steps, not successes
        return AdapterEvent(
            type="error",
            error=f"[{reason}] {message}",
        )
