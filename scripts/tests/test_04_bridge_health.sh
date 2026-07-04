#!/usr/bin/env bash
# test_04_bridge_health.sh — verify them-bridge health endpoints
# Runs curl inside the container to avoid needing exposed host ports.
# Usage: bash scripts/tests/test_04_bridge_health.sh

set -euo pipefail

CONTAINER="${BRIDGE_CONTAINER:-them-bridge}"
PORT="${BRIDGE_PORT:-8001}"
BASE="http://localhost:$PORT"
PASS=0
FAIL=0

check_http() {
    local desc="$1" path="$2" expected_status="$3"
    local status
    status=$(docker exec "$CONTAINER" curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BASE$path" 2>/dev/null || echo "000")
    if [ "$status" = "$expected_status" ]; then
        echo "  [PASS] $desc (HTTP $status)"
        ((PASS++)) || true
    else
        echo "  [FAIL] $desc (got: $status, want: $expected_status)"
        ((FAIL++)) || true
    fi
}

check_json_field() {
    local desc="$1" path="$2" field="$3" expected="$4"
    local value
    value=$(docker exec "$CONTAINER" curl -s --max-time 5 "$BASE$path" 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field','MISSING'))" 2>/dev/null || echo "ERR")
    if [ "$value" = "$expected" ]; then
        echo "  [PASS] $desc"
        ((PASS++)) || true
    else
        echo "  [FAIL] $desc (got: '$value', want: '$expected')"
        ((FAIL++)) || true
    fi
}

echo "=== test_04_bridge_health: Bridge Health ==="

check_http "GET /health returns 200"       "/health"       "200"
check_http "GET /health/live returns 200"  "/health/live"  "200"
check_http "GET /health/ready returns 200" "/health/ready" "200"
check_json_field "health status=ok" "/health" "status" "ok"

echo ""
echo "Result: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
