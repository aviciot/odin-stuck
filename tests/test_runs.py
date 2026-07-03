"""
Runs API integration tests.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.asyncio(loop_scope="session")

import app.database as db_module


async def _insert_run(orchestrator_id: str, status: str = "completed") -> str:
    """Directly insert a run row for testing the runs API."""
    async with db_module.AsyncSessionLocal() as session:
        result = await session.execute(text("""
            INSERT INTO odin.runs
                (orchestrator_id, orchestrator_name, user_id, session_id, goal, status,
                 iterations, total_tokens_in, total_tokens_out)
            VALUES
                (:orch_id, 'test_orch', 1, gen_random_uuid(), 'test goal', :status,
                 2, 100, 50)
            RETURNING id::text
        """), {"orch_id": orchestrator_id, "status": status})
        await session.commit()
        return result.scalar_one()


@pytest.mark.asyncio
async def test_runs_empty(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/runs", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_runs_stats_empty(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/runs/stats", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs"] == 0


@pytest.mark.asyncio
async def test_runs_lists_after_insert(client: AsyncClient, admin_headers: dict, orchestrator: dict):
    run_id = await _insert_run(orchestrator["id"])
    resp = await client.get("/api/v1/runs", headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == run_id


@pytest.mark.asyncio
async def test_runs_stats_after_insert(client: AsyncClient, admin_headers: dict, orchestrator: dict):
    await _insert_run(orchestrator["id"], status="completed")
    await _insert_run(orchestrator["id"], status="failed")
    resp = await client.get("/api/v1/runs/stats", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs"] == 2
    assert data["by_status"]["completed"] == 1
    assert data["by_status"]["failed"] == 1


@pytest.mark.asyncio
async def test_runs_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/runs")
    assert resp.status_code == 401
