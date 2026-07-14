from typing import Dict, Type

from app.middleware.base import Middleware
from app.middleware.spec import MiddlewareSpec
from app.middleware.builtins.guard import GuardMiddleware
from app.middleware.builtins.cache import CacheMiddleware

_KINDS: Dict[str, Type[Middleware]] = {
    "guard": GuardMiddleware,
    "cache": CacheMiddleware,
}


def build_middleware(spec: MiddlewareSpec) -> Middleware:
    cls = _KINDS.get(spec.kind)
    if cls is None:
        raise ValueError(f"Unknown middleware kind: {spec.kind!r}")
    return cls(spec.config)
