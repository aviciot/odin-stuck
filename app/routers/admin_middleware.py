import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.database as db_module
from app.database import get_db
from app.models import MiddlewareDef
from app.utils.logger import logger

router = APIRouter(prefix="/admin/middleware-defs", tags=["admin-middleware"])

_CHAIN_CACHE_PREFIX = "them:mw:chain:"
_VALID_KINDS = {"guard", "cache"}


class MiddlewareDefCreate(BaseModel):
    slug: str = Field(..., description="Unique slug")
    kind: str = Field(..., description="guard | cache")
    display_name: str
    description: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class MiddlewareDefUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class MiddlewareDefOut(BaseModel):
    id: uuid.UUID
    slug: str
    kind: str
    display_name: str
    description: str
    config: Dict[str, Any]
    is_builtin: bool
    enabled: bool

    class Config:
        from_attributes = True


async def _get_or_404(db: AsyncSession, def_id: uuid.UUID) -> MiddlewareDef:
    row = await db.get(MiddlewareDef, def_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Middleware def not found")
    return row


async def _flush_chain_cache() -> None:
    redis = db_module.redis_client
    if redis is None:
        return
    try:
        cursor = 0
        pattern = f"{_CHAIN_CACHE_PREFIX}*"
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break
    except Exception as exc:
        logger.warning("middleware: chain cache flush failed", error=str(exc))


@router.get("", response_model=List[MiddlewareDefOut])
async def list_defs(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(MiddlewareDef).order_by(MiddlewareDef.slug.asc()))).scalars().all()
    return rows


@router.get("/{def_id}", response_model=MiddlewareDefOut)
async def get_def(def_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _get_or_404(db, def_id)


@router.post("", response_model=MiddlewareDefOut, status_code=status.HTTP_201_CREATED)
async def create_def(body: MiddlewareDefCreate, db: AsyncSession = Depends(get_db)):
    if body.kind not in _VALID_KINDS:
        raise HTTPException(status_code=400, detail=f"Invalid kind: {body.kind}")
    existing = (
        await db.execute(select(MiddlewareDef).where(MiddlewareDef.slug == body.slug))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="slug already exists")
    row = MiddlewareDef(
        slug=body.slug, kind=body.kind, display_name=body.display_name,
        description=body.description, config=body.config, enabled=body.enabled, is_builtin=False,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await _flush_chain_cache()
    logger.info("middleware def created", slug=body.slug, kind=body.kind)
    return row


@router.patch("/{def_id}", response_model=MiddlewareDefOut)
async def update_def(def_id: uuid.UUID, body: MiddlewareDefUpdate, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, def_id)
    if body.display_name is not None:
        row.display_name = body.display_name
    if body.description is not None:
        row.description = body.description
    if body.config is not None:
        row.config = body.config
    if body.enabled is not None:
        row.enabled = body.enabled
    await db.commit()
    await db.refresh(row)
    await _flush_chain_cache()
    logger.info("middleware def updated", def_id=str(def_id))
    return row


@router.delete("/{def_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_def(def_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, def_id)
    if row.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete a built-in middleware def")
    await db.delete(row)
    await db.commit()
    await _flush_chain_cache()
    logger.info("middleware def deleted", def_id=str(def_id))
