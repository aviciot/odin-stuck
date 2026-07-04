"""
Admin — Orchestrators
CRUD for odin.orchestrators. Publishes odin:orchestrators:changed on any write.
"""

import json
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis
from app.models import Orchestrator
from app.utils.logger import logger

router = APIRouter(prefix="/admin/orchestrators", tags=["admin-orchestrators"])

_CHANGE_CHANNEL = "odin:orchestrators:changed"
_CACHE_PREFIX = "odin:orchestrators:"
_TTL = 600


# ------------------------------------------------------------------ #
# Pydantic schemas                                                     #
# ------------------------------------------------------------------ #

class OrchestratorCreate(BaseModel):
    name: str = Field(..., description="Unique slug used in /ws/orchestrate/{name}")
    display_name: str
    system_prompt: str = ""
    allowed_agent_ids: List[uuid.UUID] = Field(default_factory=list, description="Empty = all enabled agents")
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    max_iterations: int = 10
    max_parallel_tools: int = 4
    rate_limit_rpm: int = 30
    daily_budget_usd: Decimal = Decimal("0")
    enabled: bool = True


class OrchestratorUpdate(BaseModel):
    display_name: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_agent_ids: Optional[List[uuid.UUID]] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    max_iterations: Optional[int] = None
    max_parallel_tools: Optional[int] = None
    rate_limit_rpm: Optional[int] = None
    daily_budget_usd: Optional[Decimal] = None
    enabled: Optional[bool] = None


class OrchestratorOut(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    system_prompt: str
    allowed_agent_ids: List[uuid.UUID]
    llm_provider: Optional[str]
    llm_model: Optional[str]
    max_iterations: int
    max_parallel_tools: int
    rate_limit_rpm: int
    daily_budget_usd: Decimal
    enabled: bool

    class Config:
        from_attributes = True


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _row_to_out(row: Orchestrator) -> OrchestratorOut:
    return OrchestratorOut(
        id=row.id,
        name=row.name,
        display_name=row.display_name,
        system_prompt=row.system_prompt or "",
        allowed_agent_ids=list(row.allowed_agent_ids or []),
        llm_provider=row.llm_provider,
        llm_model=row.llm_model,
        max_iterations=row.max_iterations,
        max_parallel_tools=row.max_parallel_tools,
        rate_limit_rpm=row.rate_limit_rpm,
        daily_budget_usd=row.daily_budget_usd,
        enabled=row.enabled,
    )


async def _get_or_404(db: AsyncSession, orch_id: uuid.UUID) -> Orchestrator:
    row = await db.get(Orchestrator, orch_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orchestrator not found")
    return row


async def _invalidate(name: str) -> None:
    try:
        redis = await get_redis()
        await redis.delete(f"{_CACHE_PREFIX}{name}")
        await redis.publish(_CHANGE_CHANNEL, name)
    except Exception as exc:
        logger.warning("orchestrator: failed to invalidate cache", error=str(exc))


# ------------------------------------------------------------------ #
# Routes                                                               #
# ------------------------------------------------------------------ #

@router.get("", response_model=List[OrchestratorOut])
async def list_orchestrators(
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    q = select(Orchestrator).order_by(Orchestrator.name)
    if enabled_only:
        q = q.where(Orchestrator.enabled == True)
    result = await db.execute(q)
    return [_row_to_out(r) for r in result.scalars()]


@router.post("", response_model=OrchestratorOut, status_code=status.HTTP_201_CREATED)
async def create_orchestrator(body: OrchestratorCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Orchestrator).where(Orchestrator.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Orchestrator '{body.name}' already exists")

    row = Orchestrator(
        name=body.name,
        display_name=body.display_name,
        system_prompt=body.system_prompt,
        allowed_agent_ids=[str(i) for i in body.allowed_agent_ids],
        llm_provider=body.llm_provider,
        llm_model=body.llm_model,
        max_iterations=body.max_iterations,
        max_parallel_tools=body.max_parallel_tools,
        rate_limit_rpm=body.rate_limit_rpm,
        daily_budget_usd=body.daily_budget_usd,
        enabled=body.enabled,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await _invalidate(body.name)
    logger.info("orchestrator created", name=body.name)
    return _row_to_out(row)


@router.get("/{orch_id}", response_model=OrchestratorOut)
async def get_orchestrator(orch_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return _row_to_out(await _get_or_404(db, orch_id))


@router.patch("/{orch_id}", response_model=OrchestratorOut)
async def update_orchestrator(
    orch_id: uuid.UUID,
    body: OrchestratorUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_404(db, orch_id)

    if body.display_name is not None:
        row.display_name = body.display_name
    if body.system_prompt is not None:
        row.system_prompt = body.system_prompt
    if body.allowed_agent_ids is not None:
        row.allowed_agent_ids = [str(i) for i in body.allowed_agent_ids]
    if body.llm_provider is not None:
        row.llm_provider = body.llm_provider
    if body.llm_model is not None:
        row.llm_model = body.llm_model
    if body.max_iterations is not None:
        row.max_iterations = body.max_iterations
    if body.max_parallel_tools is not None:
        row.max_parallel_tools = body.max_parallel_tools
    if body.rate_limit_rpm is not None:
        row.rate_limit_rpm = body.rate_limit_rpm
    if body.daily_budget_usd is not None:
        row.daily_budget_usd = body.daily_budget_usd
    if body.enabled is not None:
        row.enabled = body.enabled

    name = row.name
    await db.commit()
    await db.refresh(row)
    await _invalidate(name)
    logger.info("orchestrator updated", orch_id=str(orch_id), name=name)
    return _row_to_out(row)


@router.delete("/{orch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_orchestrator(orch_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, orch_id)
    name = row.name
    await db.delete(row)
    await db.commit()
    await _invalidate(name)
    logger.info("orchestrator deleted", orch_id=str(orch_id), name=name)
