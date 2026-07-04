"""
AgentAdapter ABC + AdapterEvent dataclass.
All transports implement stream_invoke() yielding AdapterEvents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional


@dataclass
class AdapterEvent:
    type: str                   # "token" | "done" | "error"
    text: Optional[str] = None  # streaming token text
    result: Optional[str] = None  # full assembled result on "done"
    error: Optional[str] = None   # error message on "error"


class AgentAdapter(ABC):
    @abstractmethod
    async def stream_invoke(
        self,
        input: dict,
        timeout: float,
    ) -> AsyncGenerator[AdapterEvent, None]:
        """Stream AdapterEvents for a single agent invocation."""
        ...
