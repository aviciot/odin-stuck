#!/usr/bin/env bash
# test_06_orchestrators_api.sh — CRUD smoke test for /api/v1/admin/orchestrators
# Runs curl inside odin-bridge container (no host ports required).
# Usage: bash scripts/tests/test_06_orchestrators_api.sh

set -euo pipefail

CONTAINER="${BRIDGE_CONTAINER:-odin-bridge}"
PORT="${BRIDGE_PORT:-8001}"
BASE="http://localhost:$PORT/api/v1/admin/orchestrators"
PASS=0
FAIL=0

dcurl() {
    docker exec "$CONTAINER" curl -s "$@" 2>/dev/null
}

check() {
    local desc="$1" result="$2" expected="$3"
    if [ "$result" = "$expected" ]; then
        echo "  [PASS] $desc"
        ((PASS++)) || true
    else
        echo "  [FAIL] $desc  (got: '$result', want: '$expected')"
        ((FAIL++)) || true
    fi
}

py_field() {
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$1','MISSING'))" 2>/dev/null || echo "MISSING"
}

echo "=== test_06_orchestrators_api: Orchestrators CRUD ==="

# 1. List
STATUS=$(dcurl -o /dev/null -w "%{http_code}" "$BASE")
check "GET /admin/orchestrators returns 200" "$STATUS" "200"

# 2. Create
BODY='{"name":"test_smoke_orch","display_name":"Smoke Test Orchestrator","system_prompt":"You are a smoke test.","allowed_agent_ids":[],"max_iterations":5,"max_parallel_tools":2,"rate_limit_rpm":10,"daily_budget_usd":"1.00"}'

RESPONSE=$(dcurl -X POST "$BASE" -H "Content-Type: application/json" -d "$BODY")
ORCH_ID=$(echo "$RESPONSE" | py_field id)
NAME=$(echo "$RESPONSE" | py_field name)

check "POST creates orchestrator" "$NAME" "test_smoke_orch"

if [ "$ORCH_ID" = "MISSING" ]; then
    echo "  [FAIL] Could not get orchestrator ID — skipping"
    ((FAIL++)) || true
    echo ""; echo "Result: $PASS passed, $FAIL failed"; exit 1
fi

# 3. GET by ID
STATUS=$(dcurl -o /dev/null -w "%{http_code}" "$BASE/$ORCH_ID")
check "GET /admin/orchestrators/{id} returns 200" "$STATUS" "200"

# 4. PATCH
PATCH_RESP=$(dcurl -X PATCH "$BASE/$ORCH_ID" -H "Content-Type: application/json" -d '{"display_name":"Smoke Orch (updated)","max_iterations":8}')
UPDATED=$(echo "$PATCH_RESP" | py_field max_iterations)
check "PATCH updates max_iterations" "$UPDATED" "8"

# 5. Conflict
STATUS=$(dcurl -o /dev/null -w "%{http_code}" -X POST "$BASE" -H "Content-Type: application/json" -d "$BODY")
check "POST duplicate name returns 409" "$STATUS" "409"

# 6. DELETE
STATUS=$(dcurl -o /dev/null -w "%{http_code}" -X DELETE "$BASE/$ORCH_ID")
check "DELETE returns 204" "$STATUS" "204"

STATUS=$(dcurl -o /dev/null -w "%{http_code}" "$BASE/$ORCH_ID")
check "GET deleted orchestrator returns 404" "$STATUS" "404"

echo ""
echo "Result: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
