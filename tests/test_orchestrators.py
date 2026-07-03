"""
Admin orchestrators CRUD integration tests.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.asyncio
async def test_list_orchestrators_empty(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/admin/orchestrators", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_orchestrator(client: AsyncClient, admin_headers: dict, agent: dict):
    resp = await client.post("/api/v1/admin/orchestrators", headers=admin_headers, json={
        "name": "my_orch",
        "display_name": "My Orchestrator",
        "system_prompt": "You are helpful.",
        "allowed_agent_ids": [agent["id"]],
        "llm_provider": "anthropic",
        "llm_model": "claude-sonnet-4-6",
        "max_iterations": 5,
        "enabled": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "my_orch"
    assert agent["id"] in data["allowed_agent_ids"]


@pytest.mark.asyncio
async def test_create_orchestrator_duplicate(client: AsyncClient, admin_headers: dict, orchestrator: dict):
    resp = await client.post("/api/v1/admin/orchestrators", headers=admin_headers, json={
        "name": "test_orch",
        "display_name": "Duplicate",
        "system_prompt": "",
        "enabled": True,
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_orchestrator(client: AsyncClient, admin_headers: dict, orchestrator: dict):
    resp = await client.get(f"/api/v1/admin/orchestrators/{orchestrator['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "test_orch"


@pytest.mark.asyncio
async def test_update_orchestrator(client: AsyncClient, admin_headers: dict, orchestrator: dict):
    resp = await client.patch(f"/api/v1/admin/orchestrators/{orchestrator['id']}", headers=admin_headers, json={
        "display_name": "Renamed",
        "max_iterations": 7,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Renamed"
    assert data["max_iterations"] == 7


@pytest.mark.asyncio
async def test_delete_orchestrator(client: AsyncClient, admin_headers: dict, orchestrator: dict):
    resp = await client.delete(f"/api/v1/admin/orchestrators/{orchestrator['id']}", headers=admin_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/admin/orchestrators/{orchestrator['id']}", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_orchestrator_stores_api_key_hint(client: AsyncClient, admin_headers: dict):
    resp = await client.post("/api/v1/admin/orchestrators", headers=admin_headers, json={
        "name": "keyed_orch",
        "display_name": "Keyed",
        "system_prompt": "",
        "llm_api_key": "sk-ant-test1234567890abcdef",
        "enabled": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    # Key must be masked, not returned in plain text
    assert data.get("llm_api_key_hint") is not None
    assert "test1234567890abcdef" not in str(data.get("llm_api_key_hint", ""))
