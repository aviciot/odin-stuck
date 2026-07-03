"""
Integration test fixtures.

Uses a single session-scoped event loop (via anyio) for all tests.
DB + Redis initialized once; tables truncated between tests.
"""

import asyncio
import time
from unittest.mock import patch

import jwt
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

import app.database as db_module
from app.database import init_db, close_db
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

TEST_SECRET = "test-secret-key-not-for-production"
TEST_USER_ID = 1


def make_jwt(role: str = "super_admin", exp_offset: int = 3600) -> str:
    return jwt.encode({
        "sub": f"user:{TEST_USER_ID}",
        "user_id": TEST_USER_ID,
        "username": "testadmin",
        "name": "Test Admin",
        "email": "test@odin.local",
        "role": role,
        "exp": int(time.time()) + exp_offset,
    }, TEST_SECRET, algorithm="HS256")


# ── Auth mock ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def mock_auth():
    async def _fake(token: str):
        try:
            return jwt.decode(token, TEST_SECRET, algorithms=["HS256"])
        except Exception:
            return None

    with patch("app.services.auth_client.validate_jwt", side_effect=_fake):
        yield


# ── DB + Redis (session-scoped, same loop as tests) ───────────────────────────

@pytest_asyncio.fixture(scope="session")
async def db_ready():
    await init_db()
    yield
    await close_db()


@pytest_asyncio.fixture(scope="session")
async def client(db_ready) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ── Per-test table cleanup ─────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def clean_db(db_ready):
    yield
    async with db_module.AsyncSessionLocal() as session:
        await session.execute(text(
            "TRUNCATE odin.run_usage, odin.run_steps, odin.runs, "
            "odin.access_tokens, odin.orchestrators, odin.agents "
            "RESTART IDENTITY CASCADE"
        ))
        await session.commit()


# ── Convenience ────────────────────────────────────────────────────────────────

@pytest.fixture
def admin_headers() -> dict:
    return {"Authorization": f"Bearer {make_jwt()}"}


@pytest.fixture
def expired_headers() -> dict:
    return {"Authorization": f"Bearer {make_jwt(exp_offset=-1)}"}


@pytest_asyncio.fixture
async def agent(client: AsyncClient, admin_headers: dict) -> dict:
    resp = await client.post("/api/v1/admin/agents", headers=admin_headers, json={
        "slug": "test_agent",
        "display_name": "Test Agent",
        "description": "Routes general questions to the assistant",
        "transport": "omni_ws",
        "endpoint_url": "ws://mock-agent-assistant:9000",
        "enabled": True,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def orchestrator(client: AsyncClient, admin_headers: dict, agent: dict) -> dict:
    resp = await client.post("/api/v1/admin/orchestrators", headers=admin_headers, json={
        "name": "test_orch",
        "display_name": "Test Orchestrator",
        "system_prompt": "You are a test orchestrator.",
        "allowed_agent_ids": [agent["id"]],
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-6",
        "max_iterations": 3,
        "max_parallel_tools": 2,
        "enabled": True,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()
