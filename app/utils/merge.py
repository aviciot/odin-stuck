"""
deep_merge — recursive dict merge. override wins. Nested dicts merge
recursively; scalars and arrays (lists) are replaced wholesale.
Returns a new dict; inputs are not mutated.
"""
from typing import Any, Dict


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = dict(base or {})
    for key, ov in (override or {}).items():
        bv = result.get(key)
        if isinstance(bv, dict) and isinstance(ov, dict):
            result[key] = deep_merge(bv, ov)
        else:
            result[key] = ov
    return result
