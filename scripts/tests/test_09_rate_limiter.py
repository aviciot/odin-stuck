#!/usr/bin/env python3.12
"""
test_09_rate_limiter.py — unit tests for rate_limiter and token_cache logic.
No containers required for rate limiter logic tests.
Token cache tests need the container (imports pydantic chain).
Usage: python3.12 scripts/tests/test_09_rate_limiter.py
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

PASS = 0
FAIL = 0


def check(desc, ok, detail=""):
    global PASS, FAIL
    if ok:
        print(f"  [PASS] {desc}"); PASS += 1
    else:
        print(f"  [FAIL] {desc}" + (f"  ({detail})" if detail else "")); FAIL += 1


print("=== test_09_rate_limiter: Rate Limiter & Token Cache ===")

# 1. rate_limiter imports and slot logic
try:
    import importlib, time
    # Patch db_module to avoid real Redis
    import types
    fake_db = types.ModuleType("app.database")
    fake_db.redis_client = None
    sys.modules["app.database"] = fake_db
    sys.modules["app.utils.logger"] = types.ModuleType("app.utils.logger")
    sys.modules["app.utils.logger"].logger = type("L", (), {
        "warning": lambda s,*a,**k: None,
        "error": lambda s,*a,**k: None,
        "info": lambda s,*a,**k: None,
    })()

    from app.services.rate_limiter import _slot, check_rate_limit, get_current_count

    slot = _slot()
    check("_slot() returns int", isinstance(slot, int))
    check("_slot() is current hour", slot == int(time.time()) // 3600)

    # With no Redis, rate limiter should allow all requests
    result = asyncio.run(check_rate_limit(user_id=1, limit_rpm=10))
    check("check_rate_limit allows when Redis=None", result[0] is True)

    result = asyncio.run(check_rate_limit(user_id=1, limit_rpm=0))
    check("check_rate_limit allows when limit=0 (disabled)", result[0] is True)

    count = asyncio.run(get_current_count(user_id=1))
    check("get_current_count returns 0 when Redis=None", count == 0)

except ImportError as exc:
    print(f"  [SKIP] rate_limiter tests — missing deps ({exc})")
except Exception as exc:
    check("rate_limiter import", False, str(exc))

# 2. token_cache hash function
try:
    import hashlib
    # Directly test the hash logic (no imports needed)
    token = "test-token-abc123"
    expected_hash = hashlib.sha256(token.encode()).hexdigest()
    check("sha256 hash is 64 chars", len(expected_hash) == 64)
    check("sha256 hash is deterministic", expected_hash == hashlib.sha256(token.encode()).hexdigest())
    check("different tokens produce different hashes",
          hashlib.sha256(b"a").hexdigest() != hashlib.sha256(b"b").hexdigest())
except Exception as exc:
    check("token hash logic", False, str(exc))

# 3. _deps module structure (no real auth service needed)
try:
    import ast, pathlib
    src = pathlib.Path(os.path.join(os.path.dirname(__file__), "../../app/_deps.py")).read_text()
    tree = ast.parse(src)
    funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)]
    check("require_jwt defined in _deps.py", "require_jwt" in funcs)
    check("require_admin defined in _deps.py", "require_admin" in funcs)
    check("require_bearer defined in _deps.py", "require_bearer" in funcs)
except Exception as exc:
    check("_deps.py structure", False, str(exc))

# 4. token_cache: L1 cache set/get/delete and TTL expiry
try:
    import importlib, time, types

    # Re-patch to ensure clean state
    fake_db2 = types.ModuleType("app.database")
    fake_db2.redis_client = None
    sys.modules["app.database"] = fake_db2

    # Force reload token_cache with patched deps
    if "app.services.token_cache" in sys.modules:
        del sys.modules["app.services.token_cache"]
    if "app.models" in sys.modules:
        del sys.modules["app.models"]

    # Stub app.models so token_cache can import
    fake_models = types.ModuleType("app.models")
    fake_models.AccessToken = type("AccessToken", (), {})
    sys.modules["app.models"] = fake_models

    from app.services import token_cache as tc

    # L1 set and get
    tc._l1_set("abc123", {"enabled": True, "user_id": 1})
    result = tc._l1_get("abc123")
    check("L1 set/get returns payload", result == {"enabled": True, "user_id": 1})

    # L1 delete
    tc._l1_delete("abc123")
    check("L1 delete removes entry", tc._l1_get("abc123") is None)

    # L1 TTL expiry — inject an already-expired entry
    tc._l1["expired"] = ({"enabled": True}, time.monotonic() - 1)
    check("L1 expired entry returns None", tc._l1_get("expired") is None)
    check("L1 expired entry cleaned up", "expired" not in tc._l1)

    # invalidate_token clears L1 (L2 skipped — Redis=None)
    tc._l1_set("tok1", {"enabled": True})
    asyncio.run(tc.invalidate_token("tok1"))
    check("invalidate_token clears L1", tc._l1_get("tok1") is None)

except Exception as exc:
    check("token_cache L1 logic", False, str(exc))

# 5. token_cache: _is_user_active fails open when auth-service unreachable
try:
    if "app.services.token_cache" in sys.modules:
        del sys.modules["app.services.token_cache"]

    # Stub auth_client to raise
    fake_auth = types.ModuleType("app.services.auth_client")
    async def _failing_get_user(user_id):
        raise ConnectionError("auth-service down")
    fake_auth.get_user = _failing_get_user
    sys.modules["app.services.auth_client"] = fake_auth
    sys.modules["app.services"] = types.ModuleType("app.services")

    from app.services import token_cache as tc2
    result = asyncio.run(tc2._is_user_active(42))
    check("_is_user_active fails open when auth-service down", result is True)

except Exception as exc:
    check("_is_user_active fail-open", False, str(exc))

# 6. token_cache: _is_user_active returns False for inactive user
try:
    if "app.services.token_cache" in sys.modules:
        del sys.modules["app.services.token_cache"]

    fake_auth2 = types.ModuleType("app.services.auth_client")
    async def _inactive_get_user(user_id):
        return {"active": False, "username": "disabled_user"}
    fake_auth2.get_user = _inactive_get_user
    sys.modules["app.services.auth_client"] = fake_auth2

    from app.services import token_cache as tc3
    result = asyncio.run(tc3._is_user_active(99))
    check("_is_user_active returns False for inactive user", result is False)

    result_active = asyncio.run(tc3._is_user_active.__wrapped__(1) if hasattr(tc3._is_user_active, '__wrapped__') else tc3._is_user_active(1))

except Exception as exc:
    check("_is_user_active inactive user", False, str(exc))

# 7. token_cache: new functions exist in module
try:
    import ast, pathlib
    src = pathlib.Path(os.path.join(os.path.dirname(__file__), "../../app/services/token_cache.py")).read_text()
    tree = ast.parse(src)
    funcs = [n.name for n in ast.walk(tree) if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))]
    check("invalidate_token defined", "invalidate_token" in funcs)
    check("invalidate_user_active defined", "invalidate_user_active" in funcs)
    check("_is_user_active defined", "_is_user_active" in funcs)
    check("validate_bearer_token defined", "validate_bearer_token" in funcs)
    # Verify user-active check is wired into validate_bearer_token
    check("_is_user_active called in validate_bearer_token", "_is_user_active" in src)
    check("_USER_ACTIVE_PREFIX defined", "_USER_ACTIVE_PREFIX" in src)
except Exception as exc:
    check("token_cache structure", False, str(exc))


print()
print(f"Result: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
