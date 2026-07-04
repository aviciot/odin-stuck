"""
AgentAdapter ABC + AdapterEvent dataclass.
All transports implement stream_invoke() yielding AdapterEvents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional


@dataclass
class AdapterEvent:
    type: str                        # "token" | "done" | "error" | "task_created" | "artifact" | "status"
    text: Optional[str] = None       # streaming token text
    result: Optional[str] = None     # full assembled result on "done"
    error: Optional[str] = None      # error message on "error"
    remote_task_id: Optional[str] = None  # set on "task_created" event
    state: Optional[str] = None      # task state on "status" events
    artifact: Optional[dict] = None  # full A2A artifact dict (has 'parts' array)
    input_required: bool = False     # set when remote task is in 'input-required' state


class AgentAdapter(ABC):
    @abstractmethod
    async def stream_invoke(
        self,
        input: dict,
        timeout: float,
    ) -> AsyncGenerator[AdapterEvent, None]:
        """Stream AdapterEvents for a single agent invocation."""
        ...
