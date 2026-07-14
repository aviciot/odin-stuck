from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class MiddlewareSpec:
    kind: str
    def_slug: str
    node_id: Optional[str]
    position: int
    config: Dict[str, Any] = field(default_factory=dict)
