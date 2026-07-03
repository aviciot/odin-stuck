import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "instance_id" in data


@pytest.mark.asyncio
async def test_health_ready(client: AsyncClient):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_full(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "db" in data
    assert "redis" in data
