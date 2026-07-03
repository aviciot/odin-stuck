"""
Admin agents CRUD integration tests.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.asyncio
async def test_list_agents_empty(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/admin/agents", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_agent(client: AsyncClient, admin_headers: dict):
    resp = await client.post("/api/v1/admin/agents", headers=admin_headers, json={
        "slug": "my_agent",
        "display_name": "My Agent",
        "description": "Does things",
        "transport": "omni_ws",
        "endpoint_url": "ws://mock-agent-assistant:9000",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "my_agent"
    assert data["enabled"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_agent_duplicate_slug(client: AsyncClient, admin_headers: dict, agent: dict):
    resp = await client.post("/api/v1/admin/agents", headers=admin_headers, json={
        "slug": "test_agent",  # same as fixture
        "display_name": "Duplicate",
        "description": "Should fail",
        "transport": "omni_ws",
        "endpoint_url": "ws://mock-agent-assistant:9000",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_agent_invalid_slug(client: AsyncClient, admin_headers: dict):
    resp = await client.post("/api/v1/admin/agents", headers=admin_headers, json={
        "slug": "bad-slug-with-hyphens",
        "display_name": "Bad Agent",
        "description": "Should fail",
        "transport": "omni_ws",
        "endpoint_url": "ws://mock-agent-assistant:9000",
    })
    assert resp.status_code == 422
    assert "slug" in resp.text.lower()


@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient, admin_headers: dict, agent: dict):
    resp = await client.get(f"/api/v1/admin/agents/{agent['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["slug"] == "test_agent"


@pytest.mark.asyncio
async def test_update_agent(client: AsyncClient, admin_headers: dict, agent: dict):
    resp = await client.patch(f"/api/v1/admin/agents/{agent['id']}", headers=admin_headers, json={
        "display_name": "Updated Name",
        "enabled": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Updated Name"
    assert data["enabled"] is False


@pytest.mark.asyncio
async def test_delete_agent(client: AsyncClient, admin_headers: dict, agent: dict):
    resp = await client.delete(f"/api/v1/admin/agents/{agent['id']}", headers=admin_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/admin/agents/{agent['id']}", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_agents_after_create(client: AsyncClient, admin_headers: dict, agent: dict):
    resp = await client.get("/api/v1/admin/agents", headers=admin_headers)
    assert resp.status_code == 200
    slugs = [a["slug"] for a in resp.json()]
    assert "test_agent" in slugs
